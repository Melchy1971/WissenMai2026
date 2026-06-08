from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
ARCHIVE_DIR = REPORTS_DIR / "archive"
HIERARCHY_JSON = REPO_ROOT / "docs" / "gate_hierarchy.json"
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "gate_hierarchy_result.json"
DEFAULT_OUTPUT_MD = CURRENT_DIR / "gate_hierarchy_result.md"

REGRESSION_THRESHOLD = 0.20
DEFAULT_MAX_REPORT_AGE_HOURS = 168


@dataclass(frozen=True)
class GateSpec:
    id: str
    label: str
    report: str | None = None
    mandatory_children: tuple[str, ...] = ()
    accepted_statuses: tuple[str, ...] = ("PASS",)
    required_decision: str | None = None
    counter_validation: str = "required"
    min_quality_score: float | None = None
    optional_true_fields: tuple[str, ...] = ()


def _load_hierarchy(path: Path = HIERARCHY_JSON) -> tuple[dict[str, Any], tuple[GateSpec, ...]]:
    payload, error = _load_report(path)
    if error or payload is None:
        raise ValueError(error or f"missing hierarchy: {path}")

    specs: list[GateSpec] = []
    children = payload.get("children")
    parents = payload.get("parents")
    if not isinstance(children, dict) or not isinstance(parents, dict):
        raise ValueError("gate_hierarchy.json must define object fields 'children' and 'parents'")

    for gate_id, raw in children.items():
        if not isinstance(raw, dict):
            raise ValueError(f"child gate must be object: {gate_id}")
        report = raw.get("report")
        if not isinstance(report, str) or not report.startswith("reports/current/"):
            raise ValueError(f"child gate {gate_id} must use reports/current as report source")
        specs.append(
            GateSpec(
                id=str(gate_id),
                label=str(raw.get("label") or gate_id),
                report=report,
                accepted_statuses=tuple(str(value) for value in raw.get("accepted_statuses", ["PASS"])),
                required_decision=raw.get("required_decision"),
                counter_validation=str(raw.get("counter_validation", "required")),
                min_quality_score=(
                    float(raw["min_quality_score"])
                    if raw.get("min_quality_score") is not None
                    else None
                ),
                optional_true_fields=tuple(str(value) for value in raw.get("optional_true_fields", [])),
            )
        )

    known_children = {spec.id for spec in specs}
    for gate_id, raw in parents.items():
        if not isinstance(raw, dict):
            raise ValueError(f"parent gate must be object: {gate_id}")
        mandatory_children = raw.get("mandatory_children")
        if not isinstance(mandatory_children, list) or not mandatory_children:
            raise ValueError(f"parent gate {gate_id} must define mandatory children")
        missing = [child for child in mandatory_children if child not in known_children]
        if missing:
            raise ValueError(f"parent gate {gate_id} references unknown children: {', '.join(missing)}")
        specs.append(
            GateSpec(
                id=str(gate_id),
                label=str(raw.get("label") or gate_id),
                mandatory_children=tuple(str(child) for child in mandatory_children),
                counter_validation="not_required",
            )
        )

    return payload, tuple(specs)


def _report_filename(report_path: str) -> str:
    return Path(report_path).name


def dependency_graph(hierarchy_path: Path = HIERARCHY_JSON) -> dict[str, Any]:
    _, specs = _load_hierarchy(hierarchy_path)
    return {
        "nodes": [{"id": spec.id, "label": spec.label} for spec in specs],
        "edges": [
            {"from": child, "to": spec.id}
            for spec in specs
            for child in spec.mandatory_children
        ],
    }


def _load_report(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing report: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"invalid report {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"report root must be object: {path}"
    return payload, None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _report_dir_policy_errors(report_dir: Path) -> list[str]:
    resolved = report_dir.resolve()
    if _is_relative_to(resolved, ARCHIVE_DIR):
        return ["gate validators must not read reports from reports/archive"]
    if resolved == REPO_ROOT.resolve():
        return ["gate validators must read active reports from reports/current"]
    if _is_relative_to(resolved, REPORTS_DIR) and resolved != CURRENT_DIR.resolve():
        return ["gate validators must read active reports from reports/current"]
    return []


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _nested_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _status_values(report: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("status", "result"):
        value = report.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    decision_result = _nested_value(report, "decision.result")
    if isinstance(decision_result, str) and decision_result:
        values.add(decision_result)
    return values


def _regression_blocker(
    report_name: str,
    report: dict[str, Any] | None,
    baseline_collected: int | None,
) -> str | None:
    if report is None or baseline_collected is None or baseline_collected <= 0:
        return None
    current = report.get("collected")
    if isinstance(current, bool) or not isinstance(current, int):
        return None
    drop = baseline_collected - current
    if drop <= 0:
        return None
    drop_fraction = drop / baseline_collected
    if drop_fraction <= REGRESSION_THRESHOLD:
        return None
    if report.get("scope_change_reason") and report.get("approval"):
        return None
    return (
        f"{report_name}: collected regression - dropped from {baseline_collected} to {current} "
        f"({drop_fraction:.0%} > {int(REGRESSION_THRESHOLD * 100)}% threshold); "
        "add scope_change_reason and approval fields to override"
    )


def _counter_blockers(report_name: str, report: dict[str, Any], required: bool) -> list[str]:
    blockers: list[str] = []
    has_counter_fields = any(key in report for key in ("collected", "passed", "failed", "errors", "skipped"))
    if not required and not has_counter_fields:
        return blockers

    collected = _as_int(report.get("collected"))
    passed = _as_int(report.get("passed"))
    failed = _as_int(report.get("failed"))
    errors = _as_int(report.get("errors"))
    skipped = _as_int(report.get("skipped"))
    exit_code = _as_int(report.get("exit_code"))

    if collected is None or collected <= 0:
        blockers.append(f"{report_name}: collected must be > 0, got {report.get('collected')!r}")
    if passed != collected:
        blockers.append(f"{report_name}: passed ({passed!r}) must equal collected ({collected!r})")
    if failed != 0:
        blockers.append(f"{report_name}: failed must be 0, got {failed!r}")
    if errors != 0:
        blockers.append(f"{report_name}: errors must be 0, got {errors!r}")
    if skipped != 0:
        blockers.append(f"{report_name}: skipped must be 0, got {skipped!r}")
    if exit_code != 0:
        blockers.append(f"{report_name}: exit_code must be 0, got {exit_code!r}")
    return blockers


def _report_blockers(
    spec: GateSpec,
    report: dict[str, Any] | None,
    load_error: str | None,
    baseline_collected: int | None = None,
    now: datetime | None = None,
    max_report_age_hours: int | None = None,
) -> list[str]:
    report_name = _report_filename(spec.report or spec.id)
    if load_error or report is None:
        return [load_error or f"{report_name} unavailable"]

    blockers: list[str] = []
    accepted_statuses = set(spec.accepted_statuses)
    statuses = _status_values(report)
    if statuses.isdisjoint(accepted_statuses):
        blockers.append(
            f"{report_name}: status/result must be one of {sorted(accepted_statuses)}, got {sorted(statuses)}"
        )

    if not report.get("generated_by"):
        blockers.append(f"{report_name}: generated_by must be set")

    if spec.required_decision is not None:
        decision = _nested_value(report, "decision.go_no_go")
        if decision != spec.required_decision:
            blockers.append(
                f"{report_name}: decision.go_no_go must be {spec.required_decision}, got {decision!r}"
            )

    counter_required = spec.counter_validation == "required"
    blockers.extend(_counter_blockers(report_name, report, required=counter_required))

    summary_errors = _nested_value(report, "summary.errors")
    if isinstance(summary_errors, int) and summary_errors != 0:
        blockers.append(f"{report_name}: summary.errors must be 0, got {summary_errors}")

    failed_tests = report.get("failed_tests")
    if failed_tests not in ([], None):
        blockers.append(f"{report_name}: failed_tests must be empty")

    blockers_value = report.get("blockers")
    if blockers_value not in ([], None):
        blockers.append(f"{report_name}: blockers must be empty")

    for field in spec.optional_true_fields:
        if field in report and report.get(field) is not True:
            blockers.append(f"{report_name}: {field} must be true when present")

    if spec.min_quality_score is not None:
        quality_score = report.get("quality_score")
        if not isinstance(quality_score, (int, float)) or quality_score < spec.min_quality_score:
            blockers.append(
                f"{report_name}: quality_score must be >= {spec.min_quality_score:g}, got {quality_score!r}"
            )

    regression = _regression_blocker(report_name, report, baseline_collected)
    if regression:
        blockers.append(regression)

    if max_report_age_hours is not None:
        timestamp = _parse_timestamp(report.get("timestamp") or report.get("generated_at"))
        if timestamp is None:
            blockers.append(f"{report_name}: timestamp must be machine-readable")
        elif (now or datetime.now(UTC)) - timestamp > timedelta(hours=max_report_age_hours):
            blockers.append(f"{report_name}: report is older than {max_report_age_hours} hours")

    return blockers


def _report_summary(report: dict[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    if report is None:
        return {"available": False, "error": load_error}
    return {
        "available": True,
        "status": report.get("status"),
        "result": report.get("result"),
        "decision": _nested_value(report, "decision.go_no_go"),
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "errors": report.get("errors"),
        "skipped": report.get("skipped"),
        "exit_code": report.get("exit_code"),
        "quality_score": report.get("quality_score"),
        "generated_by": report.get("generated_by"),
        "test_database_url_set": report.get("test_database_url_set"),
        "timestamp": report.get("timestamp") or report.get("generated_at"),
    }


def _report_path_for_gate(gate: dict[str, Any]) -> str:
    reports = gate.get("reports")
    if isinstance(reports, list) and reports:
        return f"reports/current/{reports[0]}"
    summaries = gate.get("report_summaries")
    if isinstance(summaries, dict) and summaries:
        return f"reports/current/{next(iter(summaries))}"
    return "docs/gate_hierarchy.json"


def _next_action(reason: str, report_path: str) -> str:
    lower = reason.lower()
    if "missing report" in lower or "unavailable" in lower:
        return f"Generate the missing child report at {report_path}, then rerun scripts/validate_gate_hierarchy.py."
    if "invalid report" in lower or "root must be object" in lower:
        return f"Repair or regenerate valid JSON at {report_path}, then rerun scripts/validate_gate_hierarchy.py."
    if "generated_by" in lower:
        return f"Normalize {report_path} so generated_by is set by the producing validator."
    if "decision.go_no_go" in lower:
        return f"Rerun the child gate that writes {report_path} until decision.go_no_go matches the hierarchy requirement."
    if "quality_score" in lower:
        return f"Fix the data-quality findings or regenerate {report_path} with quality_score at or above the configured threshold."
    if "older than" in lower or "timestamp" in lower:
        return f"Regenerate {report_path} so the report timestamp is fresh and machine-readable."
    if "mandatory child not passed" in lower:
        return "Open the referenced child gate detail, fix that child report first, then rerun scripts/validate_gate_hierarchy.py."
    if any(token in lower for token in ("failed", "errors", "skipped", "exit_code", "passed", "collected")):
        return f"Fix the failing tests/counters in {report_path}, rerun the child gate, and keep failed/errors/skipped at 0."
    if "blockers must be empty" in lower:
        return f"Resolve the blockers listed inside {report_path}, regenerate that report, then rerun the hierarchy validator."
    if "reports/current" in lower or "reports/archive" in lower:
        return "Point the validator at reports/current only; archive or root-level reports are not valid gate inputs."
    return f"Inspect {report_path}, resolve the reported condition, and rerun scripts/validate_gate_hierarchy.py."


def _blocker_details(gate_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for gate_id, result in gate_results.items():
        if result["status"] == "PASS":
            continue
        report_path = _report_path_for_gate(result)
        reasons = result.get("blockers") or [f"{gate_id}: status is {result['status']}"]
        for reason in reasons:
            if str(reason).startswith("mandatory child not passed: "):
                child_id = str(reason).split(":", 1)[1].strip()
                child_result = gate_results.get(child_id)
                if isinstance(child_result, dict):
                    child_report_path = _report_path_for_gate(child_result)
                    child_reasons = child_result.get("blockers") or [f"{child_id}: status is {child_result['status']}"]
                    child_reason = "; ".join(str(item) for item in child_reasons)
                    details.append(
                        {
                            "gate": child_id,
                            "report_path": child_report_path,
                            "status": child_result["status"],
                            "reason": (
                                f"{gate_id} blocked because mandatory child {child_id} is "
                                f"{child_result['status']}. Child reason: {child_reason}"
                            ),
                            "next_action": _next_action(child_reason, child_report_path),
                        }
                    )
                    continue
            details.append(
                {
                    "gate": gate_id,
                    "report_path": report_path,
                    "status": result["status"],
                    "reason": str(reason),
                    "next_action": _next_action(str(reason), report_path),
                }
            )
    return details


def _unique_repair_path(blocker_details: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for detail in blocker_details:
        action = str(detail["next_action"])
        if action not in seen:
            seen.add(action)
            actions.append(action)
    return actions


def evaluate_gate_hierarchy(
    report_dir: Path = CURRENT_DIR,
    *,
    timestamp: str | None = None,
    baseline: dict[str, int] | None = None,
    max_report_age_hours: int | None = None,
    hierarchy_path: Path = HIERARCHY_JSON,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    now = _parse_timestamp(timestamp) or datetime.now(UTC)
    hierarchy, specs = _load_hierarchy(hierarchy_path)
    source_policy_errors = _report_dir_policy_errors(report_dir)

    report_specs = [spec for spec in specs if spec.report]
    reports: dict[str, tuple[dict[str, Any] | None, str | None]] = {}
    for spec in report_specs:
        report_name = _report_filename(spec.report or "")
        if report_name not in reports:
            reports[report_name] = _load_report(report_dir / report_name)

    gate_results: dict[str, dict[str, Any]] = {}
    for spec in specs:
        child_blockers = [
            child
            for child in spec.mandatory_children
            if gate_results[child]["status"] != "PASS"
        ]

        blockers: list[str] = []
        report_summaries: dict[str, dict[str, Any]] = {}
        reports_list: list[str] = []
        if spec.report:
            report_name = _report_filename(spec.report)
            reports_list = [report_name]
            report, load_error = reports[report_name]
            report_summaries[report_name] = _report_summary(report, load_error)
            if source_policy_errors:
                blockers.extend(source_policy_errors)
            else:
                baseline_collected = baseline.get(report_name) if baseline else None
                blockers.extend(
                    _report_blockers(
                        spec,
                        report,
                        load_error,
                        baseline_collected,
                        now,
                        max_report_age_hours,
                    )
                )
        elif child_blockers:
            blockers = [f"mandatory child not passed: {child}" for child in child_blockers]
        elif source_policy_errors:
            blockers.extend(source_policy_errors)

        if child_blockers:
            status = "BLOCKED"
        elif blockers:
            status = "FAIL"
        else:
            status = "PASS"

        gate_results[spec.id] = {
            "id": spec.id,
            "label": spec.label,
            "status": status,
            "reports": reports_list,
            "mandatory_children": list(spec.mandatory_children),
            "blockers": blockers,
            "report_summaries": report_summaries,
        }

    all_passed = all(result["status"] == "PASS" for result in gate_results.values())
    blocker_details = _blocker_details(gate_results)
    return {
        "report_schema_version": 2,
        "report_name": "gate_hierarchy_result",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "environment": "local",
        "result": "PASS" if all_passed else "FAIL",
        "status": "PASS" if all_passed else "FAIL",
        "gate": "gate_hierarchy",
        "collected": len(gate_results),
        "passed": sum(1 for result in gate_results.values() if result["status"] == "PASS"),
        "failed": sum(1 for result in gate_results.values() if result["status"] == "FAIL"),
        "errors": 0,
        "skipped": sum(1 for result in gate_results.values() if result["status"] == "BLOCKED"),
        "exit_code": 0 if all_passed else 1,
        "blockers": [
            {"gate": gate_id, "severity": "critical", "reason": "; ".join(result["blockers"])}
            for gate_id, result in gate_results.items()
            if result["status"] != "PASS"
        ],
        "blocker_details": blocker_details,
        "repair_path": _unique_repair_path(blocker_details),
        "source_command": "python scripts/validate_gate_hierarchy.py",
        "hierarchy_source": hierarchy_path.relative_to(REPO_ROOT).as_posix(),
        "report_source_policy": hierarchy.get("report_source_policy", {}),
        "gates": gate_results,
        "dependency_graph": dependency_graph(hierarchy_path),
        "evaluation_rules": hierarchy.get("validator_rules", {}),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gate Hierarchy Result",
        "",
        f"- Result: `{payload['result']}`",
        f"- Timestamp: `{payload['timestamp']}`",
        f"- Hierarchy Source: `{payload['hierarchy_source']}`",
        "",
        "## Gates",
        "",
        "| Gate | Status | Mandatory Children | Reports | Blockers |",
        "|---|---|---|---|---|",
    ]
    for gate in payload["gates"].values():
        children = ", ".join(f"`{child}`" for child in gate["mandatory_children"]) or "-"
        reports = ", ".join(f"`{report}`" for report in gate["reports"]) or "-"
        blockers = "<br>".join(gate["blockers"]) or "-"
        lines.append(f"| {gate['label']} | `{gate['status']}` | {children} | {reports} | {blockers} |")

    lines.extend(["", "## Dependency Graph", ""])
    for edge in payload["dependency_graph"]["edges"]:
        lines.append(f"- `{edge['from']}` -> `{edge['to']}`")

    lines.extend(["", "## Validator Rules", ""])
    for key, value in payload["evaluation_rules"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def write_result(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the mandatory truth gate hierarchy.")
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--hierarchy-json", type=Path, default=HIERARCHY_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--max-report-age-hours",
        type=int,
        default=DEFAULT_MAX_REPORT_AGE_HOURS,
        help="Reject gate reports older than this many hours. Use -1 to disable age validation.",
    )
    args = parser.parse_args(argv)

    max_report_age_hours = None if args.max_report_age_hours < 0 else args.max_report_age_hours
    payload = evaluate_gate_hierarchy(
        args.report_dir,
        hierarchy_path=args.hierarchy_json,
        max_report_age_hours=max_report_age_hours,
    )
    write_result(payload, args.output_json, args.output_md)

    print(f"Gate Hierarchy = {payload['result']}")
    for gate in payload["gates"].values():
        print(f"- {gate['label']}: {gate['status']}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
