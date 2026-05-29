from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_m4_backend_release_candidate.py"
spec = importlib.util.spec_from_file_location("generate_m4_backend_release_candidate", SCRIPT_PATH)
assert spec is not None
rc = importlib.util.module_from_spec(spec)
sys.modules["generate_m4_backend_release_candidate"] = rc
assert spec.loader is not None
spec.loader.exec_module(rc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _truth_report(name: str, collected: int = 1) -> dict:
    return {
        "report_schema_version": 1,
        "report_name": name.removesuffix(".json"),
        "gate": name.removesuffix(".json"),
        "status": "PASS",
        "timestamp": "2026-05-29T08:00:00+00:00",
        "environment": "local",
        "report_type": "truth",
        "collected": collected,
        "passed": collected,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "blockers": [],
        "source_command": "test",
        "generated_by": "gate_validator",
    }


def _doc_lint(errors: int = 0) -> dict:
    status = "FAIL" if errors else "PASS"
    return {
        "report_schema_version": 1,
        "report_name": "documentation_truth_lint",
        "generated_by": "documentation_truth_linter",
        "timestamp": "2026-05-29T08:00:00+00:00",
        "status": status,
        "result": status,
        "summary": {"errors": errors, "warnings": 0},
    }


def _write_green_inputs(report_dir: Path) -> None:
    for name in rc.SPLIT_REPORTS:
        _write_json(report_dir / name, _truth_report(name))
    _write_json(report_dir / rc.AGGREGATE_REPORT, _truth_report(rc.AGGREGATE_REPORT, collected=4))
    _write_json(report_dir / rc.DOC_LINT_REPORT, _doc_lint())
    preflight = rc.build_report_truth_preflight(report_dir, timestamp="2026-05-29T08:00:00+00:00")
    _write_json(report_dir / rc.PREFLIGHT_REPORT, preflight)


def test_m4_backend_release_candidate_go_when_all_inputs_green(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc, "_commit_hash", lambda: "testsha")
    _write_green_inputs(tmp_path)

    payload = rc.build_release_candidate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["status"] == "PASS"
    assert payload["decision"]["go_no_go"] == "GO"
    assert payload["blockers"] == []


def test_m4_backend_release_candidate_blocks_zero_collected_split(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc, "_commit_hash", lambda: "testsha")
    _write_green_inputs(tmp_path)
    _write_json(tmp_path / "m4a_auth_truth.json", _truth_report("m4a_auth_truth.json", collected=0))

    payload = rc.build_release_candidate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["status"] == "FAIL"
    assert payload["decision"]["go_no_go"] == "NO-GO"
    assert any("collected must be > 0" in blocker["reason"] for blocker in payload["blockers"])


def test_m4_backend_release_candidate_blocks_documentation_lint_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc, "_commit_hash", lambda: "testsha")
    _write_green_inputs(tmp_path)
    _write_json(tmp_path / rc.DOC_LINT_REPORT, _doc_lint(errors=1))

    payload = rc.build_release_candidate(tmp_path, timestamp="2026-05-29T08:00:00+00:00")

    assert payload["status"] == "FAIL"
    assert payload["decision"]["go_no_go"] == "NO-GO"
    assert any("documentation lint has 1 error" in blocker["reason"] for blocker in payload["blockers"])
