from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_data_quality.py"
spec = importlib.util.spec_from_file_location("run_data_quality", SCRIPT_PATH)
assert spec is not None
producer = importlib.util.module_from_spec(spec)
sys.modules["run_data_quality"] = producer
assert spec.loader is not None
spec.loader.exec_module(producer)


def _run_data() -> dict:
    return {
        "run_id": "run-1",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "status": "completed",
        "started_at": "2026-06-02T10:00:00+00:00",
        "finished_at": "2026-06-02T10:00:01+00:00",
        "total_documents": 12,
        "total_findings": 5,
        "quality_score": 87.5,
        "score_explanation": {"score": 87.5},
        "findings": [
            {"finding_type": "DUPLICATE_DOCUMENT", "severity": "warning"},
            {"finding_type": "MISSING_METADATA", "severity": "warning"},
            {"finding_type": "INVALID_LIFECYCLE", "severity": "error"},
            {"finding_type": "INVALID_SOURCE_STATUS", "severity": "error"},
            {"finding_type": "ORPHAN_CHUNK", "severity": "warning"},
        ],
    }


def test_build_report_payload_contains_v2_required_fields() -> None:
    payload = producer._build_report_payload(
        _run_data(),
        generated_at="2026-06-02T10:00:02+00:00",
    )

    assert payload["report_schema_version"] == 2
    assert payload["report_name"] == "data_quality_report"
    assert payload["generated_by"] == "run_data_quality_cli"
    assert payload["timestamp"] == "2026-06-02T10:00:02+00:00"
    assert payload["total_documents"] == 12
    assert payload["duplicate_findings"] == 1
    assert payload["metadata_findings"] == 1
    assert payload["lifecycle_findings"] == 1
    assert payload["source_status_findings"] == 1
    assert payload["orphan_findings"] == 1
    assert payload["quality_score"] == 87.5
    assert payload["findings_by_severity"] == {"warning": 3, "error": 2}
    assert payload["findings_by_type"]["INVALID_SOURCE_STATUS"] == 1


def test_write_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    json_path = tmp_path / "data_quality_report.json"
    md_path = tmp_path / "data_quality_report.md"

    producer._write_report(_run_data(), json_path, md_path)

    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    assert parsed["report_schema_version"] == 2
    assert parsed["orphan_findings"] == 1
    assert "# Data Quality Report V2" in markdown
    assert "| total_documents | 12 |" in markdown
