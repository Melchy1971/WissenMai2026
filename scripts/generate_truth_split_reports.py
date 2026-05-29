from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
DEFAULT_TEST_TARGET = REPO_ROOT / "backend" / "tests"

REPORT_MARKERS = (
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
    "m5_truth",
    "governance_truth",
    "observability_truth",
    "unit_fast",
)

REPORT_PATHS = {
    "m3a_truth": CURRENT_DIR / "m3a_frontend_truth.json",
    "m4a_auth_truth": CURRENT_DIR / "m4a_auth_truth.json",
    "m4b_upload_queue_truth": CURRENT_DIR / "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth": CURRENT_DIR / "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth": CURRENT_DIR / "m4e_backup_restore_truth.json",
}

M4_SPLIT_REPORT_MARKERS = (
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
)
M4_SPLIT_MARKEXPR = " or ".join(M4_SPLIT_REPORT_MARKERS)

REPORT_FORMAT_VERSION = 1
REPORT_SCHEMA_VERSION = 1

MARKER_GATES = {
    "m3a_truth": "m3a",
    "m4_truth": "m4",
    "m4a_auth_truth": "m4a",
    "m4b_upload_queue_truth": "m4b",
    "m4c_lifecycle_retrieval_truth": "m4c",
    "m4e_backup_restore_truth": "m4e",
    "m5_truth": "m5",
    "governance_truth": "governance",
    "observability_truth": "observability",
    "unit_fast": "unit_fast",
}


@dataclass
class TestOutcome:
    status: str
    nodeid: str


@dataclass(eq=False)
class TruthSplitPlugin:
    collected_by_marker: dict[str, list[str]] = field(
        default_factory=lambda: {marker: [] for marker in REPORT_MARKERS}
    )
    outcomes: dict[str, TestOutcome] = field(default_factory=dict)
    collect_errors: list[str] = field(default_factory=list)
    unmarked_truth_tests: list[str] = field(default_factory=list)
    ambiguous_truth_tests: list[dict[str, Any]] = field(default_factory=list)

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            marker_names = {marker.name for marker in item.iter_markers()}
            truth_markers = sorted(set(REPORT_MARKERS).intersection(marker_names))
            is_truth_test = bool(truth_markers) or "postgres_truth" in marker_names or "postgres_truth/" in item.nodeid.replace("\\", "/")
            if not is_truth_test:
                continue
            if not truth_markers:
                self.unmarked_truth_tests.append(item.nodeid)
                continue
            if len(truth_markers) > 1:
                self.ambiguous_truth_tests.append({"nodeid": item.nodeid, "markers": truth_markers})
                continue
            self.collected_by_marker[truth_markers[0]].append(item.nodeid)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            if report.failed:
                self.outcomes[report.nodeid] = TestOutcome(status="error", nodeid=report.nodeid)
            elif report.skipped and report.nodeid not in self.outcomes:
                self.outcomes[report.nodeid] = TestOutcome(status="skipped", nodeid=report.nodeid)
            return

        if report.passed:
            self.outcomes[report.nodeid] = TestOutcome(status="passed", nodeid=report.nodeid)
        elif report.failed:
            self.outcomes[report.nodeid] = TestOutcome(status="failed", nodeid=report.nodeid)
        elif report.skipped:
            self.outcomes[report.nodeid] = TestOutcome(status="skipped", nodeid=report.nodeid)

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.collect_errors.append(report.nodeid)


def _commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _status_from_counts(collected: int, failed: int, errors: int, skipped: int) -> str:
    if collected <= 0 or failed or errors or skipped:
        return "FAIL"
    return "PASS"


def _source_command(marker: str) -> str:
    return f"python scripts/generate_truth_split_reports.py -- -m {marker}"


def _normalize_marker_report(marker: str, report: dict[str, Any]) -> dict[str, Any]:
    collected = int(report.get("collected") or 0)
    passed = int(report.get("passed") or 0)
    failed = int(report.get("failed") or 0)
    errors = int(report.get("errors") or 0)
    skipped = int(report.get("skipped") or 0)
    status = _status_from_counts(collected, failed, errors, skipped)
    exit_code = 0 if status == "PASS" else 1
    blockers = list(report.get("blockers") or [])
    if status != "PASS" and not blockers:
        blockers.append({
            "gate": MARKER_GATES.get(marker, marker),
            "severity": "critical",
            "reason": f"{collected} collected, {failed} failed, {errors} errors, {skipped} skipped",
        })

    normalized = dict(report)
    normalized.update({
        "report_format_version": REPORT_FORMAT_VERSION,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "report_name": marker,
        "marker": marker,
        "gate": MARKER_GATES.get(marker, marker),
        "status": status,
        "environment": str(report.get("environment") or "local"),
        "report_type": "truth",
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "exit_code": exit_code,
        "blockers": blockers,
        "source_command": str(report.get("source_command") or _source_command(marker)),
        "generated_by": "gate_validator",
    })
    commit_hash = report.get("commit_hash") or _commit_hash()
    if commit_hash:
        normalized["commit_hash"] = str(commit_hash)
    return normalized


def build_write_failure_report(marker: str, exc: Exception, timestamp: str | None = None) -> dict[str, Any]:
    return _normalize_marker_report(
        marker,
        {
            "marker": marker,
            "timestamp": timestamp or datetime.now(UTC).isoformat(),
            "collected": 1,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "pytest_exit_code": 1,
            "test_database_url_set": bool(os.getenv("TEST_DATABASE_URL")),
            "failed_tests": [],
            "write_error": str(exc),
            "blockers": [{
                "gate": MARKER_GATES.get(marker, marker),
                "severity": "critical",
                "reason": f"report write failed: {exc}",
            }],
        },
    )


def build_split_reports(
    *,
    collected_by_marker: dict[str, list[str]],
    outcomes: dict[str, TestOutcome],
    collect_errors: list[str],
    unmarked_truth_tests: list[str] | None = None,
    ambiguous_truth_tests: list[dict[str, Any]] | None = None,
    exit_code: int,
    test_database_url_set: bool,
    timestamp: str,
) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    unmarked_truth_tests = sorted(unmarked_truth_tests or [])
    ambiguous_truth_tests = sorted(ambiguous_truth_tests or [], key=lambda item: item["nodeid"])
    taxonomy_error_count = len(unmarked_truth_tests) + len(ambiguous_truth_tests)

    for marker in REPORT_MARKERS:
        test_ids = sorted(collected_by_marker.get(marker, []))
        statuses = [outcomes[test_id].status for test_id in test_ids if test_id in outcomes]
        missing = sorted(test_id for test_id in test_ids if test_id not in outcomes)
        errors = sum(1 for status in statuses if status == "error")
        if collect_errors:
            errors += len(collect_errors)
        if taxonomy_error_count:
            errors += taxonomy_error_count
        if missing and exit_code != 0:
            errors += len(missing)

        failed_tests = sorted(
            test_id
            for test_id in test_ids
            if outcomes.get(test_id) is not None and outcomes[test_id].status == "failed"
        )
        skipped = sum(1 for status in statuses if status == "skipped")
        report = {
            "report_format_version": REPORT_FORMAT_VERSION,
            "marker": marker,
            "timestamp": timestamp,
            "collected": len(test_ids),
            "passed": sum(1 for status in statuses if status == "passed"),
            "failed": len(failed_tests),
            "errors": errors,
            "skipped": skipped,
            "exit_code": 0,
            "pytest_exit_code": exit_code,
            "test_database_url_set": test_database_url_set,
            "failed_tests": failed_tests,
            "unmarked_truth_tests": unmarked_truth_tests,
            "ambiguous_truth_tests": ambiguous_truth_tests,
        }
        reports[marker] = _normalize_marker_report(marker, report)

    return reports


def write_split_reports(reports: dict[str, dict[str, Any]], report_dir: Path = CURRENT_DIR) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for marker, default_path in REPORT_PATHS.items():
        path = report_dir / default_path.name
        if marker in reports:
            report = _normalize_marker_report(marker, reports[marker])
        else:
            report = build_write_failure_report(
                marker,
                KeyError(f"missing built report for marker: {marker}"),
                timestamp=datetime.now(UTC).isoformat(),
            )
        try:
            path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            failure_report = build_write_failure_report(marker, exc, timestamp=str(report.get("timestamp") or ""))
            path.write_text(json.dumps(failure_report, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def write_marker_report(
    marker: str,
    reports: dict[str, dict[str, Any]],
    report_dir: Path = CURRENT_DIR,
) -> Path:
    if marker not in REPORT_PATHS:
        raise KeyError(f"unsupported report marker: {marker}")
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / REPORT_PATHS[marker].name
    if marker in reports:
        report = _normalize_marker_report(marker, reports[marker])
    else:
        report = build_write_failure_report(
            marker,
            KeyError(f"missing built report for marker: {marker}"),
            timestamp=datetime.now(UTC).isoformat(),
        )
    try:
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        failure_report = build_write_failure_report(marker, exc, timestamp=str(report.get("timestamp") or ""))
        path.write_text(json.dumps(failure_report, indent=2) + "\n", encoding="utf-8")
    return path


def _selected_report_markers(pytest_args: list[str]) -> set[str] | None:
    marker_expression: str | None = None
    for index, arg in enumerate(pytest_args):
        if arg == "-m" and index + 1 < len(pytest_args):
            marker_expression = pytest_args[index + 1]
            break
        if arg.startswith("-m="):
            marker_expression = arg.split("=", 1)[1]
            break
        if arg.startswith("--markexpr="):
            marker_expression = arg.split("=", 1)[1]
            break

    if not marker_expression:
        return None

    selected = {marker for marker in REPORT_PATHS if marker in marker_expression}
    return selected or None


def _expand_m4_split_marker_args(pytest_args: list[str]) -> list[str]:
    selected = _selected_report_markers(pytest_args)
    if not selected or not selected.intersection(M4_SPLIT_REPORT_MARKERS):
        return pytest_args

    for index, arg in enumerate(pytest_args):
        if arg == "-m" and index + 1 < len(pytest_args):
            marker_expression = pytest_args[index + 1]
            expanded = list(pytest_args)
            expanded[index + 1] = f"({marker_expression}) or ({M4_SPLIT_MARKEXPR})"
            return expanded
        if arg.startswith("-m="):
            marker_expression = arg.split("=", 1)[1]
            expanded = list(pytest_args)
            expanded[index] = f"-m=({marker_expression}) or ({M4_SPLIT_MARKEXPR})"
            return expanded
        if arg.startswith("--markexpr="):
            marker_expression = arg.split("=", 1)[1]
            expanded = list(pytest_args)
            expanded[index] = f"--markexpr=({marker_expression}) or ({M4_SPLIT_MARKEXPR})"
            return expanded

    return pytest_args


def _has_explicit_test_target(pytest_args: list[str]) -> bool:
    skip_next = False
    for arg in pytest_args:
        if skip_next:
            skip_next = False
            continue
        if arg in {"-m", "-k", "-o"}:
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        candidate = Path(arg)
        if "::" in arg or arg.endswith(".py") or candidate.exists() or (REPO_ROOT / candidate).exists():
            return True
    return False


def _with_default_test_target(pytest_args: list[str]) -> list[str]:
    if _has_explicit_test_target(pytest_args):
        return pytest_args
    return [str(DEFAULT_TEST_TARGET), *pytest_args]


@contextlib.contextmanager
def _taxonomy_only_collection_disabled() -> Any:
    old_value = os.environ.get("WISSEN_MARKER_TAXONOMY_ONLY")
    os.environ.pop("WISSEN_MARKER_TAXONOMY_ONLY", None)
    try:
        yield
    finally:
        if old_value is None:
            os.environ.pop("WISSEN_MARKER_TAXONOMY_ONLY", None)
        else:
            os.environ["WISSEN_MARKER_TAXONOMY_ONLY"] = old_value


def generate_split_reports(pytest_args: list[str]) -> tuple[int, dict[str, dict[str, Any]], float]:
    plugin = TruthSplitPlugin()
    start = time.perf_counter()
    with _taxonomy_only_collection_disabled():
        exit_code = int(pytest.main(pytest_args, plugins=[plugin]))
    duration = round(time.perf_counter() - start, 3)
    timestamp = datetime.now(UTC).isoformat()
    taxonomy_errors = bool(plugin.unmarked_truth_tests or plugin.ambiguous_truth_tests)
    report_exit_code = 1 if taxonomy_errors and exit_code == 0 else exit_code
    reports = build_split_reports(
        collected_by_marker=plugin.collected_by_marker,
        outcomes=plugin.outcomes,
        collect_errors=plugin.collect_errors,
        unmarked_truth_tests=plugin.unmarked_truth_tests,
        ambiguous_truth_tests=plugin.ambiguous_truth_tests,
        exit_code=report_exit_code,
        test_database_url_set=bool(os.getenv("TEST_DATABASE_URL")),
        timestamp=timestamp,
    )
    return report_exit_code, reports, duration


def _default_pytest_args() -> list[str]:
    return [str(DEFAULT_TEST_TARGET), "-q"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate per-gate truth reports from pytest markers.")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=CURRENT_DIR,
        help="Directory for split JSON reports.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Optional pytest arguments after --, defaults to backend/tests -q.",
    )
    args = parser.parse_args(argv)

    pytest_args = args.pytest_args
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]
    if not pytest_args:
        pytest_args = _default_pytest_args()
    else:
        pytest_args = _with_default_test_target(pytest_args)
    pytest_args = _expand_m4_split_marker_args(pytest_args)

    exit_code, reports, duration = generate_split_reports(pytest_args)
    selected_markers = _selected_report_markers(pytest_args)
    if selected_markers:
        written = [write_marker_report(marker, reports, args.report_dir) for marker in sorted(selected_markers)]
    else:
        written = write_split_reports(reports, args.report_dir)

    print(f"Truth split reports written: {len(written)}")
    print(f"Duration: {duration}s")
    for path in written:
        print(f"- {path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
