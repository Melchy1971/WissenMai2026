from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
DEFAULT_TRUTH_REPORT = CURRENT_DIR / "connectivity_truth_report.json"
DEFAULT_JSON_REPORT = CURRENT_DIR / "frontend_runtime_connectivity_gate_report.json"
DEFAULT_MARKDOWN_REPORT = CURRENT_DIR / "frontend_runtime_connectivity_gate_report.md"
PASS_THRESHOLD = 90.0


@dataclass(frozen=True)
class GateCheck:
    id: str
    truth_check_id: str
    label: str
    blocker_id: str


GATE_CHECKS = (
    GateCheck("backend_reachable", "frontend_reaches_backend", "Backend erreichbar", "backend_not_reachable"),
    GateCheck("health_green", "health_reachable", "/health gruen", "health_not_green"),
    GateCheck("auth_me_reachable", "auth_me_reachable", "/auth/me erreichbar", "auth_me_not_reachable"),
    GateCheck("login_successful", "login_possible", "Login erfolgreich", "login_not_successful"),
    GateCheck(
        "workspace_bootstrap_successful",
        "workspace_bootstrap_successful",
        "Workspace Bootstrap erfolgreich",
        "workspace_bootstrap_failed",
    ),
    GateCheck("document_list_loads", "document_list_loads", "Dokumentliste laedt", "document_list_not_loaded"),
    GateCheck(
        "no_api_unreachable_normalflow",
        "no_api_unreachable_normalflow",
        "Kein API_UNREACHABLE im Normalflow",
        "api_unreachable_visible",
    ),
    GateCheck("no_cors_error", "no_cors_error", "Kein CORS Fehler", "cors_error_detected"),
    GateCheck(
        "no_mixed_content_error",
        "no_mixed_content_error",
        "Kein Mixed Content Fehler",
        "mixed_content_detected",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_index(truth_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(check.get("id")): check
        for check in truth_report.get("checks", [])
        if isinstance(check, dict) and check.get("id")
    }


def evaluate_gate(truth_report: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    checks_by_id = _check_index(truth_report)
    gate_checks: list[dict[str, Any]] = []
    runtime_blockers: list[dict[str, Any]] = []

    for definition in GATE_CHECKS:
        truth_check = checks_by_id.get(definition.truth_check_id)
        passed = bool(truth_check and truth_check.get("result") == "PASS")
        evidence = (
            str(truth_check.get("evidence", ""))
            if truth_check
            else f"Truth check {definition.truth_check_id!r} fehlt."
        )
        gate_check = {
            "id": definition.id,
            "label": definition.label,
            "truth_check_id": definition.truth_check_id,
            "result": "PASS" if passed else "FAIL",
            "evidence": evidence,
        }
        gate_checks.append(gate_check)
        if not passed:
            runtime_blockers.append(
                {
                    "id": definition.blocker_id,
                    "gate_check": definition.id,
                    "truth_check_id": definition.truth_check_id,
                    "evidence": evidence,
                }
            )

    passed_count = sum(1 for check in gate_checks if check["result"] == "PASS")
    score = round((passed_count / len(GATE_CHECKS)) * 100, 1)
    result = "PASS" if score >= PASS_THRESHOLD else "FAIL"
    decision = "CONNECTIVITY_STABLE" if result == "PASS" else "M3A_BLOCKED"

    return {
        "report_schema_version": 1,
        "report_name": "frontend_runtime_connectivity_gate_report",
        "generated_by": "gate_validator",
        "version": 1,
        "report": "Frontend Runtime Connectivity Gate Report",
        "generated_at": generated_at or _utc_now(),
        "source_truth_report": "reports/current/connectivity_truth_report.json",
        "frontend_base_url": truth_report.get("frontend_base_url"),
        "api_base_url": truth_report.get("api_base_url"),
        "score": score,
        "threshold": PASS_THRESHOLD,
        "result": result,
        "status": result,
        "gate": "m3a_preflight",
        "environment": "local",
        "collected": len(GATE_CHECKS),
        "passed": passed_count,
        "failed": len(GATE_CHECKS) - passed_count,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if result == "PASS" else 1,
        "blockers": [
            {"gate": "m3a_preflight", "severity": "critical", "reason": blocker["id"]}
            for blocker in runtime_blockers
        ],
        "source_command": "python scripts/validate_frontend_runtime_connectivity_gate.py",
        "decision": decision,
        "gate_effect": "Connectivity stabil" if result == "PASS" else "M3a blockiert",
        "checks": gate_checks,
        "runtime_blockers": runtime_blockers,
        "failure_classification": truth_report.get("failure_classification", []),
        "truth_result": truth_report.get("result"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Frontend Runtime Connectivity Gate Report",
        "",
        f"- Result: `{report['result']}`",
        f"- Decision: `{report['decision']}`",
        f"- Score: `{report['score']}` / 100",
        f"- Threshold: `>= {report['threshold']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Source: `{report['source_truth_report']}`",
        "",
        "## Checks",
        "",
        "| Check | Result | Evidence |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        evidence = str(check["evidence"]).replace("|", "\\|")
        lines.append(f"| {check['id']} | `{check['result']}` | {evidence} |")

    lines.extend(["", "## Runtime Blocker", ""])
    if report["runtime_blockers"]:
        for blocker in report["runtime_blockers"]:
            lines.append(f"- `{blocker['id']}`: {blocker['evidence']}")
    else:
        lines.append("- keine")

    lines.extend(["", "## Failure-Klassifikation", ""])
    classifications = report.get("failure_classification") or []
    if classifications:
        for item in classifications:
            lines.append(f"- `{item}`")
    else:
        lines.append("- keine")
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Frontend Runtime Connectivity Gate.")
    parser.add_argument("--truth-report", type=Path, default=DEFAULT_TRUTH_REPORT)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    truth_report = _load_json(args.truth_report)
    report = evaluate_gate(truth_report)
    write_reports(report, args.json_report, args.markdown_report)
    print(f"Frontend Runtime Connectivity Gate = {report['result']}")
    print(f"Score = {report['score']}")
    print(f"Decision = {report['decision']}")
    print(f"Wrote: {args.json_report}")
    print(f"Wrote: {args.markdown_report}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
