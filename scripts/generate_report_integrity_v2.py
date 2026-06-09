from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gate_engine import parse_timestamp, status_values  # noqa: E402
from report_validator import validate_payload  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
HIERARCHY_JSON = REPO_ROOT / "docs" / "gate_hierarchy.json"
OUTPUT_REPORT = "report_integrity_v2.json"
REPORT_NAME = "report_integrity_v2"
MAX_REPORT_AGE_HOURS = 168
VALID_STATUS_VALUES = {"PASS", "FAIL", "BLOCKED", "INFO", "DRAFT", "PREPARED", "PARTIAL_PASS", "COMPLETED", "WARN"}


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"read_error: {exc}"
    if not raw.strip():
        return None, "empty file"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be object"
    return payload, None


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _issue(
    issues: list[dict[str, Any]],
    *,
    check: str,
    file: str,
    code: str,
    detail: str,
    severity: str = "blocking",
    repair_action: str | None = None,
) -> None:
    item = {
        "id": f"{check}_{Path(file).stem}_{code}",
        "check": check,
        "file": file,
        "code": code,
        "severity": severity,
        "detail": detail,
    }
    if repair_action:
        item["repair_action"] = repair_action
    issues.append(item)


def _decision_value(report: dict[str, Any]) -> str | None:
    decision = report.get("decision")
    if isinstance(decision, dict):
        value = decision.get("go_no_go") or decision.get("result")
    else:
        value = decision
    return str(value).upper().replace("-", "_") if value is not None else None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _status_consistency_issues(path: Path, report: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    file = _rel(path)
    statuses = status_values(report)
    status = report.get("status")
    result = report.get("result")
    decision = _decision_value(report)

    normalized_status = status.upper().replace("-", "_") if isinstance(status, str) else None
    if normalized_status is not None and normalized_status not in VALID_STATUS_VALUES:
        _issue(
            issues,
            check="status_consistency",
            file=file,
            code="unknown_status",
            detail=f"status has unsupported value: {status!r}",
            repair_action="Normalize status to a registered value or extend the report schema registry.",
        )

    if isinstance(status, str) and isinstance(result, str):
        normalized_result = result.upper().replace("-", "_")
        if normalized_status in {"PASS", "FAIL", "BLOCKED"} and normalized_result in {"PASS", "FAIL", "BLOCKED"} and normalized_result != normalized_status:
            _issue(
                issues,
                check="status_consistency",
                file=file,
                code="status_result_mismatch",
                detail=f"status={status!r} and result={result!r} disagree",
                repair_action="Regenerate the report so root status and result are derived from the same decision.",
            )

    if "PASS" in statuses and decision == "NO_GO":
        _issue(
            issues,
            check="status_consistency",
            file=file,
            code="pass_no_go_mismatch",
            detail="PASS report contains decision NO_GO",
            repair_action="Set status to BLOCKED/FAIL or regenerate decision as GO.",
        )

    if "BLOCKED" in statuses and decision == "GO":
        _issue(
            issues,
            check="status_consistency",
            file=file,
            code="blocked_go_mismatch",
            detail="BLOCKED report contains decision GO",
            repair_action="Set decision to NO_GO or regenerate the report from gate logic.",
        )

    collected = _int_value(report.get("collected"))
    passed = _int_value(report.get("passed"))
    failed = _int_value(report.get("failed"))
    errors = _int_value(report.get("errors"))
    skipped = _int_value(report.get("skipped"))
    if None not in (collected, passed, failed, errors, skipped):
        total = int(passed) + int(failed) + int(errors) + int(skipped)
        blocked_pre_collection = normalized_status == "BLOCKED" and int(collected) == 0 and int(errors) > 0
        if int(collected) != total and not blocked_pre_collection:
            _issue(
                issues,
                check="status_consistency",
                file=file,
                code="counter_mismatch",
                detail=f"collected={collected} but passed+failed+errors+skipped={total}",
                repair_action="Regenerate report counters from the checked criteria list.",
            )
        if "PASS" in statuses and (int(failed) > 0 or int(errors) > 0 or int(skipped) > 0):
            _issue(
                issues,
                check="status_consistency",
                file=file,
                code="pass_with_negative_counters",
                detail="PASS report has failed/errors/skipped counters greater than zero",
                repair_action="Set status to FAIL/BLOCKED or regenerate counters.",
            )


def _gate_consistency_issues(path: Path, report: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    file = _rel(path)
    report_type = str(report.get("report_type") or "").lower()
    looks_like_gate = report_type == "gate" or "gate" in report or file.endswith("_gate.json")
    if not looks_like_gate:
        return

    gate = report.get("gate")
    if not isinstance(gate, str) or not gate.strip():
        _issue(
            issues,
            check="gate_consistency",
            file=file,
            code="missing_gate",
            detail="gate report has no non-empty gate field",
            repair_action="Add the canonical gate id or regenerate this gate report.",
        )
        return

    report_name = report.get("report_name")
    if isinstance(report_name, str) and gate != report_name and not report_name.endswith(gate):
        _issue(
            issues,
            check="gate_consistency",
            file=file,
            code="gate_report_name_mismatch",
            detail=f"gate={gate!r} and report_name={report_name!r} are inconsistent",
            severity="warning",
            repair_action="Use a canonical gate id that matches report_name unless this is an intentional aggregate report.",
        )

    if "PASS" in status_values(report) and _decision_value(report) not in {None, "GO"}:
        _issue(
            issues,
            check="gate_consistency",
            file=file,
            code="pass_gate_not_go",
            detail="PASS gate report does not expose GO decision",
            repair_action="Regenerate gate decision from the same criteria as status.",
        )


def _child_gate_consistency_issues(
    current_dir: Path,
    loaded_reports: dict[str, dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    hierarchy, error = _load_json(HIERARCHY_JSON)
    if error or hierarchy is None:
        _issue(
            issues,
            check="child_gate_consistency",
            file=_rel(HIERARCHY_JSON),
            code="invalid_hierarchy",
            detail=error or "missing hierarchy",
            repair_action="Regenerate docs/gate_hierarchy.json before running parent gates.",
        )
        return

    parents = hierarchy.get("parents")
    children = hierarchy.get("children")
    if not isinstance(parents, dict) or not isinstance(children, dict):
        _issue(
            issues,
            check="child_gate_consistency",
            file=_rel(HIERARCHY_JSON),
            code="invalid_hierarchy_shape",
            detail="gate_hierarchy.json must contain parents and children objects",
            repair_action="Repair gate_hierarchy.json schema.",
        )
        return

    for parent_id, parent_spec in parents.items():
        if not isinstance(parent_spec, dict):
            continue
        mandatory_children = parent_spec.get("mandatory_children")
        if not isinstance(mandatory_children, list) or not mandatory_children:
            _issue(
                issues,
                check="child_gate_consistency",
                file=_rel(HIERARCHY_JSON),
                code="missing_mandatory_children",
                detail=f"parent gate {parent_id} has no mandatory children",
                repair_action="Declare mandatory child gates in docs/gate_hierarchy.json.",
            )
            continue
        for child_id in mandatory_children:
            child_spec = children.get(child_id)
            if not isinstance(child_spec, dict):
                _issue(
                    issues,
                    check="child_gate_consistency",
                    file=_rel(HIERARCHY_JSON),
                    code="missing_child_definition",
                    detail=f"child gate {child_id} has no child definition",
                    repair_action="Add child definition in docs/gate_hierarchy.json.",
                )
                continue

            report_path = str(child_spec.get("report") or "")
            if not report_path.startswith("reports/current/"):
                _issue(
                    issues,
                    check="child_gate_consistency",
                    file=_rel(HIERARCHY_JSON),
                    code="invalid_child_report_source",
                    detail=f"{child_id} source must be reports/current, got {report_path!r}",
                    repair_action="Point child gate source to reports/current.",
                )
                continue

            child_file = report_path.removeprefix("reports/current/")
            report = loaded_reports.get(child_file)
            if report is None:
                # Self-reference is validated after write by file/schema checks.
                if child_file == OUTPUT_REPORT:
                    continue
                _issue(
                    issues,
                    check="child_gate_consistency",
                    file=report_path,
                    code="missing_child_report",
                    detail=f"mandatory child gate {child_id} report is missing or invalid",
                    repair_action=f"Regenerate {report_path}.",
                )
                continue

            accepted = {
                str(value).upper().replace("-", "_")
                for value in child_spec.get("accepted_statuses", ["PASS"])
            }
            statuses = status_values(report)
            if statuses & {"BLOCKED", "INVALID", "STALE"}:
                _issue(
                    issues,
                    check="child_gate_consistency",
                    file=report_path,
                    code="child_blocks_parent",
                    detail=f"{child_id} has blocking status {sorted(statuses & {'BLOCKED', 'INVALID', 'STALE'})}",
                    repair_action=f"Resolve blockers in {report_path} before parent gate PASS.",
                )
            elif statuses & {"FAIL", "FAILED"}:
                _issue(
                    issues,
                    check="child_gate_consistency",
                    file=report_path,
                    code="child_fails_parent",
                    detail=f"{child_id} has failing status {sorted(statuses & {'FAIL', 'FAILED'})}",
                    repair_action=f"Fix failing criteria in {report_path}.",
                )
            elif statuses.isdisjoint(accepted):
                _issue(
                    issues,
                    check="child_gate_consistency",
                    file=report_path,
                    code="child_status_not_accepted",
                    detail=f"{child_id} status {sorted(statuses)} not in accepted statuses {sorted(accepted)}",
                    repair_action=f"Regenerate {report_path} with an accepted status.",
                )


def _collect_issues(current_dir: Path) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    loaded_reports: dict[str, dict[str, Any]] = {}
    counters = {
        "json_files_checked": 0,
        "json_valid": 0,
        "schema_valid": 0,
        "timestamps_valid": 0,
        "generated_by_valid": 0,
        "status_consistent": 0,
        "gate_consistent": 0,
    }

    for path in sorted(current_dir.glob("*.json")):
        if path.name == OUTPUT_REPORT:
            continue
        counters["json_files_checked"] += 1
        file = _rel(path)
        report, error = _load_json(path)
        if error or report is None:
            _issue(
                issues,
                check="json_validity",
                file=file,
                code="invalid_json",
                detail=error or "invalid JSON",
                repair_action=f"Regenerate or archive {file}.",
            )
            continue

        counters["json_valid"] += 1
        loaded_reports[path.name] = report

        schema_result = validate_payload(report)
        if schema_result.valid:
            counters["schema_valid"] += 1
        else:
            for schema_issue in schema_result.issues:
                _issue(
                    issues,
                    check="schema_validity",
                    file=file,
                    code=schema_issue.code,
                    detail=schema_issue.message,
                    severity="blocking",
                    repair_action=f"Regenerate {file} with schema registry fields or extend report_schema_registry.py intentionally.",
                )

        timestamp = parse_timestamp(report.get("timestamp") or report.get("generated_at"))
        if timestamp is None:
            _issue(
                issues,
                check="timestamp",
                file=file,
                code="invalid_timestamp",
                detail="timestamp/generated_at missing or not machine-readable",
                repair_action=f"Regenerate {file} with ISO 8601 timestamp.",
            )
        else:
            counters["timestamps_valid"] += 1

        generated_by = report.get("generated_by")
        if isinstance(generated_by, str) and generated_by.strip():
            counters["generated_by_valid"] += 1
        else:
            _issue(
                issues,
                check="generated_by",
                file=file,
                code="missing_generated_by",
                detail="generated_by missing or empty",
                repair_action=f"Regenerate {file} through an approved generator.",
            )

        before = len(issues)
        _status_consistency_issues(path, report, issues)
        if len(issues) == before:
            counters["status_consistent"] += 1

        before = len(issues)
        _gate_consistency_issues(path, report, issues)
        if len(issues) == before:
            counters["gate_consistent"] += 1

    _child_gate_consistency_issues(current_dir, loaded_reports, issues)
    return issues, counters, loaded_reports


def build_report(current_dir: Path = CURRENT_DIR, *, timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or datetime.now(UTC).isoformat()
    issues, counters, _loaded_reports = _collect_issues(current_dir)
    blocker_details = [item for item in issues if item.get("severity") == "blocking"]
    warnings = [item for item in issues if item.get("severity") == "warning"]
    repair_actions = [
        {
            "id": item["id"],
            "file": item["file"],
            "action": item.get("repair_action") or "Review and repair report artifact.",
        }
        for item in issues
    ]

    status = "PASS" if not blocker_details else "BLOCKED"
    criteria = [
        {"id": "json_validity", "passed": not any(item["check"] == "json_validity" for item in blocker_details)},
        {"id": "schema_validity", "passed": not any(item["check"] == "schema_validity" for item in blocker_details)},
        {"id": "timestamp", "passed": not any(item["check"] == "timestamp" for item in blocker_details)},
        {"id": "generated_by", "passed": not any(item["check"] == "generated_by" for item in blocker_details)},
        {"id": "status_consistency", "passed": not any(item["check"] == "status_consistency" for item in blocker_details)},
        {"id": "gate_consistency", "passed": not any(item["check"] == "gate_consistency" for item in blocker_details)},
        {"id": "child_gate_consistency", "passed": not any(item["check"] == "child_gate_consistency" for item in blocker_details)},
    ]
    passed = sum(1 for item in criteria if item["passed"])
    failed = len(criteria) - passed
    return {
        "report_schema_version": 1,
        "report_name": REPORT_NAME,
        "gate": REPORT_NAME,
        "generated_by": "gate_validator",
        "timestamp": now,
        "environment": "local",
        "report_type": "gate",
        "status": status,
        "result": status,
        "decision": {
            "go_no_go": "GO" if status == "PASS" else "NO_GO",
            "result": "GO" if status == "PASS" else "NO_GO",
            "manual_override_allowed": False,
        },
        "collected": len(criteria),
        "passed": passed,
        "failed": failed,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "source_command": "python scripts/generate_report_integrity_v2.py",
        "checks": criteria,
        "blockers": blocker_details,
        "blocker_details": blocker_details,
        "warnings": warnings,
        "repair_actions": repair_actions,
        "summary": {
            **counters,
            "blocker_count": len(blocker_details),
            "warning_count": len(warnings),
            "repair_action_count": len(repair_actions),
        },
    }


def write_report(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    payload = build_report()
    output_path = CURRENT_DIR / OUTPUT_REPORT
    write_report(payload, output_path)
    print(f"report_integrity_v2 = {payload['status']} blockers={len(payload['blocker_details'])}")
    print(f"Wrote: {output_path}")
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
