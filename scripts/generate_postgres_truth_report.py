from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
REPORTS_DIR = REPO_ROOT / "reports"
JSON_REPORT_PATH = REPORTS_DIR / "postgres_truth_report.json"
MARKDOWN_REPORT_PATH = REPORTS_DIR / "postgres_truth_report.md"


@dataclass
class RunSummary:
    exit_code: int
    passed: int
    failed: int
    skipped: int
    errors: int
    xfailed: int
    xpassed: int
    duration_seconds: float


class CollectOnlyPlugin:
    def __init__(self) -> None:
        self.collected = 0

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collected = len(session.items)


class ResultCapturePlugin:
    def __init__(self) -> None:
        self.counts = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "xfailed": 0,
            "xpassed": 0,
        }

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            if report.when == "setup" and report.skipped:
                self.counts["skipped"] += 1
            return
        if report.passed:
            self.counts["passed"] += 1
        elif report.failed:
            self.counts["failed"] += 1
        elif report.skipped:
            self.counts["skipped"] += 1

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.counts["errors"] += 1


def _build_alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def _get_alembic_heads() -> list[str]:
    script = ScriptDirectory.from_config(_build_alembic_config())
    return sorted(script.get_heads())


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
    value = completed.stdout.strip()
    return value or None


def _run_collection() -> int:
    plugin = CollectOnlyPlugin()
    exit_code = pytest.main(
        ["-m", "postgres_truth", "tests/postgres_truth", "--collect-only", "-q"],
        plugins=[plugin],
    )
    if exit_code not in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
        raise SystemExit(int(exit_code))
    return plugin.collected


def _run_truth_suite() -> RunSummary:
    plugin = ResultCapturePlugin()
    start = time.perf_counter()
    exit_code = pytest.main(
        ["-m", "postgres_truth", "tests/postgres_truth", "-q"],
        plugins=[plugin],
    )
    duration_seconds = time.perf_counter() - start
    return RunSummary(
        exit_code=int(exit_code),
        passed=plugin.counts["passed"],
        failed=plugin.counts["failed"],
        skipped=plugin.counts["skipped"],
        errors=plugin.counts["errors"],
        xfailed=plugin.counts["xfailed"],
        xpassed=plugin.counts["xpassed"],
        duration_seconds=round(duration_seconds, 3),
    )


def _build_report_payload() -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    collected = _run_collection()
    summary = _run_truth_suite()
    test_database_url = os.getenv("TEST_DATABASE_URL")
    heads = _get_alembic_heads()
    return {
        "generated_at": generated_at,
        "command": f"{Path(sys.executable).name} -m pytest -m postgres_truth tests/postgres_truth -q",
        "test_database_url_set": bool(test_database_url),
        "alembic_heads": heads,
        "collected": collected,
        "passed": summary.passed,
        "failed": summary.failed,
        "skipped": summary.skipped,
        "errors": summary.errors,
        "xfailed": summary.xfailed,
        "xpassed": summary.xpassed,
        "duration_seconds": summary.duration_seconds,
        "pytest_exit_code": summary.exit_code,
        "commit_hash": _get_commit_hash(),
    }


def _render_markdown(report: dict[str, Any]) -> str:
    alembic_heads = report["alembic_heads"] or ["<none>"]
    lines = [
        "# PostgreSQL Truth-Test-Report",
        "",
        "| Feld | Wert |",
        "|---|---|",
        f"| Zeitpunkt | {report['generated_at']} |",
        f"| Command | `{report['command']}` |",
        f"| TEST_DATABASE_URL gesetzt | {str(report['test_database_url_set']).lower()} |",
        f"| Alembic head | {', '.join(alembic_heads)} |",
        f"| Collected | {report['collected']} |",
        f"| Passed | {report['passed']} |",
        f"| Failed | {report['failed']} |",
        f"| Skipped | {report['skipped']} |",
        f"| Errors | {report['errors']} |",
        f"| Duration | {report['duration_seconds']}s |",
        f"| Pytest exit code | {report['pytest_exit_code']} |",
        f"| Commit | {report['commit_hash'] or 'n/a'} |",
        "",
        "## Interpretation",
        "",
        "- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.",
        "- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.",
        "- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = _build_report_payload()
    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Wrote {JSON_REPORT_PATH}")
    print(f"Wrote {MARKDOWN_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())