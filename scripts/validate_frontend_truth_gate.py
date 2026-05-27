from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "current" / "m3a_frontend_truth.json"


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

    required_fields = (
        "collected",
        "passed",
        "failed",
        "skipped",
        "browser",
        "api_base_url",
        "test_database_url_set",
        "duration",
        "failed_flows",
        "timestamp",
    )
    for field in required_fields:
        if field not in report:
            failures.append(f"[schema] missing required field: {field}")

    collected = report.get("collected")
    passed = report.get("passed")
    failed = report.get("failed")
    skipped = report.get("skipped")

    if not isinstance(collected, int) or collected <= 0:
        failures.append(f"[truth] collected must be a positive integer, got {collected!r}")
    if not isinstance(passed, int) or passed <= 0:
        failures.append(f"[truth] passed must be a positive integer, got {passed!r}")
    if isinstance(collected, int) and isinstance(passed, int) and passed != collected:
        failures.append(f"[truth] passed ({passed}) must equal collected ({collected})")
    if failed != 0:
        failures.append(f"[truth] failed must be 0, got {failed!r}")
    if skipped != 0:
        failures.append(f"[truth] skipped must be 0, got {skipped!r}")

    if report.get("test_database_url_set") is not True:
        failures.append("[truth] test_database_url_set must be true; no real PostgreSQL proof")

    api_base_url = report.get("api_base_url")
    if not isinstance(api_base_url, str) or not api_base_url.startswith(("http://", "https://")):
        failures.append(f"[truth] api_base_url must be an absolute URL, got {api_base_url!r}")

    if not report.get("browser"):
        failures.append("[truth] browser must be populated")

    if not isinstance(report.get("duration"), (int, float)) or report.get("duration") <= 0:
        failures.append(f"[truth] duration must be > 0, got {report.get('duration')!r}")

    if not isinstance(report.get("failed_flows"), list):
        failures.append("[schema] failed_flows must be a list")
    elif report.get("failed_flows"):
        failures.append(f"[truth] failed_flows must be empty, got {len(report['failed_flows'])}")

    if report.get("playwright_exit_code") not in (0, None):
        failures.append(f"[truth] playwright_exit_code must be 0, got {report.get('playwright_exit_code')!r}")

    if report.get("real_api") is not True:
        failures.append("[truth] real_api must be true")
    if report.get("mock_only") is not False:
        failures.append("[truth] mock_only must be false")

    api_health = report.get("api_database_health")
    if not isinstance(api_health, dict):
        failures.append("[truth] api_database_health must be present")
    elif api_health.get("ok") is not True:
        failures.append(f"[truth] API /health/db must be ok, got {api_health!r}")

    return failures


def _print_summary(report: dict[str, Any]) -> None:
    print(f"Report:      {REPORT_PATH}")
    print(f"Timestamp:   {report.get('timestamp', 'n/a')}")
    print(f"Browser:     {report.get('browser', 'n/a')}")
    print(f"API:         {report.get('api_base_url', 'n/a')}")
    print(f"Test DB set: {report.get('test_database_url_set')}")
    print(
        f"Result:      collected={report.get('collected')} "
        f"passed={report.get('passed')} "
        f"failed={report.get('failed')} "
        f"skipped={report.get('skipped')}"
    )
    print(f"Duration:    {report.get('duration')}s")


def main() -> int:
    try:
        report = _load_report(REPORT_PATH)
    except ValueError as exc:
        print("Frontend Truth Gate = FAIL")
        print(f"- {exc}")
        return 1

    failures = _validate(report)
    _print_summary(report)

    if failures:
        print()
        print("Frontend Truth Gate = FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print()
    print("Frontend Truth Gate = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
