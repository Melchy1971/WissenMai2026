from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "detect_gate_drift.py"
spec = importlib.util.spec_from_file_location("detect_gate_drift", SCRIPT_PATH)
assert spec is not None
gate_drift = importlib.util.module_from_spec(spec)
sys.modules["detect_gate_drift"] = gate_drift
assert spec.loader is not None
spec.loader.exec_module(gate_drift)


def _report(marker: str, *, collected: int = 2, passed: int = 2, failed: int = 0, errors: int = 0) -> dict:
    return {
        "report_format_version": 1,
        "marker": marker,
        "timestamp": "2026-05-20T08:00:00+00:00",
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": 0,
        "exit_code": 0 if failed == 0 and errors == 0 else 1,
        "test_database_url_set": True,
        "failed_tests": [] if failed == 0 else ["tests/test_example.py::test_failure"],
    }


def _taxonomy(*, unclassified: list[str] | None = None, counts: dict[str, int] | None = None) -> dict:
    marker_counts = {marker: 2 for marker in gate_drift.GATE_MARKERS}
    if counts:
        marker_counts.update(counts)
    return {
        "generated_at": "2026-05-20T08:00:00+00:00",
        "taxonomy": {"gate_markers": list(gate_drift.GATE_MARKERS)},
        "collected": sum(marker_counts.values()),
        "marker_counts": marker_counts,
        "tests_by_marker": {marker: [f"tests/{marker}.py::test_ok"] for marker in gate_drift.GATE_MARKERS},
        "unclassified_tests": unclassified or [],
        "ambiguous_tests": [],
        "errors": [],
        "result": "PASS" if not unclassified else "FAIL",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_all_reports(report_dir: Path) -> None:
    marker_by_report = {
        "m3a_frontend_truth.json": "frontend_truth",
        "m3a_release_candidate.json": "m3a_truth",
        "m4_truth_report.json": "m4_truth",
        "m4a_auth_truth.json": "m4a_auth_truth",
        "m4b_upload_queue_truth.json": "m4b_upload_queue_truth",
        "m4c_lifecycle_retrieval_truth.json": "m4c_lifecycle_retrieval_truth",
        "m4e_backup_restore_truth.json": "m4e_backup_restore_truth",
        "masterplan_status.json": "governance_truth",
    }
    for filename, marker in marker_by_report.items():
        _write_json(report_dir / filename, _report(marker))


def _write_baseline(path: Path, report_dir: Path, taxonomy_path: Path) -> None:
    baseline = gate_drift.build_baseline(report_dir, taxonomy_path)
    _write_json(path, baseline)


def test_gate_drift_passes_for_current_reports_matching_baseline(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    taxonomy_path = report_dir / "truth_marker_taxonomy.json"
    baseline_path = report_dir / "gate_drift_baseline.json"
    _write_all_reports(report_dir)
    _write_json(taxonomy_path, _taxonomy())
    _write_baseline(baseline_path, report_dir, taxonomy_path)

    result = gate_drift.detect_gate_drift(
        report_dir=report_dir,
        taxonomy_path=taxonomy_path,
        baseline_path=baseline_path,
        docs=(),
        timestamp="2026-05-20T09:00:00+00:00",
    )

    assert result["result"] == "PASS"
    assert result["findings"] == []


def test_gate_drift_fails_when_report_contains_fewer_tests_than_baseline(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    taxonomy_path = report_dir / "truth_marker_taxonomy.json"
    baseline_path = report_dir / "gate_drift_baseline.json"
    _write_all_reports(report_dir)
    _write_json(taxonomy_path, _taxonomy())
    _write_baseline(baseline_path, report_dir, taxonomy_path)
    _write_json(report_dir / "m4a_auth_truth.json", _report("m4a_auth_truth", collected=1, passed=1))

    result = gate_drift.detect_gate_drift(
        report_dir=report_dir,
        taxonomy_path=taxonomy_path,
        baseline_path=baseline_path,
        docs=(),
        timestamp="2026-05-20T09:00:00+00:00",
    )

    assert result["result"] == "FAIL"
    assert any(finding["id"] == "GDD-REPORT-COLLECTED-REGRESSION" for finding in result["findings"])


def test_gate_drift_fails_for_unclassified_tests_and_marker_regression(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    taxonomy_path = report_dir / "truth_marker_taxonomy.json"
    baseline_path = report_dir / "gate_drift_baseline.json"
    _write_all_reports(report_dir)
    _write_json(taxonomy_path, _taxonomy())
    _write_baseline(baseline_path, report_dir, taxonomy_path)
    _write_json(
        taxonomy_path,
        _taxonomy(
            unclassified=["tests/test_new.py::test_without_marker"],
            counts={"m4a_auth_truth": 1},
        ),
    )

    result = gate_drift.detect_gate_drift(
        report_dir=report_dir,
        taxonomy_path=taxonomy_path,
        baseline_path=baseline_path,
        docs=(),
        timestamp="2026-05-20T09:00:00+00:00",
    )

    finding_ids = {finding["id"] for finding in result["findings"]}
    assert "GDD-UNCLASSIFIED-TESTS" in finding_ids
    assert "GDD-MARKER-COUNT-REGRESSION" in finding_ids


def test_gate_drift_fails_when_score_rises_despite_new_failures(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    taxonomy_path = report_dir / "truth_marker_taxonomy.json"
    baseline_path = report_dir / "gate_drift_baseline.json"
    _write_all_reports(report_dir)
    _write_json(taxonomy_path, _taxonomy())
    _write_json(report_dir / "m4b_upload_queue_truth.json", _report("m4b_upload_queue_truth", collected=10, passed=6))
    _write_baseline(baseline_path, report_dir, taxonomy_path)
    _write_json(
        report_dir / "m4b_upload_queue_truth.json",
        _report("m4b_upload_queue_truth", collected=10, passed=7, failed=1),
    )

    result = gate_drift.detect_gate_drift(
        report_dir=report_dir,
        taxonomy_path=taxonomy_path,
        baseline_path=baseline_path,
        docs=(),
        timestamp="2026-05-20T09:00:00+00:00",
    )

    assert any(finding["id"] == "GDD-SCORE-RISES-WITH-FAILURES" for finding in result["findings"])


def test_gate_drift_detects_documentation_references_to_stale_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    taxonomy_path = report_dir / "truth_marker_taxonomy.json"
    baseline_path = report_dir / "gate_drift_baseline.json"
    doc_path = tmp_path / "masterplan.md"
    _write_all_reports(report_dir)
    _write_json(taxonomy_path, _taxonomy())
    _write_baseline(baseline_path, report_dir, taxonomy_path)
    doc_path.write_text("M4 siehe reports/m4a_auth_truth.json\n", encoding="utf-8")

    result = gate_drift.detect_gate_drift(
        report_dir=report_dir,
        taxonomy_path=taxonomy_path,
        baseline_path=baseline_path,
        docs=(doc_path,),
        timestamp="2026-06-01T09:00:00+00:00",
        max_report_age_hours=24,
    )

    assert any(finding["id"] == "GDD-DOC-REFERENCES-STALE-REPORT" for finding in result["findings"])
