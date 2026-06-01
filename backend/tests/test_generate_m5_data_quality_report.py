from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_m5_data_quality_report.py"
spec = importlib.util.spec_from_file_location("generate_m5_data_quality_report", SCRIPT_PATH)
assert spec is not None
producer = importlib.util.module_from_spec(spec)
sys.modules["generate_m5_data_quality_report"] = producer
assert spec.loader is not None
spec.loader.exec_module(producer)


def test_success_payload_marks_pass_when_score_ge_threshold() -> None:
    payload = producer._success_payload(
        workspace_id="00000000-0000-0000-0000-000000000001",
        run_data={
            "run_id": "run-1",
            "status": "completed",
            "started_at": "2026-06-01T00:00:00+00:00",
            "finished_at": "2026-06-01T00:00:01+00:00",
            "total_findings": 0,
            "quality_score": 95.0,
            "findings": [],
        },
        threshold=80.0,
    )

    assert payload["status"] == "PASS"
    assert payload["decision"]["go_no_go"] == "GO"
    assert payload["collected"] == 1
    assert payload["passed"] == 1


def test_failure_payload_has_error_counter() -> None:
    payload = producer._failure_payload(
        workspace_id="00000000-0000-0000-0000-000000000001",
        reason="Workspace not found",
    )

    assert payload["status"] == "FAIL"
    assert payload["errors"] == 1
    assert payload["exit_code"] == 2
    assert payload["decision"]["go_no_go"] == "NO_GO"


def test_atomic_write_produces_valid_json(tmp_path: Path) -> None:
    target = tmp_path / "m5_data_quality_report.json"
    payload = producer._failure_payload(
        workspace_id="00000000-0000-0000-0000-000000000001",
        reason="simulated",
    )

    producer._write_atomic_json(target, payload)

    parsed = json.loads(target.read_text(encoding="utf-8"))
    assert parsed["report_name"] == "m5_data_quality_report"
    assert parsed["status"] == "FAIL"
