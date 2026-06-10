from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_validator():
    path = SCRIPTS_DIR / "validate_limitation_evidence.py"
    spec = importlib.util.spec_from_file_location("validate_limitation_evidence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_limitation_evidence"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _known_payload(limitation: dict[str, object]) -> dict[str, object]:
    return {
        "report_schema_version": 1,
        "report_name": "known_limitations",
        "generated_by": "gate_validator",
        "timestamp": "2026-06-10T10:00:00+00:00",
        "status": "INFO",
        "limitations": [limitation],
    }


def _codes(report: dict[str, object]) -> set[str]:
    return {str(issue["code"]) for issue in report["issues"]}  # type: ignore[index]


def test_open_blocking_limitation_accepts_valid_evidence_without_owner(tmp_path: Path) -> None:
    _write_json(tmp_path / "reports/current/evidence.json", {
        "report_name": "unit_gate",
        "status": "BLOCKED",
        "result": "BLOCKED",
    })
    _write_json(tmp_path / "reports/current/known_limitations.json", _known_payload({
        "id": "KL-TEST-001",
        "status": "open",
        "severity": "high",
        "blocks_gate": ["m5_truth_gate"],
        "target_phase": "M5A",
        "evidence_report": "reports/current/evidence.json",
        "next_action": "Regenerate the truth gate.",
    }))

    report = validator.validate(tmp_path / "reports/current/known_limitations.json", repo_root=tmp_path)

    assert report["status"] == "PASS"
    assert report["summary"]["issues"] == 0


def test_missing_open_blocking_evidence_is_reported(tmp_path: Path) -> None:
    _write_json(tmp_path / "reports/current/known_limitations.json", _known_payload({
        "id": "KL-TEST-001",
        "status": "open",
        "severity": "high",
        "blocks_gate": ["m5_truth_gate"],
        "target_phase": "M5A",
        "next_action": "Regenerate the truth gate.",
    }))

    report = validator.validate(tmp_path / "reports/current/known_limitations.json", repo_root=tmp_path)

    assert report["status"] == "FAIL"
    assert "missing_required_field" in _codes(report)
    assert "missing_evidence_report" in _codes(report)
    assert report["summary"]["missing_evidence_count"] == 2


def test_evidence_report_must_be_valid_json_for_open_blocker(tmp_path: Path) -> None:
    evidence = tmp_path / "reports/current/evidence.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("{not-json", encoding="utf-8")
    _write_json(tmp_path / "reports/current/known_limitations.json", _known_payload({
        "id": "KL-TEST-001",
        "status": "open",
        "severity": "high",
        "blocks_gate": ["m5_truth_gate"],
        "target_phase": "M5A",
        "evidence_report": "reports/current/evidence.json",
        "next_action": "Regenerate the truth gate.",
    }))

    report = validator.validate(tmp_path / "reports/current/known_limitations.json", repo_root=tmp_path)

    assert "evidence_report_not_json" in _codes(report)


def test_open_blocking_evidence_status_must_match_limitation(tmp_path: Path) -> None:
    _write_json(tmp_path / "reports/current/evidence.json", {
        "report_name": "unit_gate",
        "status": "PASS",
        "result": "PASS",
    })
    _write_json(tmp_path / "reports/current/known_limitations.json", _known_payload({
        "id": "KL-TEST-001",
        "status": "open",
        "severity": "high",
        "blocks_gate": ["m5_truth_gate"],
        "target_phase": "M5A",
        "evidence_report": "reports/current/evidence.json",
        "next_action": "Regenerate the truth gate.",
    }))

    report = validator.validate(tmp_path / "reports/current/known_limitations.json", repo_root=tmp_path)

    assert "report_status_mismatch" in _codes(report)


def test_resolved_limitation_requires_resolution_evidence(tmp_path: Path) -> None:
    _write_json(tmp_path / "reports/current/known_limitations.json", _known_payload({
        "id": "KL-TEST-001",
        "status": "resolved",
        "severity": "high",
        "blocks_gate": [],
        "target_phase": "M5A",
        "evidence_report": "reports/current/evidence.json",
        "next_action": "No action.",
    }))

    report = validator.validate(tmp_path / "reports/current/known_limitations.json", repo_root=tmp_path)

    assert "missing_resolved_field" in _codes(report)


def test_blocks_gate_must_match_target_phase(tmp_path: Path) -> None:
    _write_json(tmp_path / "reports/current/evidence.json", {
        "report_name": "unit_gate",
        "status": "BLOCKED",
    })
    _write_json(tmp_path / "reports/current/known_limitations.json", _known_payload({
        "id": "KL-TEST-001",
        "status": "open",
        "severity": "high",
        "blocks_gate": ["m5b_start_gate"],
        "target_phase": "M5A",
        "evidence_report": "reports/current/evidence.json",
        "next_action": "Regenerate the truth gate.",
    }))

    report = validator.validate(tmp_path / "reports/current/known_limitations.json", repo_root=tmp_path)

    assert "blocks_gate_mapping_mismatch" in _codes(report)
