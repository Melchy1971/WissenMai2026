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
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision},
        "collected": 1,
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
    }


def _data_quality_report_pass() -> dict:
    return {
        "report_schema_version": "1.0.0",
        "report_name": "data_quality_report",
        "timestamp": "2026-06-01T00:00:00Z",
        "quality_score": 97,
        "findings": [],
    }


def _write_required_slice_gates(report_dir: Path, *, start_go: bool = True, duplicate_pass: bool = True, metadata_pass: bool = True) -> None:
    _write(report_dir / gate.START_GATE, _gate_report(status="PASS" if start_go else "FAIL", decision="GO" if start_go else "NO_GO"))
    _write(report_dir / gate.DUPLICATE_GATE, _gate_report(status="PASS" if duplicate_pass else "FAIL", decision="GO" if duplicate_pass else "NO_GO"))
    _write(report_dir / gate.METADATA_GATE, _gate_report(status="PASS" if metadata_pass else "FAIL", decision="GO" if metadata_pass else "NO_GO"))


def test_blocks_when_data_quality_report_missing(tmp_path: Path) -> None:
    _write_required_slice_gates(tmp_path)

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert payload["decision"]["data_quality_report_state"] == "NOT_RUN"
    assert any(item["id"] == "data_quality_report_not_run" for item in payload["blockers"])


def test_passes_when_required_slices_and_data_quality_report_are_green(tmp_path: Path) -> None:
    _write_required_slice_gates(tmp_path)
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "PASS"
    assert payload["decision"]["go_no_go"] == "GO"
    assert payload["decision"]["required_slices_all_pass"] is True
    assert payload["decision"]["data_quality_report_state"] == "PASS"
    assert payload["blockers"] == []


def test_blocks_on_invalid_slice_gate_json(tmp_path: Path) -> None:
    _write_required_slice_gates(tmp_path)
    (tmp_path / gate.METADATA_GATE).write_text('{"gate": "m5a_metadata_detector_gate", "status": "PASS",', encoding="utf-8")
    _write(tmp_path / gate.DATA_QUALITY_REPORT, _data_quality_report_pass())

    payload = gate.build_gate_report(tmp_path, timestamp="2026-06-01T00:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert any(item["id"] == "invalid_m5a_metadata_detector_gate" for item in payload["blockers"])
