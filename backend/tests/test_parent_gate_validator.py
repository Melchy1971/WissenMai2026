from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "parent_gate_validator.py"
spec = importlib.util.spec_from_file_location("parent_gate_validator", SCRIPT_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
sys.modules["parent_gate_validator"] = validator
assert spec.loader is not None
spec.loader.exec_module(validator)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _gate(status: str = "PASS", decision: str = "GO", collected: int = 1) -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "generated_by": "gate_validator",
        "timestamp": "2026-06-03T08:00:00+00:00",
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


def _data_quality(score: float = 94.0) -> dict:
    return {
        "report_schema_version": 2,
        "report_name": "data_quality_report",
        "generated_by": "run_data_quality_cli",
        "timestamp": "2026-06-03T08:00:00+00:00",
        "status": "completed",
        "quality_score": score,
        "blockers": [],
    }


def _write_m5a_children(report_dir: Path) -> None:
    _write(report_dir / "m5a_start_gate.json", _gate(collected=12))
    _write(report_dir / "report_integrity_pre_m5a.json", _gate(collected=8))
    _write(report_dir / "documentation_truth_lint.json", {
        "generated_by": "documentation_truth_linter",
        "timestamp": "2026-06-03T08:00:00+00:00",
        "status": "PASS",
        "result": "PASS",
        "summary": {"errors": 0},
        "exit_code": 0,
        "blockers": [],
    })
    _write(report_dir / "data_quality_report.json", _data_quality())
    _write(report_dir / "m5a_duplicate_detector_gate.json", _gate(collected=8))
    _write(report_dir / "m5a_metadata_detector_gate.json", _gate(collected=11))
    _write(report_dir / "m5a_lifecycle_integrity_gate.json", _gate(collected=10))
    _write(report_dir / "m5a_source_status_integrity_gate.json", _gate(collected=7))
    _write(report_dir / "m5a_orphan_detector_gate.json", _gate(collected=5))


def test_parent_gate_passes_when_all_mandatory_children_pass(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)

    payload = validator.validate_parent_gate(
        "m5a",
        report_dir=tmp_path,
        timestamp="2026-06-03T08:00:00+00:00",
    )

    assert payload["status"] == "PASS"
    assert payload["decision"]["go_no_go"] == "GO"
    assert payload["blockers"] == []
    assert payload["no_manual_override"] is True


def test_parent_gate_blocks_when_child_report_missing(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)
    (tmp_path / "m5a_orphan_detector_gate.json").unlink()

    payload = validator.validate_parent_gate("m5a", report_dir=tmp_path)

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert any(blocker["child_gate_id"] == "orphan_detector_gate" for blocker in payload["blockers"])


def test_parent_gate_blocks_when_child_json_invalid(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)
    (tmp_path / "m5a_source_status_integrity_gate.json").write_text("{", encoding="utf-8")

    payload = validator.validate_parent_gate("m5a", report_dir=tmp_path)

    assert payload["status"] == "BLOCKED"
    assert payload["child_results"]["source_status_integrity_gate"]["validation_status"] == "INVALID"
    assert any(blocker["child_gate_id"] == "source_status_integrity_gate" for blocker in payload["blockers"])


def test_parent_gate_blocks_blocked_child_without_manual_override(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)
    blocked = _gate(status="BLOCKED", decision="NO_GO")
    blocked["manual_override"] = True
    _write(tmp_path / "report_integrity_pre_m5a.json", blocked)

    payload = validator.validate_parent_gate("m5a", report_dir=tmp_path)

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["manual_override_allowed"] is False
    assert payload["child_results"]["report_integrity_pre_m5a"]["validation_status"] == "BLOCKED"
    assert any(blocker["child_gate_id"] == "report_integrity_pre_m5a" for blocker in payload["blockers"])
    assert payload["gate_decision_trace"]["final_status"] == "BLOCKED"


def test_parent_gate_fails_when_child_fails(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)
    _write(tmp_path / "report_integrity_pre_m5a.json", _gate(status="FAIL", decision="NO_GO"))

    payload = validator.validate_parent_gate("m5a", report_dir=tmp_path)

    assert payload["status"] == "FAIL"
    assert payload["decision"]["go_no_go"] == "NO_GO"
    assert payload["child_results"]["report_integrity_pre_m5a"]["validation_status"] == "FAIL"
    assert payload["gate_decision_trace"]["failing_children"] == ["report_integrity_pre_m5a"]


def test_parent_gate_allows_configured_non_pass_status(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)

    payload = validator.validate_parent_gate("m5a", report_dir=tmp_path)

    assert payload["child_results"]["data_quality_report"]["validation_status"] == "PASS"


def test_parent_gate_blocks_stale_child(tmp_path: Path) -> None:
    _write_m5a_children(tmp_path)

    payload = validator.validate_parent_gate(
        "m5a",
        report_dir=tmp_path,
        timestamp="2026-06-03T08:00:00+00:00",
        max_report_age_hours=1,
    )

    assert payload["status"] == "PASS"

    stale = _gate(collected=8)
    stale["timestamp"] = "2026-06-01T08:00:00+00:00"
    _write(tmp_path / "m5a_duplicate_detector_gate.json", stale)
    payload = validator.validate_parent_gate(
        "m5a",
        report_dir=tmp_path,
        timestamp="2026-06-03T08:00:00+00:00",
        max_report_age_hours=1,
    )

    assert payload["status"] == "BLOCKED"
    assert payload["child_results"]["duplicate_detector_gate"]["validation_status"] == "STALE"
