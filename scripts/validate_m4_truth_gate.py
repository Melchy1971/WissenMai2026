from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "postgres_truth_report.json"

# Hard exit thresholds for M4 Stabilization Sprint
GATE_THRESHOLDS: dict[str, float] = {
    "m4a_gate": 95.0,
    "m4b_gate": 90.0,
    "m4c_gate": 90.0,
    "m4d_gate": 85.0,
}

GATE_LABELS: dict[str, str] = {
    "m4a_gate": "M4a (Auth/Workspace-Isolation)",
    "m4b_gate": "M4b (Upload-Stabilitaet)",
    "m4c_gate": "M4c (Lifecycle/Search/Chat)",
    "m4d_gate": "M4d (Read-only Diagnostics)",
}

RC_BLOCKER_NAMES = (
    "Race Condition",
    "Cross-Workspace Leak",
    "Dead-Letter Replay Verlust",
    "source_status Inkonsistenz",
)


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


def _check_postgres_truth(report: dict[str, Any]) -> list[str]:
    """Criterion 1: postgres_truth suite must be fully green."""
    failures: list[str] = []

    if report.get("test_database_url_set") is not True:
        failures.append("[truth] test_database_url_set must be true — kein echter PostgreSQL-Nachweis")

    collected = report.get("collected", 0)
    passed = report.get("passed", 0)
    failed = report.get("failed", 0)
    errors = report.get("errors", 0)
    skipped = report.get("skipped", 0)

    if not isinstance(passed, int) or passed <= 0:
        failures.append(f"[truth] passed must be > 0, got {passed!r}")
    elif isinstance(collected, int) and collected > 0 and passed != collected:
        failures.append(
            f"[truth] passed ({passed}) must equal collected ({collected})"
            f" — {collected - passed} Tests nicht bestanden"
        )

    if failed != 0:
        failures.append(f"[truth] failed must be 0, got {failed}")

    if errors != 0:
        failures.append(f"[truth] errors must be 0, got {errors}")

    if skipped != 0:
        failures.append(f"[truth] skipped must be 0, got {skipped}")

    if report.get("pytest_exit_code") != 0:
        failures.append(f"[truth] pytest_exit_code must be 0, got {report.get('pytest_exit_code')!r}")

    return failures


def _check_gate_scores(report: dict[str, Any]) -> list[str]:
    """Criterion 2: per-gate pass rates must meet thresholds."""
    failures: list[str] = []
    gate_scores: dict[str, Any] = report.get("gate_scores") or {}

    if not gate_scores:
        failures.append(
            "[gate_scores] field absent — report was generated without gate score tracking; "
            "re-run generate_postgres_truth_report.py to populate"
        )
        return failures

    for gate, threshold in GATE_THRESHOLDS.items():
        score = gate_scores.get(gate)
        label = GATE_LABELS[gate]

        if score is None:
            # m4d_gate has no tests yet — exempt from hard block, but warn
            if gate == "m4d_gate":
                failures.append(
                    f"[gate_scores] {label}: keine Tests registriert (Schwelle >= {threshold}%) "
                    f"— Marker @pytest.mark.{gate} fehlt in der Suite"
                )
            else:
                failures.append(
                    f"[gate_scores] {label}: keine Tests registriert (Schwelle >= {threshold}%)"
                )
        elif score < threshold:
            failures.append(
                f"[gate_scores] {label}: {score}% < {threshold}% (Schwelle nicht erreicht)"
            )

    return failures


def _check_rc_blockers(report: dict[str, Any]) -> list[str]:
    """Criterion 3: no open RC-blockers."""
    failures: list[str] = []
    rc_open: list[str] = report.get("rc_blockers_open") or []

    if "rc_blockers_open" not in report:
        failures.append(
            "[rc_blockers] field absent — report was generated without RC-blocker tracking; "
            "re-run generate_postgres_truth_report.py to populate"
        )
        return failures

    for blocker in rc_open:
        failures.append(f"[rc_blocker] offen: {blocker}")

    return failures


def _validate(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    failures.extend(_check_postgres_truth(report))
    failures.extend(_check_gate_scores(report))
    failures.extend(_check_rc_blockers(report))
    return failures


def _print_summary(report: dict[str, Any]) -> None:
    gate_scores: dict[str, Any] = report.get("gate_scores") or {}
    rc_open: list[str] = report.get("rc_blockers_open") or []

    print(f"Report:      {REPORT_PATH}")
    print(f"Zeitpunkt:   {report.get('generated_at', 'n/a')}")
    print(f"Commit:      {report.get('commit_hash') or 'n/a'}")
    print(f"Collected:   {report.get('collected', '?')}")
    print(
        f"Ergebnis:    passed={report.get('passed')} "
        f"failed={report.get('failed')} "
        f"errors={report.get('errors')} "
        f"skipped={report.get('skipped')}"
    )
    print("Gate Scores:")
    for gate, threshold in GATE_THRESHOLDS.items():
        score = gate_scores.get(gate)
        score_str = f"{score}%" if score is not None else "n/a"
        status = "PASS" if (score is not None and score >= threshold) else "FAIL"
        print(f"  {GATE_LABELS[gate]}: {score_str} (Schwelle >= {threshold}%) [{status}]")
    if rc_open:
        print(f"RC-Blocker:  {len(rc_open)} offen")
        for b in rc_open:
            print(f"  - {b}")
    else:
        print("RC-Blocker:  keine offen")


def main() -> int:
    try:
        report = _load_report(REPORT_PATH)
    except ValueError as exc:
        print("M4 Stabilization Gate = FAIL")
        print(f"- {exc}")
        return 1

    failures = _validate(report)
    _print_summary(report)

    if failures:
        print()
        print("M4 Stabilization Gate = FAIL")
        print(f"  {len(failures)} Exit-Kriterien nicht erfüllt:")
        for f in failures:
            print(f"  - {f}")
        print()
        print("M5 bleibt blockiert.")
        return 1

    print()
    print("M4 Stabilization Gate = PASS")
    print("Alle Exit-Kriterien erfüllt. M5-Freigabe kann geprüft werden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
