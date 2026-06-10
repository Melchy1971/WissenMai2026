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


def _write_required_set(path: Path, report_dir: Path) -> None:
    def report(name: str) -> str:
        return (report_dir / name).as_posix()

    _write(path, {
        "schema_version": 1,
        "max_age_hours": 168,
        "required_reports": [
            {
                "id": "m5a_start_gate",
                "file": report("m5a_start_gate.json"),
                "accepted_statuses": ["PASS"],
                "required_decision": "GO",
                "counter_validation": "required",
            },
            {
                "id": "data_quality_report",
                "file": report("data_quality_report.json"),
                "accepted_statuses": ["COMPLETED"],
                "min_quality_score": 90,
            },
        ],
        "supporting_reports": [
            {
                "id": "masterplan_status",
                "file": report("masterplan_status.json"),
                "referenced_by_parent_gate": True,
                "accepted_statuses": ["PASS"],
            }
        ],
        "optional_reports": [
            {"id": "optional", "file": report("optional.json"), "accepted_statuses": ["PASS"]}
        ],
        "legacy_reports": [
            {
                "id": "legacy",
                "file": report("legacy.json"),
                "reason": "superseded",
            }
        ],
    })


def _write_scope_reports(report_dir: Path) -> None:
    reports = {
        "m5a_start_gate.json": _gate("m5a_start_gate"),
        "data_quality_report.json": _data_quality(),
        "masterplan_status.json": _gate("masterplan_status"),
        "optional.json": _supporting("optional", status="PASS"),
        "legacy.json": _supporting("legacy", status="PASS"),
    }
    for filename, payload in reports.items():
        _write(report_dir / filename, payload)


def test_report_integrity_v2_passes_green_current_scope(tmp_path: Path) -> None:
    required_set = tmp_path / "required_set.json"
    _write_required_set(required_set, tmp_path)
    _write_scope_reports(tmp_path)

    payload = integrity.build_report(
        tmp_path,
        required_set_path=required_set,
        timestamp="2026-06-08T10:00:00+00:00",
        archive_legacy=True,
    )

    assert payload["status"] == "PASS"
    assert payload["blocker_details"] == []
    assert payload["summary"]["archived_count"] == 1
    assert not (tmp_path / "legacy.json").exists()


def test_report_integrity_v2_blocks_invalid_json(tmp_path: Path) -> None:
    required_set = tmp_path / "required_set.json"
    _write_required_set(required_set, tmp_path)
    _write_scope_reports(tmp_path)
    (tmp_path / "m5a_start_gate.json").write_text("{", encoding="utf-8")

    payload = integrity.build_report(
        tmp_path,
        required_set_path=required_set,
        timestamp="2026-06-08T10:00:00+00:00",
    )

    assert payload["status"] == "BLOCKED"
    assert any(item["check"] == "presence_json" for item in payload["blocker_details"])
    assert any("Regenerate" in item["action"] and "archive" in item["action"] for item in payload["repair_actions"])


def test_report_integrity_v2_blocks_stale_required_report(tmp_path: Path) -> None:
    required_set = tmp_path / "required_set.json"
    _write_required_set(required_set, tmp_path)
    _write_scope_reports(tmp_path)

    payload = integrity.build_report(
        tmp_path,
        required_set_path=required_set,
        timestamp="2026-06-20T10:00:00+00:00",
    )

    assert payload["status"] == "BLOCKED"
    assert any("older than 168 hours" in item["detail"] for item in payload["blocker_details"])


def test_report_integrity_v2_blocks_parent_referenced_supporting(tmp_path: Path) -> None:
    required_set = tmp_path / "required_set.json"
    _write_required_set(required_set, tmp_path)
    _write_scope_reports(tmp_path)
    broken = _gate("masterplan_status")
    broken.pop("generated_by")
    _write(tmp_path / "masterplan_status.json", broken)

    payload = integrity.build_report(
        tmp_path,
        required_set_path=required_set,
        timestamp="2026-06-08T10:00:00+00:00",
    )

    assert payload["status"] == "BLOCKED"
    assert any(item["category"] == "supporting" for item in payload["blocker_details"])


def test_report_integrity_v2_warns_on_optional_invalid(tmp_path: Path) -> None:
    required_set = tmp_path / "required_set.json"
    _write_required_set(required_set, tmp_path)
    _write_scope_reports(tmp_path)
    (tmp_path / "optional.json").write_text("{", encoding="utf-8")

    payload = integrity.build_report(
        tmp_path,
        required_set_path=required_set,
        timestamp="2026-06-08T10:00:00+00:00",
    )

    assert payload["status"] == "PASS"
    assert payload["blocker_details"] == []
    assert any(item["category"] == "optional" for item in payload["warnings"])
