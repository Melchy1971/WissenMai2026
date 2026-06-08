from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
ARCHIVE_DIR = REPORTS_DIR / "archive"
HIERARCHY_JSON = REPO_ROOT / "docs" / "gate_hierarchy.json"
CHILD_BLOCKING_STATUSES = {"BLOCKED", "INVALID", "STALE"}
CHILD_FAIL_STATUSES = {"FAIL", "FAILED"}
PARENT_BLOCKING_STATUSES = {"BLOCKED", "MISSING", "INVALID", "STALE"}
DEFAULT_MAX_REPORT_AGE_HOURS = 168


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be object"
    return payload, None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _report_dir_policy_errors(report_dir: Path) -> list[str]:
    resolved = report_dir.resolve()
    if resolved == REPO_ROOT.resolve():
        return ["parent gate validator must read active reports from reports/current"]
    if _is_relative_to(resolved, ARCHIVE_DIR):
        return ["parent gate validator must not read reports from reports/archive"]
    if _is_relative_to(resolved, REPORTS_DIR) and resolved != CURRENT_DIR.resolve():
        return ["parent gate validator must read active reports from reports/current"]
    return []


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _nested(payload: dict[str, Any], key_path: str) -> Any:
    current: Any = payload
    for key in key_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _status_values(report: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("status", "result"):
        value = report.get(key)
        if isinstance(value, str) and value:
            values.add(value.upper().replace("-", "_"))
    for key_path in ("decision.go_no_go", "decision.result"):
        value = _nested(report, key_path)
        if isinstance(value, str) and value:
            values.add(value.upper().replace("-", "_"))
    return values


def _report_name(report_path: str) -> str:
    return Path(report_path).name


def _load_hierarchy(path: Path) -> dict[str, Any]:
    hierarchy, error = _load_json(path)
    if error or hierarchy is None:
        raise ValueError(error or f"missing hierarchy: {path}")
    if not isinstance(hierarchy.get("parents"), dict) or not isinstance(hierarchy.get("children"), dict):
        raise ValueError("gate_hierarchy.json must define parents and children objects")
    return hierarchy


def _counter_blockers(report_name: str, report: dict[str, Any], required: bool) -> list[str]:
    if not required and not any(key in report for key in ("collected", "passed", "failed", "errors", "skipped")):
        return []

    blockers: list[str] = []
    collected = _as_int(report.get("collected"))
    passed = _as_int(report.get("passed"))
    failed = _as_int(report.get("failed"))
    errors = _as_int(report.get("errors"))
    skipped = _as_int(report.get("skipped"))
    exit_code = _as_int(report.get("exit_code"))

    if collected is None or collected <= 0:
        blockers.append(f"{report_name}: collected must be > 0")
    if passed != collected:
        blockers.append(f"{report_name}: passed must equal collected")
    if failed != 0:
        blockers.append(f"{report_name}: failed must be 0")
    if errors != 0:
        blockers.append(f"{report_name}: errors must be 0")
    if skipped != 0:
        blockers.append(f"{report_name}: skipped must be 0")
    if exit_code != 0:
        blockers.append(f"{report_name}: exit_code must be 0")
    return blockers


def _is_supporting_report(report: dict[str, Any]) -> bool:
    return str(report.get("report_type") or "").lower() == "supporting"


def _child_blockers(
    child_id: str,
    child_spec: dict[str, Any],
    report: dict[str, Any],
    *,
    now: datetime,
    max_report_age_hours: int | None,
) -> tuple[str, list[str]]:
    report_path = str(child_spec.get("report") or "")
    report_name = _report_name(report_path)
    accepted_statuses = {
        str(value).upper().replace("-", "_")
        for value in child_spec.get("accepted_statuses", ["PASS"])
    }
    statuses = _status_values(report)
    blockers: list[str] = []

    if statuses & CHILD_BLOCKING_STATUSES:
        return "BLOCKED", [f"{child_id}: child status is blocking ({sorted(statuses & CHILD_BLOCKING_STATUSES)})"]
    if statuses & CHILD_FAIL_STATUSES:
        return "FAIL", [f"{child_id}: child status is FAIL ({sorted(statuses & CHILD_FAIL_STATUSES)})"]
    if statuses.isdisjoint(accepted_statuses):
        blockers.append(
            f"{child_id}: status/result must be one of {sorted(accepted_statuses)}, got {sorted(statuses)}"
        )

    invalid_blockers: list[str] = []
    if not report.get("generated_by"):
        invalid_blockers.append(f"{child_id}: generated_by must be set")

    timestamp = _parse_timestamp(report.get("timestamp") or report.get("generated_at"))
    if timestamp is None:
        return "STALE", [f"{child_id}: timestamp must be machine-readable"]

    collected = _as_int(report.get("collected"))
    if not _is_supporting_report(report) and (collected is None or collected <= 0):
        invalid_blockers.append(
            f"{child_id}: passing child report requires collected > 0 or report_type=supporting"
        )

    if invalid_blockers:
        return "INVALID", invalid_blockers

    required_decision = child_spec.get("required_decision")
    if required_decision is not None:
        decision = _nested(report, "decision.go_no_go")
        if str(decision).upper().replace("-", "_") != str(required_decision).upper().replace("-", "_"):
            blockers.append(f"{child_id}: decision.go_no_go must be {required_decision}")

    counter_required = child_spec.get("counter_validation") == "required"
    blockers.extend(_counter_blockers(report_name, report, required=counter_required))

    summary_errors = _nested(report, "summary.errors")
    if isinstance(summary_errors, int) and summary_errors != 0:
        blockers.append(f"{child_id}: summary.errors must be 0")

    if report.get("failed_tests") not in ([], None):
        blockers.append(f"{child_id}: failed_tests must be empty")
    if report.get("blockers") not in ([], None):
        blockers.append(f"{child_id}: blockers must be empty")

    for field in child_spec.get("optional_true_fields", []):
        if field in report and report.get(field) is not True:
            blockers.append(f"{child_id}: {field} must be true when present")

    min_quality_score = child_spec.get("min_quality_score")
    if min_quality_score is not None:
        score = report.get("quality_score")
        if not isinstance(score, (int, float)) or score < float(min_quality_score):
            blockers.append(f"{child_id}: quality_score must be >= {min_quality_score}")

    if max_report_age_hours is not None:
        if now - timestamp > timedelta(hours=max_report_age_hours):
            return "STALE", [f"{child_id}: report is older than {max_report_age_hours} hours"]

    return ("PASS" if not blockers else "FAIL"), blockers


def _parent_status(child_results: dict[str, dict[str, Any]]) -> str:
    statuses = {str(item["validation_status"]) for item in child_results.values()}
    if statuses & PARENT_BLOCKING_STATUSES:
        return "BLOCKED"
    if "FAIL" in statuses:
        return "FAIL"
    return "PASS"


def _decision_trace(
    parent_gate_id: str,
    child_results: dict[str, dict[str, Any]],
    status: str,
) -> dict[str, Any]:
    evaluated_children = [
        {
            "child_gate_id": child_id,
            "validation_status": result["validation_status"],
            "effect": (
                "blocks_parent"
                if result["validation_status"] in PARENT_BLOCKING_STATUSES
                else "fails_parent"
                if result["validation_status"] == "FAIL"
                else "passes_parent"
            ),
            "blockers": result.get("blockers", []),
        }
        for child_id, result in child_results.items()
    ]
    return {
        "parent_gate": parent_gate_id,
        "rule": (
            "Missing child, invalid child JSON, child BLOCKED/INVALID/STALE, or invalid PASS evidence "
            "=> parent BLOCKED; child FAIL => parent FAIL; child PASS counts only with generated_by, "
            "timestamp, and collected > 0 or report_type=supporting."
        ),
        "evaluated_children": evaluated_children,
        "blocking_children": [
            item["child_gate_id"]
            for item in evaluated_children
            if item["validation_status"] in PARENT_BLOCKING_STATUSES
        ],
        "failing_children": [
            item["child_gate_id"]
            for item in evaluated_children
            if item["validation_status"] == "FAIL"
        ],
        "final_status": status,
    }


def validate_parent_gate(
    parent_gate_id: str,
    *,
    report_dir: Path = CURRENT_DIR,
    hierarchy_path: Path = HIERARCHY_JSON,
    timestamp: str | None = None,
    max_report_age_hours: int | None = DEFAULT_MAX_REPORT_AGE_HOURS,
) -> dict[str, Any]:
    hierarchy = _load_hierarchy(hierarchy_path)
    parents = hierarchy["parents"]
    children = hierarchy["children"]
    if parent_gate_id not in parents:
        raise ValueError(f"unknown parent gate: {parent_gate_id}")

    now_text = timestamp or datetime.now(UTC).isoformat()
    now = _parse_timestamp(now_text) or datetime.now(UTC)
    policy_errors = _report_dir_policy_errors(report_dir)
    child_results: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, Any]] = []

    mandatory_children = parents[parent_gate_id].get("mandatory_children")
    if not isinstance(mandatory_children, list) or not mandatory_children:
        raise ValueError(f"parent gate {parent_gate_id} has no mandatory children")

    for child_id in mandatory_children:
        child_spec = children.get(child_id)
        if not isinstance(child_spec, dict):
            child_results[child_id] = {
                "child_gate_id": child_id,
                "validation_status": "INVALID",
                "blockers": [f"{child_id}: missing child definition"],
            }
        else:
            report_path = str(child_spec.get("report") or "")
            report_name = _report_name(report_path)
            if not report_path.startswith("reports/current/"):
                child_results[child_id] = {
                    "child_gate_id": child_id,
                    "report": report_path,
                    "validation_status": "INVALID",
                    "blockers": [f"{child_id}: report source must be reports/current"],
                }
            elif policy_errors:
                child_results[child_id] = {
                    "child_gate_id": child_id,
                    "report": report_path,
                    "validation_status": "BLOCKED",
                    "blockers": policy_errors,
                }
            else:
                report, error = _load_json(report_dir / report_name)
                if error or report is None:
                    status = "MISSING" if error == "missing" else "INVALID"
                    child_results[child_id] = {
                        "child_gate_id": child_id,
                        "report": report_path,
                        "validation_status": status,
                        "blockers": [f"{child_id}: {error}"],
                    }
                else:
                    status, child_blockers = _child_blockers(
                        child_id,
                        child_spec,
                        report,
                        now=now,
                        max_report_age_hours=max_report_age_hours,
                    )
                    child_results[child_id] = {
                        "child_gate_id": child_id,
                        "report": report_path,
                        "validation_status": status,
                        "report_status": report.get("status"),
                        "report_result": report.get("result"),
                        "decision": _nested(report, "decision.go_no_go"),
                        "timestamp": report.get("timestamp") or report.get("generated_at"),
                        "generated_by": report.get("generated_by"),
                        "collected": report.get("collected"),
                        "report_type": report.get("report_type"),
                        "blockers": child_blockers,
                    }

        child_result = child_results[child_id]
        if child_result["validation_status"] != "PASS":
            blockers.append({
                "id": child_id,
                "child_gate_id": child_id,
                "severity": "blocking",
                "reason": "; ".join(child_result["blockers"]),
            })

    status = _parent_status(child_results)
    gate_decision_trace = _decision_trace(parent_gate_id, child_results, status)
    return {
        "report_schema_version": 1,
        "report_name": "parent_gate_validation",
        "generated_by": "gate_validator",
        "timestamp": now_text,
        "parent_gate": parent_gate_id,
        "status": status,
        "result": status,
        "decision": {
            "go_no_go": "GO" if status == "PASS" else "NO_GO",
            "manual_override_allowed": False,
        },
        "collected": len(mandatory_children),
        "passed": sum(1 for item in child_results.values() if item["validation_status"] == "PASS"),
        "failed": len(blockers),
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "hierarchy_source": hierarchy_path.relative_to(REPO_ROOT).as_posix(),
        "report_dir": report_dir.relative_to(REPO_ROOT).as_posix() if _is_relative_to(report_dir, REPO_ROOT) else str(report_dir),
        "no_manual_override": True,
        "mandatory_children": mandatory_children,
        "child_results": child_results,
        "blockers": blockers,
        "gate_decision_trace": gate_decision_trace,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a parent gate from docs/gate_hierarchy.json.")
    parser.add_argument("parent_gate")
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--hierarchy-json", type=Path, default=HIERARCHY_JSON)
    parser.add_argument("--max-report-age-hours", type=int, default=DEFAULT_MAX_REPORT_AGE_HOURS)
    args = parser.parse_args(argv)

    max_age = None if args.max_report_age_hours < 0 else args.max_report_age_hours
    payload = validate_parent_gate(
        args.parent_gate,
        report_dir=args.report_dir,
        hierarchy_path=args.hierarchy_json,
        max_report_age_hours=max_age,
    )
    print(json.dumps(payload, indent=2))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
