"""Masterplan Status Engine v2.

Derives system-phase status exclusively from machine-computed artifacts in
reports/current/ and docs/known_limitations.json.

Rules
-----
1. Missing required report           → report BLOCKED
2. Invalid JSON or missing fields    → report BLOCKED
3. Stale report (> STALE_DAYS days)  → report BLOCKED
4. documentation_truth_lint errors   → global BLOCKED
5. PASS granted only by gate validator (exit_code=0, passed==collected)
6. M3a → M4 → M5 → Governance boundary enforced via gate dependency chain

Inputs (exclusively)
--------------------
- reports/current/m3a_frontend_truth.json
- reports/current/m4a_auth_truth.json
- reports/current/m4b_upload_queue_truth.json
- reports/current/m4c_lifecycle_retrieval_truth.json
- reports/current/m4e_backup_restore_truth.json
- reports/current/documentation_truth_lint.json
- docs/known_limitations.json

Outputs
-------
- reports/current/masterplan_status.json
- docs/generated/status_section.md
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
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

# Reports that must be present and valid for gate evaluation
REQUIRED_SPLIT_REPORTS: tuple[str, ...] = (
    "m3a_frontend_truth.json",
    "m4a_auth_truth.json",
    "m4b_upload_queue_truth.json",
    "m4c_lifecycle_retrieval_truth.json",
    "m4e_backup_restore_truth.json",
)

REQUIRED_REPORT_FIELDS = ("collected", "passed", "failed", "errors", "exit_code")

# Maps gate hierarchy gate IDs to phase IDs
PHASE_GATE_MAP: dict[str, str] = {
    "m3a": "m3a_gate",
    "m4": "m4_overall_gate",
    "m5": "m5_start_gate",
    "governance": "operational_governance_gate",
}

PHASE_LABELS: dict[str, str] = {
    "m3a": "M3a Frontend Foundation",
    "m4": "M4 Stabilization",
    "m5": "M5 Start",
    "governance": "Operational Governance",
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
    "m5": 25.0,
    "governance": 15.0,
}


# ---------------------------------------------------------------------------
# Import gate hierarchy evaluator
# ---------------------------------------------------------------------------

def _import_gate_hierarchy() -> Any:
    gate_script = REPO_ROOT / "scripts" / "validate_gate_hierarchy.py"
    spec = importlib.util.spec_from_file_location("validate_gate_hierarchy", gate_script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_gate_hierarchy", mod)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


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
# Phase derivation from gate result
# ---------------------------------------------------------------------------

def _gate_status_to_phase(gate_status: str) -> tuple[str, str]:
    """Map gate status to (phase_status, decision)."""
    if gate_status == "PASS":
        return "gate_passed", "GO"
    if gate_status == "FAIL":
        return "tested", "NO_GO"
    return "blocked", "NO_GO"


def _build_phase(
    phase_id: str,
    gate_data: dict[str, Any],
    report_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    gate_status = gate_data.get("status", "BLOCKED")
    phase_status, decision = _gate_status_to_phase(gate_status)

    gate_blockers: list[str] = gate_data.get("blockers", [])
    combined_blockers: list[dict[str, Any]] = list(report_blockers)
    for b in gate_blockers:
        combined_blockers.append({
            "id": f"gate_{phase_id}_{hash(b) & 0xFFFF:04x}",
            "type": "gate_failure",
            "severity": "blocking",
            "detail": b,
            "source": f"gate:{gate_data.get('id', phase_id)}",
        })

    return {
        "id": phase_id,
        "label": PHASE_LABELS[phase_id],
        "status": phase_status,
        "decision": decision,
        "gate_id": gate_data.get("id"),
        "gate_status": gate_status,
        "source": f"reports/current/{REQUIRED_SPLIT_REPORTS[0] if phase_id == 'm3a' else 'gate_hierarchy'}",
        "blockers": combined_blockers,
        "report_summaries": gate_data.get("report_summaries", {}),
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
    gate_mod = _import_gate_hierarchy()

    # Step 1: Load and validate all required split reports
    report_blockers: list[dict[str, Any]] = []
    report_load_status: dict[str, dict[str, Any]] = {}
    for fname in REQUIRED_SPLIT_REPORTS:
        payload, err = _load_json(current_dir / fname)
        issues = _validate_report(fname, payload, err)
        report_blockers.extend(issues)
        report_load_status[fname] = {
            "available": payload is not None,
            "error": err,
            "stale": payload is not None and _is_stale(payload),
            "timestamp": (payload or {}).get("timestamp") or (payload or {}).get("generated_at"),
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

    # Step 3: Load known limitations
    limitations = _load_known_limitations(known_limitations_path)
    limitation_blockers = _limitation_blockers(limitations)

    # Step 4: Load regression baseline (optional)
    baseline: dict[str, int] | None = None
    if baseline_path.exists():
        try:
            raw = json.loads(baseline_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                baseline = {k: v for k, v in raw.items() if isinstance(v, int)}
        except (json.JSONDecodeError, OSError):
            pass

    # Step 5: Evaluate gate hierarchy (reads from current_dir)
    gate_result = gate_mod.evaluate_gate_hierarchy(current_dir, baseline=baseline)
    gates = gate_result.get("gates", {})

    # Step 6: Build phase objects from gate results
    phases: dict[str, dict[str, Any]] = {}
    phase_report_blockers: dict[str, list[dict[str, Any]]] = {
        "m3a": [b for b in report_blockers if b.get("report") == "m3a_frontend_truth.json"],
        "m4": [b for b in report_blockers if b.get("report") in (
            "m4a_auth_truth.json", "m4b_upload_queue_truth.json",
            "m4c_lifecycle_retrieval_truth.json", "m4e_backup_restore_truth.json",
        )],
        "m5": [],
        "governance": [],
    }
    for phase_id, gate_id in PHASE_GATE_MAP.items():
        gate_data = gates.get(gate_id, {"id": gate_id, "status": "BLOCKED", "blockers": [], "report_summaries": {}})
        phases[phase_id] = _build_phase(phase_id, gate_data, phase_report_blockers.get(phase_id, []))

    # Step 7: Aggregate all blockers
    all_blockers: list[dict[str, Any]] = []
    all_blockers.extend(report_blockers)
    all_blockers.extend(doc_blockers)
    all_blockers.extend(limitation_blockers)

    overall_blocked = bool(all_blockers) or any(
        p["decision"] != "GO" for p in phases.values()
    )
    progress = _overall_progress(phases)

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
            "known_limitations": str(known_limitations_path),
            "split_reports": report_load_status,
            "gate_hierarchy_evaluated": True,
            "regression_baseline_loaded": baseline is not None,
        },
        "overall": {
            "status": "blocked" if overall_blocked else "pass",
            "progress_percent": progress,
            "release_allowed": not overall_blocked,
            "blocker_count": len(all_blockers),
            "gate_hierarchy_result": gate_result.get("result"),
        },
        "phases": phases,
        "gate_hierarchy": {
            "result": gate_result.get("result"),
            "gates": {
                gate_id: {
                    "status": g.get("status"),
                    "blockers": g.get("blockers", []),
                }
                for gate_id, g in gates.items()
            },
        },
        "documentation_lint": {
            "available": doc_lint is not None,
            "result": (doc_lint or {}).get("result"),
            "errors": (doc_lint or {}).get("summary", {}).get("errors", 0),
            "warnings": (doc_lint or {}).get("summary", {}).get("warnings", 0),
            "source": "reports/current/documentation_truth_lint.json",
        },
        "known_limitations": {
            "total": len(limitations),
            "blocking": len(limitation_blockers),
            "source": str(known_limitations_path),
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
