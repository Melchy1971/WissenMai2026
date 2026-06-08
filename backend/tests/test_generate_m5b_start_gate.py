from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_m5b_start_gate.py"
spec = importlib.util.spec_from_file_location("generate_m5b_start_gate", SCRIPT_PATH)
assert spec is not None
generator = importlib.util.module_from_spec(spec)
sys.modules["generate_m5b_start_gate"] = generator
assert spec.loader is not None
spec.loader.exec_module(generator)

pytestmark = pytest.mark.m3a_truth


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _m5a_gate(status: str = "PASS", decision: str = "GO") -> dict:
    return {
        "report_schema_version": 1,
        "report_name": "m5a_data_quality_gate",
        "generated_by": "gate_validator",
        "status": status,
        "result": status,
        "decision": {"go_no_go": decision, "result": decision},
        "timestamp": "2026-06-05T10:00:00+00:00",
        "collected": 1,
        "passed": 1 if status == "PASS" else 0,
        "failed": 0 if status == "PASS" else 1,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "blockers": [],
    }


def _retrieval_baseline() -> dict:
    return {
        "report_name": "retrieval_quality_baseline_report",
        "generated_by": "gate_validator",
        "status": "WARN",
        "result": "WARN",
        "timestamp": "2026-06-05T10:00:00+00:00",
        "decision": {
            "go_no_go": "NO_GO",
            "baseline_release_grade": False,
            "requires_golden_retrieval_benchmark": True,
        },
    }


def _doc_lint() -> dict:
    return {
        "report_name": "documentation_truth_lint",
        "generated_by": "documentation_truth_linter",
        "status": "PASS",
        "result": "PASS",
        "timestamp": "2026-06-05T10:00:00+00:00",
        "summary": {"errors": 0, "warnings": 0},
        "exit_code": 0,
    }


def _write_inputs(report_dir: Path, *, m5a_status: str = "PASS", decision: str = "GO") -> None:
    _write(report_dir / generator.M5A_DATA_QUALITY_GATE, _m5a_gate(m5a_status, decision))
    _write(report_dir / generator.RETRIEVAL_BASELINE, _retrieval_baseline())
    _write(report_dir / generator.DOCUMENTATION_TRUTH_LINT, _doc_lint())


def test_m5b_start_gate_blocks_until_m5a_pass(tmp_path: Path) -> None:
    _write_inputs(tmp_path, m5a_status="BLOCKED", decision="NO_GO")

    payload = generator.build_m5b_start_gate(tmp_path, timestamp="2026-06-05T10:00:00+00:00")

    assert payload["status"] == "BLOCKED"
    assert payload["decision"]["m5b_preparation_allowed"] is False
    assert payload["blockers"][0]["id"] == "M5A_PARENT_GATE_NOT_PASSED"


def test_m5b_start_gate_prepared_after_m5a_pass_but_no_implementation(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    payload = generator.build_m5b_start_gate(tmp_path, timestamp="2026-06-05T10:00:00+00:00")

    assert payload["status"] == "PREPARED"
    assert payload["blockers"] == []
    assert payload["decision"]["m5b_preparation_allowed"] is True
    assert payload["decision"]["m5b_implementation_allowed"] is False
    assert payload["decision"]["m5b_implementation_gate_required"] is True
    assert any(blocker["id"] == "M5B_IMPLEMENTATION_GATE_REQUIRED" for blocker in payload["implementation_blockers"])
