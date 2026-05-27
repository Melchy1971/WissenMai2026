from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DOCS_DIR = REPO_ROOT / "docs"

DEFAULT_OUTPUT_JSON = REPORTS_DIR / "masterplan_status.json"
DEFAULT_OUTPUT_SECTION = REPORTS_DIR / "masterplan_status_section.md"
DEFAULT_SCHEMA = DOCS_DIR / "masterplan_status.schema.json"

STATUS_PROGRESS = {
    "draft": 0.0,
    "implemented": 0.35,
    "tested": 0.5,
    "truth_validated": 0.7,
    "gate_passed": 0.9,
    "released": 1.0,
    "blocked": 0.0,
    "missing": 0.0,
}

PHASE_WEIGHTS = {
    "m3a": 25.0,
    "m4": 35.0,
    "m5": 25.0,
    "governance": 15.0,
}


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"JSON root must be object: {path}"
    return payload, None


def _go_no_go_result(payload: dict[str, Any]) -> str | None:
    value = payload.get("go_no_go")
    if isinstance(value, dict):
        result = value.get("result")
        return result if isinstance(result, str) else None
    return value if isinstance(value, str) else None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _truth_score(report: dict[str, Any] | None) -> float | None:
    if not report:
        return None
    collected = report.get("collected")
    passed = report.get("passed")
    if not isinstance(collected, int) or not isinstance(passed, int) or collected <= 0:
        return None
    return round((passed / collected) * 100, 2)


def _load_artifacts(report_dir: Path, docs_dir: Path) -> dict[str, Any]:
    # Prefer reports/current/<gate>.json, fallback to legacy reports/
    current_dir = report_dir / "current"
    paths = {
        "m3a_release_candidate": (current_dir / "m3a_release_candidate.json", report_dir / "m3a_release_candidate.json"),
        "m4_release_candidate": (current_dir / "m4_release_candidate.json", report_dir / "m4_release_candidate.json"),
        "frontend_truth": (current_dir / "frontend_truth_report.json", report_dir / "frontend_truth_report.json"),
        "postgres_truth": (current_dir / "postgres_truth_report.json", report_dir / "postgres_truth_report.json"),
        "gate_hierarchy": (current_dir / "gate_hierarchy_result.json", report_dir / "gate_hierarchy_result.json"),
        "gate_drift": (current_dir / "gate_drift_report.json", report_dir / "gate_drift_report.json"),
        "documentation_audit": (current_dir / "documentation_release_audit.json", report_dir / "documentation_release_audit.json"),
        "known_limitations": (docs_dir / "known_limitations.json", docs_dir / "known_limitations.json"),
        "truth_marker_taxonomy": (current_dir / "truth_marker_taxonomy.json", report_dir / "truth_marker_taxonomy.json"),
    }
    artifacts: dict[str, Any] = {}
    for key, (current_path, legacy_path) in paths.items():
        if current_path.exists():
            payload, error = _load_json(current_path)
            path_used = current_path
        else:
            payload, error = _load_json(legacy_path)
            path_used = legacy_path
        artifacts[key] = {
            "path": _rel(path_used),
            "available": payload is not None,
            "payload": payload,
            "error": error,
        }
    return artifacts


def _m3a_phase(artifacts: dict[str, Any]) -> dict[str, Any]:
    rc = artifacts["m3a_release_candidate"]["payload"]
    if not rc:
        return {
            "id": "m3a",
            "label": "M3a Frontend Foundation",
            "status": "missing",
            "decision": "NO_GO",
            "score": None,
            "source": artifacts["m3a_release_candidate"]["path"],
            "blockers": [artifacts["m3a_release_candidate"]["error"]],
        }
    status = rc.get("status", "draft")
    decision = _go_no_go_result(rc) or "UNKNOWN"
    scores = rc.get("scores", {}) if isinstance(rc.get("scores"), dict) else {}
    return {
        "id": "m3a",
        "label": "M3a Frontend Foundation",
        "status": status,
        "decision": decision,
        "score": _as_float(scores.get("m3a_gate_score")),
        "source": artifacts["m3a_release_candidate"]["path"],
        "blockers": rc.get("blockers", []) if isinstance(rc.get("blockers"), list) else [],
    }


def _m4_phase(artifacts: dict[str, Any]) -> dict[str, Any]:
    rc = artifacts["m4_release_candidate"]["payload"]
    if not rc:
        return {
            "id": "m4",
            "label": "M4 Stabilization",
            "status": "missing",
            "decision": "NO_GO",
            "score": None,
            "source": artifacts["m4_release_candidate"]["path"],
            "blockers": [artifacts["m4_release_candidate"]["error"]],
        }
    decision = _go_no_go_result(rc) or "UNKNOWN"
    status = rc.get("status", "draft")
    blockers = rc.get("blockers", []) if isinstance(rc.get("blockers"), list) else []
    postgres_truth = artifacts["postgres_truth"]["payload"]
    return {
        "id": "m4",
        "label": "M4 Stabilization",
        "status": status,
        "decision": decision,
        "score": _truth_score(postgres_truth),
        "source": artifacts["m4_release_candidate"]["path"],
        "blockers": blockers,
    }


def _dependent_phase(
    *,
    phase_id: str,
    label: str,
    dependency: dict[str, Any],
    blocking_gate: str,
    limitations: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers = [
        {
            "id": item.get("id"),
            "severity": "blocking",
            "detail": item.get("beschreibung"),
            "source": "docs/known_limitations.json",
        }
        for item in limitations
        if blocking_gate in item.get("blockiert_gate", [])
    ]
    blocked = dependency.get("decision") != "GO" and dependency.get("status") != "gate_passed"
    if blocked and not blockers:
        blockers.append(
            {
                "id": f"{phase_id}_dependency_blocked",
                "severity": "blocking",
                "detail": f"{label} ist durch {dependency['label']} blockiert.",
                "source": dependency.get("source"),
            }
        )
    return {
        "id": phase_id,
        "label": label,
        "status": "blocked" if blocked or blockers else "draft",
        "decision": "NO_GO" if blocked or blockers else "GO",
        "score": None,
        "source": "docs/known_limitations.json",
        "blockers": blockers,
    }


def _known_limitations(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    payload = artifacts["known_limitations"]["payload"]
    if not payload:
        return []
    limitations = payload.get("limitations", [])
    return limitations if isinstance(limitations, list) else []


def _gate_scores(artifacts: dict[str, Any], phases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    m4_rc = artifacts["m4_release_candidate"]["payload"] or {}
    m4_scores = m4_rc.get("m4_scores", {}) if isinstance(m4_rc.get("m4_scores"), dict) else {}
    postgres = artifacts["postgres_truth"]["payload"] or {}
    return {
        "m3a_gate": {
            "score": phases["m3a"].get("score"),
            "status": phases["m3a"].get("status"),
            "source": phases["m3a"].get("source"),
        },
        "frontend_truth": {
            "score": _truth_score(artifacts["frontend_truth"]["payload"]),
            "source": artifacts["frontend_truth"]["path"],
        },
        "m4a_auth": {
            "score": m4_scores.get("m4a_auth", {}).get("score") if isinstance(m4_scores.get("m4a_auth"), dict) else None,
            "status": m4_scores.get("m4a_auth", {}).get("status") if isinstance(m4_scores.get("m4a_auth"), dict) else None,
            "source": "reports/m4_release_candidate.json",
        },
        "m4b_upload_queue": {
            "score": m4_scores.get("m4b_upload_queue", {}).get("score") if isinstance(m4_scores.get("m4b_upload_queue"), dict) else None,
            "status": m4_scores.get("m4b_upload_queue", {}).get("status") if isinstance(m4_scores.get("m4b_upload_queue"), dict) else None,
            "source": "reports/m4_release_candidate.json",
        },
        "m4c_lifecycle_retrieval": {
            "score": m4_scores.get("m4c_lifecycle_retrieval", {}).get("score") if isinstance(m4_scores.get("m4c_lifecycle_retrieval"), dict) else None,
            "status": m4_scores.get("m4c_lifecycle_retrieval", {}).get("status") if isinstance(m4_scores.get("m4c_lifecycle_retrieval"), dict) else None,
            "source": "reports/m4_release_candidate.json",
        },
        "m4_postgres_truth": {
            "score": _truth_score(postgres),
            "collected": postgres.get("collected"),
            "passed": postgres.get("passed"),
            "failed": postgres.get("failed"),
            "errors": postgres.get("errors"),
            "exit_code": postgres.get("pytest_exit_code", postgres.get("exit_code")),
            "source": artifacts["postgres_truth"]["path"],
        },
    }


def _blockers(artifacts: dict[str, Any], phases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for phase in phases.values():
        for blocker in phase.get("blockers", []):
            if isinstance(blocker, dict):
                normalized = {"phase": phase["id"], **blocker}
                normalized.setdefault("source", phase.get("source"))
                blockers.append(normalized)
            else:
                blockers.append({"phase": phase["id"], "id": "phase_blocker", "severity": "blocking", "detail": blocker, "source": phase.get("source")})

    for item in _known_limitations(artifacts):
        gates = item.get("blockiert_gate", [])
        if gates:
            blockers.append(
                {
                    "phase": item.get("zielphase"),
                    "id": item.get("id"),
                    "severity": "blocking",
                    "detail": item.get("beschreibung"),
                    "blocked_gates": gates,
                    "source": "docs/known_limitations.json",
                }
            )

    doc_audit = artifacts["documentation_audit"]["payload"]
    if doc_audit and doc_audit.get("release_decision", {}).get("freigabe") != "ja":
        for finding_id in doc_audit.get("release_decision", {}).get("blocking_findings", []):
            blockers.append(
                {
                    "phase": "documentation",
                    "id": finding_id,
                    "severity": "blocking",
                    "detail": "Documentation Release Audit blockiert Freigabe.",
                    "source": "reports/documentation_release_audit.json",
                }
            )

    drift = artifacts["gate_drift"]["payload"]
    if drift and drift.get("result") != "PASS":
        blockers.append(
            {
                "phase": "gate_drift",
                "id": "gate_drift_fail",
                "severity": "blocking",
                "detail": f"Gate Drift Detection meldet {len(drift.get('findings', []))} Findings.",
                "source": "reports/gate_drift_report.json",
            }
        )
    return blockers


def _overall_progress(phases: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for phase_id, weight in PHASE_WEIGHTS.items():
        status = phases[phase_id].get("status", "draft")
        total += weight * STATUS_PROGRESS.get(status, 0.0)
    return round(total, 1)


def build_masterplan_status(
    *,
    report_dir: Path = REPORTS_DIR,
    docs_dir: Path = DOCS_DIR,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).isoformat()
    artifacts = _load_artifacts(report_dir, docs_dir)
    limitations = _known_limitations(artifacts)

    m3a = _m3a_phase(artifacts)
    m4 = _m4_phase(artifacts)
    m5 = _dependent_phase(
        phase_id="m5",
        label="M5 Start",
        dependency=m4,
        blocking_gate="m5_start_gate",
        limitations=limitations,
    )
    governance = _dependent_phase(
        phase_id="governance",
        label="Operational Governance",
        dependency=m5,
        blocking_gate="operational_governance_gate",
        limitations=limitations,
    )
    phases = {phase["id"]: phase for phase in (m3a, m4, m5, governance)}
    blockers = _blockers(artifacts, phases)
    gate_scores = _gate_scores(artifacts, phases)
    documentation_audit = artifacts["documentation_audit"]["payload"] or {}
    gate_drift = artifacts["gate_drift"]["payload"] or {}

    return {
        "version": 1,
        "generated_at": generated_at,
        "schema": "docs/masterplan_status.schema.json",
        "authority": {
            "source_of_truth": "machine_artifacts",
            "manual_status_override_allowed": False,
            "rule": "Manuelle Statusaussagen duerfen maschinell erzeugten Status nicht ueberschreiben.",
        },
        "inputs": {
            key: {"path": value["path"], "available": value["available"], "error": value["error"]}
            for key, value in artifacts.items()
        },
        "overall": {
            "status": "blocked" if blockers else "pass",
            "progress_percent": _overall_progress(phases),
            "release_allowed": False if blockers else True,
            "blocker_count": len(blockers),
        },
        "phases": phases,
        "gate_scores": gate_scores,
        "blockers": blockers,
        "known_limitations_summary": {
            "total": len(limitations),
            "blocking": sum(1 for item in limitations if item.get("blockiert_gate")),
            "non_blocking": sum(1 for item in limitations if not item.get("blockiert_gate")),
        },
        "documentation_audit": {
            "source": artifacts["documentation_audit"]["path"],
            "freigabe": documentation_audit.get("release_decision", {}).get("freigabe"),
            "blocking_findings": documentation_audit.get("release_decision", {}).get("blocking_findings", []),
        },
        "gate_drift": {
            "source": artifacts["gate_drift"]["path"],
            "result": gate_drift.get("result"),
            "findings": len(gate_drift.get("findings", [])) if isinstance(gate_drift.get("findings"), list) else None,
        },
    }


def render_status_section(payload: dict[str, Any]) -> str:
    lines = [
        "<!-- BEGIN GENERATED MASTERPLAN STATUS -->",
        "## Maschinenstatus Masterplan",
        "",
        f"Stand: `{payload['generated_at']}`",
        "",
        f"Gesamtstatus: `{payload['overall']['status']}`",
        f"Gesamtfortschritt: `{payload['overall']['progress_percent']}%`",
        f"Freigabe: `{'ja' if payload['overall']['release_allowed'] else 'nein'}`",
        "",
        "> Dieser Abschnitt ist maschinell aus Artefakten generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.",
        "",
        "### Phasen",
        "",
        "| Phase | Status | Entscheidung | Score | Quelle |",
        "|---|---|---|---|---|",
    ]
    for phase in payload["phases"].values():
        score = "-" if phase.get("score") is None else f"{phase['score']}"
        lines.append(
            f"| {phase['label']} | `{phase['status']}` | `{phase['decision']}` | {score} | `{phase['source']}` |"
        )
    lines.extend(["", "### Gate-Scores", "", "| Gate | Score | Status | Quelle |", "|---|---:|---|---|"])
    for gate_id, gate in payload["gate_scores"].items():
        score = "-" if gate.get("score") is None else f"{gate['score']}"
        status = gate.get("status") or "-"
        lines.append(f"| `{gate_id}` | {score} | `{status}` | `{gate.get('source')}` |")

    lines.extend(["", "### Blocker", ""])
    if payload["blockers"]:
        for blocker in payload["blockers"]:
            source = blocker.get("source") or "-"
            lines.append(
                f"- `{blocker.get('id')}` ({blocker.get('phase')}, {blocker.get('severity')}): {blocker.get('detail')} Quelle: `{source}`"
            )
    else:
        lines.append("- keine")
    lines.append("<!-- END GENERATED MASTERPLAN STATUS -->")
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], json_path: Path, section_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    section_path.write_text(render_status_section(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate machine-derived masterplan status from gate artifacts.")
    parser.add_argument("--report-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-section", type=Path, default=DEFAULT_OUTPUT_SECTION)
    args = parser.parse_args(argv)

    payload = build_masterplan_status(report_dir=args.report_dir, docs_dir=args.docs_dir)
    write_outputs(payload, args.output_json, args.output_section)
    print(f"Masterplan Status = {payload['overall']['status']}")
    print(f"Progress: {payload['overall']['progress_percent']}%")
    print(f"Blockers: {payload['overall']['blocker_count']}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_section}")
    return 0 if payload["overall"]["release_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
