from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gate_engine import (  # noqa: E402
    ChildGateReference,
    GateDefinition,
    evaluate_gate,
    parse_timestamp as _parse_timestamp,
)

REPORTS_DIR = REPO_ROOT / "reports"
CURRENT_DIR = REPORTS_DIR / "current"
ARCHIVE_DIR = REPORTS_DIR / "archive"
HIERARCHY_JSON = REPO_ROOT / "docs" / "gate_hierarchy.json"
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


def _report_name(report_path: str) -> str:
    return Path(report_path).name


def _load_hierarchy(path: Path) -> dict[str, Any]:
    hierarchy, error = _load_json(path)
    if error or hierarchy is None:
        raise ValueError(error or f"missing hierarchy: {path}")
    if not isinstance(hierarchy.get("parents"), dict) or not isinstance(hierarchy.get("children"), dict):
        raise ValueError("gate_hierarchy.json must define parents and children objects")
    return hierarchy


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
    child_references: list[ChildGateReference] = []
    child_inputs: dict[str, dict[str, Any]] = {}

    mandatory_children = parents[parent_gate_id].get("mandatory_children")
    if not isinstance(mandatory_children, list) or not mandatory_children:
        raise ValueError(f"parent gate {parent_gate_id} has no mandatory children")

    for child_id in mandatory_children:
        child_spec = children.get(child_id)
        if not isinstance(child_spec, dict):
            child_references.append(ChildGateReference(child_gate_id=child_id, report=""))
            child_inputs[child_id] = {"error": "invalid: missing child definition"}
            continue

        reference = ChildGateReference.from_spec(child_id, child_spec)
        child_references.append(reference)
        report_path = reference.report
        report_name = _report_name(report_path)
        if not report_path.startswith("reports/current/"):
            child_inputs[child_id] = {"error": "invalid: report source must be reports/current"}
        elif policy_errors:
            child_inputs[child_id] = {"error": f"blocked: {'; '.join(policy_errors)}"}
        else:
            report, error = _load_json(report_dir / report_name)
            child_inputs[child_id] = {"report": report, "error": error}

    gate_definition = GateDefinition(
        parent_gate_id=parent_gate_id,
        mandatory_children=tuple(child_references),
        hierarchy_source=hierarchy_path.relative_to(REPO_ROOT).as_posix()
        if _is_relative_to(hierarchy_path, REPO_ROOT)
        else str(hierarchy_path),
    )
    gate_result = evaluate_gate(
        gate_definition,
        child_inputs,
        now=now,
        max_report_age_hours=max_report_age_hours,
    )
    status = gate_result.status
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
            "manual_override_allowed": gate_result.manual_override_allowed,
        },
        "collected": gate_result.collected,
        "passed": gate_result.passed,
        "failed": gate_result.failed,
        "errors": gate_result.errors,
        "skipped": gate_result.skipped,
        "exit_code": gate_result.exit_code,
        "hierarchy_source": hierarchy_path.relative_to(REPO_ROOT).as_posix(),
        "report_dir": report_dir.relative_to(REPO_ROOT).as_posix() if _is_relative_to(report_dir, REPO_ROOT) else str(report_dir),
        "no_manual_override": True,
        "mandatory_children": mandatory_children,
        "child_results": gate_result.child_results,
        "blockers": gate_result.blockers,
        "gate_decision_trace": gate_result.decision_trace.to_dict(),
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
