from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import run_gui_truth


ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = ROOT / "reports" / "current"
GROUP_DIR = CURRENT_DIR / "frontend_truth_groups"
PLAN_REPORT = CURRENT_DIR / "frontend_full_suite_activation_plan.json"
FINAL_REPORT = CURRENT_DIR / "frontend_full_suite_staged_report.json"

GROUPS = [
    {
        "rank": 1,
        "slug": "auth",
        "name": "Auth",
        "specs": ["test_01_login.spec.js", "test_02_auth_bootstrap.spec.js"],
    },
    {
        "rank": 2,
        "slug": "workspace",
        "name": "Workspace",
        "specs": ["test_03_workspace_loading.spec.js", "test_10_workspace_bootstrap.spec.js"],
    },
    {"rank": 3, "slug": "documents", "name": "Documents", "specs": ["test_04_documents.spec.js"]},
    {"rank": 4, "slug": "upload", "name": "Upload", "specs": ["test_05_upload.spec.js"]},
    {"rank": 5, "slug": "search", "name": "Search", "specs": ["test_06_search.spec.js"]},
    {"rank": 6, "slug": "chat", "name": "Chat", "specs": ["test_07_chat.spec.js"]},
    {"rank": 7, "slug": "lifecycle", "name": "Lifecycle", "specs": ["test_08_lifecycle.spec.js"]},
    {"rank": 8, "slug": "diagnostics", "name": "Diagnostics", "specs": ["test_09_diagnostics.spec.js"]},
    {"rank": 9, "slug": "error_states", "name": "Error States", "specs": ["test_11_state_invariants.spec.js"]},
    {"rank": 10, "slug": "concurrency", "name": "Concurrency", "specs": ["test_12_concurrency.spec.js"]},
]


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _schema_base(
    *,
    report_name: str,
    status: str,
    collected: int,
    passed: int,
    failed: int,
    errors: int,
    skipped: int,
    exit_code: int,
    report_type: str,
    source_command: str,
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "report_schema_version": 1,
        "report_name": report_name,
        "gate": "m3a",
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": "local",
        "report_type": report_type,
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "exit_code": exit_code,
        "blockers": blockers or [],
        "source_command": source_command,
        "generated_by": "gate_validator",
    }
    commit_hash = _commit_hash()
    if commit_hash:
        payload["commit_hash"] = commit_hash
    return payload


def write_activation_plan() -> dict[str, Any]:
    groups = [
        {
            "rank": group["rank"],
            "group": group["name"],
            "slug": group["slug"],
            "specs": group["specs"],
            "activation_rule": "activate only if all previous groups are PASS",
            "report": f"reports/current/frontend_truth_groups/{group['rank']:02d}_{group['slug']}_report.json",
        }
        for group in GROUPS
    ]
    payload = _schema_base(
        report_name="frontend_full_suite_activation_plan",
        status="INFO",
        collected=len(groups),
        passed=len(groups),
        failed=0,
        errors=0,
        skipped=0,
        exit_code=0,
        report_type="informational",
        source_command="python scripts/run_frontend_full_suite_staged.py",
    )
    payload.update({
        "rule": "Nur naechste Gruppe aktivieren, wenn vorherige Gruppe gruen ist.",
        "groups": groups,
        "final_report": "reports/current/frontend_full_suite_staged_report.json",
    })
    PLAN_REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _blocked_group_report(group: dict[str, Any], blocked_by: str) -> dict[str, Any]:
    return _schema_base(
        report_name=f"frontend_truth_group_{group['slug']}",
        status="BLOCKED",
        collected=1,
        passed=0,
        failed=1,
        errors=0,
        skipped=0,
        exit_code=1,
        report_type="truth",
        source_command=f"python scripts/run_frontend_full_suite_staged.py --group {group['slug']}",
        blockers=[{
            "gate": "m3a",
            "severity": "critical",
            "reason": f"Previous group failed: {blocked_by}",
        }],
    ) | {
        "group": group["name"],
        "slug": group["slug"],
        "rank": group["rank"],
        "specs": group["specs"],
        "activation_status": "blocked",
        "blocked_by": blocked_by,
    }


def _write_group_report(group: dict[str, Any], payload: dict[str, Any]) -> Path:
    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    path = GROUP_DIR / f"{group['rank']:02d}_{group['slug']}_report.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _group_passed(report: dict[str, Any]) -> bool:
    return (
        report.get("status") == "PASS"
        and report.get("failed") == 0
        and report.get("errors") == 0
        and report.get("skipped") == 0
        and report.get("exit_code") == 0
    )


def build_final_report(group_reports: list[dict[str, Any]], stopped_at: str | None) -> dict[str, Any]:
    collected = sum(int(report.get("collected") or 0) for report in group_reports)
    passed = sum(int(report.get("passed") or 0) for report in group_reports)
    failed = sum(int(report.get("failed") or 0) for report in group_reports)
    errors = sum(int(report.get("errors") or 0) for report in group_reports)
    skipped = sum(int(report.get("skipped") or 0) for report in group_reports)
    status = "PASS" if stopped_at is None and failed == 0 and errors == 0 and skipped == 0 else "FAIL"
    blockers = []
    if status != "PASS":
        blockers.append({
            "gate": "m3a",
            "severity": "critical",
            "reason": f"Staged full suite stopped at {stopped_at}",
        })
    payload = _schema_base(
        report_name="frontend_full_suite_staged",
        status=status,
        collected=collected,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        exit_code=0 if status == "PASS" else 1,
        report_type="truth",
        source_command="python scripts/run_frontend_full_suite_staged.py",
        blockers=blockers,
    )
    payload.update({
        "activation_rule": "Nur naechste Gruppe aktivieren, wenn vorherige Gruppe gruen ist.",
        "stopped_at": stopped_at,
        "groups": group_reports,
    })
    return payload


def run_staged(*, headed: bool, start_api: bool, start_frontend: bool, no_cleanup: bool) -> int:
    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        print("ERROR: TEST_DATABASE_URL not set", file=sys.stderr)
        return 1

    import psycopg

    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    write_activation_plan()
    api_base_url = os.environ.get("VITE_API_BASE_URL") or os.environ.get("API_BASE_URL") or run_gui_truth.DEFAULT_API_BASE_URL
    if start_api and not (os.environ.get("VITE_API_BASE_URL") or os.environ.get("API_BASE_URL")):
        api_base_url = run_gui_truth._reserve_free_api_base_url(run_gui_truth.DEFAULT_GUI_TRUTH_API_BASE_URL)
        os.environ["API_BASE_URL"] = api_base_url
        os.environ["VITE_API_BASE_URL"] = api_base_url
    frontend_base_url = os.environ.get("GUI_TRUTH_BASE_URL") or "http://127.0.0.1:7474"
    if start_frontend and not os.environ.get("GUI_TRUTH_BASE_URL"):
        frontend_base_url = run_gui_truth._reserve_free_frontend_base_url(frontend_base_url)
        os.environ["GUI_TRUTH_BASE_URL"] = frontend_base_url

    api_process = None
    frontend_process = None
    group_reports: list[dict[str, Any]] = []
    stopped_at: str | None = None
    start = datetime.now(UTC)
    try:
        if start_api:
            api_process = run_gui_truth.start_api_process(api_base_url, os.environ.get("DATABASE_URL") or db_url)
        if start_frontend:
            frontend_process = run_gui_truth.start_frontend_process(frontend_base_url)
            os.environ["GUI_TRUTH_EXTERNAL_FRONTEND"] = "1"

        with psycopg.connect(run_gui_truth._psycopg_url(db_url)) as conn:
            if not no_cleanup:
                print("Pre-cleaning stale GUI truth data...")
                run_gui_truth.cleanup(conn)
            print(f"Seeding GUI truth data (workspace={run_gui_truth.WORKSPACE_ID[:16]}...)...")
            seeds = run_gui_truth.seed(conn)
            api_health = run_gui_truth.check_api_database_health(api_base_url, seeds)

            try:
                for group in GROUPS:
                    if stopped_at:
                        blocked_report = _blocked_group_report(group, stopped_at)
                        _write_group_report(group, blocked_report)
                        group_reports.append(blocked_report)
                        continue

                    print(f"Running group {group['rank']:02d} {group['name']}...")
                    group_start = datetime.now(UTC)
                    pw_result = run_gui_truth.run_playwright(seeds, headed, group["specs"])
                    duration = (datetime.now(UTC) - group_start).total_seconds()
                    report = run_gui_truth.build_truth_report(
                        pw_result,
                        duration,
                        api_health,
                        report_name=f"frontend_truth_group_{group['slug']}",
                        source_command=f"python scripts/run_frontend_full_suite_staged.py --group {group['slug']}",
                    )
                    report.update({
                        "group": group["name"],
                        "slug": group["slug"],
                        "rank": group["rank"],
                        "specs": group["specs"],
                        "activation_status": "active",
                    })
                    _write_group_report(group, report)
                    group_reports.append(report)

                    if not _group_passed(report):
                        stopped_at = group["name"]
                        print(f"Stopping staged activation at {group['name']}: group is not green.")
            finally:
                if not no_cleanup:
                    print("Cleaning up GUI truth data...")
                    run_gui_truth.cleanup(conn)
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

    final_report = build_final_report(group_reports, stopped_at)
    final_report["duration_seconds"] = round((datetime.now(UTC) - start).total_seconds(), 2)
    FINAL_REPORT.write_text(json.dumps(final_report, indent=2), encoding="utf-8")

    print(f"Activation plan written: {PLAN_REPORT.relative_to(ROOT)}")
    print(f"Group reports written: {GROUP_DIR.relative_to(ROOT)}")
    print(f"Final report written: {FINAL_REPORT.relative_to(ROOT)}")
    print(f"Frontend Full-Suite Staged = {final_report['status']}")
    return int(final_report["exit_code"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Frontend Truth groups in gated activation order.")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--start-api", action="store_true")
    parser.add_argument("--start-frontend", action="store_true")
    parser.add_argument("--no-cleanup", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_staged(
        headed=args.headed,
        start_api=args.start_api,
        start_frontend=args.start_frontend,
        no_cleanup=args.no_cleanup,
    )


if __name__ == "__main__":
    raise SystemExit(main())
