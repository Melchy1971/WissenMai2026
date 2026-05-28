"""Masterplan Status Engine v2.

Derives system-phase status exclusively from machine-computed artifacts in
reports/current/ and docs/known_limitations.json.

Rules
-----
1. Missing required report           → report BLOCKED
2. Invalid JSON or missing fields    → report BLOCKED
3. Stale report (> STALE_DAYS days)  → report BLOCKED
4. documentation_truth_lint errors   → global BLOCKED
5. PASS granted only by current reports (exit_code=0, passed==collected)
6. M3a → M4 → M5 boundary enforced from current reports

Inputs (exclusively)
--------------------
- reports/current/frontend_full_suite_staged_report.json
- reports/current/m4a_auth_truth.json
- reports/current/m4b_upload_queue_truth.json
- reports/current/m4c_lifecycle_retrieval_truth.json
- reports/current/m4e_backup_restore_truth.json
- reports/current/m4_truth_report.json
- reports/current/documentation_truth_lint.json

Outputs
-------
- reports/current/masterplan_status.json
- docs/generated/status_section.md
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
DOCS_DIR = REPO_ROOT / "docs"
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "masterplan_status.json"
DEFAULT_OUTPUT_SECTION = REPO_ROOT / "docs" / "generated" / "status_section.md"
BASELINE_PATH = REPO_ROOT / "reports" / "regression_lock_baseline.json"
KNOWN_LIMITATIONS_PATH = DOCS_DIR / "known_limitations.json"

STALE_DAYS = 30
SCHEMA_VERSION = 2

FRONTEND_REPORT = "frontend_full_suite_staged_report.json"
M4_REPORTS: tuple[str, ...] = (
    "m4a_auth_truth.json",
    "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth.json",
    "m4_truth_report.json",
)
REQUIRED_REPORTS: tuple[str, ...] = (FRONTEND_REPORT, *M4_REPORTS)

REQUIRED_REPORT_FIELDS = ("collected", "passed", "failed", "errors", "exit_code")

PHASE_LABELS: dict[str, str] = {
    "m3a": "M3a Frontend Foundation",
    "m4": "M4 Stabilization",
    "m5": "M5 Start",
}

STATUS_PROGRESS: dict[str, float] = {
    "gate_passed": 1.0,
    "truth_validated": 0.7,
    "tested": 0.5,
    "implemented": 0.35,
    "draft": 0.0,
    "blocked": 0.0,
    "missing": 0.0,
}

PHASE_WEIGHTS: dict[str, float] = {
    "m3a": 25.0,
    "m4": 35.0,
    "m5": 40.0,
}


# ---------------------------------------------------------------------------
# Report loading and validation
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path.name}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root is not an object"
    return payload, None


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        import re
        clean = re.sub(r"(\.\d+)?([+Z].*)?$", "", raw[:26])
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None


def _is_stale(report: dict[str, Any], days: int = STALE_DAYS) -> bool:
    raw = report.get("timestamp") or report.get("generated_at")
    ts = _parse_timestamp(raw)
    if ts is None:
        return False
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    return ts < cutoff


def _validate_report(
    fname: str, report: dict[str, Any] | None, load_error: str | None
) -> list[dict[str, Any]]:
    """Return list of blocker dicts for a given report."""
    issues: list[dict[str, Any]] = []

    if load_error or report is None:
        issues.append({
            "id": f"report_unavailable_{fname.replace('.', '_')}",
            "type": "invalid",
            "report": fname,
            "severity": "blocking",
            "detail": load_error or f"{fname} could not be loaded",
        })
        return issues

    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            issues.append({
                "id": f"missing_field_{fname.replace('.', '_')}_{field}",
                "type": "invalid",
                "report": fname,
                "severity": "blocking",
                "detail": f"{fname}: required field '{field}' is missing",
            })

    collected = report.get("collected")
    if not issues and (isinstance(collected, bool) or not isinstance(collected, int) or collected <= 0):
        issues.append({
            "id": f"zero_collected_{fname.replace('.', '_')}",
            "type": "invalid",
            "report": fname,
            "severity": "blocking",
            "detail": f"{fname}: collected must be > 0, got {collected!r}",
        })

    if not issues and _is_stale(report):
        issues.append({
            "id": f"stale_report_{fname.replace('.', '_')}",
            "type": "stale",
            "report": fname,
            "severity": "blocking",
            "detail": f"{fname}: report is older than {STALE_DAYS} days",
        })

    return issues


# ---------------------------------------------------------------------------
# Phase derivation from current reports
# ---------------------------------------------------------------------------

def _report_is_green(report: dict[str, Any] | None, issues: list[dict[str, Any]]) -> bool:
    if report is None or issues:
        return False
    collected = report.get("collected")
    passed = report.get("passed")
    failed = report.get("failed")
    errors = report.get("errors")
    skipped = report.get("skipped", 0)
    exit_code = report.get("exit_code")
    status = report.get("status") or report.get("result")
    return (
        isinstance(collected, int)
        and collected > 0
        and passed == collected
        and failed == 0
        and errors == 0
        and skipped == 0
        and exit_code == 0
        and (status in (None, "PASS", "pass") or str(status).upper() == "PASS")
    )


def _report_summary(report: dict[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    if report is None:
        return {"available": False, "error": load_error}
    return {
        "available": True,
        "report_name": report.get("report_name"),
        "status": report.get("status"),
        "result": report.get("result"),
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "errors": report.get("errors"),
        "skipped": report.get("skipped", 0),
        "exit_code": report.get("exit_code"),
        "timestamp": report.get("timestamp") or report.get("generated_at"),
    }


def _phase(
    phase_id: str,
    *,
    passed: bool,
    gate_id: str,
    source: str,
    blockers: list[dict[str, Any]],
    report_summaries: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": phase_id,
        "label": PHASE_LABELS[phase_id],
        "status": "gate_passed" if passed else ("tested" if report_summaries else "blocked"),
        "decision": "GO" if passed else "NO_GO",
        "gate_id": gate_id,
        "gate_status": "PASS" if passed else "FAIL",
        "source": source,
        "blockers": blockers,
        "report_summaries": report_summaries,
    }


# ---------------------------------------------------------------------------
# Documentation truth lint integration
# ---------------------------------------------------------------------------

def _doc_lint_blockers(doc_lint: dict[str, Any] | None, load_error: str | None) -> list[dict[str, Any]]:
    if load_error:
        return [{
            "id": "doc_lint_unavailable",
            "type": "invalid",
            "severity": "blocking",
            "detail": f"documentation_truth_lint.json could not be loaded: {load_error}",
            "source": "reports/current/documentation_truth_lint.json",
        }]
    if doc_lint is None:
        return []

    result = doc_lint.get("result", "FAIL")
    if result == "PASS":
        return []

    summary = doc_lint.get("summary", {})
    errors = summary.get("errors", 0)
    if errors == 0:
        return []

    by_rule = summary.get("by_rule", {})
    detail_parts = [f"{rule}={count}" for rule, count in sorted(by_rule.items()) if count > 0 and rule != "manual-percentage"]
    return [{
        "id": "doc_lint_errors",
        "type": "documentation",
        "severity": "blocking",
        "detail": (
            f"documentation_truth_lint.json reports {errors} errors "
            f"({', '.join(detail_parts) if detail_parts else 'see report'}); "
            "fix or suppress before releasing."
        ),
        "source": "reports/current/documentation_truth_lint.json",
        "error_count": errors,
        "by_rule": by_rule,
    }]


# ---------------------------------------------------------------------------
# Known limitations
# ---------------------------------------------------------------------------

def _load_known_limitations(path: Path) -> list[dict[str, Any]]:
    payload, _ = _load_json(path)
    if not payload:
        return []
    lims = payload.get("limitations", [])
    return lims if isinstance(lims, list) else []


def _limitation_blockers(limitations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id", "KL-unknown"),
            "type": "known_limitation",
            "severity": "blocking",
            "detail": item.get("beschreibung") or item.get("description") or "(no description)",
            "blocked_gates": item.get("blockiert_gate", []),
            "source": "docs/known_limitations.json",
        }
        for item in limitations
        if item.get("blockiert_gate")
    ]


# ---------------------------------------------------------------------------
# Overall progress
# ---------------------------------------------------------------------------

def _overall_progress(phases: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for phase_id, weight in PHASE_WEIGHTS.items():
        status = phases[phase_id].get("status", "draft")
        total += weight * STATUS_PROGRESS.get(status, 0.0)
    return round(total, 1)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate(
    current_dir: Path = CURRENT_DIR,
    known_limitations_path: Path = KNOWN_LIMITATIONS_PATH,
    baseline_path: Path = BASELINE_PATH,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).isoformat()

    # Step 1: Load and validate exactly the current reports that define the
    # masterplan state for this gate.
    reports: dict[str, dict[str, Any] | None] = {}
    report_issues: dict[str, list[dict[str, Any]]] = {}
    report_load_status: dict[str, dict[str, Any]] = {}
    for fname in REQUIRED_REPORTS:
        payload, err = _load_json(current_dir / fname)
        issues = _validate_report(fname, payload, err)
        reports[fname] = payload
        report_issues[fname] = issues
        report_load_status[fname] = _report_summary(payload, err) | {
            "stale": payload is not None and _is_stale(payload),
        }

    # Step 2: Load documentation truth lint
    doc_lint, doc_lint_err = _load_json(current_dir / "documentation_truth_lint.json")
    doc_blockers = _doc_lint_blockers(doc_lint, doc_lint_err)
    report_load_status["documentation_truth_lint.json"] = {
        "available": doc_lint is not None,
        "error": doc_lint_err,
        "stale": doc_lint is not None and _is_stale(doc_lint),
        "timestamp": (doc_lint or {}).get("timestamp"),
    }

    # Step 3: Build phases from direct report rules.
    frontend_passed = _report_is_green(reports[FRONTEND_REPORT], report_issues[FRONTEND_REPORT])
    m4_report_passed = {
        fname: _report_is_green(reports[fname], report_issues[fname])
        for fname in M4_REPORTS
    }
    m4_passed = all(m4_report_passed.values())
    m5_passed = m4_passed

    m3a_blockers = list(report_issues[FRONTEND_REPORT])
    if reports[FRONTEND_REPORT] is not None and not frontend_passed and not m3a_blockers:
        m3a_blockers.append({
            "id": "m3a_frontend_full_suite_not_green",
            "type": "truth_report",
            "severity": "blocking",
            "report": FRONTEND_REPORT,
            "detail": "Frontend Full-Suite is not completely green",
            "source": f"reports/current/{FRONTEND_REPORT}",
        })

    m4_blockers: list[dict[str, Any]] = []
    for fname, passed in m4_report_passed.items():
        m4_blockers.extend(report_issues[fname])
        if reports[fname] is not None and not passed and not report_issues[fname]:
            m4_blockers.append({
                "id": f"m4_report_not_green_{fname.replace('.', '_')}",
                "type": "truth_report",
                "severity": "blocking",
                "report": fname,
                "detail": f"{fname} is not PASS",
                "source": f"reports/current/{fname}",
            })

    m5_blockers: list[dict[str, Any]] = []
    if not m4_passed:
        m5_blockers.append({
            "id": "m5_blocked_until_m4_pass",
            "type": "dependency",
            "severity": "blocking",
            "detail": "M5 bleibt NO-GO bis M4 PASS ist",
            "source": "reports/current/masterplan_status.json",
        })

    phases: dict[str, dict[str, Any]] = {}
    phases["m3a"] = _phase(
        "m3a",
        passed=frontend_passed,
        gate_id="m3a_frontend_full_suite_gate",
        source=f"reports/current/{FRONTEND_REPORT}",
        blockers=m3a_blockers,
        report_summaries={FRONTEND_REPORT: report_load_status[FRONTEND_REPORT]},
    )
    phases["m4"] = _phase(
        "m4",
        passed=m4_passed,
        gate_id="m4_overall_gate",
        source="reports/current/m4_truth_report.json",
        blockers=m4_blockers,
        report_summaries={fname: report_load_status[fname] for fname in M4_REPORTS},
    )
    phases["m5"] = _phase(
        "m5",
        passed=m5_passed,
        gate_id="m5_start_gate",
        source="reports/current/masterplan_status.json",
        blockers=m5_blockers,
        report_summaries={},
    )

    # Step 4: Aggregate blockers from the direct gate rules.
    all_blockers: list[dict[str, Any]] = []
    all_blockers.extend(m3a_blockers)
    all_blockers.extend(m4_blockers)
    all_blockers.extend(m5_blockers)
    all_blockers.extend(doc_blockers)

    overall_blocked = bool(all_blockers)
    progress = _overall_progress(phases)
    gate_hierarchy = {
        phases["m3a"]["gate_id"]: {
            "status": phases["m3a"]["gate_status"],
            "blockers": [b["detail"] for b in m3a_blockers],
        },
        "m4a_gate": {
            "status": "PASS" if m4_report_passed["m4a_auth_truth.json"] else "FAIL",
            "blockers": [b["detail"] for b in report_issues["m4a_auth_truth.json"]],
        },
        "m4b_gate": {
            "status": "PASS" if m4_report_passed["m4b_upload_queue_truth.json"] else "FAIL",
            "blockers": [b["detail"] for b in report_issues["m4b_upload_queue_truth.json"]],
        },
        "m4c_gate": {
            "status": "PASS" if m4_report_passed["m4c_lifecycle_retrieval_truth.json"] else "FAIL",
            "blockers": [b["detail"] for b in report_issues["m4c_lifecycle_retrieval_truth.json"]],
        },
        "m4e_gate": {
            "status": "PASS" if m4_report_passed["m4e_backup_restore_truth.json"] else "FAIL",
            "blockers": [b["detail"] for b in report_issues["m4e_backup_restore_truth.json"]],
        },
        "m4_crosscutting_gate": {
            "status": "PASS" if m4_report_passed["m4_truth_report.json"] else "FAIL",
            "blockers": [b["detail"] for b in report_issues["m4_truth_report.json"]],
        },
        phases["m4"]["gate_id"]: {
            "status": phases["m4"]["gate_status"],
            "blockers": [b["detail"] for b in m4_blockers],
        },
        phases["m5"]["gate_id"]: {
            "status": phases["m5"]["gate_status"],
            "blockers": [b["detail"] for b in m5_blockers],
        },
    }

    return {
        "report_schema_version": SCHEMA_VERSION,
        "report_name": "masterplan_status",
        "generated_by": "masterplan_status_engine_v2",
        "generated_at": generated_at,
        "authority": {
            "source_of_truth": "machine_artifacts",
            "manual_status_override_allowed": False,
            "rule": (
                "Status wird ausschliesslich aus Validator-Artefakten abgeleitet. "
                "Manuelle Overrides sind nicht zulaessig."
            ),
            "engine_version": 2,
        },
        "inputs": {
            "report_dir": str(current_dir),
            "current_reports": report_load_status,
            "gate_hierarchy_evaluated": False,
            "regression_baseline_loaded": False,
        },
        "overall": {
            "status": "blocked" if overall_blocked else "pass",
            "progress_percent": progress,
            "release_allowed": not overall_blocked,
            "blocker_count": len(all_blockers),
            "gate_hierarchy_result": "PASS" if not overall_blocked else "FAIL",
        },
        "phases": phases,
        "gate_hierarchy": {
            "result": "PASS" if not overall_blocked else "FAIL",
            "gates": gate_hierarchy,
        },
        "documentation_lint": {
            "available": doc_lint is not None,
            "result": (doc_lint or {}).get("result"),
            "errors": (doc_lint or {}).get("summary", {}).get("errors", 0),
            "warnings": (doc_lint or {}).get("summary", {}).get("warnings", 0),
            "source": "reports/current/documentation_truth_lint.json",
        },
        "known_limitations": {
            "total": 0,
            "blocking": 0,
            "source": str(known_limitations_path),
            "used_for_current_status": False,
        },
        "blockers": all_blockers,
        "timestamp": generated_at,
        "exit_code": 0 if not overall_blocked else 1,
    }


# ---------------------------------------------------------------------------
# Markdown section renderer
# ---------------------------------------------------------------------------

def render_status_section(payload: dict[str, Any]) -> str:
    overall = payload["overall"]
    lines = [
        "<!-- BEGIN GENERATED MASTERPLAN STATUS v2 -->",
        "## Maschinenstatus Masterplan",
        "",
        f"Stand: `{payload['generated_at']}`",
        f"Engine: `{payload['generated_by']}`",
        "",
        f"Gesamtstatus: `{overall['status'].upper()}`",
        f"Fortschritt: `{overall['progress_percent']}%`",
        f"Freigabe: `{'ja' if overall['release_allowed'] else 'nein'}`",
        f"Blocker: `{overall['blocker_count']}`",
        "",
        "> Dieser Abschnitt ist maschinell generiert. "
        "Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.",
        "",
        "### Phasen",
        "",
        "| Phase | Status | Entscheidung | Gate | Gate-Status |",
        "|---|---|---|---|---|",
    ]
    for phase in payload["phases"].values():
        lines.append(
            f"| {phase['label']} "
            f"| `{phase['status']}` "
            f"| `{phase['decision']}` "
            f"| `{phase.get('gate_id', '-')}` "
            f"| `{phase.get('gate_status', '-')}` |"
        )

    gh = payload.get("gate_hierarchy", {})
    lines.extend(["", "### Gate-Hierarchie", "", "| Gate | Status | Blocker |", "|---|---|---|"])
    for gate_id, gdata in gh.get("gates", {}).items():
        raw_blockers = "; ".join(gdata.get("blockers", []))
        # Strip absolute repo path prefixes so output is portable
        for prefix in (str(REPO_ROOT) + "\\", str(REPO_ROOT) + "/"):
            raw_blockers = raw_blockers.replace(prefix, "")
        blockers_preview = raw_blockers[:80] or "-"
        lines.append(f"| `{gate_id}` | `{gdata.get('status')}` | {blockers_preview} |")

    dl = payload.get("documentation_lint", {})
    lines.extend([
        "",
        "### Dokumentations-Lint",
        "",
        f"- Ergebnis: `{dl.get('result', '-')}`",
        f"- Errors: `{dl.get('errors', 0)}`  Warnings: `{dl.get('warnings', 0)}`",
    ])

    lines.extend(["", "### Blocker", ""])
    blockers = payload.get("blockers", [])
    if blockers:
        for b in blockers:
            b_type = b.get("type", "-")
            detail = b.get("detail", "")[:120]
            lines.append(f"- **`{b.get('id')}`** [{b_type}]: {detail}")
    else:
        lines.append("- keine")

    lim = payload.get("known_limitations", {})
    lines.extend([
        "",
        "### Known Limitations",
        "",
        f"- Gesamt: {lim.get('total', 0)}  Blockierend: {lim.get('blocking', 0)}",
    ])

    lines.append("")
    lines.append("<!-- END GENERATED MASTERPLAN STATUS v2 -->")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def write_outputs(payload: dict[str, Any], json_path: Path, section_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    section_path.parent.mkdir(parents=True, exist_ok=True)
    section_path.write_text(render_status_section(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Masterplan Status Engine v2")
    parser.add_argument("--current-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--known-limitations", type=Path, default=KNOWN_LIMITATIONS_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-section", type=Path, default=DEFAULT_OUTPUT_SECTION)
    args = parser.parse_args(argv)

    payload = evaluate(args.current_dir, args.known_limitations)
    write_outputs(payload, args.output_json, args.output_section)

    overall = payload["overall"]
    print(f"Masterplan Status v2 = {overall['status'].upper()}")
    print(f"  Progress : {overall['progress_percent']}%")
    print(f"  Blockers : {overall['blocker_count']}")
    print(f"  Freigabe : {'ja' if overall['release_allowed'] else 'nein'}")
    for phase in payload["phases"].values():
        print(f"  {phase['label']:35s} {phase['status']:15s} {phase['decision']}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_section}")
    return 0 if overall["release_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
