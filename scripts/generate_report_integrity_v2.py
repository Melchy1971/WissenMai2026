from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import shutil
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gate_engine import parse_timestamp, status_values  # noqa: E402
from report_validator import validate_payload  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
ARCHIVE_DIR = REPO_ROOT / "reports" / "archive" / "legacy"
REQUIRED_SET = REPO_ROOT / "report_integrity_required_set.json"
OUTPUT_REPORT = "report_integrity_v2.json"
REPORT_NAME = "report_integrity_v2"
DEFAULT_MAX_AGE_HOURS = 168
BLOCKING_STATUSES = {"BLOCKED", "INVALID", "STALE", "FAIL", "FAILED"}


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


def _normalize(value: Any) -> str:
    return str(value).upper().replace("-", "_")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value)


def _timestamp_slug(value: str) -> str:
    parsed = parse_timestamp(value)
    if parsed is None:
        parsed = datetime.now(UTC)
    return parsed.strftime("%Y%m%dT%H%M%SZ")


def _list_specs(required_set: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = required_set.get(key, [])
    return [item for item in value if isinstance(item, dict)]


def _spec_path(spec: dict[str, Any]) -> Path:
    path = Path(str(spec.get("file") or ""))
    return path if path.is_absolute() else REPO_ROOT / path


def _issue(
    issues: list[dict[str, Any]],
    *,
    check: str,
    file: str,
    code: str,
    detail: str,
    severity: str,
    category: str,
    repair_action: str,
) -> None:
    issues.append({
        "id": f"{category}_{check}_{Path(file).stem}_{code}",
        "category": category,
        "check": check,
        "file": file,
        "code": code,
        "severity": severity,
        "detail": detail,
        "repair_action": repair_action,
    })


def _blocking_for(category: str, spec: dict[str, Any]) -> bool:
    if category == "required":
        return True
    if category == "supporting":
        return _as_bool(spec.get("referenced_by_parent_gate")) or bool(spec.get("referenced_by"))
    return False


def _severity(category: str, spec: dict[str, Any]) -> str:
    return "blocking" if _blocking_for(category, spec) else "warning"


def _decision_value(report: dict[str, Any]) -> str | None:
    decision = report.get("decision")
    if isinstance(decision, dict):
        value = decision.get("go_no_go") or decision.get("result")
    else:
        value = decision
    return _normalize(value) if value is not None else None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _counter_issues(report: dict[str, Any], required: bool) -> list[str]:
    counter_keys = ("collected", "passed", "failed", "errors", "skipped", "exit_code")
    if not required and not all(key in report for key in counter_keys):
        return []

    collected = _int_value(report.get("collected"))
    passed = _int_value(report.get("passed"))
    failed = _int_value(report.get("failed"))
    errors = _int_value(report.get("errors"))
    skipped = _int_value(report.get("skipped"))
    exit_code = _int_value(report.get("exit_code"))
    issues: list[str] = []
    if collected is None or collected <= 0:
        issues.append("collected must be > 0")
    if passed != collected:
        issues.append("passed must equal collected")
    if failed != 0:
        issues.append("failed must be 0")
    if errors != 0:
        issues.append("errors must be 0")
    if skipped != 0:
        issues.append("skipped must be 0")
    if exit_code != 0:
        issues.append("exit_code must be 0")
    return issues


def _status_issues(report: dict[str, Any], spec: dict[str, Any], category: str) -> list[str]:
    issues: list[str] = []
    statuses = status_values(report)
    accepted = spec.get("accepted_statuses")
    if isinstance(accepted, list) and accepted:
        accepted_statuses = {_normalize(value) for value in accepted}
        if statuses.isdisjoint(accepted_statuses):
            issues.append(f"status/result must be one of {sorted(accepted_statuses)}, got {sorted(statuses)}")
    elif category in {"required", "optional"} and statuses & BLOCKING_STATUSES:
        issues.append(f"status/result contains blocking value {sorted(statuses & BLOCKING_STATUSES)}")

    required_decision = spec.get("required_decision")
    if isinstance(required_decision, str) and _decision_value(report) != _normalize(required_decision):
        issues.append(f"decision.go_no_go must be {required_decision}")

    status = report.get("status")
    result = report.get("result")
    if isinstance(status, str) and isinstance(result, str):
        normalized_status = _normalize(status)
        normalized_result = _normalize(result)
        terminal = {"PASS", "FAIL", "BLOCKED"}
        if normalized_status in terminal and normalized_result in terminal and normalized_status != normalized_result:
            issues.append(f"status={status!r} and result={result!r} disagree")

    if "PASS" in statuses and _decision_value(report) == "NO_GO":
        issues.append("PASS report contains decision NO_GO")
    if "BLOCKED" in statuses and _decision_value(report) == "GO":
        issues.append("BLOCKED report contains decision GO")
    return issues


def _validate_report(
    *,
    path: Path,
    spec: dict[str, Any],
    category: str,
    now: datetime,
    max_age_hours: int,
    issues: list[dict[str, Any]],
    evaluated: list[dict[str, Any]],
) -> None:
    rel_path = _rel(path)
    if spec.get("self_report") is True and path.name == OUTPUT_REPORT:
        evaluated.append({
            "file": rel_path,
            "category": category,
            "validation_status": "SELF_REPORT_PENDING_WRITE",
            "issues": [],
        })
        return

    severity = _severity(category, spec)
    payload, error = _load_json(path)
    if error or payload is None:
        if category == "optional" and error == "missing":
            evaluated.append({"file": rel_path, "category": category, "validation_status": "MISSING_OPTIONAL"})
            return
        _issue(
            issues,
            check="presence_json",
            file=rel_path,
            code="missing_or_invalid_json",
            detail=error or "invalid JSON",
            severity=severity,
            category=category,
            repair_action=f"Regenerate {rel_path} or archive it if it is no longer in scope.",
        )
        evaluated.append({"file": rel_path, "category": category, "validation_status": "INVALID"})
        return

    report_issues: list[str] = []
    schema_result = validate_payload(payload)
    report_issues.extend(f"{item.code}: {item.message}" for item in schema_result.issues)

    timestamp = parse_timestamp(payload.get("timestamp") or payload.get("generated_at"))
    if timestamp is None:
        report_issues.append("timestamp/generated_at missing or not machine-readable")
    elif spec.get("self_report") is not True and spec.get("allow_stale") is not True:
        if now - timestamp > timedelta(hours=int(spec.get("max_age_hours", max_age_hours))):
            report_issues.append(f"report is older than {int(spec.get('max_age_hours', max_age_hours))} hours")

    if not payload.get("generated_by"):
        report_issues.append("generated_by missing or empty")

    if spec.get("self_report") is not True:
        report_issues.extend(_status_issues(payload, spec, category))
        report_issues.extend(_counter_issues(payload, spec.get("counter_validation") == "required"))
        min_quality_score = spec.get("min_quality_score")
        if isinstance(min_quality_score, (int, float)):
            score = payload.get("quality_score")
            if not isinstance(score, (int, float)) or score < float(min_quality_score):
                report_issues.append(f"quality_score must be >= {float(min_quality_score):g}")
        if spec.get("blockers_must_be_empty") is True and payload.get("blockers") not in ([], None):
            report_issues.append("blockers must be empty")

    validation_status = "PASS" if not report_issues else ("BLOCKED" if severity == "blocking" else "WARNING")
    evaluated.append({
        "file": rel_path,
        "category": category,
        "validation_status": validation_status,
        "status": payload.get("status"),
        "result": payload.get("result"),
        "timestamp": payload.get("timestamp") or payload.get("generated_at"),
        "referenced_by_parent_gate": _blocking_for(category, spec),
        "issues": report_issues,
    })
    for index, detail in enumerate(report_issues, start=1):
        _issue(
            issues,
            check="report_validation",
            file=rel_path,
            code=f"invalid_{index}",
            detail=detail,
            severity=severity,
            category=category,
            repair_action=f"Regenerate {rel_path} with fresh, schema-valid evidence for its required set category.",
        )


def _collect_unclassified_specs(
    current_dir: Path,
    known_files: set[str],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for path in sorted(current_dir.glob("*.json")):
        rel_path = _rel(path)
        if rel_path in known_files or path.name == OUTPUT_REPORT:
            continue
        specs.append({
            "id": path.stem,
            "file": rel_path,
            "classification": "optional",
            "reason": "unclassified reports/current JSON is warning-only for Report Integrity v2",
        })
    return specs


def _archive_legacy(
    specs: list[dict[str, Any]],
    *,
    current_dir: Path,
    archive_root: Path,
    timestamp: str,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    target_dir = archive_root / f"report_integrity_v2_{_timestamp_slug(timestamp)}"
    current_root = current_dir.resolve()
    archive_resolved = archive_root.resolve()
    for spec in specs:
        source = _spec_path(spec)
        rel_source = _rel(source)
        if not source.exists():
            archived = sorted(archive_root.glob(f"report_integrity_v2_*/{source.name}"), reverse=True)
            action: dict[str, Any] = {"from": rel_source, "action": "already_absent_from_current"}
            if archived:
                action = {"from": rel_source, "to": _rel(archived[0]), "action": "already_archived"}
            actions.append(action)
            continue
        try:
            source.resolve().relative_to(current_root)
        except ValueError:
            actions.append({"from": rel_source, "action": "skipped", "reason": "source is outside reports/current"})
            continue

        target = target_dir / source.name
        counter = 2
        while target.exists():
            target = target_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.resolve().relative_to(archive_resolved)
        except ValueError as exc:
            raise RuntimeError(f"refusing to archive outside archive root: {target}") from exc
        shutil.move(str(source), str(target))
        actions.append({
            "from": rel_source,
            "to": _rel(target),
            "action": "archived",
            "reason": spec.get("reason") or "legacy report is no longer active current evidence",
        })
    return actions


def build_report(
    current_dir: Path = CURRENT_DIR,
    *,
    required_set_path: Path = REQUIRED_SET,
    timestamp: str | None = None,
    archive_legacy: bool = False,
) -> dict[str, Any]:
    now_text = timestamp or datetime.now(UTC).isoformat()
    now = parse_timestamp(now_text) or datetime.now(UTC)
    required_set, required_set_error = _load_json(required_set_path)
    issues: list[dict[str, Any]] = []
    evaluated: list[dict[str, Any]] = []
    archive_actions: list[dict[str, Any]] = []

    if required_set_error or required_set is None:
        _issue(
            issues,
            check="required_set",
            file=_rel(required_set_path),
            code="missing_or_invalid",
            detail=required_set_error or "required set is invalid",
            severity="blocking",
            category="required_set",
            repair_action="Create report_integrity_required_set.json with required/supporting/optional/legacy classifications.",
        )
        required_set = {}

    max_age_hours = int(required_set.get("max_age_hours", DEFAULT_MAX_AGE_HOURS))
    required_specs = _list_specs(required_set, "required_reports")
    supporting_specs = _list_specs(required_set, "supporting_reports")
    optional_specs = _list_specs(required_set, "optional_reports")
    legacy_specs = _list_specs(required_set, "legacy_reports")

    known_files = {
        str(spec.get("file"))
        for spec in [*required_specs, *supporting_specs, *optional_specs, *legacy_specs]
        if spec.get("file")
    }
    optional_specs = [*optional_specs, *_collect_unclassified_specs(current_dir, known_files)]

    if archive_legacy:
        archive_root = ARCHIVE_DIR if current_dir.resolve() == CURRENT_DIR.resolve() else current_dir.parent / "archive" / "legacy"
        archive_actions = _archive_legacy(
            legacy_specs,
            current_dir=current_dir,
            archive_root=archive_root,
            timestamp=now_text,
        )
    else:
        for spec in legacy_specs:
            source = _spec_path(spec)
            archive_actions.append({
                "from": _rel(source),
                "action": "pending_archive" if source.exists() else "already_absent_from_current",
                "reason": spec.get("reason") or "legacy report is no longer active current evidence",
            })

    for category, specs in (
        ("required", required_specs),
        ("supporting", supporting_specs),
        ("optional", optional_specs),
    ):
        for spec in specs:
            _validate_report(
                path=_spec_path(spec),
                spec=spec,
                category=category,
                now=now,
                max_age_hours=max_age_hours,
                issues=issues,
                evaluated=evaluated,
            )

    blockers = [item for item in issues if item["severity"] == "blocking"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    checks = [
        {"id": "required_set_loaded", "passed": not any(item["check"] == "required_set" for item in blockers)},
        {"id": "required_reports_valid", "passed": not any(item["category"] == "required" for item in blockers)},
        {"id": "supporting_parent_references_valid", "passed": not any(item["category"] == "supporting" for item in blockers)},
        {"id": "optional_reports_warning_only", "passed": True},
        {"id": "legacy_reports_archived", "passed": not any(item["action"] == "pending_archive" for item in archive_actions)},
    ]
    status = "PASS" if not blockers else "BLOCKED"
    repair_actions = [
        {"id": item["id"], "file": item["file"], "action": item["repair_action"]}
        for item in issues
    ]

    return {
        "report_schema_version": 1,
        "report_name": REPORT_NAME,
        "gate": REPORT_NAME,
        "generated_by": "gate_validator",
        "timestamp": now_text,
        "environment": "local",
        "report_type": "gate",
        "status": status,
        "result": status,
        "decision": {
            "go_no_go": "GO" if status == "PASS" else "NO_GO",
            "result": "GO" if status == "PASS" else "NO_GO",
            "manual_override_allowed": False,
        },
        "collected": len(checks),
        "passed": sum(1 for item in checks if item["passed"]),
        "failed": sum(1 for item in checks if not item["passed"]),
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "source_command": "python scripts/generate_report_integrity_v2.py",
        "required_set": {
            "path": _rel(required_set_path),
            "version": required_set.get("schema_version"),
            "max_age_hours": max_age_hours,
        },
        "evaluation_rules": [
            "Required invalid, missing, or stale reports are blocking.",
            "Supporting invalid reports are blocking when referenced by the parent gate.",
            "Optional invalid reports are warnings only.",
            "Legacy reports are archived out of reports/current before evaluation.",
        ],
        "checks": checks,
        "evaluated_reports": evaluated,
        "archive_actions": archive_actions,
        "blockers": blockers,
        "blocker_details": blockers,
        "warnings": warnings,
        "repair_actions": repair_actions,
        "summary": {
            "required_count": len(required_specs),
            "supporting_count": len(supporting_specs),
            "optional_count": len(optional_specs),
            "legacy_count": len(legacy_specs),
            "evaluated_count": len(evaluated),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
            "archived_count": sum(1 for item in archive_actions if item["action"] == "archived"),
            "pending_archive_count": sum(1 for item in archive_actions if item["action"] == "pending_archive"),
            "repair_action_count": len(repair_actions),
        },
    }


def write_report(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    payload = build_report(archive_legacy=True)
    output_path = CURRENT_DIR / OUTPUT_REPORT
    write_report(payload, output_path)
    print(f"report_integrity_v2 = {payload['status']} blockers={len(payload['blocker_details'])}")
    print(f"Wrote: {output_path}")
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
