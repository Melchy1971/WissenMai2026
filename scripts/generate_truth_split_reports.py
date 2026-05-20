from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_TEST_TARGET = REPO_ROOT / "backend" / "tests"

REPORT_MARKERS = (
    "frontend_truth",
    "m3a_truth",
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
    "m5_truth",
    "governance_truth",
)

REPORT_PATHS = {
    marker: REPORTS_DIR / f"{marker}_report.json"
    for marker in REPORT_MARKERS
}

REPORT_FORMAT_VERSION = 1


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

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            marker_names = {marker.name for marker in item.iter_markers()}
            for marker in REPORT_MARKERS:
                if marker in marker_names:
                    self.collected_by_marker[marker].append(item.nodeid)

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


def build_split_reports(
    *,
    collected_by_marker: dict[str, list[str]],
    outcomes: dict[str, TestOutcome],
    collect_errors: list[str],
    exit_code: int,
    test_database_url_set: bool,
    timestamp: str,
) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}

    for marker in REPORT_MARKERS:
        test_ids = sorted(collected_by_marker.get(marker, []))
        statuses = [outcomes[test_id].status for test_id in test_ids if test_id in outcomes]
        missing = sorted(test_id for test_id in test_ids if test_id not in outcomes)
        errors = sum(1 for status in statuses if status == "error")
        if collect_errors:
            errors += len(collect_errors)
        if missing and exit_code != 0:
            errors += len(missing)

        failed_tests = sorted(
            test_id
            for test_id in test_ids
            if outcomes.get(test_id) is not None and outcomes[test_id].status == "failed"
        )

        reports[marker] = {
            "report_format_version": REPORT_FORMAT_VERSION,
            "marker": marker,
            "timestamp": timestamp,
            "collected": len(test_ids),
            "passed": sum(1 for status in statuses if status == "passed"),
            "failed": len(failed_tests),
            "errors": errors,
            "skipped": sum(1 for status in statuses if status == "skipped"),
            "exit_code": exit_code,
            "test_database_url_set": test_database_url_set,
            "failed_tests": failed_tests,
        }

    return reports


def write_split_reports(reports: dict[str, dict[str, Any]], report_dir: Path = REPORTS_DIR) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for marker in REPORT_MARKERS:
        path = report_dir / f"{marker}_report.json"
        path.write_text(json.dumps(reports[marker], indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


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
    reports = build_split_reports(
        collected_by_marker=plugin.collected_by_marker,
        outcomes=plugin.outcomes,
        collect_errors=plugin.collect_errors,
        exit_code=exit_code,
        test_database_url_set=bool(os.getenv("TEST_DATABASE_URL")),
        timestamp=timestamp,
    )
    return exit_code, reports, duration


def _default_pytest_args() -> list[str]:
    return [str(DEFAULT_TEST_TARGET), "-q"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate per-gate truth reports from pytest markers.")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORTS_DIR,
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

    exit_code, reports, duration = generate_split_reports(pytest_args)
    written = write_split_reports(reports, args.report_dir)

    print(f"Truth split reports written: {len(written)}")
    print(f"Duration: {duration}s")
    for path in written:
        print(f"- {path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
