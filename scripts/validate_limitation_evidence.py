from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "reports" / "current" / "known_limitations.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "current" / "limitation_evidence_validation.json"

REQUIRED_OPEN_BLOCKING_FIELDS = (
    "evidence_report",
    "next_action",
    "target_phase",
    "severity",
)
RESOLVED_REQUIRED_FIELDS = ("resolved_at", "resolving_report")
PASS_STATUSES = {"PASS", "GO", "COMPLETED"}
OPEN_EVIDENCE_STATUSES = {
    "BLOCKED",
    "FAIL",
    "FAILED",
    "WARN",
    "WARNING",
    "DRAFT",
    "PARTIAL_PASS",
    "NO_GO",
    "INFO",
}
ALLOWED_GATES_BY_TARGET_PHASE = {
    "M5A": {
        "m5_truth_gate",
        "m5a_start_gate",
        "m5a_data_quality_gate",
        "report_integrity_v2",
        "documentation_truth_lint",
        "data_quality_report",
        "duplicate_detector_gate",
        "metadata_detector_gate",
        "lifecycle_integrity_gate",
        "source_status_integrity_gate",
        "orphan_detector_gate",
    },
    "M5B_PREP": {"m5b_start_gate"},
    "M5B_IMPL": {"m5b_implementation_gate"},
    "GOVERNANCE": {"operational_governance_gate"},
    "M5C_PLUS": set(),
}


@dataclass(frozen=True)
class EvidenceIssue:
    id: str
    limitation_id: str
    severity: str
    code: str
    field: str
    detail: str
    fix: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(
    known_limitations_path: Path = DEFAULT_REPORT,
    *,
    repo_root: Path = REPO_ROOT,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(timezone.utc).isoformat()
    payload, root_error = _load_json_object(known_limitations_path)
    limitations = payload.get("limitations", []) if payload else []
    if not isinstance(limitations, list):
        limitations = []

    issues: list[EvidenceIssue] = []
    if root_error:
        issues.append(EvidenceIssue(
            id="known_limitations_invalid_json",
            limitation_id="known_limitations",
            severity="blocking",
            code="invalid_known_limitations_json",
            field=str(_relative_path(known_limitations_path, repo_root)),
            detail=root_error,
            fix="Repair reports/current/known_limitations.json so it is valid JSON with a limitations array.",
        ))

    checks: list[dict[str, Any]] = []
    for index, item in enumerate(limitations):
        if not isinstance(item, dict):
            continue
        limitation_id = str(item.get("id") or f"limitations[{index}]")
        item_issues = _validate_limitation(item, repo_root=repo_root)
        issues.extend(item_issues)
        checks.append(_check_summary(item, item_issues, repo_root=repo_root))

    missing_evidence = [
        _issue_payload(issue)
        for issue in issues
        if issue.code in {
            "missing_evidence_report",
            "missing_required_field",
            "evidence_report_missing",
            "evidence_report_not_json",
            "resolving_report_missing",
            "resolving_report_not_json",
        }
    ]
    fix_list = [_fix_payload(issue, index) for index, issue in enumerate(issues, start=1)]
    blocking_issues = [issue for issue in issues if issue.severity == "blocking"]

    return {
        "report_schema_version": 1,
        "report_name": "limitation_evidence_validation",
        "generated_by": "limitation_evidence_validator",
        "generated_at": generated_at,
        "timestamp": generated_at,
        "environment": "local",
        "report_type": "validation",
        "status": "PASS" if not blocking_issues else "FAIL",
        "result": "PASS" if not blocking_issues else "FAIL",
        "source_command": "python scripts/validate_limitation_evidence.py",
        "inputs": {
            "known_limitations": _display_path(known_limitations_path, repo_root),
        },
        "rules": {
            "open_blocking_required_fields": list(REQUIRED_OPEN_BLOCKING_FIELDS),
            "owner_required": False,
            "resolved_required_fields": list(RESOLVED_REQUIRED_FIELDS),
            "blocks_gate_semantics": "non-empty blocks_gate is effective true; empty blocks_gate is effective false",
            "gate_mapping": {
                phase: sorted(gates)
                for phase, gates in ALLOWED_GATES_BY_TARGET_PHASE.items()
            },
        },
        "summary": {
            "limitations_checked": len(checks),
            "issues": len(issues),
            "blocking_issues": len(blocking_issues),
            "missing_evidence_count": len(missing_evidence),
            "fix_count": len(fix_list),
        },
        "checks": checks,
        "missing_evidence": missing_evidence,
        "fix_list": fix_list,
        "issues": [_issue_payload(issue) for issue in issues],
        "blockers": [_issue_payload(issue) for issue in blocking_issues],
    }


def _validate_limitation(item: dict[str, Any], *, repo_root: Path) -> list[EvidenceIssue]:
    limitation_id = str(item.get("id") or "unknown_limitation")
    issues: list[EvidenceIssue] = []
    status = str(item.get("status") or "").lower()
    blocks_gate = _gate_list(item)
    is_open_blocking = status == "open" and bool(blocks_gate)

    if is_open_blocking:
        for field in REQUIRED_OPEN_BLOCKING_FIELDS:
            if not _has_text(item.get(field)):
                issues.append(EvidenceIssue(
                    id=f"{limitation_id}_{field}_missing",
                    limitation_id=limitation_id,
                    severity="blocking",
                    code="missing_required_field",
                    field=field,
                    detail=f"Open blocking limitation {limitation_id} requires {field}.",
                    fix=f"Set {field} for {limitation_id}.",
                ))
        issues.extend(_evidence_report_issues(item, repo_root=repo_root))

    if status == "resolved":
        for field in RESOLVED_REQUIRED_FIELDS:
            if not _has_text(item.get(field)):
                issues.append(EvidenceIssue(
                    id=f"{limitation_id}_{field}_missing",
                    limitation_id=limitation_id,
                    severity="blocking",
                    code="missing_resolved_field",
                    field=field,
                    detail=f"Resolved limitation {limitation_id} requires {field}.",
                    fix=f"Set {field} for {limitation_id}.",
                ))
        issues.extend(_resolved_report_issues(item, repo_root=repo_root))

    if blocks_gate:
        issues.extend(_gate_mapping_issues(item, blocks_gate))

    return issues


def _evidence_report_issues(item: dict[str, Any], *, repo_root: Path) -> list[EvidenceIssue]:
    limitation_id = str(item.get("id") or "unknown_limitation")
    path_value = item.get("evidence_report")
    if not _has_text(path_value):
        return [EvidenceIssue(
            id=f"{limitation_id}_evidence_report_missing",
            limitation_id=limitation_id,
            severity="blocking",
            code="missing_evidence_report",
            field="evidence_report",
            detail=f"Open blocking limitation {limitation_id} has no evidence_report.",
            fix=f"Set evidence_report for {limitation_id} to a current JSON report that supports the blocking state.",
        )]

    evidence_path = _resolve_local_path(str(path_value), repo_root)
    if evidence_path is None:
        return [EvidenceIssue(
            id=f"{limitation_id}_evidence_report_remote",
            limitation_id=limitation_id,
            severity="blocking",
            code="evidence_report_not_local",
            field="evidence_report",
            detail=f"evidence_report for {limitation_id} must be a local JSON report, got {path_value}.",
            fix=f"Point evidence_report for {limitation_id} to a local reports/current/*.json artifact.",
        )]
    if not evidence_path.exists():
        return [EvidenceIssue(
            id=f"{limitation_id}_evidence_report_missing_file",
            limitation_id=limitation_id,
            severity="blocking",
            code="evidence_report_missing",
            field="evidence_report",
            detail=f"evidence_report does not exist: {path_value}.",
            fix=f"Generate {path_value} or update {limitation_id}.evidence_report to an existing JSON report.",
        )]

    report, error = _load_json_object(evidence_path)
    if error:
        return [EvidenceIssue(
            id=f"{limitation_id}_evidence_report_not_json",
            limitation_id=limitation_id,
            severity="blocking",
            code="evidence_report_not_json",
            field="evidence_report",
            detail=f"evidence_report is not valid JSON: {path_value}: {error}",
            fix=f"Replace {path_value} with a valid JSON report or point {limitation_id}.evidence_report elsewhere.",
        )]

    if not _open_status_matches(item, report):
        return [EvidenceIssue(
            id=f"{limitation_id}_evidence_status_mismatch",
            limitation_id=limitation_id,
            severity="blocking",
            code="report_status_mismatch",
            field="evidence_report",
            detail=(
                f"evidence_report {path_value} does not support open blocking state for {limitation_id}; "
                f"status={_report_status(report) or '-'} and limitation id was not found in the report."
            ),
            fix=(
                f"Update {limitation_id}.evidence_report to a current BLOCKED/FAIL/WARN/DRAFT report, "
                "or regenerate the evidence report so it mentions the limitation id."
            ),
        )]
    return []


def _resolved_report_issues(item: dict[str, Any], *, repo_root: Path) -> list[EvidenceIssue]:
    limitation_id = str(item.get("id") or "unknown_limitation")
    path_value = item.get("resolving_report")
    if not _has_text(path_value):
        return []

    report_path = _resolve_local_path(str(path_value), repo_root)
    if report_path is None:
        return [EvidenceIssue(
            id=f"{limitation_id}_resolving_report_remote",
            limitation_id=limitation_id,
            severity="blocking",
            code="resolving_report_not_local",
            field="resolving_report",
            detail=f"resolving_report for {limitation_id} must be local, got {path_value}.",
            fix=f"Point resolving_report for {limitation_id} to a local JSON report.",
        )]
    if not report_path.exists():
        return [EvidenceIssue(
            id=f"{limitation_id}_resolving_report_missing",
            limitation_id=limitation_id,
            severity="blocking",
            code="resolving_report_missing",
            field="resolving_report",
            detail=f"resolving_report does not exist: {path_value}.",
            fix=f"Generate {path_value} or update {limitation_id}.resolving_report to an existing JSON report.",
        )]

    report, error = _load_json_object(report_path)
    if error:
        return [EvidenceIssue(
            id=f"{limitation_id}_resolving_report_not_json",
            limitation_id=limitation_id,
            severity="blocking",
            code="resolving_report_not_json",
            field="resolving_report",
            detail=f"resolving_report is not valid JSON: {path_value}: {error}",
            fix=f"Replace {path_value} with a valid JSON report or point {limitation_id}.resolving_report elsewhere.",
        )]

    if _report_status(report) not in PASS_STATUSES and _decision(report) != "GO":
        return [EvidenceIssue(
            id=f"{limitation_id}_resolving_status_mismatch",
            limitation_id=limitation_id,
            severity="blocking",
            code="resolved_report_status_mismatch",
            field="resolving_report",
            detail=f"Resolved limitation {limitation_id} needs PASS/GO resolving_report, got status={_report_status(report) or '-'}.",
            fix=f"Regenerate {path_value} as PASS/GO or reopen {limitation_id}.",
        )]
    return []


def _gate_mapping_issues(item: dict[str, Any], blocks_gate: list[str]) -> list[EvidenceIssue]:
    limitation_id = str(item.get("id") or "unknown_limitation")
    phase = str(item.get("target_phase") or "")
    allowed = ALLOWED_GATES_BY_TARGET_PHASE.get(phase)
    if allowed is None:
        return [EvidenceIssue(
            id=f"{limitation_id}_target_phase_unknown",
            limitation_id=limitation_id,
            severity="blocking",
            code="unknown_target_phase",
            field="target_phase",
            detail=f"{limitation_id} has blocks_gate set but target_phase is unknown: {phase or '-'}",
            fix=f"Set target_phase for {limitation_id} to one of {sorted(ALLOWED_GATES_BY_TARGET_PHASE)}.",
        )]

    invalid = [gate for gate in blocks_gate if gate not in allowed]
    if not invalid:
        return []
    return [EvidenceIssue(
        id=f"{limitation_id}_blocks_gate_mapping_invalid",
        limitation_id=limitation_id,
        severity="blocking",
        code="blocks_gate_mapping_mismatch",
        field="blocks_gate",
        detail=f"{limitation_id} target_phase={phase} cannot block gates {invalid}; allowed gates are {sorted(allowed)}.",
        fix=f"Clear blocks_gate for {limitation_id} or map it to an allowed {phase} gate.",
    )]


def _check_summary(item: dict[str, Any], issues: list[EvidenceIssue], *, repo_root: Path) -> dict[str, Any]:
    evidence_path = item.get("evidence_report")
    evidence_status = None
    evidence_json_valid = None
    requires_json_evidence = str(item.get("status") or "").lower() == "open" and bool(_gate_list(item))
    if _has_text(evidence_path) and (requires_json_evidence or str(evidence_path).lower().endswith(".json")):
        local_path = _resolve_local_path(str(evidence_path), repo_root)
        if local_path is not None and local_path.exists():
            report, error = _load_json_object(local_path)
            evidence_json_valid = error is None
            if report is not None:
                evidence_status = _report_status(report)
        else:
            evidence_json_valid = False

    return {
        "id": str(item.get("id") or "unknown_limitation"),
        "status": item.get("status"),
        "severity": item.get("severity"),
        "target_phase": item.get("target_phase"),
        "blocks_gate": _gate_list(item),
        "blocks_gate_effective": bool(_gate_list(item)),
        "evidence_report": evidence_path,
        "evidence_json_valid": evidence_json_valid,
        "evidence_status": evidence_status,
        "valid": not issues,
        "issues": [issue.code for issue in issues],
    }


def _open_status_matches(item: dict[str, Any], report: dict[str, Any]) -> bool:
    status = _report_status(report)
    if status in OPEN_EVIDENCE_STATUSES:
        return True
    if _decision(report) == "NO_GO":
        return True
    limitation_id = item.get("id")
    return isinstance(limitation_id, str) and _contains_text(report, limitation_id)


def _report_status(report: dict[str, Any]) -> str | None:
    raw = report.get("status") or report.get("result")
    return str(raw).upper() if raw is not None else None


def _decision(report: dict[str, Any]) -> str | None:
    raw_decision = report.get("decision")
    if isinstance(raw_decision, dict):
        raw = raw_decision.get("go_no_go") or raw_decision.get("result") or raw_decision.get("status")
    else:
        raw = raw_decision
    return str(raw).upper().replace("-", "_") if raw is not None else None


def _contains_text(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(_contains_text(child, needle) for child in value.values())
    if isinstance(value, list):
        return any(_contains_text(child, needle) for child in value)
    return False


def _gate_list(item: dict[str, Any]) -> list[str]:
    raw = item.get("blocks_gate", [])
    return [str(value) for value in raw] if isinstance(raw, list) else []


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON root must be an object"
    return payload, None


def _resolve_local_path(value: str, repo_root: Path) -> Path | None:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return None
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _relative_path(path: Path, repo_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return path


def _display_path(path: Path, repo_root: Path) -> str:
    return _relative_path(path, repo_root).as_posix()


def _issue_payload(issue: EvidenceIssue) -> dict[str, Any]:
    return {
        "id": issue.id,
        "limitation_id": issue.limitation_id,
        "severity": issue.severity,
        "code": issue.code,
        "field": issue.field,
        "detail": issue.detail,
        "fix": issue.fix,
    }


def _fix_payload(issue: EvidenceIssue, index: int) -> dict[str, Any]:
    return {
        "priority": index,
        "limitation_id": issue.limitation_id,
        "code": issue.code,
        "action": issue.fix,
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate evidence for known limitations.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = validate(args.report)
    write_report(report, args.output)
    print(f"{report['status']} {args.output}")
    print(f"issues: {report['summary']['issues']}")
    print(f"missing_evidence: {report['summary']['missing_evidence_count']}")
    print(f"fixes: {report['summary']['fix_count']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
