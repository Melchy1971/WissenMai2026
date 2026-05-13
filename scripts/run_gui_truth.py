#!/usr/bin/env python3
"""
GUI Truth Runner — seeds DB, runs Playwright tests, cleans up, writes report.

Usage:
    python scripts/run_gui_truth.py [--headed] [--no-cleanup] [--filter SPEC]

Env:
    TEST_DATABASE_URL   PostgreSQL DSN (required)
    TRUTH_LOGIN         Login for seeded test user (default: gui_truth_user)
    TRUTH_PASSWORD      Password for seeded test user (default: gui_truth_pw_42)
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports" / "gui_truth"

NAMESPACE = "gui_truth_static"
TRUTH_LOGIN = os.environ.get("TRUTH_LOGIN", "gui_truth_user")
TRUTH_PASSWORD = os.environ.get("TRUTH_PASSWORD", "gui_truth_pw_42")
TRUTH_SALT = "gui_truth_static_salt"


def _digest(*parts: str) -> str:
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()


def _uuid_with_prefix(prefix: str, namespace: str, label: str) -> str:
    tail = _digest(namespace, label)
    return f"{prefix}-{tail[:4]}-{tail[4:8]}-{tail[8:12]}-{tail[12:24]}"


WORKSPACE_ID = _uuid_with_prefix("f1000000", NAMESPACE, "workspace")
USER_ID = _uuid_with_prefix("f2000000", NAMESPACE, "user")
MEMBERSHIP_ID = "truth-gui-truth-membership-1"
SESSION_ID = "truth-gui-truth-session-1"
SESSION_TOKEN = f"gui-truth-session-token-{NAMESPACE}"


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def hash_password(password: str, *, salt: str) -> str:
    """Mirrors backend app/services/auth.py hash_password."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"pbkdf2_sha256$600000${salt}${dk.hex()}"


def hash_token(token: str) -> str:
    """Mirrors backend app/services/auth.py hash_token."""
    return hashlib.sha256(token.encode()).hexdigest()


def seed(conn) -> dict:
    password_hash = hash_password(TRUTH_PASSWORD, salt=TRUTH_SALT)
    token_hash = hash_token(SESSION_TOKEN)
    created = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)
    expires = datetime(2036, 5, 13, 10, 0, tzinfo=UTC)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO workspaces (id, name, is_default, created_at)
            VALUES (%s::uuid, %s, false, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (WORKSPACE_ID, "GUI Truth Workspace", created),
        )
        cur.execute(
            """
            INSERT INTO users (id, display_name, login, password_hash, is_active, is_default, created_at)
            VALUES (%s::uuid, %s, %s, %s, true, false, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (USER_ID, "GUI Truth User", TRUTH_LOGIN, password_hash, created),
        )
        cur.execute(
            """
            INSERT INTO workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at)
            VALUES (%s, %s::uuid, %s::uuid, 'owner', %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (MEMBERSHIP_ID, WORKSPACE_ID, USER_ID, created, created),
        )
        cur.execute(
            """
            INSERT INTO auth_sessions
                (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, null)
            ON CONFLICT (id) DO NOTHING
            """,
            (SESSION_ID, USER_ID, token_hash, expires, created, created),
        )
    conn.commit()

    return {
        "workspace_id": WORKSPACE_ID,
        "user_id": USER_ID,
        "token": SESSION_TOKEN,
        "login": TRUTH_LOGIN,
        "password": TRUTH_PASSWORD,
    }


def cleanup(conn) -> None:
    def _try(cur, sql, params=()):
        try:
            cur.execute(sql, params)
        except Exception as exc:
            print(f"  cleanup warning: {exc}", file=sys.stderr)

    with conn.cursor() as cur:
        _try(cur, "DELETE FROM chat_citations WHERE id::text LIKE 'truth-%'")
        _try(cur, "DELETE FROM chat_messages WHERE id::text LIKE 'truth-%'")
        _try(cur, "DELETE FROM chat_sessions WHERE id::text LIKE 'truth-%'")
        _try(
            cur,
            "DELETE FROM background_jobs WHERE id LIKE 'truth-%' OR workspace_id::text = %s",
            (WORKSPACE_ID,),
        )
        _try(
            cur,
            """
            DELETE FROM document_chunks
            WHERE document_id IN (
                SELECT id FROM documents WHERE workspace_id::text = %s
            )
            """,
            (WORKSPACE_ID,),
        )
        _try(
            cur,
            "UPDATE documents SET current_version_id = NULL WHERE workspace_id::text = %s",
            (WORKSPACE_ID,),
        )
        _try(
            cur,
            """
            DELETE FROM document_versions
            WHERE document_id IN (
                SELECT id FROM documents WHERE workspace_id::text = %s
            )
            """,
            (WORKSPACE_ID,),
        )
        _try(cur, "DELETE FROM documents WHERE workspace_id::text = %s", (WORKSPACE_ID,))
        _try(cur, "DELETE FROM auth_sessions WHERE id = %s", (SESSION_ID,))
        _try(cur, "DELETE FROM workspace_memberships WHERE id = %s", (MEMBERSHIP_ID,))
        _try(cur, "DELETE FROM users WHERE id::text = %s", (USER_ID,))
        _try(cur, "DELETE FROM workspaces WHERE id::text = %s", (WORKSPACE_ID,))
    conn.commit()


def run_playwright(seeds: dict, headed: bool, spec_filter: str | None) -> dict:
    env = {
        **os.environ,
        "TRUTH_WORKSPACE_ID": seeds["workspace_id"],
        "TRUTH_TOKEN": seeds["token"],
        "TRUTH_LOGIN": seeds["login"],
        "TRUTH_PASSWORD": seeds["password"],
        "TRUTH_USER_ID": seeds["user_id"],
    }

    cmd = ["npx", "playwright", "test", "--reporter=json"]
    if headed:
        cmd.append("--headed")
    if spec_filter:
        cmd.append(spec_filter)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT / "frontend",
    )

    stdout = result.stdout.strip()
    json_start = stdout.find("{")
    try:
        pw_report = json.loads(stdout[json_start:] if json_start >= 0 else stdout)
    except json.JSONDecodeError:
        pw_report = {"error": "playwright output not parseable", "raw": stdout[-2000:]}

    return {
        "exit_code": result.returncode,
        "playwright": pw_report,
        "stderr": result.stderr[-2000:],
    }


def _walk_suites(suite: dict, passed: list, failed: list, skipped: list) -> None:
    prefix = suite.get("title", "")
    for spec in suite.get("specs", []):
        name = f"{prefix} > {spec.get('title', '')}" if prefix else spec.get("title", "")
        for test in spec.get("tests", []):
            status = test.get("status", "unknown")
            if status in ("expected", "passed"):
                passed.append(name)
            elif status == "skipped":
                skipped.append(name)
            else:
                err_parts = []
                for r in test.get("results", []):
                    for e in r.get("errors", []):
                        err_parts.append(e.get("message", ""))
                failed.append({"name": name, "error": " ".join(err_parts)[:500]})
    for child in suite.get("suites", []):
        _walk_suites(child, passed, failed, skipped)


def build_truth_report(pw_result: dict, duration: float) -> dict:
    pw = pw_result.get("playwright", {})
    passed: list[str] = []
    failed: list[dict] = []
    skipped: list[str] = []
    errors: list[str] = []

    for suite in pw.get("suites", []):
        _walk_suites(suite, passed, failed, skipped)

    if pw_result["exit_code"] != 0 and not failed and "error" in pw:
        errors.append(str(pw.get("error", "unknown")))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "errors": errors,
        "exit_code": pw_result["exit_code"],
        "duration_seconds": round(duration, 2),
        "failed_tests": failed,
        "passed_tests": passed,
    }


def write_reports(report: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    for name in (f"{ts}.json", "latest.json"):
        (REPORTS_DIR / name).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Report written: reports/gui_truth/{ts}.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true", help="Run browser headed")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip DB cleanup")
    parser.add_argument("--filter", dest="spec_filter", default=None, help="Playwright filter (e.g. test_01)")
    args = parser.parse_args()

    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        print("ERROR: TEST_DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    import psycopg

    start = datetime.now(UTC)
    with psycopg.connect(_psycopg_url(db_url)) as conn:
        print(f"Seeding GUI truth data (workspace={WORKSPACE_ID[:16]}...)...")
        seeds = seed(conn)

        try:
            print("Running Playwright tests...")
            pw_result = run_playwright(seeds, args.headed, args.spec_filter)
        finally:
            if not args.no_cleanup:
                print("Cleaning up GUI truth data...")
                cleanup(conn)

    duration = (datetime.now(UTC) - start).total_seconds()
    report = build_truth_report(pw_result, duration)
    write_reports(report)

    print(
        f"\nResult: {report['passed']} passed, "
        f"{report['failed']} failed, "
        f"{report['skipped']} skipped "
        f"({report['duration_seconds']}s)"
    )
    if report["failed_tests"]:
        print("Failed tests:")
        for f in report["failed_tests"]:
            print(f"  - {f['name']}")
            if f["error"]:
                print(f"    {f['error'][:120]}")

    sys.exit(report["exit_code"])


if __name__ == "__main__":
    main()
