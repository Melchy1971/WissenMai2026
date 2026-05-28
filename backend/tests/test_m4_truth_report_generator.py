from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.m3a_truth


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_m4_truth_report.py"
spec = importlib.util.spec_from_file_location("generate_m4_truth_report", SCRIPT_PATH)
assert spec is not None
m4_report = importlib.util.module_from_spec(spec)
sys.modules["generate_m4_truth_report"] = m4_report
assert spec.loader is not None
spec.loader.exec_module(m4_report)


def _write_split_report(report_dir: Path, name: str, *, collected: int, timestamp: str) -> None:
    payload = {
        "report_schema_version": 1,
        "report_name": name.removesuffix(".json"),
        "gate": name.split("_", 1)[0],
        "status": "PASS",
        "timestamp": timestamp,
        "environment": "local",
        "report_type": "truth",
        "collected": collected,
        "passed": collected,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0,
        "failed_tests": [],
        "generated_by": "gate_validator",
    }
    (report_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def _write_all_split_reports(report_dir: Path, *, collected: int = 1, timestamp: str = "2026-05-28T00:00:00Z") -> None:
    for name in m4_report.SUB_REPORTS:
        _write_split_report(report_dir, name, collected=collected, timestamp=timestamp)


def test_m4_truth_report_passes_when_all_split_reports_are_current_and_green(tmp_path: Path, monkeypatch) -> None:
    _write_all_split_reports(tmp_path)
    monkeypatch.setattr(m4_report, "CURRENT_DIR", tmp_path)
    monkeypatch.setattr(m4_report, "_commit_hash", lambda: "testsha")

    report = m4_report.build_report(now=datetime(2026, 5, 28, tzinfo=UTC))

    assert report["status"] == "PASS"
    assert report["collected"] == 4
    assert report["passed"] == 4
    assert report["decision"]["go_no_go"] == "GO"


def test_m4_truth_report_fails_zero_collected_component(tmp_path: Path, monkeypatch) -> None:
    _write_all_split_reports(tmp_path)
    _write_split_report(tmp_path, "m4a_auth_truth.json", collected=0, timestamp="2026-05-28T00:00:00Z")
    monkeypatch.setattr(m4_report, "CURRENT_DIR", tmp_path)
    monkeypatch.setattr(m4_report, "_commit_hash", lambda: "testsha")

    report = m4_report.build_report(now=datetime(2026, 5, 28, tzinfo=UTC))

    assert report["status"] == "FAIL"
    assert report["decision"]["go_no_go"] == "NO-GO"
    assert any("collected must be > 0" in blocker["reason"] for blocker in report["blockers"])


def test_m4_truth_report_fails_stale_component(tmp_path: Path, monkeypatch) -> None:
    _write_all_split_reports(tmp_path, timestamp="2026-01-01T00:00:00Z")
    monkeypatch.setattr(m4_report, "CURRENT_DIR", tmp_path)
    monkeypatch.setattr(m4_report, "_commit_hash", lambda: "testsha")

    report = m4_report.build_report(now=datetime(2026, 5, 28, tzinfo=UTC))

    assert report["status"] == "FAIL"
    assert any("stale" in blocker["reason"] for blocker in report["blockers"])
