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
            "m4_truth": ["tests/test_m4.py::test_ok", "tests/test_m4.py::test_fail"],
            "m5_truth": ["tests/test_m5.py::test_error"],
        },
        outcomes={
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
        path.name for path in split_reports.REPORT_PATHS.values()
    )
    payload = json.loads((tmp_path / "m4b_upload_queue_truth.json").read_text(encoding="utf-8"))
    assert payload["marker"] == "m4b_upload_queue_truth"
    assert payload["collected"] == 0
    assert payload["status"] == "FAIL"
    assert payload["exit_code"] == 1


def test_unmarked_truth_tests_make_split_reports_fail() -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={"m4_truth": ["tests/test_m4.py::test_ok"]},
        outcomes={
            "tests/test_m4.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/test_m4.py::test_ok",
            ),
        },
        collect_errors=[],
        unmarked_truth_tests=["tests/postgres_truth/test_unmarked.py::test_truth"],
        ambiguous_truth_tests=[],
        exit_code=1,
        test_database_url_set=True,
        timestamp="2026-05-20T08:00:00+00:00",
    )

    assert reports["m4_truth"]["errors"] == 1
    assert reports["m4_truth"]["unmarked_truth_tests"] == ["tests/postgres_truth/test_unmarked.py::test_truth"]


def test_m4b_zero_tests_collected_writes_fail_report() -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={"m4b_upload_queue_truth": []},
        outcomes={},
        collect_errors=[],
        exit_code=0,
        test_database_url_set=True,
        timestamp="2026-05-27T08:00:00+00:00",
    )

    report = reports["m4b_upload_queue_truth"]

    assert report["report_schema_version"] == 1
    assert report["report_name"] == "m4b_upload_queue_truth"
    assert report["generated_by"] == "gate_validator"
    assert report["status"] == "FAIL"
    assert report["collected"] == 0
    assert report["failed"] == 0
    assert report["errors"] == 0
    assert report["skipped"] == 0
    assert report["exit_code"] == 1


def test_m4b_five_passed_writes_pass_report() -> None:
    test_ids = [f"tests/postgres_truth/test_m4b.py::test_{index}" for index in range(5)]
    reports = split_reports.build_split_reports(
        collected_by_marker={"m4b_upload_queue_truth": test_ids},
        outcomes={
            test_id: split_reports.TestOutcome(status="passed", nodeid=test_id)
            for test_id in test_ids
        },
        collect_errors=[],
        exit_code=0,
        test_database_url_set=True,
        timestamp="2026-05-27T08:00:00+00:00",
    )

    report = reports["m4b_upload_queue_truth"]

    assert report["status"] == "PASS"
    assert report["collected"] == 5
    assert report["passed"] == 5
    assert report["failed"] == 0
    assert report["errors"] == 0
    assert report["skipped"] == 0
    assert report["exit_code"] == 0


def test_m4b_one_failed_writes_fail_report() -> None:
    test_ids = [f"tests/postgres_truth/test_m4b.py::test_{index}" for index in range(5)]
    outcomes = {
        test_id: split_reports.TestOutcome(status="passed", nodeid=test_id)
        for test_id in test_ids
    }
    outcomes[test_ids[-1]] = split_reports.TestOutcome(status="failed", nodeid=test_ids[-1])

    reports = split_reports.build_split_reports(
        collected_by_marker={"m4b_upload_queue_truth": test_ids},
        outcomes=outcomes,
        collect_errors=[],
        exit_code=1,
        test_database_url_set=True,
        timestamp="2026-05-27T08:00:00+00:00",
    )

    report = reports["m4b_upload_queue_truth"]

    assert report["status"] == "FAIL"
    assert report["collected"] == 5
    assert report["passed"] == 4
    assert report["failed"] == 1
    assert report["failed_tests"] == [test_ids[-1]]
    assert report["exit_code"] == 1


def test_m4b_write_exception_retries_with_fail_report(tmp_path: Path, monkeypatch) -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={"m4b_upload_queue_truth": ["tests/postgres_truth/test_m4b.py::test_ok"]},
        outcomes={
            "tests/postgres_truth/test_m4b.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/postgres_truth/test_m4b.py::test_ok",
            )
        },
        collect_errors=[],
        exit_code=0,
        test_database_url_set=True,
        timestamp="2026-05-27T08:00:00+00:00",
    )
    original_write_text = Path.write_text
    failed_once = {"value": False}

    def flaky_write_text(self, data, *args, **kwargs):
        if self.name == "m4b_upload_queue_truth.json" and not failed_once["value"]:
            failed_once["value"] = True
            raise OSError("disk full during m4b write")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    split_reports.write_split_reports(reports, tmp_path)

    payload = json.loads((tmp_path / "m4b_upload_queue_truth.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAIL"
    assert payload["errors"] == 1
    assert payload["exit_code"] == 1
    assert payload["write_error"] == "disk full during m4b write"


def test_m4b_report_json_is_always_valid(tmp_path: Path) -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={"m4b_upload_queue_truth": ["tests/postgres_truth/test_m4b.py::test_ok"]},
        outcomes={
            "tests/postgres_truth/test_m4b.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/postgres_truth/test_m4b.py::test_ok",
            )
        },
        collect_errors=[],
        exit_code=0,
        test_database_url_set=True,
        timestamp="2026-05-27T08:00:00+00:00",
    )

    split_reports.write_split_reports(reports, tmp_path)

    payload = json.loads((tmp_path / "m4b_upload_queue_truth.json").read_text(encoding="utf-8"))
    assert payload["report_schema_version"] == 1
    assert payload["generated_by"] == "gate_validator"
    assert payload["status"] == "PASS"


def test_write_marker_report_writes_only_m4b(tmp_path: Path) -> None:
    reports = split_reports.build_split_reports(
        collected_by_marker={"m4b_upload_queue_truth": ["tests/postgres_truth/test_m4b.py::test_ok"]},
        outcomes={
            "tests/postgres_truth/test_m4b.py::test_ok": split_reports.TestOutcome(
                status="passed",
                nodeid="tests/postgres_truth/test_m4b.py::test_ok",
            )
        },
        collect_errors=[],
        exit_code=0,
        test_database_url_set=True,
        timestamp="2026-05-27T08:00:00+00:00",
    )

    path = split_reports.write_marker_report("m4b_upload_queue_truth", reports, tmp_path)

    assert path == tmp_path / "m4b_upload_queue_truth.json"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["m4b_upload_queue_truth.json"]


def test_selected_report_markers_detects_single_marker_expression() -> None:
    selected = split_reports._selected_report_markers(["-m", "m4a_auth_truth", "-q"])

    assert selected == {"m4a_auth_truth"}


def test_selected_report_markers_detects_multiple_marker_expression() -> None:
    selected = split_reports._selected_report_markers([
        "backend/tests",
        "--markexpr=m4a_auth_truth or m4b_upload_queue_truth",
        "-q",
    ])

    assert selected == {"m4a_auth_truth", "m4b_upload_queue_truth"}


def test_m4_split_marker_args_expand_single_marker_to_all_m4_splits() -> None:
    pytest_args = split_reports._expand_m4_split_marker_args([
        "backend/tests",
        "-m",
        "m4b_upload_queue_truth",
        "-q",
    ])

    selected = split_reports._selected_report_markers(pytest_args)

    assert selected == set(split_reports.M4_SPLIT_REPORT_MARKERS)


def test_m4_split_selected_run_writes_all_current_m4_reports(tmp_path: Path) -> None:
    collected_by_marker = {
        marker: [f"tests/postgres_truth/{marker}.py::test_ok"]
        for marker in split_reports.M4_SPLIT_REPORT_MARKERS
    }
    outcomes = {
        test_id: split_reports.TestOutcome(status="passed", nodeid=test_id)
        for test_ids in collected_by_marker.values()
        for test_id in test_ids
    }
    reports = split_reports.build_split_reports(
        collected_by_marker=collected_by_marker,
        outcomes=outcomes,
        collect_errors=[],
        exit_code=0,
        test_database_url_set=True,
        timestamp="2026-05-29T08:00:00+00:00",
    )
    pytest_args = split_reports._expand_m4_split_marker_args(["-m", "m4b_upload_queue_truth"])
    selected = split_reports._selected_report_markers(pytest_args)
    assert selected is not None

    written = [split_reports.write_marker_report(marker, reports, tmp_path) for marker in sorted(selected)]

    assert sorted(path.name for path in written) == [
        "m4a_auth_truth.json",
        "m4b_upload_queue_truth.json",
        "m4c_lifecycle_retrieval_truth.json",
        "m4e_backup_restore_truth.json",
    ]
    for marker in split_reports.M4_SPLIT_REPORT_MARKERS:
        payload = json.loads((tmp_path / f"{marker}.json").read_text(encoding="utf-8"))
        assert payload["status"] == "PASS"
        assert payload["collected"] == 1


def test_with_default_test_target_prepends_target_for_marker_only_args() -> None:
    pytest_args = split_reports._with_default_test_target(["-m", "m4c_lifecycle_retrieval_truth", "-q"])

    assert pytest_args[0] == str(split_reports.DEFAULT_TEST_TARGET)
    assert pytest_args[1:] == ["-m", "m4c_lifecycle_retrieval_truth", "-q"]


def test_with_default_test_target_preserves_explicit_target() -> None:
    pytest_args = split_reports._with_default_test_target(["backend/tests", "-m", "m4a_auth_truth"])

    assert pytest_args == ["backend/tests", "-m", "m4a_auth_truth"]
