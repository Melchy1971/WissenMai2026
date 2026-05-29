from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_m4b_regression_lock.py"
spec = importlib.util.spec_from_file_location("validate_m4b_regression_lock", SCRIPT_PATH)
assert spec is not None
m4b_lock = importlib.util.module_from_spec(spec)
sys.modules["validate_m4b_regression_lock"] = m4b_lock
assert spec.loader is not None
spec.loader.exec_module(m4b_lock)


pytestmark = pytest.mark.m3a_truth


def _m4b_report(collected: int = 48) -> dict:
    return {
        "report_schema_version": 1,
        "report_name": "m4b_upload_queue_truth",
        "marker": "m4b_upload_queue_truth",
        "status": "PASS",
        "collected": collected,
        "passed": collected,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "failed_tests": [],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_m4b_regression_lock_passes_current_green_report(tmp_path: Path) -> None:
    report_path = tmp_path / "m4b_upload_queue_truth.json"
    output_path = tmp_path / "m4b_regression_lock.json"
    _write_json(report_path, _m4b_report(collected=48))

    payload = m4b_lock.evaluate_m4b_regression_lock(
        report_path,
        output_path,
        timestamp="2026-05-29T08:00:00+00:00",
    )

    assert payload["status"] == "PASS"
    assert payload["lock"]["baseline_collected"] == 48
    assert payload["lock"]["required_zero_fields"] == ["failed", "errors", "skipped"]
    assert payload["queue_recovery_fixes"]
    assert "backend/tests/integration/test_documents_import.py::test_parallel_duplicate_imports_create_single_document" in payload["blocker_tests"]


def test_m4b_regression_lock_blocks_unapproved_collected_drop(tmp_path: Path) -> None:
    report_path = tmp_path / "m4b_upload_queue_truth.json"
    output_path = tmp_path / "m4b_regression_lock.json"
    _write_json(output_path, {"lock": {"baseline_collected": 48}})
    _write_json(report_path, _m4b_report(collected=47))

    payload = m4b_lock.evaluate_m4b_regression_lock(
        report_path,
        output_path,
        timestamp="2026-05-29T08:00:00+00:00",
    )

    assert payload["status"] == "FAIL"
    assert payload["lock"]["baseline_collected"] == 48
    assert "collected dropped from 48 to 47" in payload["blockers"][0]["reason"]


def test_m4b_regression_lock_blocks_failed_errors_or_skips(tmp_path: Path) -> None:
    report_path = tmp_path / "m4b_upload_queue_truth.json"
    output_path = tmp_path / "m4b_regression_lock.json"
    report = _m4b_report(collected=48)
    report.update({"status": "FAIL", "passed": 47, "failed": 1, "exit_code": 1, "failed_tests": ["test_m4b.py::test_fail"]})
    _write_json(report_path, report)

    payload = m4b_lock.evaluate_m4b_regression_lock(
        report_path,
        output_path,
        timestamp="2026-05-29T08:00:00+00:00",
    )

    assert payload["status"] == "FAIL"
    reasons = " ".join(blocker["reason"] for blocker in payload["blockers"])
    assert "failed_zero" in reasons
    assert "failed_tests_empty" in reasons
