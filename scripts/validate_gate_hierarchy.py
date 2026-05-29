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
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "gate_hierarchy_result.json"
DEFAULT_OUTPUT_MD = CURRENT_DIR / "gate_hierarchy_result.md"

REGRESSION_THRESHOLD = 0.20
DEFAULT_MAX_REPORT_AGE_HOURS = 168


@dataclass(frozen=True)
class GateSpec:
    id: str
    label: str
    reports: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()


GATE_SPECS: tuple[GateSpec, ...] = (
    GateSpec(
        id="m3a_gate",
        label="M3a Gate",
        reports=("m3a_frontend_truth.json",),
    ),
    GateSpec(
        id="m4a_gate",
        label="M4a Gate",
        reports=("m4a_auth_truth.json",),
    ),
    GateSpec(
        id="m4b_gate",
        label="M4b Gate",
        reports=("m4b_upload_queue_truth.json",),
    ),
    GateSpec(
        id="m4c_gate",
        label="M4c Gate",
        reports=("m4c_lifecycle_retrieval_truth.json",),
    ),
    GateSpec(
        id="m4e_gate",
        label="M4e Gate",
        reports=("m4e_backup_restore_truth.json",),
    ),
    GateSpec(
        id="m4_crosscutting_gate",
        label="M4 Cross-Cutting Gate",
        reports=("m4_truth_report.json",),
    ),
    GateSpec(
        id="m4_overall_gate",
        label="M4 Gesamtgate",
        dependencies=("m4_crosscutting_gate", "m4a_gate", "m4b_gate", "m4c_gate", "m4e_gate"),
    ),
    GateSpec(
        id="m5_start_gate",
        label="M5 Startgate",
        dependencies=("m4_overall_gate",),
    ),
    GateSpec(
        id="operational_governance_gate",
        label="Operational Governance Gate",
        reports=("governance_truth_report.json",),
        dependencies=("m5_start_gate",),
    ),
)


def dependency_graph() -> dict[str, Any]:
    return {
        "nodes": [{"id": spec.id, "label": spec.label} for spec in GATE_SPECS],
        "edges": [
            {"from": dependency, "to": spec.id}
            for spec in GATE_SPECS
            for dependency in spec.dependencies
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
        f"{report_name}: collected regression — dropped from {baseline_collected} to {current} "
        f"({drop_fraction:.0%} > {int(REGRESSION_THRESHOLD * 100)}% threshold); "
        "add scope_change_reason and approval fields to override"
    )


def _report_blockers(
    report_name: str,
    report: dict[str, Any] | None,
    load_error: str | None,
    baseline_collected: int | None = None,
    now: datetime | None = None,
    max_report_age_hours: int | None = None,
) -> list[str]:
    if load_error or report is None:
        return [load_error or f"{report_name} unavailable"]

    blockers: list[str] = []
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

    failed_tests = report.get("failed_tests")
    if failed_tests not in ([], None):
        blockers.append(f"{report_name}: failed_tests must be empty")
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
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "errors": report.get("errors"),
        "skipped": report.get("skipped"),
        "exit_code": report.get("exit_code"),
        "test_database_url_set": report.get("test_database_url_set"),
        "timestamp": report.get("timestamp"),
    }


def evaluate_gate_hierarchy(
    report_dir: Path = CURRENT_DIR,
    *,
    timestamp: str | None = None,
    baseline: dict[str, int] | None = None,
    max_report_age_hours: int | None = None,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    now = _parse_timestamp(timestamp) or datetime.now(UTC)
    source_policy_errors = _report_dir_policy_errors(report_dir)
    reports: dict[str, tuple[dict[str, Any] | None, str | None]] = {}
    for spec in GATE_SPECS:
        for report_name in spec.reports:
            if report_name not in reports:
                reports[report_name] = _load_report(report_dir / report_name)

    gate_results: dict[str, dict[str, Any]] = {}
    for spec in GATE_SPECS:
        dependency_blockers = [
            dependency
            for dependency in spec.dependencies
            if gate_results[dependency]["status"] != "PASS"
        ]

        blockers: list[str] = []
        report_summaries: dict[str, dict[str, Any]] = {}
        if source_policy_errors:
            blockers.extend(source_policy_errors)
            for report_name in spec.reports:
                report, load_error = reports[report_name]
                report_summaries[report_name] = _report_summary(report, load_error)
        elif not dependency_blockers:
            for report_name in spec.reports:
                report, load_error = reports[report_name]
                baseline_collected = baseline.get(report_name) if baseline else None
                blockers.extend(
                    _report_blockers(
                        report_name,
                        report,
                        load_error,
                        baseline_collected,
                        now,
                        max_report_age_hours,
                    )
                )
                report_summaries[report_name] = _report_summary(report, load_error)
        else:
            for report_name in spec.reports:
                report, load_error = reports[report_name]
                report_summaries[report_name] = _report_summary(report, load_error)

        if dependency_blockers:
            status = "BLOCKED"
            blockers = [f"dependency not passed: {dependency}" for dependency in dependency_blockers]
        elif blockers:
            status = "FAIL"
        else:
            status = "PASS"

        gate_results[spec.id] = {
            "id": spec.id,
            "label": spec.label,
            "status": status,
            "reports": list(spec.reports),
            "dependencies": list(spec.dependencies),
            "blockers": blockers,
            "report_summaries": report_summaries,
        }

    return {
        "report_schema_version": 1,
        "report_name": "gate_hierarchy_result",
        "generated_by": "gate_validator",
        "timestamp": timestamp,
        "environment": "local",
        "result": "PASS"
        if all(result["status"] == "PASS" for result in gate_results.values())
        else "FAIL",
        "status": "PASS" if all(result["status"] == "PASS" for result in gate_results.values()) else "FAIL",
        "gate": "gate_hierarchy",
        "collected": len(gate_results),
        "passed": sum(1 for result in gate_results.values() if result["status"] == "PASS"),
        "failed": sum(1 for result in gate_results.values() if result["status"] == "FAIL"),
        "errors": 0,
        "skipped": sum(1 for result in gate_results.values() if result["status"] == "BLOCKED"),
        "exit_code": 0 if all(result["status"] == "PASS" for result in gate_results.values()) else 1,
        "blockers": [
            {"gate": gate_id, "severity": "critical", "reason": "; ".join(result["blockers"])}
            for gate_id, result in gate_results.items()
            if result["status"] != "PASS"
        ],
        "source_command": "python scripts/validate_gate_hierarchy.py",
        "gates": gate_results,
        "dependency_graph": dependency_graph(),
        "evaluation_rules": {
            "m3a_gate": ["m3a_frontend_truth.json"],
            "m4a_gate": ["m4a_auth_truth.json"],
            "m4b_gate": ["m4b_upload_queue_truth.json"],
            "m4c_gate": ["m4c_lifecycle_retrieval_truth.json"],
            "m4e_gate": ["m4e_backup_restore_truth.json"],
            "m4_crosscutting_gate": ["m4_truth_report.json"],
            "m4_overall_gate": ["m4_crosscutting_gate", "m4a_gate", "m4b_gate", "m4c_gate", "m4e_gate"],
            "m5_start_gate": ["m4_overall_gate"],
            "operational_governance_gate": ["m5_start_gate", "governance_truth_report.json"],
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gate Hierarchy Result",
        "",
        f"- Result: `{payload['result']}`",
        f"- Timestamp: `{payload['timestamp']}`",
        "",
        "## Gates",
        "",
        "| Gate | Status | Dependencies | Reports | Blockers |",
        "|---|---|---|---|---|",
    ]
    for gate in payload["gates"].values():
        dependencies = ", ".join(f"`{dep}`" for dep in gate["dependencies"]) or "-"
        reports = ", ".join(f"`{report}`" for report in gate["reports"]) or "-"
        blockers = "<br>".join(gate["blockers"]) or "-"
        lines.append(f"| {gate['label']} | `{gate['status']}` | {dependencies} | {reports} | {blockers} |")

    lines.extend(["", "## Dependency Graph", ""])
    for edge in payload["dependency_graph"]["edges"]:
        lines.append(f"- `{edge['from']}` -> `{edge['to']}`")
    return "\n".join(lines) + "\n"


def write_result(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the truth gate hierarchy from split reports.")
    parser.add_argument("--report-dir", type=Path, default=CURRENT_DIR)
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
    payload = evaluate_gate_hierarchy(args.report_dir, max_report_age_hours=max_report_age_hours)
    write_result(payload, args.output_json, args.output_md)

    print(f"Gate Hierarchy = {payload['result']}")
    for gate in payload["gates"].values():
        print(f"- {gate['label']}: {gate['status']}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
