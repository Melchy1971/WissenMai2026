"""Masterplan Status Engine v3.

Derives the current masterplan state from release-candidate reports only.
Manual status text and historical truth reports are not authority inputs.

Stale Guard (M3a RC):
  A STALE RC is never treated as PASS.  The engine loads the three mandatory
  M3a input reports and checks whether any of them carries a timestamp newer
  than the RC itself.  If so, the RC is considered outdated and the M3a gate
  is treated as BLOCKED until the RC is regenerated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from m3a_stale_guard import check_staleness  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "masterplan_status.json"
DEFAULT_OUTPUT_SECTION = REPO_ROOT / "docs" / "generated" / "status_section.md"

M3A_RC = "m3a_release_candidate.json"
M4_BACKEND_RC = "m4_backend_release_candidate.json"
DOC_LINT = "documentation_truth_lint.json"
KNOWN_LIMITATIONS = "known_limitations.json"
M4E_OPERATIONS_RELEASE = "m4e_operations_release_report.json"
SCHEMA_VERSION = 3

# Inputs loaded additionally for the M3a stale guard.
FRONTEND_FULL_SUITE = "frontend_full_suite_staged_report.json"
PREFLIGHT = "report_truth_preflight.json"


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be an object"
    return payload, None


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _is_pass_report(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    go_no_go = decision.get("go_no_go") or decision.get("result") or report.get("go_no_go")
    status = report.get("status") or report.get("result")
    # STALE and BLOCKED are never PASS.
    if str(status).upper() in ("STALE", "BLOCKED"):
        return False
    return (
        str(status).upper() == "PASS"
        and _int_value(report.get("collected")) > 0
        and _int_value(report.get("failed")) == 0
        and _int_value(report.get("errors")) == 0
        and _int_value(report.get("skipped")) == 0
        and _int_value(report.get("exit_code")) == 0
        and (go_no_go is None or str(go_no_go).upper() == "GO")
    )


def _check_m3a_stale(
    m3a: dict[str, Any] | None,
    current_dir: Path,
) -> dict[str, Any] | None:
    """Return a blocker dict when the M3a RC is stale, None otherwise.

    Loads frontend_full_suite_staged_report and report_truth_preflight from
    *current_dir* and delegates the freshness comparison to check_staleness().
    DOC_LINT is already loaded by the caller; we reload it here to avoid
    changing the function signature of evaluate().
    """
    frontend_full_path = current_dir / FRONTEND_FULL_SUITE
    preflight_path = current_dir / PREFLIGHT
    doc_lint_path = current_dir / DOC_LINT

    def _quick_load(p: Path) -> dict[str, Any] | None:
        if not p.exists():
            return None
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    stale_result = check_staleness(
        m3a,
        _quick_load(frontend_full_path),
        _quick_load(preflight_path),
        _quick_load(doc_lint_path),
    )
    if not stale_result.is_stale:
        return None
    return {
        "id": "m3a_rc_stale",
        "type": "stale_guard",
        "severity": "blocking",
        "detail": (
            "M3a RC is STALE: mandatory input reports are newer than the RC. "
            f"Regenerate with: python scripts/generate_m3a_release_candidate.py "
            f"({stale_result.stale_reason})"
        ),
        "source": f"reports/current/{M3A_RC}",
        "stale_reasons": stale_result.reasons,
    }


def _doc_lint_errors(report: dict[str, Any] | None) -> int:
    if report is None:
        return 1
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return _int_value(summary.get("errors"))


def _known_limitations_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    limitations = report.get("limitations", []) if report else []
    if not isinstance(limitations, list):
        limitations = []
    active_limitations = [
        item for item in limitations
        if isinstance(item, dict)
        and str(item.get("status", "open")).lower() not in {"resolved", "closed", "released"}
    ]
    blocking = [
        item for item in active_limitations
        if item.get("blockiert_gate")
    ]
    operations_open = [
        item for item in active_limitations
        if not item.get("blockiert_gate")
        and (
            "Operations" in str(item.get("zielphase", ""))
            or "Operations" in str(item.get("bereich", ""))
            or "M4e" in str(item.get("bereich", ""))
        )
    ]
    return {
        "total": len(limitations),
        "active": len(active_limitations),
        "blocking": len(blocking),
        "blocking_ids": [str(item.get("id")) for item in blocking],
        "operations_explicitly_released": len(operations_open) == 0,
        "operations_open_ids": [str(item.get("id")) for item in operations_open],
    }


def _summary(report: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    if report is None:
        return {"available": False, "error": error}
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    return {
        "available": True,
        "report_name": report.get("report_name"),
        "status": report.get("status"),
        "result": report.get("result"),
        "decision": decision.get("go_no_go") or decision.get("result") or report.get("go_no_go"),
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "errors": report.get("errors"),
        "skipped": report.get("skipped"),
        "exit_code": report.get("exit_code"),
        "timestamp": report.get("timestamp") or report.get("generated_at"),
    }


def _phase(
    phase_id: str,
    label: str,
    *,
    passed: bool,
    decision: str,
    gate_id: str,
    source: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": phase_id,
        "label": label,
        "status": "gate_passed" if passed else "blocked",
        "decision": decision,
        "gate_id": gate_id,
        "gate_status": "PASS" if passed else "FAIL",
        "source": source,
        "blockers": blockers,
    }


def evaluate(
    current_dir: Path = CURRENT_DIR,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(timezone.utc).isoformat()
    m3a, m3a_error = _load_json(current_dir / M3A_RC)
    m4, m4_error = _load_json(current_dir / M4_BACKEND_RC)
    doc_lint, doc_error = _load_json(current_dir / DOC_LINT)
    known, known_error = _load_json(current_dir / KNOWN_LIMITATIONS)
    m4e_operations, m4e_operations_error = _load_json(current_dir / M4E_OPERATIONS_RELEASE)

    # Stale guard: checked before _is_pass_report so a stale RC is never PASS.
    m3a_stale_blocker = _check_m3a_stale(m3a, current_dir)
    m3a_pass = _is_pass_report(m3a) and m3a_stale_blocker is None
    m4_pass = _is_pass_report(m4)
    m4e_operations_pass = _is_pass_report(m4e_operations)
    doc_errors = _doc_lint_errors(doc_lint)
    known_summary = _known_limitations_summary(known)
    m5_preparation_allowed = m4_pass
    m5_implementation_allowed = (
        m4_pass
        and m4e_operations_pass
        and known_summary["operations_explicitly_released"]
    )

    blockers: list[dict[str, Any]] = []
    m3a_blockers: list[dict[str, Any]] = []
    m4_blockers: list[dict[str, Any]] = []
    release_blockers: list[dict[str, Any]] = []
    m5_impl_blockers: list[dict[str, Any]] = []

    if m3a_stale_blocker is not None:
        m3a_blockers.append(m3a_stale_blocker)
    if m3a_error or not m3a_pass:
        m3a_blockers.append({
            "id": "m3a_rc_not_pass",
            "type": "release_candidate",
            "severity": "blocking",
            "detail": f"{M3A_RC} must be PASS/GO (not STALE/BLOCKED)",
            "source": f"reports/current/{M3A_RC}",
        })
    if m4_error or not m4_pass:
        m4_blockers.append({
            "id": "m4_backend_rc_not_pass",
            "type": "release_candidate",
            "severity": "blocking",
            "detail": f"{M4_BACKEND_RC} must be PASS/GO",
            "source": f"reports/current/{M4_BACKEND_RC}",
        })
    if doc_error or doc_errors:
        release_blockers.append({
            "id": "documentation_truth_lint_errors",
            "type": "documentation",
            "severity": "blocking",
            "detail": f"{DOC_LINT} has {doc_errors} error(s) or is unavailable",
            "source": f"reports/current/{DOC_LINT}",
        })
    if known_error:
        release_blockers.append({
            "id": "known_limitations_missing",
            "type": "known_limitations",
            "severity": "blocking",
            "detail": f"{KNOWN_LIMITATIONS} is required as current input",
            "source": f"reports/current/{KNOWN_LIMITATIONS}",
        })
    if m4_pass and (m4e_operations_error or not m4e_operations_pass):
        m5_impl_blockers.append({
            "id": "m5_implementation_no_go_until_m4e_operations_release",
            "type": "dependency",
            "severity": "blocking",
            "detail": f"{M4E_OPERATIONS_RELEASE} must be PASS/GO",
            "source": f"reports/current/{M4E_OPERATIONS_RELEASE}",
        })
    if m4_pass and not known_summary["operations_explicitly_released"]:
        m5_impl_blockers.append({
            "id": "m5_implementation_blocked_by_known_operations_limitation",
            "type": "known_limitations",
            "severity": "blocking",
            "detail": "known_limitations.json still contains an active M4e/Operations limitation",
            "source": f"reports/current/{KNOWN_LIMITATIONS}",
        })

    blockers.extend(m3a_blockers)
    blockers.extend(m4_blockers)
    blockers.extend(release_blockers)

    phases = {
        "m3a": _phase(
            "m3a",
            "M3a Frontend Foundation",
            passed=m3a_pass,
            decision="GO" if m3a_pass else "NO_GO",
            gate_id="m3a_release_candidate_gate",
            source=f"reports/current/{M3A_RC}",
            blockers=m3a_blockers,
        ),
        "m4": _phase(
            "m4",
            "M4 Backend",
            passed=m4_pass,
            decision="GO" if m4_pass else "NO_GO",
            gate_id="m4_backend_release_candidate_gate",
            source=f"reports/current/{M4_BACKEND_RC}",
            blockers=m4_blockers,
        ),
        "m5_preparation": _phase(
            "m5_preparation",
            "M5 Vorbereitung",
            passed=m5_preparation_allowed,
            decision="GO" if m5_preparation_allowed else "NO_GO",
            gate_id="m5_preparation_gate",
            source=f"reports/current/{M4_BACKEND_RC}",
            blockers=[] if m5_preparation_allowed else m4_blockers,
        ),
        "m5_implementation": _phase(
            "m5_implementation",
            "M5 Implementierung",
            passed=m5_implementation_allowed,
            decision="GO" if m5_implementation_allowed else "NO_GO",
            gate_id="m5_implementation_gate",
            source=f"reports/current/{M4E_OPERATIONS_RELEASE}",
            blockers=[] if m5_implementation_allowed else m5_impl_blockers,
        ),
    }

    release_allowed = m3a_pass and m4_pass and doc_errors == 0 and not known_error
    progress = round(
        (25 if m3a_pass else 0)
        + (35 if m4_pass else 0)
        + (20 if m5_preparation_allowed else 0)
        + (20 if m5_implementation_allowed else 0),
        1,
    )

    return {
        "report_schema_version": SCHEMA_VERSION,
        "report_name": "masterplan_status",
        "generated_by": "masterplan_status_engine_v3",
        "generated_at": generated_at,
        "authority": {
            "source_of_truth": "reports/current release-candidate artifacts",
            "manual_status_override_allowed": False,
            "engine_version": 3,
            "rule": "M3a and M4 status are derived from RC reports; M5 implementation requires PASS/GO in the explicit M4e/Operations release report.",
        },
        "inputs": {
            "current_reports": {
                M3A_RC: _summary(m3a, m3a_error),
                M4_BACKEND_RC: _summary(m4, m4_error),
                M4E_OPERATIONS_RELEASE: _summary(m4e_operations, m4e_operations_error),
                DOC_LINT: _summary(doc_lint, doc_error),
                KNOWN_LIMITATIONS: {
                    "available": known is not None,
                    "error": known_error,
                    **known_summary,
                },
            },
        },
        "overall": {
            "status": "pass" if release_allowed else "blocked",
            "progress_percent": progress,
            "release_allowed": release_allowed,
            "blocker_count": len(blockers),
        },
        "phases": phases,
        "gate_hierarchy": {
            "result": "PASS" if release_allowed else "FAIL",
            "gates": {
                phase["gate_id"]: {
                    "status": phase["gate_status"],
                    "blockers": [b["detail"] for b in phase["blockers"]],
                }
                for phase in phases.values()
            },
        },
        "documentation_lint": {
            "available": doc_lint is not None,
            "result": (doc_lint or {}).get("result") or (doc_lint or {}).get("status"),
            "errors": doc_errors,
            "warnings": _int_value(((doc_lint or {}).get("summary") or {}).get("warnings")),
            "source": f"reports/current/{DOC_LINT}",
        },
        "known_limitations": {
            "source": f"reports/current/{KNOWN_LIMITATIONS}",
            **known_summary,
        },
        "m5": {
            "preparation_allowed": m5_preparation_allowed,
            "implementation_allowed": m5_implementation_allowed,
            "implementation_decision": "GO" if m5_implementation_allowed else "NO_GO",
            "implementation_gate_dependency": {
                "source": f"reports/current/{M4E_OPERATIONS_RELEASE}",
                "operations_release_status": "GO" if m4e_operations_pass else "NO_GO",
                "satisfied": m4e_operations_pass and known_summary["operations_explicitly_released"],
            },
            "implementation_blockers": m5_impl_blockers,
        },
        "blockers": blockers,
        "timestamp": generated_at,
        "exit_code": 0 if release_allowed else 1,
    }


def render_status_section(payload: dict[str, Any]) -> str:
    lines = [
        "<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->",
        "## Maschinenstatus Masterplan",
        "",
        f"Stand: `{payload['generated_at']}`",
        f"Engine: `{payload['generated_by']}`",
        "",
        f"Gesamtstatus: `{payload['overall']['status'].upper()}`",
        f"Fortschritt: `{payload['overall']['progress_percent']}%`",
        f"Release-Freigabe: `{'ja' if payload['overall']['release_allowed'] else 'nein'}`",
        f"Blocker: `{payload['overall']['blocker_count']}`",
        "",
        "> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.",
        "",
        "### Phasen",
        "",
        "| Phase | Status | Entscheidung | Gate | Gate-Status |",
        "|---|---|---|---|---|",
    ]
    for phase in payload["phases"].values():
        lines.append(
            f"| {phase['label']} | `{phase['status']}` | `{phase['decision']}` | "
            f"`{phase['gate_id']}` | `{phase['gate_status']}` |"
        )
    lines.extend([
        "",
        "### M5",
        "",
        f"- Vorbereitung erlaubt: `{'ja' if payload['m5']['preparation_allowed'] else 'nein'}`",
        f"- Implementierung erlaubt: `{'ja' if payload['m5']['implementation_allowed'] else 'nein'}`",
        f"- Implementierungsentscheidung: `{payload['m5']['implementation_decision']}`",
        "",
        "### Dokumentations-Lint",
        "",
        f"- Ergebnis: `{payload['documentation_lint']['result']}`",
        f"- Errors: `{payload['documentation_lint']['errors']}`  Warnings: `{payload['documentation_lint']['warnings']}`",
        "",
        "### Blocker",
        "",
    ])
    if payload["blockers"]:
        lines.extend(f"- `{item['id']}`: {item['detail']}" for item in payload["blockers"])
    else:
        lines.append("- keine Release-Blocker")
    if payload["m5"]["implementation_blockers"]:
        lines.append("")
        lines.append("### M5-Implementierungsblocker")
        lines.append("")
        lines.extend(
            f"- `{item['id']}`: {item['detail']} Quelle: `{item['source']}`."
            for item in payload["m5"]["implementation_blockers"]
        )
    lines.extend([
        "",
        "<!-- END GENERATED MASTERPLAN STATUS v3 -->",
        "",
    ])
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], output_json: Path, output_section: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_section.parent.mkdir(parents=True, exist_ok=True)
    output_section.write_text(render_status_section(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Masterplan Status Engine v3")
    parser.add_argument("--current-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-section", type=Path, default=DEFAULT_OUTPUT_SECTION)
    args = parser.parse_args(argv)

    payload = evaluate(args.current_dir)
    write_outputs(payload, args.output_json, args.output_section)
    print(f"Masterplan Status v3 = {payload['overall']['status'].upper()}")
    print(f"  Progress : {payload['overall']['progress_percent']}%")
    print(f"  Release  : {'ja' if payload['overall']['release_allowed'] else 'nein'}")
    print(f"  M5 Prep  : {'ja' if payload['m5']['preparation_allowed'] else 'nein'}")
    print(f"  M5 Impl  : {payload['m5']['implementation_decision']}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_section}")
    return 0 if payload["overall"]["release_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
lementierung erlaubt: `{'ja' if payload['m5']['implementation_allowed'] else 'nein'}`",
        f"- Implementierungsentscheidung: `{payload['m5']['implementation_decision']}`",
        "",
        "### Dokumentations-Lint",
        "",
        f"- Ergebnis: `{payload['documentation_lint']['result']}`",
        f"- Errors: `{payload['documentation_lint']['errors']}`  Warnings: `{payload['documentation_lint']['warnings']}`",
        "",
        "### Blocker",
        "",
    ])
    if payload["blockers"]:
        lines.extend(f"- `{item['id']}`: {item['detail']}" for item in payload["blockers"])
    else:
        lines.append("- keine Release-Blocker")
    if payload["m5"]["implementation_blockers"]:
        lines.append("")
        lines.append("### M5-Implementierungsblocker")
        lines.append("")
        lines.extend(
            f"- `{item['id']}`: {item['detail']} Quelle: `{item['source']}`."
            for item in payload["m5"]["implementation_blockers"]
        )
    lines.extend([
        "",
        "<!-- END GENERATED MASTERPLAN STATUS v3 -->",
        "",
    ])
    return "\n".join(lines)


def write_outputs(
    current_dir: Path = CURRENT_DIR,
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_section: Path = DEFAULT_OUTPUT_SECTION,
) -> dict[str, Any]:
    payload = evaluate(current_dir)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_section.parent.mkdir(parents=True, exist_ok=True)
    output_section.write_text(render_status_section(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the masterplan status report v3.")
    parser.add_argument("--current-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-section", type=Path, default=DEFAULT_OUTPUT_SECTION)
    args = parser.parse_args(argv)
    payload = write_outputs(args.current_dir, args.output_json, args.output_section)
    status = payload["overall"]["status"]
    print(f"Masterplan Status: {status.upper()}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_section}")
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
