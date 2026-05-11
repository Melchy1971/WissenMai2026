from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "postgres_truth_report.json"


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"missing report: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON report: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("report root must be a JSON object")
    return payload


def _validate(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    if report.get("test_database_url_set") is not True:
        failures.append("test_database_url_set must be true")

    if report.get("skipped") != 0:
        failures.append(f"skipped must be 0, got {report.get('skipped')!r}")

    if report.get("failed") != 0:
        failures.append(f"failed must be 0, got {report.get('failed')!r}")

    passed = report.get("passed")
    if not isinstance(passed, int) or passed <= 0:
        failures.append(f"passed must be > 0, got {passed!r}")

    if report.get("pytest_exit_code") != 0:
        failures.append(f"pytest_exit_code must be 0, got {report.get('pytest_exit_code')!r}")

    return failures


def main() -> int:
    try:
        report = _load_report(REPORT_PATH)
    except ValueError as exc:
        print("M4 Truth Gate = FAIL")
        print(f"- {exc}")
        return 1

    failures = _validate(report)
    if failures:
        print("M4 Truth Gate = FAIL")
        print(f"Report: {REPORT_PATH}")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("M4 Truth Gate = PASS")
    print(f"Report: {REPORT_PATH}")
    print(f"passed={report.get('passed')} failed={report.get('failed')} skipped={report.get('skipped')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
