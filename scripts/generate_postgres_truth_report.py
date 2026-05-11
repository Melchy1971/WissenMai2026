from __future__ import annotations

from dataclasses import dataclass, field
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
VERSIONED_DIR = REPORTS_DIR / "postgres_truth"
JSON_REPORT_PATH = REPORTS_DIR / "postgres_truth_report.json"
MARKDOWN_REPORT_PATH = REPORTS_DIR / "postgres_truth_report.md"
DELTA_MARKDOWN_PATH = REPORTS_DIR / "postgres_truth_delta.md"
LATEST_JSON_PATH = VERSIONED_DIR / "latest.json"

GATE_MARKERS = ("m4a_gate", "m4b_gate", "m4c_gate", "m4d_gate")

# One representative test per RC-blocker category. A blocker is open if its
# canonical test is not in passed_tests (failed, skipped, or did not run).
RC_BLOCKER_PATTERNS: dict[str, str] = {
    "Race Condition": "test_chaos_advisory_lock_document_import_scope_blocks_concurrent_session",
    "Cross-Workspace Leak": "test_m4a_user_a_cannot_import_into_workspace_b",
    "Dead-Letter Replay Verlust": "test_chaos_dead_letter_replay_blocks_concurrent_session",
    "source_status Inkonsistenz": "test_chaos_source_status_live_lookup_reflects_lifecycle_transitions",
}


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
    failed_tests: list[str] = field(default_factory=list)
    passed_tests: list[str] = field(default_factory=list)


class CollectOnlyPlugin:
    def __init__(self) -> None:
        self.collected = 0
        self.marker_test_ids: dict[str, list[str]] = {m: [] for m in GATE_MARKERS}

    @property
    def marker_counts(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.marker_test_ids.items()}

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collected = len(session.items)
        for item in session.items:
            for marker_name in self.marker_test_ids:
                if item.get_closest_marker(marker_name) is not None:
                    self.marker_test_ids[marker_name].append(item.nodeid)


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
        self.failed_tests: list[str] = []
        self.passed_tests: list[str] = []

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        was_xfail = hasattr(report, "wasxfail")
        if report.when != "call":
            if report.skipped:
                self.counts["skipped"] += 1
            elif report.failed:
                self.counts["errors"] += 1
            return
        if report.passed and was_xfail:
            self.counts["xpassed"] += 1
        elif report.passed:
            self.counts["passed"] += 1
            self.passed_tests.append(report.nodeid)
        elif report.failed and was_xfail:
            self.counts["xfailed"] += 1
        elif report.failed:
            self.counts["failed"] += 1
            self.failed_tests.append(report.nodeid)
        elif report.skipped and was_xfail:
            self.counts["xfailed"] += 1
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


def _run_collection() -> tuple[int, dict[str, int], dict[str, list[str]]]:
    plugin = CollectOnlyPlugin()
    exit_code = pytest.main(
        ["-m", "postgres_truth", "tests/postgres_truth", "--collect-only", "-q"],
        plugins=[plugin],
    )
    if exit_code not in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
        raise SystemExit(int(exit_code))
    return plugin.collected, plugin.marker_counts, plugin.marker_test_ids


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
        failed_tests=sorted(plugin.failed_tests),
        passed_tests=sorted(plugin.passed_tests),
    )


def _compute_gate_scores(
    marker_test_ids: dict[str, list[str]],
    passed_tests: list[str],
) -> dict[str, float | None]:
    passed_set = set(passed_tests)
    scores: dict[str, float | None] = {}
    for gate, test_ids in marker_test_ids.items():
        if test_ids:
            n_passed = sum(1 for t in test_ids if t in passed_set)
            scores[gate] = round(n_passed / len(test_ids) * 100, 1)
        else:
            scores[gate] = None  # no tests registered for this gate
    return scores


def _compute_rc_blockers(passed_tests: list[str]) -> list[str]:
    passed_set = set(passed_tests)
    return [
        name
        for name, pattern in RC_BLOCKER_PATTERNS.items()
        if not any(pattern in t for t in passed_set)
    ]


def _build_report_payload() -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    collected, marker_counts, marker_test_ids = _run_collection()
    summary = _run_truth_suite()
    test_database_url = os.getenv("TEST_DATABASE_URL")
    heads = _get_alembic_heads()

    gate_scores = _compute_gate_scores(marker_test_ids, summary.passed_tests)
    rc_blockers_open = _compute_rc_blockers(summary.passed_tests)

    gate_blockers = []
    if not test_database_url:
        gate_blockers.append("TEST_DATABASE_URL fehlt")
    if summary.failed:
        gate_blockers.append(f"{summary.failed} Testfehler")
    if summary.errors:
        gate_blockers.append(f"{summary.errors} Setup-/Collect-Fehler")
    if test_database_url and summary.skipped:
        gate_blockers.append(f"{summary.skipped} unerlaubte Skips bei gesetzter TEST_DATABASE_URL")

    m4_gate_impact = "M4-Gate BLOCKED" if gate_blockers else "M4-Gate PASS"
    return {
        "generated_at": generated_at,
        "command": f"{Path(sys.executable).name} -m pytest -m postgres_truth tests/postgres_truth -q",
        "test_database_url_set": bool(test_database_url),
        "alembic_heads": heads,
        "collected": collected,
        "marker_counts": marker_counts,
        "passed": summary.passed,
        "failed": summary.failed,
        "skipped": summary.skipped,
        "errors": summary.errors,
        "xfailed": summary.xfailed,
        "xpassed": summary.xpassed,
        "duration_seconds": summary.duration_seconds,
        "pytest_exit_code": summary.exit_code,
        "commit_hash": _get_commit_hash(),
        "m4_gate_impact": m4_gate_impact,
        "m4_gate_blockers": gate_blockers,
        "gate_scores": gate_scores,
        "rc_blockers_open": rc_blockers_open,
        "failed_tests": summary.failed_tests,
        "passed_tests": summary.passed_tests,
    }


def _load_previous_report() -> dict[str, Any] | None:
    if not LATEST_JSON_PATH.exists():
        return None
    try:
        return json.loads(LATEST_JSON_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _compute_delta(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    metrics = ("passed", "failed", "errors", "skipped")
    delta = {m: current.get(m, 0) - previous.get(m, 0) for m in metrics}

    prev_failed = set(previous.get("failed_tests") or [])
    curr_failed = set(current.get("failed_tests") or [])
    prev_passed = set(previous.get("passed_tests") or [])

    new_failures = sorted(curr_failed - prev_failed)
    resolved = sorted(prev_failed - curr_failed)
    newly_appeared_failures = sorted(curr_failed - prev_failed - prev_passed)

    prev_gate = previous.get("m4_gate_impact", "")
    curr_gate = current.get("m4_gate_impact", "")
    if prev_gate == "M4-Gate PASS" and curr_gate == "M4-Gate BLOCKED":
        gate_trend = "REGRESSION"
    elif prev_gate == "M4-Gate BLOCKED" and curr_gate == "M4-Gate PASS":
        gate_trend = "IMPROVEMENT"
    else:
        gate_trend = "UNCHANGED"

    return {
        "previous_run": previous.get("generated_at", "unknown"),
        "current_run": current.get("generated_at", "unknown"),
        "previous_commit": previous.get("commit_hash"),
        "current_commit": current.get("commit_hash"),
        "delta": delta,
        "new_failures": new_failures,
        "resolved": resolved,
        "newly_appeared_failures": newly_appeared_failures,
        "gate_trend": gate_trend,
        "has_regression": bool(new_failures) or gate_trend == "REGRESSION",
    }


def _render_delta_markdown(delta: dict[str, Any] | None, current: dict[str, Any]) -> str:
    lines = ["# PostgreSQL Truth — Delta-Report", ""]

    if delta is None:
        lines += [
            "Erster Lauf — kein Vorgänger vorhanden.",
            "",
            "| Metrik | Wert |",
            "|---|---|",
            f"| Zeitpunkt | {current['generated_at']} |",
            f"| Passed | {current['passed']} |",
            f"| Failed | {current['failed']} |",
            f"| Errors | {current['errors']} |",
            f"| Skipped | {current['skipped']} |",
            f"| M4-Gate | {current['m4_gate_impact']} |",
        ]
        return "\n".join(lines) + "\n"

    def fmt(n: int) -> str:
        return f"+{n}" if n > 0 else str(n)

    d = delta["delta"]
    trend_label = {"REGRESSION": "REGRESSION", "IMPROVEMENT": "IMPROVEMENT", "UNCHANGED": "—"}
    gate_label = trend_label.get(delta["gate_trend"], delta["gate_trend"])

    lines += [
        "## Zusammenfassung",
        "",
        "| Feld | Vorheriger Lauf | Aktueller Lauf | Delta |",
        "|---|---|---|---|",
    ]
    for metric in ("passed", "failed", "errors", "skipped"):
        prev_val = current.get(metric, 0) - d[metric]
        curr_val = current.get(metric, 0)
        lines.append(f"| {metric.capitalize()} | {prev_val} | {curr_val} | {fmt(d[metric])} |")

    lines += [
        f"| M4-Gate | {delta['previous_run'][:10]} | {current['m4_gate_impact']} | {gate_label} |",
        "",
        "## Läufe",
        "",
        "| | Zeitpunkt | Commit |",
        "|---|---|---|",
        f"| Vorher | {delta['previous_run']} | {delta['previous_commit'] or 'n/a'} |",
        f"| Jetzt | {delta['current_run']} | {delta['current_commit'] or 'n/a'} |",
    ]

    if delta["resolved"]:
        lines += ["", "## Gelöste Tests", ""]
        lines.extend(f"- `{t}`" for t in delta["resolved"])

    if delta["new_failures"]:
        lines += ["", "## Neue Fehlschläge", ""]
        lines.extend(f"- `{t}`" for t in delta["new_failures"])

    if delta["has_regression"]:
        lines += [
            "",
            "## Regressionserkennung",
            "",
            "**REGRESSION DETECTED** — dieser Lauf hat neue Testfehler oder blockiert das M4-Gate.",
        ]
        if delta["newly_appeared_failures"]:
            lines += ["", "Erstmals fehlschlagende Tests:"]
            lines.extend(f"- `{t}`" for t in delta["newly_appeared_failures"])
    else:
        lines += ["", "## Regressionserkennung", "", "Keine Regression erkannt."]

    return "\n".join(lines) + "\n"


def _render_markdown(report: dict[str, Any]) -> str:
    alembic_heads = report["alembic_heads"] or ["<none>"]
    gate_scores = report.get("gate_scores") or {}
    rc_blockers = report.get("rc_blockers_open") or []

    def score_str(key: str) -> str:
        v = gate_scores.get(key)
        return f"{v}%" if v is not None else "n/a (keine Tests)"

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
        f"| M4a-Gate Tests | {report.get('marker_counts', {}).get('m4a_gate', 0)} |",
        f"| M4b-Gate Tests | {report.get('marker_counts', {}).get('m4b_gate', 0)} |",
        f"| M4c-Gate Tests | {report.get('marker_counts', {}).get('m4c_gate', 0)} |",
        f"| M4d-Gate Tests | {report.get('marker_counts', {}).get('m4d_gate', 0)} |",
        f"| Passed | {report['passed']} |",
        f"| Failed | {report['failed']} |",
        f"| Skipped | {report['skipped']} |",
        f"| Errors | {report['errors']} |",
        f"| Duration | {report['duration_seconds']}s |",
        f"| Pytest exit code | {report['pytest_exit_code']} |",
        f"| Commit | {report['commit_hash'] or 'n/a'} |",
        f"| M4-Gate-Auswirkung | {report['m4_gate_impact']} |",
        "",
        "## Gate Scores",
        "",
        "| Gate | Score | Schwelle | Status |",
        "|---|---|---|---|",
        f"| M4a | {score_str('m4a_gate')} | >= 95% | {'PASS' if (gate_scores.get('m4a_gate') or 0) >= 95 else 'FAIL'} |",
        f"| M4b | {score_str('m4b_gate')} | >= 90% | {'PASS' if (gate_scores.get('m4b_gate') or 0) >= 90 else 'FAIL'} |",
        f"| M4c | {score_str('m4c_gate')} | >= 90% | {'PASS' if (gate_scores.get('m4c_gate') or 0) >= 90 else 'FAIL'} |",
        f"| M4d | {score_str('m4d_gate')} | >= 85% | {'PASS' if (gate_scores.get('m4d_gate') or 0) >= 85 else 'n/a' if gate_scores.get('m4d_gate') is None else 'FAIL'} |",
        "",
        "## RC-Blocker",
        "",
    ]

    if rc_blockers:
        lines += [f"- OPEN: {b}" for b in rc_blockers]
    else:
        lines.append("Keine offenen RC-Blocker.")

    lines += [
        "",
        "## Interpretation",
        "",
        "- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.",
        "- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.",
        "- Bei gesetzter `TEST_DATABASE_URL` sind Skips, Migrationfehler, Setup-Errors und Testfehler Gate-blockierend.",
        "- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.",
    ]
    blockers = report.get("m4_gate_blockers") or []
    if blockers:
        lines.extend(["", "## M4-Gate-Blocker", ""])
        lines.extend(f"- {blocker}" for blocker in blockers)
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    VERSIONED_DIR.mkdir(parents=True, exist_ok=True)

    previous = _load_previous_report()
    report = _build_report_payload()

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    timestamped_path = VERSIONED_DIR / f"{ts}.json"
    timestamped_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    LATEST_JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(_render_markdown(report), encoding="utf-8")

    delta = _compute_delta(report, previous) if previous is not None else None
    DELTA_MARKDOWN_PATH.write_text(_render_delta_markdown(delta, report), encoding="utf-8")

    print(f"Wrote {timestamped_path}")
    print(f"Wrote {LATEST_JSON_PATH}")
    print(f"Wrote {JSON_REPORT_PATH}")
    print(f"Wrote {MARKDOWN_REPORT_PATH}")
    print(f"Wrote {DELTA_MARKDOWN_PATH}")

    if delta and delta["has_regression"]:
        print("WARNING: REGRESSION DETECTED — neue Testfehler seit letztem Lauf!")

    rc_open = report.get("rc_blockers_open") or []
    if rc_open:
        print(f"WARNING: {len(rc_open)} offene RC-Blocker: {', '.join(rc_open)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
