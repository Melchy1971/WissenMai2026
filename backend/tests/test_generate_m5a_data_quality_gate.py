from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_m5a_data_quality_gate.py"
spec = importlib.util.spec_from_file_location("generate_m5a_data_quality_gate", SCRIPT_PATH)
assert spec is not None
gate = importlib.util.module_from_spec(spec)
sys.modules["generate_m5a_data_quality_gate"] = gate
assert spec.loader is not None
spec.loader.exec_module(gate)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _gate_report(*, status: str = "PASS", decision: str = "GO") -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "report_name": "gate",
        "gate": "gate",
        "generated_by": "gate_validator",
        "timestamp": "2026-06-01T00:00:00Z",
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision},
        "collected": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
        "failed_tests": [],
        "blockers": [],
    }


def _data_quality_report_pass() -> dict:
    return {
        "report_schema_version": 2,
        "report_name": "data_quality_report",
        "report_type": "supporting",
        "generated_by": "run_data_quality_cli",
        "timestamp": "2026-06-01T00:00:00Z",
        "run_id": "run-1",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "status": "completed",
        "started_at": "2026-06-01T00:00:00Z",
        "finished_at": "2026-06-01T00:00:01Z",
        "total_documents": 1,
        "total_findings": 0,
        "duplicate_findings": 0,
        "metadata_findings": 0,
        "lifecycle_findings": 0,
        "source_status_findings": 0,
        "orphan_findings": 0,
        "quality_score": 97,
        "findings_by_severity": {},
        "findings_by_type": {},
        "findings": [],
    }


def _write_required_slice_gates(report_dir: Path, *, start_go: bool = True, duplicate_pass: bool = True, metadata_pass: bool = True) -> None:
    _write(report_dir / gate.START_GATE, _gate_report(status="PASS" if start_go else "FAIL", decision="GO" if start_go else "NO_GO"))
    _write(report_dir / gate.DUPLICATE_GATE, _gate_report(status="PASS" if duplicate_pass else "FAIL", decision="GO" if duplicate_pass else "NO_GO"))
    _write(report_dir / gate.METADATA_GATE, _gate_report(status="PASS" if metadata_pass else "FAIL", decision="GO" if metadata_pass else "NO_GO"))
    _write(report_dir / gate.LIFECYCLE_GATE, _gate_report(status="PASS", decision="GO"))
    _write(report_dir / "m5a_source_status_integrity_gate.json", _gate_report(status="PASS", decision="GO"))
    _write(report_dir / "m5a_orphan_detector_gate.json", _gate_report(status="PASS", decision="GO"))
    _write(report_dir / gate.DOC_TRUTH_LINT, {
        "generated_by": "documentation_truth_linter",
        "timestamp": "2026-06-01T00:00:00Z",
        "report_type": "supporting",
        "status": "PASS",
        "result": "PASS",
        "summary": {"errors": 0},
        "exit_code": 0,
        "blockers": [],
    })
    report_integrity = _gate_report(status="PASS", decision="GO")
    report_integrity.update({
        "criteria": [
            {"id": "reports_current_json_valid", "passed": True},
        ],
    })
    _write(report_dir / gate.REPORT_INTEGRITY, report_integrity)


def test_blocks_when_data_quality_report_missing(tmp_path: Path) -> None:
    _write_required_slice_gates(tmp_path)

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert payload["decision"]["data_quality_report_state"] == "NOT_RUN"
    assert any(item["id"] == "child_gate_data_quality_report" for item in payload["blockers"])
    assert any(item["id"] == "data_quality_report_not_run" for item in payload["diagnostic_blockers"])


def test_passes_when_required_slices_and_data_quality_report_are_green(tmp_path: Path) -> None:
    _write_required_slice_gates(tmp_path)
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "PASS"
    assert payload["decision"]["go_no_go"] == "GO"
    assert payload["decision"]["required_slices_all_pass"] is True
    assert payload["decision"]["data_quality_report_state"] == "COMPLETED"
    assert payload["blockers"] == []


def test_blocks_on_invalid_slice_gate_json(tmp_path: Path) -> None:
    _write_required_slice_gates(tmp_path)
    (tmp_path / gate.METADATA_GATE).write_text('{"gate": "m5a_metadata_detector_gate", "status": "PASS",', encoding="utf-8")
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert any(item["id"] == "child_gate_metadata_detector_gate" for item in payload["blockers"])
    assert any(item["id"] == "invalid_m5a_metadata_detector_gate" for item in payload["diagnostic_blockers"])


# ---------------------------------------------------------------------------
# Regression tests for mandatory gate enforcement
# Bug: report_integrity_pre_m5a=BLOCKED was not a criterion, so gate could
#      incorrectly report PASS while decision.report_integrity_pre_m5a_pass=false.
# ---------------------------------------------------------------------------

def _write_required_slice_gates_with_report_integrity(
    report_dir: Path,
    *,
    report_integrity_status: str = "PASS",
) -> None:
    """Like _write_required_slice_gates but allows overriding report_integrity status."""
    _write(report_dir / gate.START_GATE, _gate_report(status="PASS", decision="GO"))
    _write(report_dir / gate.DUPLICATE_GATE, _gate_report(status="PASS", decision="GO"))
    _write(report_dir / gate.METADATA_GATE, _gate_report(status="PASS", decision="GO"))
    _write(report_dir / gate.LIFECYCLE_GATE, _gate_report(status="PASS", decision="GO"))
    _write(report_dir / "m5a_source_status_integrity_gate.json", _gate_report(status="PASS", decision="GO"))
    _write(report_dir / "m5a_orphan_detector_gate.json", _gate_report(status="PASS", decision="GO"))
    _write(report_dir / gate.DOC_TRUTH_LINT, {
        "generated_by": "documentation_truth_linter",
        "timestamp": "2026-06-01T00:00:00Z",
        "report_type": "supporting",
        "status": "PASS",
        "result": "PASS",
        "summary": {"errors": 0},
        "exit_code": 0,
        "blockers": [],
    })
    ri_pass = report_integrity_status == "PASS"
    ri = _gate_report(
        status=report_integrity_status,
        decision="GO" if ri_pass else "NO_GO",
    )
    ri["failed"] = 0 if ri_pass else 2
    ri["passed"] = 1 if ri_pass else 0  # adjust so _is_pass_gate works correctly
    if not ri_pass:
        # Simulate BLOCKED: collected=8, passed=6, failed=2
        ri["collected"] = 8
        ri["passed"] = 6
        ri["failed"] = 2
        ri["exit_code"] = 1
    ri.update({
        "criteria": [
            {"id": "reports_current_json_valid", "passed": True},
        ],
    })
    _write(report_dir / gate.REPORT_INTEGRITY, ri)


def test_regression_report_integrity_blocked_makes_gate_blocked(tmp_path: Path) -> None:
    """
    Regression: Previously all 9 implementation criteria could pass while
    report_integrity_pre_m5a was BLOCKED, causing the gate to output PASS.
    The gate must output BLOCKED when any mandatory gate is not PASS.
    """
    _write_required_slice_gates_with_report_integrity(
        tmp_path, report_integrity_status="BLOCKED"
    )
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "BLOCKED", (
        f"Expected BLOCKED when report_integrity_pre_m5a is BLOCKED, got {payload['status']}"
    )
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert payload["decision"]["report_integrity_pre_m5a_pass"] is False
    blocker_ids = [b["id"] for b in payload["blockers"]]
    assert "child_gate_report_integrity_pre_m5a" in blocker_ids, (
        f"report_integrity_pre_m5a must be a child-gate blocker, got: {blocker_ids}"
    )
    # Verify criterion is present in criteria list
    criterion_ids = [c["id"] for c in payload["criteria"]]
    assert "report_integrity_pre_m5a_pass" in criterion_ids


def test_regression_report_integrity_fail_makes_gate_fail(tmp_path: Path) -> None:
    """report_integrity_pre_m5a=FAIL makes the parent gate FAIL."""
    _write_required_slice_gates_with_report_integrity(
        tmp_path, report_integrity_status="FAIL"
    )
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "FAIL"
    assert payload["decision"]["go_no_go"] == "NO_GO"


def test_start_gate_fail_makes_gate_fail(tmp_path: Path) -> None:
    """m5a_start_gate FAIL → M5a Data Quality Gate BLOCKED."""
    _write_required_slice_gates_with_report_integrity(tmp_path)
    # Overwrite start gate with FAIL
    _write(tmp_path / gate.START_GATE, _gate_report(status="FAIL", decision="NO_GO"))
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "FAIL"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert payload["decision"]["m5a_start_gate_pass"] is False
    blocker_ids = [b["id"] for b in payload["blockers"]]
    assert "child_gate_m5a_start_gate" in blocker_ids


def test_doc_lint_fail_makes_gate_fail(tmp_path: Path) -> None:
    """documentation_truth_lint FAIL → M5a Data Quality Gate BLOCKED."""
    _write_required_slice_gates_with_report_integrity(tmp_path)
    # Overwrite doc lint with FAIL (errors > 0)
    _write(tmp_path / gate.DOC_TRUTH_LINT, {
        "generated_by": "documentation_truth_linter",
        "timestamp": "2026-06-01T00:00:00Z",
        "report_type": "supporting",
        "status": "FAIL",
        "result": "FAIL",
        "summary": {"errors": 5, "warnings": 2},
        "exit_code": 1,
        "blockers": [],
    })
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "FAIL"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert payload["decision"]["documentation_truth_lint_pass"] is False
    blocker_ids = [b["id"] for b in payload["blockers"]]
    assert "child_gate_documentation_truth_lint" in blocker_ids


def test_mandatory_gates_all_pass_allows_pass(tmp_path: Path) -> None:
    """All mandatory gates PASS + all implementation criteria PASS → status=PASS."""
    _write_required_slice_gates_with_report_integrity(tmp_path, report_integrity_status="PASS")
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["decision"]["report_integrity_pre_m5a_pass"] is True
    assert payload["decision"]["m5a_start_gate_pass"] is True
    assert payload["decision"]["documentation_truth_lint_pass"] is True
    assert payload["status"] == "PASS"


def test_criteria_list_contains_all_mandatory_gates(tmp_path: Path) -> None:
    """Mandatory gate IDs must appear in criteria list, not only in decision.*."""
    _write_required_slice_gates_with_report_integrity(tmp_path)
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    criterion_ids = {c["id"] for c in payload["criteria"]}
    assert "m5a_start_gate_pass" in criterion_ids
    assert "documentation_truth_lint_pass" in criterion_ids
    assert "report_integrity_pre_m5a_pass" in criterion_ids
    assert "parent_gate_validation_pass" in criterion_ids
    assert len(payload["criteria"]) == 13
