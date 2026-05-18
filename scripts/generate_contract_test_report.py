from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
REPORTS_DIR = REPO_ROOT / "reports"
JSON_REPORT_PATH = REPORTS_DIR / "contract_test_report.json"
MARKDOWN_REPORT_PATH = REPORTS_DIR / "contract_test_report.md"
TEST_TARGET = "tests/test_frontend_backend_contracts.py"


@dataclass(eq=False)
class ResultCapturePlugin:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    passed_tests: list[str] = field(default_factory=list)
    failed_tests: list[str] = field(default_factory=list)
    skipped_tests: list[str] = field(default_factory=list)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            if report.failed:
                self.errors += 1
            elif report.skipped:
                self.skipped += 1
                self.skipped_tests.append(report.nodeid)
            return
        if report.passed:
            self.passed += 1
            self.passed_tests.append(report.nodeid)
        elif report.failed:
            self.failed += 1
            self.failed_tests.append(report.nodeid)
        elif report.skipped:
            self.skipped += 1
            self.skipped_tests.append(report.nodeid)

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.errors += 1


class CollectOnlyPlugin:
    def __init__(self) -> None:
        self.collected = 0

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collected = len(session.items)


def _get_commit_hash() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _collect() -> int:
    plugin = CollectOnlyPlugin()
    exit_code = pytest.main([TEST_TARGET, "--collect-only", "-q"], plugins=[plugin])
    if exit_code not in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
        raise SystemExit(int(exit_code))
    return plugin.collected


def _run() -> tuple[int, float, ResultCapturePlugin]:
    plugin = ResultCapturePlugin()
    start = time.perf_counter()
    exit_code = pytest.main([TEST_TARGET, "-q"], plugins=[plugin])
    return int(exit_code), round(time.perf_counter() - start, 3), plugin


def _build_report() -> dict[str, Any]:
    collected = _collect()
    exit_code, duration, result = _run()
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "command": f"{Path(sys.executable).name} -m pytest {TEST_TARGET} -q",
        "collected": collected,
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "errors": result.errors,
        "duration_seconds": duration,
        "pytest_exit_code": exit_code,
        "commit_hash": _get_commit_hash(),
        "passed_tests": result.passed_tests,
        "failed_tests": result.failed_tests,
        "skipped_tests": result.skipped_tests,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Contract Test Report",
        "",
        "| Feld | Wert |",
        "|---|---|",
        f"| timestamp | `{report['timestamp']}` |",
        f"| command | `{report['command']}` |",
        f"| collected | {report['collected']} |",
        f"| passed | {report['passed']} |",
        f"| failed | {report['failed']} |",
        f"| skipped | {report['skipped']} |",
        f"| errors | {report['errors']} |",
        f"| duration_seconds | {report['duration_seconds']} |",
        f"| pytest_exit_code | {report['pytest_exit_code']} |",
        "",
        "## Failed Tests",
        "",
    ]
    failed = report.get("failed_tests") or []
    lines.extend(f"- `{test}`" for test in failed) if failed else lines.append("- keine")
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = _build_report()
    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Wrote {JSON_REPORT_PATH}")
    print(f"Wrote {MARKDOWN_REPORT_PATH}")
    print(
        f"Result: {report['passed']} passed, {report['failed']} failed, "
        f"{report['skipped']} skipped, {report['errors']} errors"
    )
    return 0 if report["pytest_exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
