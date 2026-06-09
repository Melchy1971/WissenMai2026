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
        "generated_by": "gate_validator",
        "status": "PASS",
        "result": "PASS",
        "collected": collected,
        "passed": collected,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "test_database_url_set": True,
        "failed_tests": [],
        "blockers": [],
    }


def _go_gate(marker: str, collected: int = 1) -> dict:
    return {
        **_green_report(marker, collected=collected),
        "decision": {
            "go_no_go": "GO",
            "result": "GO",
        },
    }


def _data_quality_report(score: float = 94.0) -> dict:
    return {
        "report_schema_version": 2,
        "report_name": "data_quality_report",
        "generated_by": "run_data_quality_cli",
        "timestamp": "2026-05-20T08:00:00+00:00",
        "status": "completed",
        "quality_score": score,
        "total_documents": 1,
        "duplicate_findings": 0,
        "metadata_findings": 0,
        "lifecycle_findings": 0,
        "source_status_findings": 0,
        "orphan_findings": 0,
        "findings_by_severity": {},
        "findings_by_type": {},
        "blockers": [],
    }


def _write_report(report_dir: Path, filename: str, payload: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / filename).write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_all_green_reports(report_dir: Path) -> None:
    reports = {
        "runtime_connectivity_gate.json": _green_report("runtime_connectivity_gate", collected=9),
        "m3a_release_candidate.json": _go_gate("m3a_release_candidate", collected=4),
        "documentation_truth_lint.json": {
            "report_schema_version": 1,
            "report_name": "documentation_truth_lint",
            "generated_by": "documentation_truth_linter",
            "timestamp": "2026-05-20T08:00:00+00:00",
            "status": "PASS",
            "result": "PASS",
            "summary": {"errors": 0},
            "exit_code": 0,
            "blockers": [],
        },
        "m4a_auth_truth.json": _green_report("m4a_auth_truth"),
        "m4b_upload_queue_truth.json": _green_report("m4b_upload_queue_truth"),
        "m4c_lifecycle_retrieval_truth.json": _green_report("m4c_lifecycle_retrieval_truth"),
        "m4e_backup_restore_truth.json": _green_report("m4e_backup_restore_truth"),
        "report_truth_preflight.json": _green_report("report_truth_preflight", collected=6),
        "m5a_start_gate.json": _go_gate("m5a_start_gate", collected=12),
        "report_integrity_v2.json": _go_gate("report_integrity_v2", collected=8),
        "data_quality_report.json": _data_quality_report(),
        "m5a_duplicate_detector_gate.json": _go_gate("m5a_duplicate_detector_gate", collected=8),
        "m5a_metadata_detector_gate.json": _go_gate("m5a_metadata_detector_gate", collected=11),
        "m5a_lifecycle_integrity_gate.json": _go_gate("m5a_lifecycle_integrity_gate", collected=10),
        "m5a_source_status_integrity_gate.json": _go_gate("m5a_source_status_integrity_gate", collected=7),
        "m5a_orphan_detector_gate.json": _go_gate("m5a_orphan_detector_gate", collected=5),
    }
    for filename, payload in reports.items():
        _write_report(report_dir, filename, payload)


def test_gate_hierarchy_passes_when_all_mandatory_children_are_green(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        timestamp="2026-05-20T08:00:00+00:00",
    )

    assert result["result"] == "PASS"
    assert result["hierarchy_source"] == "docs/gate_hierarchy.json"
    assert result["gates"]["m3a"]["mandatory_children"] == [
        "runtime_connectivity_gate",
        "m3a_release_candidate",
        "documentation_truth_lint",
    ]
    assert result["gates"]["m4"]["mandatory_children"] == [
        "m4a_auth_truth",
        "m4b_upload_queue_truth",
        "m4c_lifecycle_retrieval_truth",
        "m4e_backup_restore_truth",
        "report_truth_preflight",
    ]
    assert result["gates"]["m5a"]["status"] == "PASS"


def test_parent_gates_are_blocked_by_failed_mandatory_child(tmp_path: Path) -> None:
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
    _write_report(tmp_path, "m4b_upload_queue_truth.json", failed_m4b)

    result = gate_hierarchy.evaluate_gate_hierarchy(tmp_path)

    assert result["gates"]["m4b_upload_queue_truth"]["status"] == "FAIL"
    assert result["gates"]["m4"]["status"] == "BLOCKED"
    assert "mandatory child not passed: m4b_upload_queue_truth" in result["gates"]["m4"]["blockers"]
    assert any(
        detail["gate"] == "m4b_upload_queue_truth"
        and detail["report_path"] == "reports/current/m4b_upload_queue_truth.json"
        and detail["status"] == "FAIL"
        and "Fix the failing tests/counters" in detail["next_action"]
        for detail in result["blocker_details"]
    )
    assert any(
        detail["gate"] == "m4b_upload_queue_truth"
        and detail["report_path"] == "reports/current/m4b_upload_queue_truth.json"
        and detail["status"] == "FAIL"
        and "m4 blocked because mandatory child" in detail["reason"]
        and "Fix the failing tests/counters" in detail["next_action"]
        for detail in result["blocker_details"]
    )


def test_m5a_parent_requires_data_quality_score_threshold(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    _write_report(tmp_path, "data_quality_report.json", _data_quality_report(score=89.9))

    result = gate_hierarchy.evaluate_gate_hierarchy(tmp_path)

    assert result["gates"]["data_quality_report"]["status"] == "FAIL"
    assert result["gates"]["m5a"]["status"] == "BLOCKED"
    assert "quality_score" in " ".join(result["gates"]["data_quality_report"]["blockers"])
    assert any(
        detail["gate"] == "data_quality_report"
        and detail["report_path"] == "reports/current/data_quality_report.json"
        and "quality_score" in detail["reason"]
        and "quality_score at or above" in detail["next_action"]
        for detail in result["blocker_details"]
    )


def test_missing_child_report_includes_repair_path(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    (tmp_path / "m5a_orphan_detector_gate.json").unlink()

    result = gate_hierarchy.evaluate_gate_hierarchy(tmp_path)

    assert result["gates"]["orphan_detector_gate"]["status"] == "FAIL"
    assert any(
        detail["gate"] == "orphan_detector_gate"
        and detail["report_path"] == "reports/current/m5a_orphan_detector_gate.json"
        and "missing report" in detail["reason"]
        and "Generate the missing child report" in detail["next_action"]
        for detail in result["blocker_details"]
    )
    assert result["repair_path"]


def test_dependency_graph_contains_required_parent_edges() -> None:
    graph = gate_hierarchy.dependency_graph()

    assert {"from": "runtime_connectivity_gate", "to": "m3a"} in graph["edges"]
    assert {"from": "report_truth_preflight", "to": "m4"} in graph["edges"]
    assert {"from": "duplicate_detector_gate", "to": "m5a"} in graph["edges"]
    assert {"from": "source_status_integrity_gate", "to": "m5a"} in graph["edges"]


def test_regression_lock_blocks_gate_when_collected_drops_over_threshold(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    _write_report(tmp_path, "m4a_auth_truth.json", _green_report("m4a_auth_truth", collected=79))

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        baseline={"m4a_auth_truth.json": 100},
    )

    assert result["gates"]["m4a_auth_truth"]["status"] == "FAIL"
    blockers_text = " ".join(result["gates"]["m4a_auth_truth"]["blockers"])
    assert "regression" in blockers_text.lower()
    assert "100" in blockers_text
    assert "79" in blockers_text


def test_regression_lock_passes_when_drop_within_threshold(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    _write_report(tmp_path, "m4a_auth_truth.json", _green_report("m4a_auth_truth", collected=80))

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        baseline={"m4a_auth_truth.json": 100},
    )

    assert result["gates"]["m4a_auth_truth"]["status"] == "PASS"


def test_regression_lock_passes_with_justified_scope_change(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    justified = {
        **_green_report("m4a_auth_truth", collected=60),
        "scope_change_reason": "Removed deprecated endpoint tests after endpoint removal",
        "approval": "lead-architect-2026-05-26",
    }
    _write_report(tmp_path, "m4a_auth_truth.json", justified)

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        baseline={"m4a_auth_truth.json": 100},
    )

    assert result["gates"]["m4a_auth_truth"]["status"] == "PASS"


def test_regression_lock_requires_both_reason_and_approval(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    partial = {
        **_green_report("m4a_auth_truth", collected=60),
        "scope_change_reason": "Removed deprecated endpoint tests after endpoint removal",
    }
    _write_report(tmp_path, "m4a_auth_truth.json", partial)

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        baseline={"m4a_auth_truth.json": 100},
    )

    assert result["gates"]["m4a_auth_truth"]["status"] == "FAIL"


def test_regression_lock_skipped_when_no_baseline(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)
    _write_report(tmp_path, "m4a_auth_truth.json", _green_report("m4a_auth_truth", collected=1))

    result = gate_hierarchy.evaluate_gate_hierarchy(tmp_path, baseline=None)

    assert result["gates"]["m4a_auth_truth"]["status"] == "PASS"


def test_report_dir_under_repo_must_be_current() -> None:
    result = gate_hierarchy.evaluate_gate_hierarchy(gate_hierarchy.REPO_ROOT)

    assert result["result"] == "FAIL"
    assert any(
        "reports/current" in blocker["reason"]
        for blocker in result["blockers"]
    )


def test_archive_report_dir_is_rejected() -> None:
    result = gate_hierarchy.evaluate_gate_hierarchy(gate_hierarchy.ARCHIVE_DIR / "legacy")

    assert result["result"] == "FAIL"
    assert any(
        "reports/archive" in blocker["reason"]
        for blocker in result["blockers"]
    )


def test_stale_gate_report_is_rejected(tmp_path: Path) -> None:
    _write_all_green_reports(tmp_path)

    result = gate_hierarchy.evaluate_gate_hierarchy(
        tmp_path,
        timestamp="2026-05-29T08:00:00+00:00",
        max_report_age_hours=24,
    )

    assert result["gates"]["runtime_connectivity_gate"]["status"] == "FAIL"
    assert "older than 24 hours" in " ".join(result["gates"]["runtime_connectivity_gate"]["blockers"])
