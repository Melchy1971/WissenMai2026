from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_report_integrity_v2.py"
spec = importlib.util.spec_from_file_location("generate_report_integrity_v2", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
integrity = importlib.util.module_from_spec(spec)
sys.modules["generate_report_integrity_v2"] = integrity
spec.loader.exec_module(integrity)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _gate(name: str, *, status: str = "PASS", decision: str = "GO", collected: int = 1) -> dict:
    passed = status == "PASS"
    return {
        "report_schema_version": 1,
        "report_name": name,
        "report_type": "gate",
        "gate": name,
        "generated_by": "gate_validator",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision, "result": decision},
        "collected": collected,
        "passed": collected if passed else 0,
        "failed": 0 if passed else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if passed else 1,
        "blockers": [],
    }


def _supporting(name: str, *, status: str = "PASS") -> dict:
    return {
        "report_schema_version": 1,
        "report_name": name,
        "report_type": "supporting",
        "generated_by": "support_runner",
        "timestamp": "2026-06-08T10:00:00+00:00",
        "status": status,
        "summary": {},
    }


def _data_quality() -> dict:
    payload = _supporting("data_quality_report", status="completed")
    payload.update({"quality_score": 94.0, "findings": [], "metrics": {}})
    return payload


def _write_hierarchy_reports(report_dir: Path) -> None:
    reports = {
        "runtime_connectivity_gate.json": _gate("runtime_connectivity_gate"),
        "m3a_release_candidate.json": _gate("m3a_release_candidate"),
        "documentation_truth_lint.json": _supporting("documentation_truth_lint"),
        "m4a_auth_truth.json": _gate("m4a_auth_truth"),
        "m4b_upload_queue_truth.json": _gate("m4b_upload_queue_truth"),
        "m4c_lifecycle_retrieval_truth.json": _gate("m4c_lifecycle_retrieval_truth"),
        "m4e_backup_restore_truth.json": _gate("m4e_backup_restore_truth"),
        "report_truth_preflight.json": _gate("report_truth_preflight"),
        "m5a_start_gate.json": _gate("m5a_start_gate"),
        "data_quality_report.json": _data_quality(),
        "m5a_duplicate_detector_gate.json": _gate("m5a_duplicate_detector_gate"),
        "m5a_metadata_detector_gate.json": _gate("m5a_metadata_detector_gate"),
        "m5a_lifecycle_integrity_gate.json": _gate("m5a_lifecycle_integrity_gate"),
        "m5a_source_status_integrity_gate.json": _gate("m5a_source_status_integrity_gate"),
        "m5a_orphan_detector_gate.json": _gate("m5a_orphan_detector_gate"),
    }
    for filename, payload in reports.items():
        _write(report_dir / filename, payload)


def test_report_integrity_v2_passes_green_current_scope(tmp_path: Path) -> None:
    _write_hierarchy_reports(tmp_path)

    payload = integrity.build_report(tmp_path, timestamp="2026-06-08T10:00:00+00:00")

    assert payload["status"] == "PASS"
    assert payload["blocker_details"] == []
    assert payload["repair_actions"] == []
    assert {item["id"] for item in payload["checks"]} == {
        "json_validity",
        "schema_validity",
        "timestamp",
        "generated_by",
        "status_consistency",
        "gate_consistency",
        "child_gate_consistency",
    }


def test_report_integrity_v2_blocks_invalid_json(tmp_path: Path) -> None:
    _write_hierarchy_reports(tmp_path)
    (tmp_path / "m5a_metadata_detector_gate.json").write_text("{", encoding="utf-8")

    payload = integrity.build_report(tmp_path, timestamp="2026-06-08T10:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert any(item["check"] == "json_validity" for item in payload["blocker_details"])
    assert any("Regenerate or archive" in item["action"] for item in payload["repair_actions"])


def test_report_integrity_v2_blocks_schema_missing_generated_by(tmp_path: Path) -> None:
    _write_hierarchy_reports(tmp_path)
    broken = _gate("m5a_duplicate_detector_gate")
    broken.pop("generated_by")
    _write(tmp_path / "m5a_duplicate_detector_gate.json", broken)

    payload = integrity.build_report(tmp_path, timestamp="2026-06-08T10:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert any(item["check"] == "schema_validity" for item in payload["blocker_details"])
    assert any(item["check"] == "generated_by" for item in payload["blocker_details"])


def test_report_integrity_v2_blocks_child_gate_failure(tmp_path: Path) -> None:
    _write_hierarchy_reports(tmp_path)
    _write(
        tmp_path / "m5a_orphan_detector_gate.json",
        _gate("m5a_orphan_detector_gate", status="BLOCKED", decision="NO_GO"),
    )

    payload = integrity.build_report(tmp_path, timestamp="2026-06-08T10:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert any(item["check"] == "child_gate_consistency" for item in payload["blocker_details"])
