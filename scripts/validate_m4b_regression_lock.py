from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
DEFAULT_REPORT_PATH = CURRENT_DIR / "m4b_upload_queue_truth.json"
DEFAULT_OUTPUT_PATH = CURRENT_DIR / "m4b_regression_lock.json"
REPORT_NAME = "m4b_regression_lock"
MARKER = "m4b_upload_queue_truth"

QUEUE_RECOVERY_FIXES = [
    {
        "id": "retryable_backoff_guard",
        "evidence": "backend/tests/postgres_truth/test_m4b_upload_queue_truth.py::test_m4b_retryable_job_is_not_claimed_before_backoff_expires",
        "guarantee": "retryable import jobs stay unclaimed until the retry backoff has expired",
    },
    {
        "id": "retryable_reclaim_after_backoff",
        "evidence": "backend/tests/postgres_truth/test_m4b_upload_queue_truth.py::test_m4b_retryable_job_is_claimed_after_backoff_expires",
        "guarantee": "expired retryable jobs can be reclaimed and increment attempt_count deterministically",
    },
    {
        "id": "stale_import_recovery_no_duplicates",
        "evidence": "backend/tests/postgres_truth/test_m4_truth_flows.py::test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows",
        "guarantee": "stale import recovery does not create duplicate document/version/chunk rows",
    },
    {
        "id": "crash_recovery_no_duplicate_rows",
        "evidence": "backend/tests/postgres_truth/test_m4_crash_recovery_truth.py::test_import_worker_crash_recovery_preserves_retryability_and_no_duplicate_rows",
        "guarantee": "worker crash recovery preserves retryability and duplicate-row invariants",
    },
]

BLOCKER_TESTS = [
    "backend/tests/integration/test_documents_import.py::test_parallel_duplicate_imports_create_single_document",
]


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _previous_baseline(output_path: Path) -> int | None:
    if not output_path.exists():
        return None
    try:
        data = _load_json(output_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    baseline = data.get("lock", {}).get("baseline_collected")
    if isinstance(baseline, bool) or not isinstance(baseline, int):
        return None
    return baseline


def _has_scope_approval(report: dict[str, Any]) -> bool:
    return bool(report.get("scope_change_reason") and report.get("approval"))


def evaluate_m4b_regression_lock(
    report_path: Path = DEFAULT_REPORT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    blockers: list[dict[str, str]] = []

    try:
        report = _load_json(report_path)
    except FileNotFoundError:
        report = {}
        blockers.append({"severity": "critical", "reason": f"missing report: {report_path}"})
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {}
        blockers.append({"severity": "critical", "reason": f"invalid report JSON: {exc}"})

    collected = report.get("collected")
    passed = report.get("passed")
    failed = report.get("failed")
    errors = report.get("errors")
    skipped = report.get("skipped")
    status = report.get("status")
    marker = report.get("marker")
    exit_code = report.get("exit_code")
    failed_tests = report.get("failed_tests")

    checks = [
        {"id": "report_exists", "passed": bool(report), "detail": str(report_path)},
        {"id": "marker", "passed": marker == MARKER, "detail": marker},
        {"id": "status_pass", "passed": status == "PASS", "detail": status},
        {"id": "collected_positive", "passed": isinstance(collected, int) and not isinstance(collected, bool) and collected > 0, "detail": collected},
        {"id": "passed_equals_collected", "passed": passed == collected, "detail": {"passed": passed, "collected": collected}},
        {"id": "failed_zero", "passed": failed == 0, "detail": failed},
        {"id": "errors_zero", "passed": errors == 0, "detail": errors},
        {"id": "skipped_zero", "passed": skipped == 0, "detail": skipped},
        {"id": "exit_code_zero", "passed": exit_code == 0, "detail": exit_code},
        {"id": "failed_tests_empty", "passed": failed_tests == [], "detail": failed_tests},
    ]

    for check in checks:
        if not check["passed"]:
            blockers.append({"severity": "critical", "reason": f"{check['id']} failed: {check['detail']}"})

    previous_baseline = _previous_baseline(output_path)
    current_collected = collected if isinstance(collected, int) and not isinstance(collected, bool) else 0
    baseline_collected = previous_baseline if previous_baseline is not None else current_collected
    scope_approved = _has_scope_approval(report)

    if current_collected < baseline_collected and not scope_approved:
        blockers.append({
            "severity": "critical",
            "reason": (
                f"collected dropped from {baseline_collected} to {current_collected} without "
                "scope_change_reason and approval"
            ),
        })
    if current_collected > baseline_collected:
        baseline_collected = current_collected

    result = "FAIL" if blockers else "PASS"
    return {
        "report_schema_version": 1,
        "report_name": REPORT_NAME,
        "generated_by": "m4b_regression_lock",
        "timestamp": timestamp,
        "status": result,
        "result": result,
        "inputs": {
            "m4b_report": str(report_path.relative_to(REPO_ROOT)),
        },
        "lock": {
            "marker": MARKER,
            "baseline_collected": baseline_collected,
            "current_collected": current_collected,
            "collected_may_drop_only_with": ["scope_change_reason", "approval"],
            "required_zero_fields": ["failed", "errors", "skipped"],
            "scope_change_approved": scope_approved,
        },
        "checks": checks,
        "queue_recovery_fixes": QUEUE_RECOVERY_FIXES,
        "blocker_tests": BLOCKER_TESTS,
        "blockers": blockers,
    }


def write_report(payload: dict[str, Any], output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and lock the green M4b upload queue truth report.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    payload = evaluate_m4b_regression_lock(args.report, args.output)
    write_report(payload, args.output)
    print(f"M4b Regression Lock = {payload['status']}")
    print(f"Wrote: {args.output}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
