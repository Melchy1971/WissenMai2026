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
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports" / "gui_truth"
FRONTEND_JSON_REPORT_PATH = ROOT / "reports" / "frontend_truth_report.json"
FRONTEND_MARKDOWN_REPORT_PATH = ROOT / "reports" / "frontend_truth_report.md"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
LOCAL_DEV_DATABASE_URL = "postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test"

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
LOGOUT_SESSION_ID = "truth-gui-truth-logout-session-1"
LOGOUT_SESSION_TOKEN = f"gui-truth-logout-token-{NAMESPACE}"

# No-membership user: valid session, zero workspace memberships → WORKSPACE_NOT_CONFIGURED
NO_MEMBERSHIP_USER_ID = _uuid_with_prefix("f2000000", NAMESPACE, "no-membership-user")
NO_MEMBERSHIP_SESSION_ID = "truth-gui-truth-no-membership-session"
NO_MEMBERSHIP_TOKEN = f"gui-truth-no-membership-token-{NAMESPACE}"

# Multi-workspace user: memberships to 2 workspaces → workspace switcher visible
WORKSPACE_2_ID = _uuid_with_prefix("f1000000", NAMESPACE, "workspace-2")
MULTI_WS_USER_ID = _uuid_with_prefix("f2000000", NAMESPACE, "multi-workspace-user")
MULTI_WS_SESSION_ID = "truth-gui-truth-multi-ws-session"
MULTI_WS_TOKEN = f"gui-truth-multi-ws-token-{NAMESPACE}"
MULTI_WS_MEMBERSHIP_1_ID = "truth-gui-truth-mw-membership-1"
MULTI_WS_MEMBERSHIP_2_ID = "truth-gui-truth-mw-membership-2"


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
    no_membership_token_hash = hash_token(NO_MEMBERSHIP_TOKEN)
    logout_token_hash = hash_token(LOGOUT_SESSION_TOKEN)
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
        cur.execute(
            """
            INSERT INTO auth_sessions
                (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, null)
            ON CONFLICT (id) DO NOTHING
            """,
            (LOGOUT_SESSION_ID, USER_ID, logout_token_hash, expires, created, created),
        )
        # No-membership user: valid session, no workspace_membership → WORKSPACE_NOT_CONFIGURED
        cur.execute(
            """
            INSERT INTO users (id, display_name, login, password_hash, is_active, is_default, created_at)
            VALUES (%s::uuid, 'GUI Truth No Membership', 'gui-truth-no-membership', %s, true, false, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (NO_MEMBERSHIP_USER_ID, hash_password("nm-pw", salt="nm-salt"), created),
        )
        cur.execute(
            """
            INSERT INTO auth_sessions
                (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, null)
            ON CONFLICT (id) DO NOTHING
            """,
            (NO_MEMBERSHIP_SESSION_ID, NO_MEMBERSHIP_USER_ID, no_membership_token_hash, expires, created, created),
        )
        # Multi-workspace user: memberships to WORKSPACE_ID and WORKSPACE_2_ID
        cur.execute(
            """
            INSERT INTO workspaces (id, name, is_default, created_at)
            VALUES (%s::uuid, %s, false, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (WORKSPACE_2_ID, "GUI Truth Workspace 2", created),
        )
        cur.execute(
            """
            INSERT INTO users (id, display_name, login, password_hash, is_active, is_default, created_at)
            VALUES (%s::uuid, 'GUI Truth Multi WS', 'gui-truth-multi-ws', %s, true, false, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (MULTI_WS_USER_ID, hash_password("mw-pw", salt="mw-salt"), created),
        )
        cur.execute(
            """
            INSERT INTO workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at)
            VALUES (%s, %s::uuid, %s::uuid, 'owner', %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (MULTI_WS_MEMBERSHIP_1_ID, WORKSPACE_ID, MULTI_WS_USER_ID, created, created),
        )
        cur.execute(
            """
            INSERT INTO workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at)
            VALUES (%s, %s::uuid, %s::uuid, 'member', %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (MULTI_WS_MEMBERSHIP_2_ID, WORKSPACE_2_ID, MULTI_WS_USER_ID, created, created),
        )
        cur.execute(
            """
            INSERT INTO auth_sessions
                (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, null)
            ON CONFLICT (id) DO NOTHING
            """,
            (MULTI_WS_SESSION_ID, MULTI_WS_USER_ID, hash_token(MULTI_WS_TOKEN), expires, created, created),
        )
    conn.commit()

    return {
        "workspace_id": WORKSPACE_ID,
        "workspace_2_id": WORKSPACE_2_ID,
        "user_id": USER_ID,
        "token": SESSION_TOKEN,
        "logout_token": LOGOUT_SESSION_TOKEN,
        "login": TRUTH_LOGIN,
        "password": TRUTH_PASSWORD,
        "no_membership_token": NO_MEMBERSHIP_TOKEN,
        "multi_ws_token": MULTI_WS_TOKEN,
        "multi_ws_workspace_id": WORKSPACE_ID,
        "multi_ws_workspace_2_id": WORKSPACE_2_ID,
    }


def cleanup(conn) -> None:
    def _try(cur, sql, params=()):
        try:
            cur.execute(sql, params)
        except Exception as exc:
            print(f"  cleanup warning: {exc}", file=sys.stderr)

    with conn.cursor() as cur:
        _try(cur, "DELETE FROM chat_citations WHERE id::text LIKE %s", ("truth-%",))
        _try(cur, "DELETE FROM chat_messages WHERE id::text LIKE %s", ("truth-%",))
        _try(cur, "DELETE FROM chat_sessions WHERE id::text LIKE %s", ("truth-%",))
        _try(
            cur,
            "DELETE FROM background_jobs WHERE id LIKE %s OR workspace_id::text = %s",
            ("truth-%", WORKSPACE_ID),
        )
        _try(
            cur,
            """
            DELETE FROM document_chunks
            WHERE document_id IN (
                SELECT id FROM documents WHERE workspace_id::text IN (%s, %s)
            )
            """,
            (WORKSPACE_ID, WORKSPACE_2_ID),
        )
        _try(
            cur,
            """
            UPDATE documents
            SET import_status = 'pending', current_version_id = NULL
            WHERE workspace_id::text IN (%s, %s)
            """,
            (WORKSPACE_ID, WORKSPACE_2_ID),
        )
        _try(
            cur,
            """
            DELETE FROM document_versions
            WHERE document_id IN (
                SELECT id FROM documents WHERE workspace_id::text IN (%s, %s)
            )
            """,
            (WORKSPACE_ID, WORKSPACE_2_ID),
        )
        _try(cur, "DELETE FROM documents WHERE workspace_id::text IN (%s, %s)", (WORKSPACE_ID, WORKSPACE_2_ID))
        _try(cur, "DELETE FROM auth_sessions WHERE id = %s", (SESSION_ID,))
        _try(cur, "DELETE FROM auth_sessions WHERE id = %s", (NO_MEMBERSHIP_SESSION_ID,))
        _try(cur, "DELETE FROM auth_sessions WHERE id = %s", (LOGOUT_SESSION_ID,))
        _try(cur, "DELETE FROM auth_sessions WHERE id = %s", (MULTI_WS_SESSION_ID,))
        _try(cur, "DELETE FROM workspace_memberships WHERE id = %s", (MEMBERSHIP_ID,))
        _try(cur, "DELETE FROM workspace_memberships WHERE id = %s", (MULTI_WS_MEMBERSHIP_1_ID,))
        _try(cur, "DELETE FROM workspace_memberships WHERE id = %s", (MULTI_WS_MEMBERSHIP_2_ID,))
        _try(cur, "DELETE FROM users WHERE id::text = %s", (USER_ID,))
        _try(cur, "DELETE FROM users WHERE id::text = %s", (NO_MEMBERSHIP_USER_ID,))
        _try(cur, "DELETE FROM users WHERE id::text = %s", (MULTI_WS_USER_ID,))
        _try(cur, "DELETE FROM workspaces WHERE id::text = %s", (WORKSPACE_ID,))
        _try(cur, "DELETE FROM workspaces WHERE id::text = %s", (WORKSPACE_2_ID,))
    conn.commit()


def run_playwright(seeds: dict, headed: bool, spec_filter: str | None) -> dict:
    api_base_url = os.environ.get("VITE_API_BASE_URL") or os.environ.get("API_BASE_URL") or DEFAULT_API_BASE_URL
    env = {
        **os.environ,
        "VITE_API_BASE_URL": api_base_url,
        "TRUTH_WORKSPACE_ID": seeds["workspace_id"],
        "TRUTH_WORKSPACE_2_ID": seeds["workspace_2_id"],
        "TRUTH_TOKEN": seeds["token"],
        "TRUTH_LOGOUT_TOKEN": seeds["logout_token"],
        "TRUTH_LOGIN": seeds["login"],
        "TRUTH_PASSWORD": seeds["password"],
        "TRUTH_USER_ID": seeds["user_id"],
        "TRUTH_NO_MEMBERSHIP_TOKEN": seeds["no_membership_token"],
        "TRUTH_MULTI_WS_TOKEN": seeds["multi_ws_token"],
        "TRUTH_MULTI_WS_WORKSPACE_ID": seeds["multi_ws_workspace_id"],
        "TRUTH_MULTI_WS_WORKSPACE_2_ID": seeds["multi_ws_workspace_2_id"],
        "GUI_TRUTH_EXTERNAL_FRONTEND": os.environ.get("GUI_TRUTH_EXTERNAL_FRONTEND", ""),
    }

    npx = "npx.cmd" if os.name == "nt" else "npx"
    global_timeout_ms = int(os.environ.get("GUI_TRUTH_GLOBAL_TIMEOUT_MS", "600000"))
    test_timeout_ms = int(os.environ.get("GUI_TRUTH_TEST_TIMEOUT_MS", "30000"))
    cmd = [
        npx,
        "playwright",
        "test",
        "--reporter=json",
        f"--timeout={test_timeout_ms}",
        f"--global-timeout={global_timeout_ms}",
    ]
    if headed:
        cmd.append("--headed")
    if spec_filter:
        cmd.append(spec_filter)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=ROOT / "frontend",
            timeout=(global_timeout_ms / 1000) + 30,
        )
        returncode = result.returncode
        stdout = result.stdout.strip()
        stderr = result.stderr[-2000:]
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        stderr = ((exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "")
        pw_report = {
            "error": "playwright global timeout exceeded",
            "raw": stdout[-2000:],
        }
        return {
            "exit_code": returncode,
            "playwright": pw_report,
            "stderr": stderr,
        }

    json_start = stdout.find("{")
    try:
        pw_report = json.loads(stdout[json_start:] if json_start >= 0 else stdout)
    except json.JSONDecodeError:
        pw_report = {"error": "playwright output not parseable", "raw": stdout[-2000:]}

    return {
        "exit_code": returncode,
        "playwright": pw_report,
        "stderr": stderr,
    }


def check_api_database_health(api_base_url: str, seeds: dict | None = None) -> dict:
    health_url = f"{api_base_url.rstrip('/')}/health/db"
    headers = {"Accept": "application/json"}
    if seeds:
        headers["Authorization"] = f"Bearer {seeds['token']}"
        headers["X-Workspace-Id"] = seeds["workspace_id"]
    request = Request(health_url, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            status = payload.get("status") or ("ok" if response.status == 200 else "error")
            return {
                "url": health_url,
                "ok": response.status == 200 and status in {"ok", "healthy"},
                "status_code": response.status,
                "status": status,
            }
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {
            "url": health_url,
            "ok": False,
            "status_code": None,
            "status": "unreachable",
            "error": str(exc)[:500],
        }


def _check_api_process_health(api_base_url: str) -> bool:
    health_url = f"{api_base_url.rstrip('/')}/health"
    try:
        with urlopen(Request(health_url, headers={"Accept": "application/json"}), timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def start_api_process(api_base_url: str, database_url: str) -> subprocess.Popen | None:
    if _check_api_process_health(api_base_url):
        return None

    backend_python = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
    if not backend_python.exists():
        backend_python = ROOT / "backend" / ".venv" / "bin" / "python"
    if not backend_python.exists():
        raise RuntimeError(f"Backend virtual environment not found: {backend_python}")

    env = {
        **os.environ,
        "DATABASE_URL": database_url,
    }
    out = (ROOT / "reports" / "frontend-api-8000.out.log").open("ab")
    err = (ROOT / "reports" / "frontend-api-8000.err.log").open("ab")
    process = subprocess.Popen(
        [
            str(backend_python),
            "-m",
            "uvicorn",
            "--app-dir",
            str(ROOT / "backend"),
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        env=env,
        stdout=out,
        stderr=err,
    )

    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError(f"API process exited during startup with code {process.returncode}")
        if _check_api_process_health(api_base_url):
            return process
        time.sleep(1)

    process.terminate()
    raise RuntimeError("API process did not become healthy within 30s")


def _check_frontend_health(base_url: str) -> bool:
    try:
        with urlopen(Request(base_url, headers={"Accept": "text/html"}), timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def start_frontend_process(base_url: str) -> subprocess.Popen | None:
    if _check_frontend_health(base_url):
        return None

    npm = "npm.cmd" if os.name == "nt" else "npm"
    out = (ROOT / "reports" / "frontend-vite-7474.out.log").open("ab")
    err = (ROOT / "reports" / "frontend-vite-7474.err.log").open("ab")
    env = {
        **os.environ,
        "VITE_API_BASE_URL": os.environ.get("VITE_API_BASE_URL")
        or os.environ.get("API_BASE_URL")
        or DEFAULT_API_BASE_URL,
    }
    process = subprocess.Popen(
        [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "7474"],
        cwd=ROOT / "frontend",
        env=env,
        stdout=out,
        stderr=err,
    )

    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError(f"Frontend process exited during startup with code {process.returncode}")
        if _check_frontend_health(base_url):
            return process
        time.sleep(1)

    process.terminate()
    raise RuntimeError("Frontend process did not become healthy within 30s")


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


def _browser_name(pw: dict) -> str:
    project_names = [
        project.get("name")
        for project in pw.get("config", {}).get("projects", [])
        if project.get("name")
    ]
    return ",".join(project_names) if project_names else "unknown"


def build_truth_report(pw_result: dict, duration: float, api_health: dict) -> dict:
    pw = pw_result.get("playwright", {})
    passed: list[str] = []
    failed: list[dict] = []
    skipped: list[str] = []
    errors: list[str] = []

    for suite in pw.get("suites", []):
        _walk_suites(suite, passed, failed, skipped)

    if pw_result["exit_code"] != 0 and not failed and "error" in pw:
        errors.append(str(pw.get("error", "unknown")))

    collected = len(passed) + len(failed) + len(skipped)
    api_base_url = os.environ.get("VITE_API_BASE_URL") or os.environ.get("API_BASE_URL") or DEFAULT_API_BASE_URL
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "collected": collected,
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "browser": _browser_name(pw),
        "api_base_url": api_base_url,
        "test_database_url_set": bool(os.environ.get("TEST_DATABASE_URL")),
        "duration": round(duration, 2),
        "duration_seconds": round(duration, 2),
        "failed_flows": failed,
        "errors": errors,
        "exit_code": pw_result["exit_code"],
        "playwright_exit_code": pw_result["exit_code"],
        "real_api": True,
        "mock_only": False,
        "api_database_health": api_health,
        "failed_tests": failed,
        "skipped_tests": skipped,
        "passed_tests": passed,
    }


def write_reports(report: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    for name in (f"{ts}.json", "latest.json"):
        (REPORTS_DIR / name).write_text(json.dumps(report, indent=2), encoding="utf-8")

    FRONTEND_JSON_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    FRONTEND_MARKDOWN_REPORT_PATH.write_text(render_markdown_report(report), encoding="utf-8")

    print(f"Report written: reports/gui_truth/{ts}.json")
    print("Report written: reports/frontend_truth_report.json")
    print("Report written: reports/frontend_truth_report.md")


def render_markdown_report(report: dict) -> str:
    failed_flows = report.get("failed_flows") or []
    lines = [
        "# Frontend Truth Report",
        "",
        "| Feld | Wert |",
        "|---|---|",
        f"| timestamp | `{report.get('timestamp')}` |",
        f"| collected | {report.get('collected')} |",
        f"| passed | {report.get('passed')} |",
        f"| failed | {report.get('failed')} |",
        f"| skipped | {report.get('skipped')} |",
        f"| browser | `{report.get('browser')}` |",
        f"| api_base_url | `{report.get('api_base_url')}` |",
        f"| test_database_url_set | {str(report.get('test_database_url_set')).lower()} |",
        f"| duration | {report.get('duration')}s |",
        f"| playwright_exit_code | {report.get('playwright_exit_code')} |",
        f"| real_api | {str(report.get('real_api')).lower()} |",
        f"| mock_only | {str(report.get('mock_only')).lower()} |",
        f"| api_database_health | {str((report.get('api_database_health') or {}).get('ok')).lower()} |",
        "",
        "## Failed Flows",
        "",
    ]
    if failed_flows:
        for flow in failed_flows:
            lines.append(f"- `{flow.get('name', 'unknown')}`: {flow.get('error', '')}")
    else:
        lines.append("- keine")
    lines.extend(
        [
            "",
            "## Gate-Regeln",
            "",
            "- `TEST_DATABASE_URL` muss gesetzt sein.",
            "- `/health/db` der echten API muss erfolgreich sein.",
            "- `collected > 0`, `passed == collected`, `failed == 0`, `skipped == 0`.",
            "- `playwright_exit_code == 0`.",
            "- `mock_only == false` und `real_api == true`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true", help="Run browser headed")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip DB cleanup")
    parser.add_argument("--filter", dest="spec_filter", default=None, help="Playwright filter (e.g. test_01)")
    parser.add_argument("--start-api", action="store_true", help="Start the real FastAPI backend for this run")
    parser.add_argument("--start-frontend", action="store_true", help="Start the real Vite frontend for this run")
    args = parser.parse_args()

    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        print("ERROR: TEST_DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    import psycopg

    start = datetime.now(UTC)
    api_base_url = os.environ.get("VITE_API_BASE_URL") or os.environ.get("API_BASE_URL") or DEFAULT_API_BASE_URL
    frontend_base_url = os.environ.get("GUI_TRUTH_BASE_URL") or "http://127.0.0.1:7474"
    api_process = None
    frontend_process = None
    try:
        if args.start_api:
            api_process = start_api_process(api_base_url, os.environ.get("DATABASE_URL") or db_url or LOCAL_DEV_DATABASE_URL)
        if args.start_frontend:
            frontend_process = start_frontend_process(frontend_base_url)
            os.environ["GUI_TRUTH_EXTERNAL_FRONTEND"] = "1"
        with psycopg.connect(_psycopg_url(db_url)) as conn:
            print(f"Seeding GUI truth data (workspace={WORKSPACE_ID[:16]}...)...")
            seeds = seed(conn)
            api_health = check_api_database_health(api_base_url, seeds)

            try:
                print("Running Playwright tests...")
                pw_result = run_playwright(seeds, args.headed, args.spec_filter)
            finally:
                if not args.no_cleanup:
                    print("Cleaning up GUI truth data...")
                    cleanup(conn)
    finally:
        if api_process is not None and api_process.poll() is None:
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_process.kill()
        if frontend_process is not None and frontend_process.poll() is None:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                frontend_process.kill()

    duration = (datetime.now(UTC) - start).total_seconds()
    report = build_truth_report(pw_result, duration, api_health)
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
