from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "postgres_truth_report.json"

GATE_THRESHOLDS: dict[str, float] = {
    "m4_truth": 90.0,
    "m4a_auth_truth": 95.0,
    "m4b_upload_queue_truth": 90.0,
    "m4c_lifecycle_retrieval_truth": 90.0,
    "m4e_backup_restore_truth": 90.0,
}

GATE_LABELS: dict[str, str] = {
    "m4_truth": "M4 (Backend Stabilization)",
    "m4a_auth_truth": "M4a (Auth/Workspace-Isolation)",
    "m4b_upload_queue_truth": "M4b (Upload-Stabilitaet)",
    "m4c_lifecycle_retrieval_truth": "M4c (Lifecycle/Search/Chat)",
    "m4e_backup_restore_truth": "M4e (Backup/Restore)",
}


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


def _classify_postgres_truth_nodeid(nodeid: str, *, kind: str = "failure") -> dict[str, str]:
    lowered = nodeid.lower()
    if not nodeid or nodeid.startswith("unclassified_setup_error_"):
        return {
            "nodeid": nodeid,
            "kind": kind,
            "group": "Setup/Error",
            "domain": "Report integrity",
            "m4_critical": "yes",
            "m5_critical": "yes",
            "m3a_relevant": "no",
            "reason": "Setup-/Collect-Error ohne Nodeid im historischen Report",
        }

    if "test_entropy_truth.py" in lowered or "test_queue_aging_truth.py" in lowered:
        return {
            "nodeid": nodeid,
            "kind": kind,
            "group": "M5 entropy/drift",
            "domain": "M5 Operational Truth",
            "m4_critical": "no",
            "m5_critical": "yes",
            "m3a_relevant": "no",
            "reason": "Entropy, Queue Aging oder Drift gehoeren nicht zum M4a/b/c Gate",
        }

    if any(
        token in lowered
        for token in (
            "test_m5_",
            "cleanup_governance",
            "citation_longevity",
            "reindex_governance",
        )
    ):
        return {
            "nodeid": nodeid,
            "kind": kind,
            "group": "M5 entropy/drift",
            "domain": "M5 Operational Truth",
            "m4_critical": "no",
            "m5_critical": "yes",
            "m3a_relevant": "no",
            "reason": "Operational-Hardening fuer M5, keine M3a- oder M4a/b/c-Pflicht",
        }

    if any(token in lowered for token in ("test_m4a_", "auth_workspace", "workspace_bootstrap")):
        return {
            "nodeid": nodeid,
            "kind": kind,
            "group": "M4a",
            "domain": "M4 Backend Truth",
            "m4_critical": "yes",
            "m5_critical": "no",
            "m3a_relevant": "no",
            "reason": "Auth-/Workspace-Isolation ist M4a-gate-kritisch",
        }

    if any(
        token in lowered
        for token in (
            "test_m4b_",
            "upload",
            "duplicate",
            "queue",
            "replay",
            "recover_stale_import_job",
            "import_job",
        )
    ):
        return {
            "nodeid": nodeid,
            "kind": kind,
            "group": "M4b",
            "domain": "M4 Backend Truth",
            "m4_critical": "yes",
            "m5_critical": "no",
            "m3a_relevant": "no",
            "reason": "Upload-/Queue-Recovery ist M4b-gate-kritisch",
        }

    if any(token in lowered for token in ("test_m4c_", "lifecycle", "retrieval", "search", "chat")):
        return {
            "nodeid": nodeid,
            "kind": kind,
            "group": "M4c",
            "domain": "M4 Backend Truth",
            "m4_critical": "yes",
            "m5_critical": "no",
            "m3a_relevant": "no",
            "reason": "Lifecycle/Search/Chat ist M4c-gate-kritisch",
        }

    return {
        "nodeid": nodeid,
        "kind": kind,
        "group": "Setup/Error",
        "domain": "Report integrity",
        "m4_critical": "yes",
        "m5_critical": "yes",
        "m3a_relevant": "no",
        "reason": "Unbekannter postgres_truth-Scope muss vor Freigabe geklaert werden",
    }


def _failure_gate_matrix(report: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        _classify_postgres_truth_nodeid(str(nodeid), kind="failure")
        for nodeid in (report.get("failed_tests") or [])
    ]
    error_tests = [str(nodeid) for nodeid in (report.get("error_tests") or [])]
    rows.extend(_classify_postgres_truth_nodeid(nodeid, kind="error") for nodeid in error_tests)

    error_count = report.get("errors", 0)
    if isinstance(error_count, int) and error_count > len(error_tests):
        for index in range(error_count - len(error_tests)):
            rows.append(
                _classify_postgres_truth_nodeid(
                    f"unclassified_setup_error_{index + 1}",
                    kind="error",
                )
            )
    return rows


def _check_postgres_truth(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    if report.get("test_database_url_set") is not True:
        failures.append("[truth] test_database_url_set must be true - kein echter PostgreSQL-Nachweis")

    passed = report.get("passed", 0)
    skipped = report.get("skipped", 0)

    if not isinstance(passed, int) or passed <= 0:
        failures.append(f"[truth] passed must be > 0, got {passed!r}")

    if "m4_skipped_tests" not in report and skipped != 0:
        failures.append(f"[truth] skipped must be 0, got {skipped}")

    if "m4_failed_tests" in report:
        for nodeid in report.get("m4_failed_tests") or []:
            failures.append(f"[M4] failure: {nodeid}")
        for nodeid in report.get("m4_skipped_tests") or []:
            failures.append(f"[M4] skipped: {nodeid}")
        for nodeid in report.get("m4_error_tests") or []:
            failures.append(f"[Setup/Error] error: {nodeid}")
        errors = report.get("errors", 0)
        known_errors = len(report.get("error_tests") or [])
        if isinstance(errors, int) and errors > known_errors:
            failures.append(f"[Setup/Error] {errors - known_errors} unclassified setup/collect error(s)")
    else:
        for row in _failure_gate_matrix(report):
            if row["m4_critical"] == "yes":
                failures.append(f"[{row['group']}] {row['kind']}: {row['nodeid']} - {row['reason']}")

    return failures


def _check_gate_scores(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    gate_scores: dict[str, Any] = report.get("gate_scores") or {}

    if not gate_scores:
        failures.append(
            "[gate_scores] field absent - report was generated without gate score tracking; "
            "re-run generate_postgres_truth_report.py to populate"
        )
        return failures

    for gate, threshold in GATE_THRESHOLDS.items():
        score = gate_scores.get(gate)
        label = GATE_LABELS[gate]

        if score is None:
            if gate != "m4e_backup_restore_truth":
                failures.append(f"[gate_scores] {label}: keine Tests registriert (Schwelle >= {threshold}%)")
        elif score < threshold:
            failures.append(f"[gate_scores] {label}: {score}% < {threshold}% (Schwelle nicht erreicht)")

    return failures


def _check_rc_blockers(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    rc_open: list[str] = report.get("rc_blockers_open") or []

    if "rc_blockers_open" not in report:
        failures.append(
            "[rc_blockers] field absent - report was generated without RC-blocker tracking; "
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
        status = "PASS" if (score is not None and score >= threshold) else "n/a" if gate == "m4e_backup_restore_truth" else "FAIL"
        print(f"  {GATE_LABELS[gate]}: {score_str} (Schwelle >= {threshold}%) [{status}]")

    if rc_open:
        print(f"RC-Blocker:  {len(rc_open)} offen")
        for blocker in rc_open:
            print(f"  - {blocker}")
    else:
        print("RC-Blocker:  keine offen")

    matrix = _failure_gate_matrix(report)
    if matrix:
        print("Failure-to-Gate Matrix:")
        for row in matrix:
            print(
                f"  - {row['group']}: {row['kind']} | "
                f"M4={row['m4_critical']} M5={row['m5_critical']} M3a={row['m3a_relevant']} | "
                f"{row['nodeid']}"
            )


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
        print(f"  {len(failures)} Exit-Kriterien nicht erfuellt:")
        for failure in failures:
            print(f"  - {failure}")
        print()
        print("M5 bleibt blockiert.")
        return 1

    print()
    print("M4 Stabilization Gate = PASS")
    print("Alle Exit-Kriterien erfuellt. M5-Freigabe kann geprueft werden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
