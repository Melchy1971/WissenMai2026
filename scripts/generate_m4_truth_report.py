from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
OUTPUT_FILE = CURRENT_DIR / "m4_truth_report.json"
STALE_DAYS = 30

SUB_REPORTS = [
    "m4a_auth_truth.json",
    "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth.json",
]


def _parse_timestamp(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        clean = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_stale(report: dict[str, Any], *, now: datetime, days: int = STALE_DAYS) -> bool:
    timestamp = _parse_timestamp(report.get("timestamp") or report.get("generated_at"))
    if timestamp is None:
        return True
    return timestamp < now - timedelta(days=days)


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        val = result.stdout.strip()
        if val:
            return val
    return None


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _component_blockers(name: str, payload: dict[str, Any], *, now: datetime) -> list[str]:
    blockers: list[str] = []
    collected = _int_value(payload.get("collected"))
    passed = _int_value(payload.get("passed"))
    failed = _int_value(payload.get("failed"))
    errors = _int_value(payload.get("errors"))
    skipped = _int_value(payload.get("skipped"))
    exit_code = _int_value(payload.get("exit_code"))

    if collected <= 0:
        blockers.append(f"{name}: collected must be > 0, got {payload.get('collected')!r}")
    if payload.get("status") != "PASS":
        blockers.append(f"{name}: status must be PASS, got {payload.get('status')!r}")
    if passed != collected:
        blockers.append(f"{name}: passed ({passed}) must equal collected ({collected})")
    if failed != 0:
        blockers.append(f"{name}: failed must be 0, got {failed}")
    if errors != 0:
        blockers.append(f"{name}: errors must be 0, got {errors}")
    if skipped != 0:
        blockers.append(f"{name}: skipped must be 0, got {skipped}")
    if exit_code != 0:
        blockers.append(f"{name}: exit_code must be 0, got {exit_code}")
    if _is_stale(payload, now=now):
        blockers.append(f"{name}: report is stale or missing a valid timestamp")
    if payload.get("failed_tests") not in ([], None):
        blockers.append(f"{name}: failed_tests must be empty")
    return blockers


def build_report(*, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    collected = 0
    passed = 0
    failed = 0
    errors = 0
    skipped = 0
    failed_tests = []
    blockers = []
    components: list[dict[str, Any]] = []
    loaded_reports = {}

    for r_name in SUB_REPORTS:
        path = CURRENT_DIR / r_name
        if not path.exists():
            blockers.append({
                "gate": "m4_crosscutting_gate",
                "severity": "critical",
                "reason": f"{r_name}: missing required split report",
            })
            components.append({
                "name": r_name,
                "path": f"reports/current/{r_name}",
                "available": False,
                "status": "FAIL",
                "blockers": [f"{r_name}: missing required split report"],
            })
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON root is not an object")
            loaded_reports[r_name] = payload
        except Exception as exc:
            print(f"Error loading {r_name}: {exc}", file=sys.stderr)
            blockers.append({
                "gate": "m4_crosscutting_gate",
                "severity": "critical",
                "reason": f"{r_name}: invalid required split report: {exc}",
            })
            components.append({
                "name": r_name,
                "path": f"reports/current/{r_name}",
                "available": False,
                "status": "FAIL",
                "blockers": [f"{r_name}: invalid required split report: {exc}"],
            })

    for r_name, payload in loaded_reports.items():
        component_blockers = _component_blockers(r_name, payload, now=now)
        collected += _int_value(payload.get("collected"))
        passed += _int_value(payload.get("passed"))
        failed += _int_value(payload.get("failed"))
        errors += _int_value(payload.get("errors"))
        skipped += _int_value(payload.get("skipped"))
        failed_tests.extend(payload.get("failed_tests") or [])
        components.append({
            "name": r_name,
            "gate": payload.get("gate"),
            "path": f"reports/current/{r_name}",
            "available": True,
            "timestamp": payload.get("timestamp"),
            "status": "FAIL" if component_blockers else "PASS",
            "collected": payload.get("collected"),
            "passed": payload.get("passed"),
            "failed": payload.get("failed"),
            "errors": payload.get("errors"),
            "skipped": payload.get("skipped"),
            "exit_code": payload.get("exit_code"),
            "failed_tests": payload.get("failed_tests") or [],
            "blockers": component_blockers,
        })
        for reason in component_blockers:
            blockers.append({
                "gate": payload.get("gate") or "m4_crosscutting_gate",
                "severity": "critical",
                "reason": reason,
            })

    status = "PASS" if not blockers else "FAIL"
    exit_code = 0 if status == "PASS" else 1
    timestamp = now.isoformat().replace("+00:00", "Z")
    commit = _commit_hash()

    report = {
        "report_schema_version": 2,
        "schema_name": "truth_gate_aggregate_v2",
        "report_name": "m4_truth_report",
        "gate": "m4_crosscutting_gate",
        "status": status,
        "timestamp": timestamp,
        "environment": "local",
        "report_type": "truth",
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "exit_code": exit_code,
        "blockers": blockers,
        "rules": {
            "pass_requires_all_part_reports_pass": True,
            "fail_when_collected_lte_zero": True,
            "fail_when_missing_part_report": True,
            "fail_when_stale_part_report": True,
            "m5_governance_excluded_from_m4": True,
        },
        "inputs": [f"reports/current/{name}" for name in SUB_REPORTS],
        "components": components,
        "source_command": "python scripts/generate_m4_truth_report.py",
        "generated_by": "gate_validator",
        "failed_tests": sorted(failed_tests),
        "decision": {
            "gate_passed": status == "PASS",
            "go_no_go": "GO" if status == "PASS" else "NO-GO",
        },
    }

    if commit:
        report["commit_hash"] = commit

    return report


def main() -> int:
    report = build_report()
    status = report["status"]
    exit_code = int(report["exit_code"])

    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"M4 Truth Report status: {status}")
    print(
        f"Collected: {report['collected']}, Passed: {report['passed']}, "
        f"Failed: {report['failed']}, Errors: {report['errors']}, Skipped: {report['skipped']}"
    )
    print(f"Wrote {OUTPUT_FILE}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
