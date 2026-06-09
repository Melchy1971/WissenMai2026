from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_masterplan_status_v3.py"
spec = importlib.util.spec_from_file_location("generate_masterplan_status_v3", SCRIPT_PATH)
assert spec is not None
engine = importlib.util.module_from_spec(spec)
sys.modules["generate_masterplan_status_v3"] = engine
assert spec.loader is not None
spec.loader.exec_module(engine)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _rc(status: str = "PASS", decision: str = "GO") -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "report_name": "rc",
        "generated_by": "test",
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision},
        "timestamp": "2026-05-29T08:00:00+00:00",
        "collected": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
    }


def _doc_lint(errors: int = 0) -> dict:
    status = "FAIL" if errors else "PASS"
    return {
        "report_name": "documentation_truth_lint",
        "report_type": "supporting",
        "generated_by": "test",
        "status": status,
        "result": status,
        "timestamp": "2026-05-29T08:00:00+00:00",
        "summary": {"errors": errors, "warnings": 0},
    }


def _known_limitations(operations_open: bool = True) -> dict:
    limitations = []
    if operations_open:
        limitations.append({
            "id": "KL-NB-OPS",
            "bereich": "M4e Operations",
            "zielphase": "M5 Operations",
            "blockiert_gate": [],
        })
    return {"generated_by": "test", "limitations": limitations}


def _operations_release(status: str = "PASS", decision: str = "GO") -> dict:
    payload = _rc(status, decision)
    payload.update({
        "report_name": "m4e_operations_release_report",
        "gate": "m4e_operations_release",
        "operations_release_status": decision,
    })
    return payload


def _m5a_start_gate(decision: str = "GO") -> dict:
    return {
        "report_name": "m5a_start_gate",
        "generated_by": "test",
        "gate": "m5a_start_gate",
        "status": "PASS" if decision == "GO" else "FAIL",
        "result": "PASS" if decision == "GO" else "FAIL",
        "decision": {"go_no_go": decision, "result": decision},
        "timestamp": "2026-05-29T08:00:00+00:00",
        "collected": 1,
        "passed": 1 if decision == "GO" else 0,
        "failed": 0 if decision == "GO" else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if decision == "GO" else 1,
    }


def _data_quality_report() -> dict:
    return {
        "report_name": "data_quality_report",
        "report_type": "supporting",
        "generated_by": "test",
        "status": "completed",
        "timestamp": "2026-05-29T08:00:00+00:00",
        "quality_score": 94.0,
        "blockers": [],
    }


def _m5a_data_quality_gate(status: str = "PASS", decision: str = "GO") -> dict:
    return {
        "report_name": "m5a_data_quality_gate",
        "generated_by": "gate_validator",
        "gate": "m5a_data_quality_gate",
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision, "result": decision},
        "timestamp": "2026-05-29T08:00:00+00:00",
        "collected": 1,
        "passed": 1 if status == "PASS" else 0,
        "failed": 0 if status == "PASS" else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "blockers": [],
    }


def _m5b_start_gate(status: str = "PREPARED") -> dict:
    return {
        "report_name": "m5b_start_gate",
        "generated_by": "gate_validator",
        "gate": "m5b_start_gate",
        "status": status,
        "result": status,
        "decision": {
            "go_no_go": "GO" if status == "PREPARED" else "NO_GO",
            "m5b_preparation_allowed": status == "PREPARED",
            "m5b_implementation_allowed": False,
            "m5b_implementation_gate_required": True,
        },
        "timestamp": "2026-05-29T08:00:00+00:00",
        "blockers": [] if status == "PREPARED" else [{"id": "M5A_PARENT_GATE_NOT_PASSED"}],
    }


def _write_m5a_pass_inputs(report_dir: Path) -> None:
    _write(report_dir / engine.M5A_START_GATE, _m5a_start_gate("GO"))
    _write(report_dir / "report_integrity_v2.json", _rc())
    _write(report_dir / "data_quality_report.json", _data_quality_report())
    _write(report_dir / "m5a_duplicate_detector_gate.json", _rc())
    _write(report_dir / "m5a_metadata_detector_gate.json", _rc())
    _write(report_dir / "m5a_lifecycle_integrity_gate.json", _rc())
    _write(report_dir / "m5a_source_status_integrity_gate.json", _rc())
    _write(report_dir / "m5a_orphan_detector_gate.json", _rc())
    _write(report_dir / engine.M5A_DATA_QUALITY_GATE, _m5a_data_quality_gate())


def _m5_gate_assessment(*, implementation_allowed: bool = False, slice_start_allowed: bool = False) -> dict:
    return {
        "report_name": "m5_gate_assessment",
        "generated_by": "test",
        "gate": "m5_gate_assessment",
        "decision": "GO",
        "assessment": {
            "m5_preparation_allowed": True,
            "m5_implementation_allowed": implementation_allowed,
            "m5_slice_start_allowed": slice_start_allowed,
        },
    }


def _write_parent_children(report_dir: Path) -> None:
    _write(report_dir / "runtime_connectivity_gate.json", _rc())
    _write(report_dir / "m4a_auth_truth.json", _rc())
    _write(report_dir / "m4b_upload_queue_truth.json", _rc())
    _write(report_dir / "m4c_lifecycle_retrieval_truth.json", _rc())
    _write(report_dir / "m4e_backup_restore_truth.json", _rc())


def _write_inputs(
    report_dir: Path,
    *,
    m3a: dict | None = None,
    m4: dict | None = None,
    doc_errors: int = 0,
    operations_open: bool = False,
    operations_release: dict | None = None,
    m5a_start_gate: dict | None = None,
    m5_gate_assessment: dict | None = None,
) -> None:
    _write(report_dir / engine.M3A_RC, m3a or _rc())
    _write(report_dir / engine.M4_BACKEND_RC, m4 or _rc())
    _write(report_dir / engine.M4E_OPERATIONS_RELEASE, operations_release or _operations_release())
    _write(report_dir / engine.DOC_LINT, _doc_lint(doc_errors))
    _write(report_dir / engine.KNOWN_LIMITATIONS, _known_limitations(operations_open))
    _write(report_dir / engine.FRONTEND_FULL_SUITE, _rc())
    _write(report_dir / engine.PREFLIGHT, _rc())
    _write_parent_children(report_dir)
    if m5a_start_gate is not None:
        _write(report_dir / engine.M5A_START_GATE, m5a_start_gate)
    if m5_gate_assessment is not None:
        _write(report_dir / engine.M5_GATE_ASSESSMENT, m5_gate_assessment)


def test_v3_blocks_release_when_m3a_rc_is_not_pass(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m3a=_rc("FAIL", "NO-GO"), operations_open=False)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m3a"]["decision"] == "NO_GO"
    assert payload["phases"]["m4"]["decision"] == "GO"
    assert payload["m5"]["preparation_allowed"] is True
    assert payload["overall"]["release_allowed"] is False
    assert payload["timestamp"] == "2026-05-29T08:00:00+00:00"
    assert payload["status"] == payload["overall"]["status"]


def test_v3_m5_preparation_depends_on_m4e_operations_not_m4_alone(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m4=_rc("FAIL", "NO-GO"), operations_open=False)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m4"]["decision"] == "NO_GO"
    assert payload["m5"]["preparation_allowed"] is True
    assert payload["m5"]["status"] == "PREPARATION_ALLOWED"


def test_v3_keeps_m5_implementation_no_go_until_operations_release(tmp_path: Path) -> None:
    _write_inputs(tmp_path, operations_release=_operations_release("FAIL", "NO-GO"))

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m3a"]["decision"] == "GO"
    assert payload["phases"]["m4"]["decision"] == "GO"
    assert payload["m5"]["preparation_allowed"] is False
    assert payload["m5"]["implementation_allowed"] is False
    assert payload["m5"]["implementation_decision"] == "NO_GO"
    assert payload["m5"]["status"] == "NOT_STARTED"
    assert payload["overall"]["release_allowed"] is False


def test_v3_m4e_operations_go_allows_preparation_only_without_slice_gate(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["m5"]["preparation_allowed"] is True
    assert payload["m5"]["implementation_allowed"] is False
    assert payload["m5"]["implementation_decision"] == "NO_GO"
    assert payload["m5"]["status"] == "PREPARATION_ALLOWED"


def test_v3_allows_slice_start_when_m5a_start_gate_is_go(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m5a_start_gate=_m5a_start_gate("GO"))

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["m5"]["status"] == "SLICE_IMPLEMENTING"
    assert payload["m5"]["slice_start_allowed"] is True
    assert payload["m5"]["implementation_allowed"] is False
    assert payload["phases"]["m5_implementation"]["gate_status"] == "BLOCKED"
    assert payload["phases"]["m5_implementation"]["decision"] == "NO_GO"


def test_v3_keeps_m5_implementation_no_go_for_active_known_operations_limitation(tmp_path: Path) -> None:
    _write_inputs(tmp_path, operations_open=True, m5a_start_gate=_m5a_start_gate("GO"))

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["m5"]["implementation_allowed"] is False
    assert payload["m5"]["implementation_decision"] == "NO_GO"
    assert payload["known_limitations"]["operations_open_ids"] == ["KL-NB-OPS"]


def test_v3_blocks_m5_status_when_slice_report_json_is_invalid(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    (tmp_path / engine.M5A_DATA_QUALITY_GATE).write_text('{"gate": "m5a_data_quality_gate", "timestamp": "', encoding="utf-8")

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["m5"]["status"] == "BLOCKED"
    assert payload["overall"]["release_allowed"] is False
    assert any(item["id"] == "invalid_m5a_data_quality_gate" for item in payload["input_integrity_issues"])


def test_v3_blocks_contradictory_m5_implementation_assessment(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m5_gate_assessment=_m5_gate_assessment(implementation_allowed=True))

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["m5"]["status"] == "BLOCKED"
    assert payload["m5"]["implementation_allowed"] is False
    assert any(item["id"] == "m5_assessment_implementation_contradiction" for item in payload["report_contradictions"])


def test_v3_blocks_data_quality_gate_without_m5a_start_gate(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _write(tmp_path / engine.M5A_DATA_QUALITY_GATE, _operations_release())

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["m5"]["status"] == "BLOCKED"
    assert any(item["id"] == "m5a_data_quality_without_start_gate" for item in payload["report_contradictions"])


def test_v3_doc_lint_errors_block_release(tmp_path: Path) -> None:
    _write_inputs(tmp_path, doc_errors=2)

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["documentation_lint"]["errors"] == 2
    assert payload["overall"]["release_allowed"] is False
    assert any(blocker["id"] == "documentation_truth_lint_errors" for blocker in payload["blockers"])


def test_v3_status_section_uses_v3_markers(tmp_path: Path) -> None:
    _write_inputs(tmp_path, operations_release=_operations_release("FAIL", "NO-GO"))
    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    section = engine.render_status_section(payload)

    assert "<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->" in section
    assert "M5 Implementierung" in section
    assert "NO_GO" in section
    assert "Statusmodell" in section
    assert "<!-- END GENERATED MASTERPLAN STATUS v3 -->" in section


def test_v3_blocks_m5b_until_m5a_pass(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _write(tmp_path / engine.M5B_START_GATE, _m5b_start_gate("PREPARED"))

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m5b_drift"]["gate_status"] == "PREPARED"
    assert payload["phases"]["m5b_drift"]["decision"] == "NO_GO"
    assert any(
        blocker["id"] == "M5A_PARENT_GATE_NOT_PASSED"
        for blocker in payload["phases"]["m5b_drift"]["blockers"]
    )


def test_v3_allows_m5b_prepared_after_m5a_pass_without_implementation(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _write_m5a_pass_inputs(tmp_path)
    _write(tmp_path / engine.M5B_START_GATE, _m5b_start_gate("PREPARED"))

    payload = engine.evaluate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["phases"]["m5b_drift"]["decision"] == "PREPARED"
    assert payload["phases"]["m5b_drift"]["gate_status"] == "PREPARED"
    assert payload["m5"]["m5b_implementation_allowed"] is False
    assert payload["m5"]["m5b_implementation_gate_required"] is True
    assert payload["gate_hierarchy"]["m5b_implementation_gate"]["status"] == "BLOCKED"
    assert payload["overall"]["release_allowed"] is False
    assert payload["overall"]["progress_percent"] < 100
    assert payload["progress_model"]["m5_complete"] is False
    assert payload["progress_model"]["documentation_pass_counted"] is False
