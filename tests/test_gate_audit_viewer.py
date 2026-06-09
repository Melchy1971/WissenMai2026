from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "gate_audit_viewer.py"
spec = importlib.util.spec_from_file_location("gate_audit_viewer", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
gate_audit = importlib.util.module_from_spec(spec)
sys.modules["gate_audit_viewer"] = gate_audit
spec.loader.exec_module(gate_audit)


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_build_audit_log_extracts_gate_decision(tmp_path: Path) -> None:
    _write(
        tmp_path / "unit_gate.json",
        {
            "report_schema_version": 1,
            "report_name": "unit_gate",
            "report_type": "gate",
            "gate": "unit_gate",
            "generated_by": "test",
            "timestamp": "2026-06-09T10:00:00+00:00",
            "status": "PASS",
            "result": "PASS",
            "decision": {"go_no_go": "GO"},
            "blockers": [],
            "inputs": {"child": "reports/current/child_gate.json"},
        },
    )

    payload = gate_audit.build_audit_log(tmp_path, generated_at="2026-06-09T10:01:00Z")

    assert payload["status"] == "PASS"
    assert payload["summary"]["gate_decisions"] == 1
    entry = payload["entries"][0]
    assert entry["gate"] == "unit_gate"
    assert entry["decision"]["go_no_go"] == "GO"
    assert set(entry["report_sources"]) == {
        "reports/current/child_gate.json",
        str(tmp_path / "unit_gate.json"),
    }


def test_build_audit_log_extracts_parent_validation_child_gates(tmp_path: Path) -> None:
    _write(
        tmp_path / "parent_gate.json",
        {
            "report_schema_version": 1,
            "report_name": "parent_gate",
            "report_type": "gate",
            "gate": "parent_gate",
            "generated_by": "test",
            "timestamp": "2026-06-09T10:00:00+00:00",
            "status": "BLOCKED",
            "result": "BLOCKED",
            "decision": {"go_no_go": "NO_GO"},
            "blockers": [{"id": "child"}],
            "parent_gate_validation": {
                "report_name": "parent_gate_validation",
                "parent_gate": "parent",
                "timestamp": "2026-06-09T10:00:00+00:00",
                "status": "BLOCKED",
                "result": "BLOCKED",
                "decision": {"go_no_go": "NO_GO"},
                "child_results": {
                    "child": {
                        "child_gate_id": "child",
                        "validation_status": "BLOCKED",
                        "report": "reports/current/child.json",
                        "blockers": ["child blocked"],
                    }
                },
                "blockers": [{"id": "child"}],
            },
        },
    )

    payload = gate_audit.build_audit_log(tmp_path)

    assert payload["summary"]["gate_decisions"] == 2
    parent_entry = next(item for item in payload["entries"] if item["gate"] == "parent")
    assert parent_entry["source_report"].endswith("#parent_gate_validation")
    assert parent_entry["child_gates"] == [
        {
            "child_gate": "child",
            "status": "BLOCKED",
            "decision": None,
            "effect": None,
            "report": "reports/current/child.json",
            "blockers": ["child blocked"],
        }
    ]


def test_write_audit_log_writes_json(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    output = tmp_path / "gate_audit_log.json"
    _write(
        report_dir / "unit_gate.json",
        {
            "report_name": "unit_gate",
            "report_type": "gate",
            "timestamp": "2026-06-09T10:00:00+00:00",
            "status": "PASS",
            "decision": {"go_no_go": "GO"},
            "blockers": [],
        },
    )

    payload = gate_audit.write_audit_log(output, report_dir=report_dir)

    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == payload
