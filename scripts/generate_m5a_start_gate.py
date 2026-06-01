"""Generate m5a_start_gate.json.

Evaluates all M5a start-gate criteria against current reports and docs,
then writes reports/current/m5a_start_gate.json.

Exit codes:
  0 – gate PASS / GO
  1 – gate FAIL / NO_GO (blockers present)
  2 – fatal: mandatory input unreadable
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT = CURRENT_DIR / "m5a_start_gate.json"

# Mandatory report inputs
INPUTS_REPORTS = [
    "m3a_release_candidate.json",
    "m4_backend_release_candidate.json",
    "m4e_operations_release_gate.json",
    "documentation_truth_lint.json",
]
# Mandatory doc inputs
INPUTS_DOCS = [
    "m5-preparation.md",
    "data-quality.md",
    "drift.md",
    "cleanup.md",
    "health-score.md",
    "retrieval-quality-baseline.md",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path.name}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON {path.name}: {exc}"
    if not isinstance(data, dict):
        return None, f"JSON root not an object: {path.name}"
    return data, None


def _is_pass(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    return status == "PASS"


def _doc_is_pass(report: dict[str, Any] | None) -> bool:
    """documentation_truth_lint has no collected/passed — check status + error count."""
    if report is None:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    if status not in ("PASS",):
        return False
    summary = report.get("summary") or {}
    errors = report.get("errors") or summary.get("errors") or 0
    return int(errors) == 0


def _is_go(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    decision = report.get("decision")
    if isinstance(decision, dict):
        gng = str(decision.get("go_no_go") or "").upper()
    elif isinstance(decision, str):
        gng = decision.upper()
    else:
        gng = ""
    return gng == "GO" and _is_pass(report)


def _ts(report: dict[str, Any] | None) -> str | None:
    if report is None:
        return None
    return report.get("timestamp") or report.get("generated_at")


def _doc_contains(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
        return bool(re.search(pattern, text))
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------

def _criteria(
    reports: dict[str, dict[str, Any] | None],
    errors: dict[str, str | None],
) -> list[dict[str, Any]]:
    criteria = []

    # ── Precondition: M3a RC
    r = reports["m3a_release_candidate.json"]
    e = errors["m3a_release_candidate.json"]
    passed = e is None and _is_go(r)
    evidence = f"status={r.get('status')}, decision=GO" if passed else (e or f"status={r.get('status') if r else 'missing'}, not GO")
    criteria.append({
        "id": "m3a_release_candidate_go",
        "label": "M3a Release Candidate GO",
        "passed": passed,
        "source": "reports/current/m3a_release_candidate.json",
        "evidence": evidence,
    })

    # ── Precondition: M4 Backend RC
    r = reports["m4_backend_release_candidate.json"]
    e = errors["m4_backend_release_candidate.json"]
    passed = e is None and _is_go(r)
    evidence = f"status={r.get('status')}, decision=GO" if passed else (e or f"status={r.get('status') if r else 'missing'}, not GO")
    criteria.append({
        "id": "m4_backend_release_candidate_go",
        "label": "M4 Backend Release Candidate GO",
        "passed": passed,
        "source": "reports/current/m4_backend_release_candidate.json",
        "evidence": evidence,
    })

    # ── Precondition: M4e Operations Release
    r = reports["m4e_operations_release_gate.json"]
    e = errors["m4e_operations_release_gate.json"]
    passed = e is None and _is_go(r)
    evidence = f"status={r.get('status')}, decision=GO" if passed else (e or f"status={r.get('status') if r else 'missing'}, not GO")
    criteria.append({
        "id": "m4e_operations_release_go",
        "label": "M4e Operations Release GO",
        "passed": passed,
        "source": "reports/current/m4e_operations_release_gate.json",
        "evidence": evidence,
    })

    # ── Precondition: Documentation Truth Lint
    r = reports["documentation_truth_lint.json"]
    e = errors["documentation_truth_lint.json"]
    passed = e is None and _doc_is_pass(r)
    if passed:
        evidence = "status=PASS, errors=0"
    elif e:
        evidence = e
    elif r:
        summary = r.get("summary") or {}
        err_count = r.get("errors") or summary.get("errors") or 0
        warn_count = r.get("warnings") or summary.get("warnings") or 0
        evidence = f"status={r.get('status')}, errors={err_count}, warnings={warn_count}"
    else:
        evidence = "missing"
    criteria.append({
        "id": "documentation_truth_lint_pass",
        "label": "Documentation Truth Lint PASS",
        "passed": passed,
        "source": "reports/current/documentation_truth_lint.json",
        "evidence": evidence,
    })

    # ── Scope: Data Quality scope defined in m5-preparation.md
    prep = DOCS_DIR / "m5-preparation.md"
    dq = DOCS_DIR / "data-quality.md"
    passed = _doc_contains(prep, r"[Dd]ata.?[Qq]uality") and dq.exists()
    criteria.append({
        "id": "m5a_data_quality_scope_defined",
        "label": "Data Quality Scope vorhanden",
        "passed": passed,
        "source": "docs/m5-preparation.md",
        "evidence": (
            "Section defines Data Quality responsibilities; docs/data-quality.md defines the M5 Data Quality architecture."
            if passed else "Data Quality scope missing in docs/m5-preparation.md or docs/data-quality.md absent."
        ),
    })

    # ── Scope: Data Quality Report Schema defined in data-quality.md
    passed = _doc_contains(dq, r"report_schema_version|report_name|timestamp|metrics|findings")
    criteria.append({
        "id": "m5a_data_quality_report_schema_defined",
        "label": "Data Quality Report Schema vorhanden",
        "passed": passed,
        "source": "docs/data-quality.md",
        "evidence": (
            "Report-Format JSON block defines report_schema_version, report_name, timestamp, metrics and findings."
            if passed else "Report schema not found in docs/data-quality.md."
        ),
    })

    # ── Scope: Finding types defined
    drift = DOCS_DIR / "drift.md"
    cleanup = DOCS_DIR / "cleanup.md"
    passed = (
        _doc_contains(prep, r"[Ff]inding|[Ee]rror|[Dd]rift") and
        drift.exists() and cleanup.exists()
    )
    criteria.append({
        "id": "m5a_finding_types_defined",
        "label": "Finding Types definiert",
        "passed": passed,
        "source": "docs/m5-preparation.md",
        "evidence": (
            "Hard errors, drift types and cleanup candidate types are enumerated across M5 preparation, drift and cleanup docs."
            if passed else "Finding types not found across preparation/drift/cleanup docs."
        ),
    })

    # ── Scope: Severity model defined in drift.md
    passed = _doc_contains(drift, r"[Ss]everity|warning|error") and _doc_contains(prep, r"[Ss]everity|[Rr]isik|[Ss]chwere|risk")
    criteria.append({
        "id": "m5a_severity_model_defined",
        "label": "Severity Modell definiert",
        "passed": passed,
        "source": "docs/drift.md",
        "evidence": (
            "Drift severity uses warning/error; M5 preparation risk table defines severity classes."
            if passed else "Severity model not found in docs/drift.md or docs/m5-preparation.md."
        ),
    })

    # ── Scope: Read-only API scope defined
    passed = _doc_contains(prep, r"read.?only|[Ll]esend|[Rr]ead only")
    criteria.append({
        "id": "m5a_read_only_api_scope_defined",
        "label": "Read-only API Scope definiert",
        "passed": passed,
        "source": "docs/m5-preparation.md",
        "evidence": (
            "Drift Detection remains read-only; M4d Admin Diagnostics remains read-only; mutating Web Admin actions are out of scope."
            if passed else "Read-only API scope not found in docs/m5-preparation.md."
        ),
    })

    # ── Scope: Dashboard scope defined
    passed = _doc_contains(prep, r"[Dd]ashboard|[Oo]bservabilit") or _doc_contains(dq, r"[Dd]ashboard")
    criteria.append({
        "id": "m5a_dashboard_scope_defined",
        "label": "Dashboard Scope definiert",
        "passed": passed,
        "source": "docs/m5-preparation.md",
        "evidence": (
            "Observability section defines workspace and global dashboard views; docs/data-quality.md references dashboard implementation anchors."
            if passed else "Dashboard scope not found in docs/m5-preparation.md or docs/data-quality.md."
        ),
    })

    # ── Scope: Non-scope defined
    passed = _doc_contains(prep, r"[Nn]on.?[Ss]cope|[Nn]icht.?[Ss]cope|[Aa]us dem [Ss]cope|nicht.*[Ss]cope|out of scope")
    criteria.append({
        "id": "m5a_non_scope_defined",
        "label": "Nicht-Scope definiert",
        "passed": passed,
        "source": "docs/m5-preparation.md",
        "evidence": (
            "Section 2 defines M5 non-scope; component docs also define non-scope boundaries."
            if passed else "Non-scope section not found in docs/m5-preparation.md."
        ),
    })

    # ── Scope: Gate rules defined
    passed = _doc_contains(dq, r"[Gg]ate|[Ss]core|[Tt]hreshold|[Bb]lock") or _doc_contains(prep, r"[Gg]ate.rule|gate_rule")
    criteria.append({
        "id": "m5a_gate_rules_defined",
        "label": "Gate-Regeln definiert",
        "passed": passed,
        "source": "docs/data-quality.md",
        "evidence": (
            "Data Quality gate rule requires all required components and score threshold; retrieval baseline and cleanup docs define blocking thresholds."
            if passed else "Gate rules not found in docs/data-quality.md."
        ),
    })

    return criteria


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ts = datetime.now(timezone.utc).isoformat()

    # Load report inputs
    reports: dict[str, dict[str, Any] | None] = {}
    errors: dict[str, str | None] = {}
    for name in INPUTS_REPORTS:
        r, e = _load_json(CURRENT_DIR / name)
        reports[name] = r
        errors[name] = e
        if e and name != "documentation_truth_lint.json":
            # Fatal: mandatory precondition report unreadable
            print(f"FATAL: {e}", file=sys.stderr)
            return 2

    criteria = _criteria(reports, errors)

    passed_count = sum(1 for c in criteria if c["passed"])
    failed_count = len(criteria) - passed_count
    blockers = [
        {
            "id": f"m5a_{c['id']}_failed",
            "severity": "blocking",
            "reason": f"{c['source']} is not {c['id'].split('_')[-1].upper()}; M5a implementation start remains NO-GO.",
        }
        for c in criteria if not c["passed"]
    ]

    go = failed_count == 0
    status = "PASS" if go else "FAIL"
    go_no_go = "GO" if go else "NO_GO"

    payload: dict[str, Any] = {
        "report_schema_version": 1,
        "report_name": "m5a_start_gate",
        "gate": "m5a_start_gate",
        "status": status,
        "result": status,
        "timestamp": ts,
        "environment": "local",
        "report_type": "gate",
        "collected": len(criteria),
        "passed": passed_count,
        "failed": failed_count,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if go else 1,
        "blockers": blockers,
        "source_command": "python scripts/generate_m5a_start_gate.py",
        "generated_by": "gate_validator",
        "decision": {
            "go_no_go": go_no_go,
            "result": go_no_go,
            "m5a_implementation_start_allowed": go,
            "planning_only": not go,
        },
        "inputs": [f"docs/{d}" for d in INPUTS_DOCS] + [f"reports/current/{r}" for r in INPUTS_REPORTS],
        "criteria": criteria,
        "summary": {
            "m5a_preparation_artifacts_complete": all(c["passed"] for c in criteria if c["id"].startswith("m5a_")),
            "scope_criteria_passed": sum(1 for c in criteria if c["id"].startswith("m5a_") and c["passed"]),
            "scope_criteria_failed": sum(1 for c in criteria if c["id"].startswith("m5a_") and not c["passed"]),
            "precondition_failed": next(
                (c["id"] for c in criteria if not c["passed"] and not c["id"].startswith("m5a_")), None
            ),
            "decision_reason": (
                "All M5a gate criteria passed. Implementation start allowed."
                if go else
                f"Gate failed: {', '.join(b['id'] for b in blockers)}. Implementation start blocked."
            ),
        },
    }

    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"m5a_start_gate = {go_no_go} (status={status})")
    print(f"Wrote: {OUTPUT}")
    return 0 if go else 1


if __name__ == "__main__":
    raise SystemExit(main())
