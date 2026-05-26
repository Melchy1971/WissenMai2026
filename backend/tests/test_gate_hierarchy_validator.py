from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_gate_hierarchy.py"
spec = importlib.util.spec_from_file_location("validate_gate_hierarchy", SCRIPT_PATH)
assert spec is not None
gate_hierarchy = importlib.util.module_from_spec(spec)
sys.modules["validate_gate_hierarchy"] = gate_hierarchy
assert spec.loader is not None
spec.loader.exec_module(gate_hierarchy)


def _green_report(marker: str, collected: int = 1) -> dict:
    return {
        "report_format_version": 1,
        "marker": marker,
        "timestamp": "2026-05-20T08:00:00+00:00",
        "collected": collected,
        "passed": collected,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "test_database_url_set": True,
        "failed_tests": [],
    }


def _write_report(report_dir: Path, filename: str, payload: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / filename).write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_all_green_reports(report_dir: Path) -> None:
    marker_by_report = {
        "frontend_truth_report.json": "frontend_truth",
        "m3a_truth_report.json": "m3a_truth",
        "m4_truth_report.json": "m4_truth",
        "m4a_auth_truth_report.json": "m4a_auth_truth",
        "m4b_upload_queue_truth_report.json": "m4b_upload_queue_truth",
        "m4c_lifecycle_retrieval_truth_report.json": "m4c_lifecycle_retrieval_truth",
        "m4e_backup_restore_truth_report.json": "m4e_backup_restore_truth",
        "governance_truth_report.json": "governance_truth",
    }
    for filename, marker in marker_by_report.items():
        _write_report(report_dir, filename, _green_report(marker))


def test_gate_hierarchy_passes_when_all_required_split_reports_are_green(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        timestamp="2026-05-20T08:00:00+00:00",
    )

    assert result["result"] == "PASS"
    assert result["gates"]["m3a_gate"]["reports"] == [
        "m3a_truth_report.json",
        "frontend_truth_report.json",
    ]
    assert result["gates"]["m4_overall_gate"]["dependencies"] == [
        "m4_crosscutting_gate",
        "m4a_gate",
        "m4b_gate",
        "m4c_gate",
        "m4e_gate",
    ]
    assert result["gates"]["m5_start_gate"]["dependencies"] == ["m4_overall_gate"]
    assert result["gates"]["operational_governance_gate"]["dependencies"] == ["m5_start_gate"]


def test_m4_overall_and_m5_are_blocked_by_failed_m4_subgate(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    failed_m4b = _green_report("m4b_upload_queue_truth")
    failed_m4b.update(
        {
            "passed": 0,
            "failed": 1,
            "exit_code": 1,
            "failed_tests": ["tests/test_m4b.py::test_upload"],
        }
    )
    _write_report(tmp_path, "m4b_upload_queue_truth_report.json", failed_m4b)

    result = gate_hierarchy.evaluate_gate_hierarchy(tmp_path)

    assert result["gates"]["m4b_gate"]["status"] == "FAIL"
    assert result["gates"]["m4_overall_gate"]["status"] == "BLOCKED"
    assert result["gates"]["m5_start_gate"]["status"] == "BLOCKED"
    assert result["gates"]["operational_governance_gate"]["status"] == "BLOCKED"


def test_governance_failure_does_not_block_before_m5_start(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    failed_governance = _green_report("governance_truth")
    failed_governance.update(
        {
            "passed": 0,
            "failed": 1,
            "exit_code": 1,
            "failed_tests": ["tests/test_governance.py::test_cleanup"],
        }
    )
    _write_report(tmp_path, "governance_truth_report.json", failed_governance)

    result = gate_hierarchy.evaluate_gate_hierarchy(tmp_path)

    assert result["gates"]["m4_overall_gate"]["status"] == "PASS"
    assert result["gates"]["m5_start_gate"]["status"] == "PASS"
    assert result["gates"]["operational_governance_gate"]["status"] == "FAIL"


def test_dependency_graph_contains_expected_edges() -> None:
    graph = gate_hierarchy.dependency_graph()

    assert {"from": "m4_overall_gate", "to": "m5_start_gate"} in graph["edges"]
    assert {"from": "m5_start_gate", "to": "operational_governance_gate"} in graph["edges"]
    assert {"from": "m4a_gate", "to": "m4_overall_gate"} in graph["edges"]
    assert {"from": "m4_crosscutting_gate", "to": "m4_overall_gate"} in graph["edges"]
