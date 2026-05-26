from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_OUTPUT_JSON = REPORTS_DIR / "gate_hierarchy_result.json"
DEFAULT_OUTPUT_MD = REPORTS_DIR / "gate_hierarchy_result.md"


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
        reports=("m3a_truth_report.json", "frontend_truth_report.json"),
    ),
    GateSpec(
        id="m4a_gate",
        label="M4a Gate",
        reports=("m4a_auth_truth_report.json",),
    ),
    GateSpec(
        id="m4b_gate",
        label="M4b Gate",
        reports=("m4b_upload_queue_truth_report.json",),
    ),
    GateSpec(
        id="m4c_gate",
        label="M4c Gate",
        reports=("m4c_lifecycle_retrieval_truth_report.json",),
    ),
    GateSpec(
        id="m4e_gate",
        label="M4e Gate",
        reports=("m4e_backup_restore_truth_report.json",),
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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON report {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"report root must be object: {path}"
    return payload, None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _report_blockers(report_name: str, report: dict[str, Any] | None, load_error: str | None) -> list[str]:
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


def evaluate_gate_hierarchy(report_dir: Path = REPORTS_DIR, *, timestamp: str | None = None) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
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
        if not dependency_blockers:
            for report_name in spec.reports:
                report, load_error = reports[report_name]
                blockers.extend(_report_blockers(report_name, report, load_error))
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
        "timestamp": timestamp,
        "result": "PASS"
        if all(result["status"] == "PASS" for result in gate_results.values())
        else "FAIL",
        "gates": gate_results,
        "dependency_graph": dependency_graph(),
        "evaluation_rules": {
            "m3a_gate": ["m3a_truth_report.json", "frontend_truth_report.json"],
            "m4a_gate": ["m4a_auth_truth_report.json"],
            "m4b_gate": ["m4b_upload_queue_truth_report.json"],
            "m4c_gate": ["m4c_lifecycle_retrieval_truth_report.json"],
            "m4e_gate": ["m4e_backup_restore_truth_report.json"],
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
    parser.add_argument("--report-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args(argv)

    payload = evaluate_gate_hierarchy(args.report_dir)
    write_result(payload, args.output_json, args.output_md)

    print(f"Gate Hierarchy = {payload['result']}")
    for gate in payload["gates"].values():
        print(f"- {gate['label']}: {gate['status']}")
    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
