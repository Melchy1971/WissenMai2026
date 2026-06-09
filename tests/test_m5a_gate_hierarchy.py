from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_m5a_data_quality_gate.py"
spec = importlib.util.spec_from_file_location("generate_m5a_data_quality_gate", SCRIPT_PATH)
assert spec is not None
m5a_gate = importlib.util.module_from_spec(spec)
sys.modules["generate_m5a_data_quality_gate"] = m5a_gate
assert spec.loader is not None
spec.loader.exec_module(m5a_gate)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _gate_report(
    *,
    status: str = "PASS",
    decision: str = "GO",
    collected: int = 1,
    timestamp: str = "2026-06-03T08:00:00+00:00",
) -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "report_name": "gate",
        "gate": "gate",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision, "result": decision},
        "collected": collected,
        "passed": collected if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
        "failed_tests": [],
        "blockers": [],
    }


def _documentation_lint(status: str = "PASS") -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "report_name": "documentation_truth_lint",
        "generated_by": "documentation_truth_linter",
        "timestamp": "2026-06-03T08:00:00+00:00",
        "report_type": "supporting",
        "status": status,
        "result": status,
        "summary": {"errors": 0 if passed else 1},
        "exit_code": 0 if passed else 1,
        "blockers": [],
    }


def _data_quality_report(score: float = 94.0, *, timestamp: str = "2026-06-03T08:00:00+00:00") -> dict:
    return {
        "report_schema_version": 2,
        "report_name": "data_quality_report",
        "report_type": "supporting",
        "generated_by": "run_data_quality_cli",
        "timestamp": timestamp,
        "run_id": "run-1",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "status": "completed",
        "started_at": timestamp,
        "finished_at": timestamp,
        "total_documents": 1,
        "total_findings": 0,
        "duplicate_findings": 0,
        "metadata_findings": 0,
        "lifecycle_findings": 0,
        "source_status_findings": 0,
        "orphan_findings": 0,
        "quality_score": score,
        "findings_by_severity": {},
        "findings_by_type": {},
        "findings": [],
        "blockers": [],
    }


def _write_all_child_gates(report_dir: Path) -> None:
    _write(report_dir / m5a_gate.START_GATE, _gate_report(collected=12))
    _write(report_dir / m5a_gate.REPORT_INTEGRITY, _gate_report(collected=8))
    _write(report_dir / m5a_gate.DOC_TRUTH_LINT, _documentation_lint())
    _write(report_dir / m5a_gate.DATA_QUALITY_REPORT, _data_quality_report())
    _write(report_dir / m5a_gate.DUPLICATE_GATE, _gate_report(collected=8))
    _write(report_dir / m5a_gate.METADATA_GATE, _gate_report(collected=11))
    _write(report_dir / m5a_gate.LIFECYCLE_GATE, _gate_report(collected=10))
    _write(report_dir / "m5a_source_status_integrity_gate.json", _gate_report(collected=7))
    _write(report_dir / "m5a_orphan_detector_gate.json", _gate_report(collected=5))


def _build(report_dir: Path) -> dict:
    return m5a_gate.build_gate_report(report_dir, timestamp="2026-06-03T08:00:00+00:00")


def test_report_integrity_blocked_blocks_m5a_data_quality_gate(tmp_path: Path) -> None:
    _write_all_child_gates(tmp_path)
    _write(
        tmp_path / m5a_gate.REPORT_INTEGRITY,
        _gate_report(status="BLOCKED", decision="NO_GO", collected=8),
    )

    payload = _build(tmp_path)

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert any(blocker.get("child_gate_id") == "report_integrity_v2" for blocker in payload["blockers"])


def test_missing_child_gate_blocks_m5a_data_quality_gate(tmp_path: Path) -> None:
    _write_all_child_gates(tmp_path)
    (tmp_path / "m5a_orphan_detector_gate.json").unlink()

    payload = _build(tmp_path)

    assert payload["status"] == "BLOCKED"
    assert any(blocker.get("child_gate_id") == "orphan_detector_gate" for blocker in payload["blockers"])


def test_invalid_json_child_blocks_m5a_data_quality_gate(tmp_path: Path) -> None:
    _write_all_child_gates(tmp_path)
    (tmp_path / "m5a_source_status_integrity_gate.json").write_text("{", encoding="utf-8")

    payload = _build(tmp_path)

    assert payload["status"] == "BLOCKED"
    child = payload["parent_gate_validation"]["child_results"]["source_status_integrity_gate"]
    assert child["validation_status"] == "INVALID"


def test_stale_child_blocks_m5a_data_quality_gate(tmp_path: Path) -> None:
    _write_all_child_gates(tmp_path)
    _write(
        tmp_path / m5a_gate.DUPLICATE_GATE,
        _gate_report(collected=8, timestamp="2026-05-20T08:00:00+00:00"),
    )

    payload = _build(tmp_path)

    assert payload["status"] == "BLOCKED"
    child = payload["parent_gate_validation"]["child_results"]["duplicate_detector_gate"]
    assert child["validation_status"] == "STALE"


def test_all_child_gates_pass_makes_m5a_data_quality_gate_pass(tmp_path: Path) -> None:
    _write_all_child_gates(tmp_path)

    payload = _build(tmp_path)

    assert payload["status"] == "PASS"
    assert payload["decision"]["go_no_go"] == "GO"
    assert payload["parent_gate_validation"]["status"] == "PASS"


def test_slice_gate_pass_but_mandatory_parent_child_fail_blocks_gate(tmp_path: Path) -> None:
    _write_all_child_gates(tmp_path)
    _write(
        tmp_path / m5a_gate.REPORT_INTEGRITY,
        _gate_report(status="FAIL", decision="NO_GO", collected=8),
    )
    assert json.loads((tmp_path / m5a_gate.DUPLICATE_GATE).read_text(encoding="utf-8"))["status"] == "PASS"
    assert json.loads((tmp_path / m5a_gate.METADATA_GATE).read_text(encoding="utf-8"))["status"] == "PASS"
    assert json.loads((tmp_path / m5a_gate.LIFECYCLE_GATE).read_text(encoding="utf-8"))["status"] == "PASS"

    payload = _build(tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["decision"]["required_slices_all_pass"] is True
    assert payload["gate_decision_trace"]["final_status"] == "FAIL"
    assert any(blocker.get("child_gate_id") == "report_integrity_v2" for blocker in payload["blockers"])
