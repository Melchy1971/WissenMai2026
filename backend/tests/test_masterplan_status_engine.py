from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_masterplan_status.py"
spec = importlib.util.spec_from_file_location("generate_masterplan_status", SCRIPT_PATH)
assert spec is not None
status_engine = importlib.util.module_from_spec(spec)
sys.modules["generate_masterplan_status"] = status_engine
assert spec.loader is not None
spec.loader.exec_module(status_engine)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _seed_artifacts(report_dir: Path, docs_dir: Path) -> None:
    _write(
        report_dir / "m3a_release_candidate.json",
        {
            "status": "gate_passed",
            "go_no_go": {"result": "GO"},
            "scores": {"m3a_gate_score": 100.0},
            "blockers": [],
        },
    )
    _write(
        report_dir / "m4_release_candidate.json",
        {
            "status": "tested",
            "go_no_go": {"result": "NO_GO"},
            "m4_scores": {
                "m4a_auth": {"score": 100.0, "status": "PARTIAL_PASS_BLOCKED_BY_M4_TRUTH"},
                "m4b_upload_queue": {"score": 91.7, "status": "PARTIAL_PASS_BLOCKED_BY_M4_TRUTH"},
                "m4c_lifecycle_retrieval": {"score": 100.0, "status": "PARTIAL_PASS_BLOCKED_BY_M4_TRUTH"},
            },
            "blockers": [{"id": "postgres_truth_m4_not_green", "severity": "blocking", "detail": "red"}],
        },
    )
    _write(
        report_dir / "frontend_truth_report.json",
        {"collected": 10, "passed": 10, "failed": 0, "errors": 0, "exit_code": 0},
    )
    _write(
        report_dir / "postgres_truth_report.json",
        {"collected": 10, "passed": 8, "failed": 2, "errors": 0, "pytest_exit_code": 1},
    )
    _write(report_dir / "gate_drift_report.json", {"result": "PASS", "findings": []})
    _write(
        report_dir / "documentation_release_audit.json",
        {"release_decision": {"freigabe": "ja", "blocking_findings": []}},
    )
    _write(report_dir / "truth_marker_taxonomy.json", {"collected": 10, "unclassified_tests": [], "ambiguous_tests": []})
    _write(
        docs_dir / "known_limitations.json",
        {
            "limitations": [
                {
                    "id": "KL-M4-001",
                    "beschreibung": "M4 blocked",
                    "blockiert_gate": ["m4_overall_gate", "m5_start_gate"],
                    "zielphase": "M4",
                }
            ]
        },
    )


def test_masterplan_status_is_derived_from_artifacts_and_blocks_on_m4(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    docs_dir = tmp_path / "docs"
    _seed_artifacts(report_dir, docs_dir)

    payload = status_engine.build_masterplan_status(
        report_dir=report_dir,
        docs_dir=docs_dir,
        timestamp="2026-05-20T10:00:00+00:00",
    )

    assert payload["authority"]["source_of_truth"] == "machine_artifacts"
    assert payload["authority"]["manual_status_override_allowed"] is False
    assert payload["phases"]["m3a"]["status"] == "gate_passed"
    assert payload["phases"]["m4"]["decision"] == "NO_GO"
    assert payload["phases"]["m5"]["status"] == "blocked"
    assert payload["overall"]["release_allowed"] is False
    assert payload["overall"]["progress_percent"] == 40.0
    assert payload["gate_scores"]["m4_postgres_truth"]["score"] == 80.0
    assert any(blocker["id"] == "postgres_truth_m4_not_green" for blocker in payload["blockers"])


def test_status_section_contains_generated_markers_and_blockers(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    docs_dir = tmp_path / "docs"
    _seed_artifacts(report_dir, docs_dir)
    payload = status_engine.build_masterplan_status(report_dir=report_dir, docs_dir=docs_dir)

    section = status_engine.render_status_section(payload)

    assert "<!-- BEGIN GENERATED MASTERPLAN STATUS -->" in section
    assert "Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben" in section
    assert "postgres_truth_m4_not_green" in section
    assert "<!-- END GENERATED MASTERPLAN STATUS -->" in section


def test_documentation_audit_and_gate_drift_are_blocking_inputs(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    docs_dir = tmp_path / "docs"
    _seed_artifacts(report_dir, docs_dir)
    _write(report_dir / "gate_drift_report.json", {"result": "FAIL", "findings": [{"id": "GDD-BASELINE-MISSING"}]})
    _write(
        report_dir / "documentation_release_audit.json",
        {"release_decision": {"freigabe": "nein", "blocking_findings": ["DRA-001"]}},
    )

    payload = status_engine.build_masterplan_status(report_dir=report_dir, docs_dir=docs_dir)
    blocker_ids = {blocker["id"] for blocker in payload["blockers"]}

    assert "gate_drift_fail" in blocker_ids
    assert "DRA-001" in blocker_ids
    assert payload["documentation_audit"]["freigabe"] == "nein"
    assert payload["gate_drift"]["result"] == "FAIL"
