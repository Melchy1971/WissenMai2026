from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_truth_split_reports.py"
spec = importlib.util.spec_from_file_location("generate_truth_split_reports", SCRIPT_PATH)
assert spec is not None
split_reports = importlib.util.module_from_spec(spec)
sys.modules["generate_truth_split_reports"] = split_reports
assert spec.loader is not None
spec.loader.exec_module(split_reports)


def test_build_split_reports_emits_required_report_format_for_each_gate() -> None:
    timestamp = "2026-05-20T08:00:00+00:00"
    reports = split_reports.build_split_reports(
        collected_by_marker={
            "frontend_truth": ["tests/test_contract.py::test_ok"],
            "m4_truth": ["tests/test_m4.py::test_ok", "tests/test_m4.py::test_fail"],
            "m5_truth": ["tests/test_m5.py::test_error"],
        },
        outcomes={
            "tests/test_contract.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/test_contract.py::test_ok",
            ),
            "tests/test_m4.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/test_m4.py::test_ok",
            ),
            "tests/test_m4.py::test_fail": split_reports.TestOutcome(
                status="failed",
                nodeid="tests/test_m4.py::test_fail",
            ),
            "tests/test_m5.py::test_error": split_reports.TestOutcome(
                status="error",
                nodeid="tests/test_m5.py::test_error",
            ),
        },
        collect_errors=[],
        exit_code=1,
        test_database_url_set=True,
        timestamp=timestamp,
    )

    assert set(reports) == set(split_reports.REPORT_MARKERS)
    for marker, report in reports.items():
        assert report["marker"] == marker
        assert report["timestamp"] == timestamp
        assert set(report) >= {
            "collected",
            "passed",
            "failed",
            "errors",
            "skipped",
            "exit_code",
            "test_database_url_set",
            "failed_tests",
            "timestamp",
        }

    assert reports["frontend_truth"]["collected"] == 1
    assert reports["frontend_truth"]["passed"] == 1
    assert reports["m4_truth"]["collected"] == 2
    assert reports["m4_truth"]["failed"] == 1
    assert reports["m4_truth"]["failed_tests"] == ["tests/test_m4.py::test_fail"]
    assert reports["m5_truth"]["errors"] == 1


def test_split_reports_do_not_leak_other_gate_failures() -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={
            "m4_truth": ["tests/test_m4.py::test_ok"],
            "governance_truth": ["tests/test_governance.py::test_fail"],
        },
        outcomes={
            "tests/test_m4.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/test_m4.py::test_ok",
            ),
            "tests/test_governance.py::test_fail": split_reports.TestOutcome(
                status="failed",
                nodeid="tests/test_governance.py::test_fail",
            ),
        },
        collect_errors=[],
        exit_code=1,
        test_database_url_set=False,
        timestamp="2026-05-20T08:00:00+00:00",
    )

    assert reports["m4_truth"]["passed"] == 1
    assert reports["m4_truth"]["failed"] == 0
    assert reports["m4_truth"]["failed_tests"] == []
    assert reports["governance_truth"]["failed"] == 1
    assert reports["governance_truth"]["failed_tests"] == ["tests/test_governance.py::test_fail"]


def test_write_split_reports_creates_one_json_file_per_report_marker(tmp_path: Path) -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={},
        outcomes={},
        collect_errors=[],
        exit_code=0,
        test_database_url_set=False,
        timestamp="2026-05-20T08:00:00+00:00",
    )

    written = split_reports.write_split_reports(reports, tmp_path)

    assert sorted(path.name for path in written) == sorted(
        f"{marker}_report.json" for marker in split_reports.REPORT_MARKERS
    )
    payload = json.loads((tmp_path / "m4_truth_report.json").read_text(encoding="utf-8"))
    assert payload["marker"] == "m4_truth"
    assert payload["collected"] == 0
    assert payload["exit_code"] == 0
