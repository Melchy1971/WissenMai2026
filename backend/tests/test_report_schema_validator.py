from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.m3a_truth


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_reports.py"
spec = importlib.util.spec_from_file_location("validate_reports", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
validate_reports = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_reports
spec.loader.exec_module(validate_reports)


def _valid_report(**overrides):
    report = {
        "report_schema_version": 1,
        "report_name": "unit_report",
        "gate": "unit",
        "status": "PASS",
        "timestamp": "2026-05-27T00:00:00Z",
        "environment": "test",
        "collected": 1,
        "passed": 1,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "blockers": [],
        "source_command": "pytest backend/tests/test_report_schema_validator.py",
        "generated_by": "gate_validator",
    }
    report.update(overrides)
    return report


def _codes(report):
    return {issue.code for issue in validate_reports.validate_payload(report)}


def test_missing_schema_version_is_invalid() -> None:
    report = _valid_report()
    report.pop("report_schema_version")

    codes = _codes(report)

    assert "missing_required_field" in codes
    assert "missing_schema_version" in codes


def test_unknown_schema_version_is_invalid() -> None:
    assert "unknown_schema_version" in _codes(_valid_report(report_schema_version=999))


def test_pass_requires_zero_failed_errors_and_skipped() -> None:
    report = _valid_report(collected=2, passed=1, failed=1, status="PASS")

    assert "invalid_pass_status" in _codes(report)


def test_collected_must_be_positive_except_informational() -> None:
    assert "empty_collected" in _codes(_valid_report(collected=0, passed=0))
    assert "empty_collected" not in _codes(
        _valid_report(
            status="INFO",
            report_type="informational",
            collected=0,
            passed=0,
            exit_code=0,
        )
    )


def test_counts_must_be_consistent() -> None:
    report = _valid_report(collected=3, passed=1, failed=0, errors=0, skipped=0)

    assert "inconsistent_counts" in _codes(report)


def test_missing_generated_by_is_invalid() -> None:
    report = _valid_report()
    report.pop("generated_by")

    codes = _codes(report)

    assert "missing_required_field" in codes
    assert "missing_generated_by" in codes


def test_manual_generated_by_is_invalid() -> None:
    assert "invalid_generated_by" in _codes(_valid_report(generated_by="manual"))


def test_final_release_must_come_from_gate_validator() -> None:
    report = _valid_report(report_name="m3a_final_release", generated_by="manual")

    codes = _codes(report)

    assert "invalid_generated_by" in codes
    assert "invalid_final_release_source" in codes


def test_active_report_source_must_be_current(tmp_path: Path) -> None:
    report_path = validate_reports.REPO_ROOT / "frontend_truth_report.json"

    issues = validate_reports._source_policy_issues(report_path, _valid_report())

    assert "non_current_report_source" in {issue.code for issue in issues}


def test_archive_report_source_is_invalid() -> None:
    report_path = validate_reports.REPO_ROOT / "reports" / "archive" / "legacy" / "old_report.json"

    issues = validate_reports._source_policy_issues(report_path, _valid_report())

    assert "archive_report_source" in {issue.code for issue in issues}


def test_stale_report_source_is_invalid() -> None:
    report = _valid_report(timestamp="2026-05-01T00:00:00+00:00")
    report_path = validate_reports.REPO_ROOT / "reports" / "current" / "unit_report.json"

    issues = validate_reports._source_policy_issues(report_path, report, max_report_age_hours=24)

    assert "stale_report_source" in {issue.code for issue in issues}
