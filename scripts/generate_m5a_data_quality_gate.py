from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"

START_GATE = "m5a_start_gate.json"
DUPLICATE_GATE = "m5a_duplicate_detector_gate.json"
METADATA_GATE = "m5a_metadata_detector_gate.json"
DATA_QUALITY_REPORT = "data_quality_report.json"
DOC_TRUTH_LINT = "documentation_truth_lint.json"
REPORT_INTEGRITY = "report_integrity_pre_m5a.json"

OUTPUT_GATE = "m5a_data_quality_gate.json"


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return None, "empty file"
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be object"
    return payload, None


def _int_value(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _decision_value(report: dict[str, Any] | None) -> str | None:
    if not report:
        return None
    decision = report.get("decision")
    if isinstance(decision, dict):
        value = decision.get("go_no_go") or decision.get("result")
    else:
        value = decision
    if value is None:
        return None
    return str(value).upper().replace("-", "_")


def _is_pass_gate(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    collected = _int_value(report.get("collected"), 0)
    failed = _int_value(report.get("failed"), 0)
    errors = _int_value(report.get("errors"), 0)
    skipped = _int_value(report.get("skipped"), 0)
    exit_code = _int_value(report.get("exit_code"), 1)
    return status == "PASS" and collected > 0 and failed == 0 and errors == 0 and skipped == 0 and exit_code == 0


def _is_pass_status(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    return str(report.get("status") or report.get("result") or "").upper() == "PASS"


def _criterion_passed(report: dict[str, Any] | None, criterion_id: str) -> bool:
    if not report:
        return False
    criteria = report.get("criteria")
    if not isinstance(criteria, list):
        return False
    for item in criteria:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") == criterion_id:
            return bool(item.get("passed") is True)
    return False


def _data_quality_report_state(report: dict[str, Any] | None) -> tuple[str, bool]:
    if not report:
        return "NOT_RUN", False

    status = str(report.get("status") or report.get("result") or "").upper()
    if status == "NOT_RUN":
        return "NOT_RUN", False

    completed = str(report.get("status") or "").lower() == "completed"
    has_required_fields = (
        isinstance(report.get("run_id"), str)
        and isinstance(report.get("workspace_id"), str)
        and isinstance(report.get("total_findings"), int)
        and isinstance(report.get("quality_score"), int | float)
        and isinstance(report.get("findings"), list)
        and isinstance(report.get("started_at"), str)
        and isinstance(report.get("finished_at"), str)
    )
    if completed and has_required_fields:
        return "COMPLETED", True

    return "INCOMPLETE", False


def build_gate_report(current_dir: Path = CURRENT_DIR, *, timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or datetime.now(UTC).isoformat()

    start_gate, start_gate_error = _load_json(current_dir / START_GATE)
    duplicate_gate, duplicate_gate_error = _load_json(current_dir / DUPLICATE_GATE)
    metadata_gate, metadata_gate_error = _load_json(current_dir / METADATA_GATE)
    dq_report, dq_report_error = _load_json(current_dir / DATA_QUALITY_REPORT)
    doc_lint, doc_lint_error = _load_json(current_dir / DOC_TRUTH_LINT)
    report_integrity, report_integrity_error = _load_json(current_dir / REPORT_INTEGRITY)

    blockers: list[dict[str, Any]] = []

    for report_name, error in (
        (START_GATE, start_gate_error),
        (DUPLICATE_GATE, duplicate_gate_error),
        (METADATA_GATE, metadata_gate_error),
        (DATA_QUALITY_REPORT, dq_report_error),
        (DOC_TRUTH_LINT, doc_lint_error),
        (REPORT_INTEGRITY, report_integrity_error),
    ):
        if error:
            blockers.append({
                "id": f"invalid_{Path(report_name).stem}",
                "severity": "blocking",
                "reason": f"Invalid or missing gate input JSON in reports/current/{report_name}: {error}",
            })

    start_pass = _is_pass_gate(start_gate)
    duplicate_pass = _is_pass_gate(duplicate_gate)
    metadata_pass = _is_pass_gate(metadata_gate)
    dq_state, dq_completed = _data_quality_report_state(dq_report if dq_report_error is None else None)
    doc_lint_pass = _is_pass_status(doc_lint) and _int_value((doc_lint or {}).get("summary", {}).get("errors"), 0) == 0
    report_integrity_pass = _is_pass_gate(report_integrity)
    no_invalid_json = _criterion_passed(report_integrity, "reports_current_json_valid")

    partial_pass = duplicate_pass and metadata_pass
    full_pass = partial_pass and dq_completed and start_pass and report_integrity_pass and doc_lint_pass

    if not start_pass:
        blockers.append({
            "id": "m5a_start_gate_not_pass",
            "severity": "blocking",
            "reason": "m5a_start_gate must be PASS before M5a Data Quality can pass.",
        })
    if not duplicate_pass:
        blockers.append({
            "id": "required_slice_missing_duplicate_detector",
            "severity": "blocking",
            "reason": "Required slice gate m5a_duplicate_detector_gate is not PASS.",
        })
    if not metadata_pass:
        blockers.append({
            "id": "required_slice_missing_metadata_detector",
            "severity": "blocking",
            "reason": "Required slice gate m5a_metadata_detector_gate is not PASS.",
        })

    if dq_state == "NOT_RUN":
        blockers.append({
            "id": "data_quality_report_not_run",
            "severity": "blocking",
            "reason": "M5a Data Quality report is NOT_RUN/missing; gate remains BLOCKED.",
        })
    elif dq_state == "INCOMPLETE":
        blockers.append({
            "id": "data_quality_report_incomplete",
            "severity": "blocking",
            "reason": "M5a Data Quality report is present but not a completed full run.",
        })

    if blockers:
        status = "BLOCKED"
        go_no_go = "NO_GO"
    elif full_pass:
        status = "PASS"
        go_no_go = "GO"
    elif partial_pass:
        status = "PARTIAL_PASS"
        go_no_go = "NO_GO"
    else:
        status = "BLOCKED"
        go_no_go = "NO_GO"

    criteria: list[dict[str, Any]] = [
        {
            "id": "m5a_start_gate_go",
            "label": "M5a Start Gate PASS",
            "passed": start_pass,
            "source": f"reports/current/{START_GATE}",
            "evidence": str((start_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "m5a_duplicate_detector_slice_pass",
            "label": "M5a Duplicate Detector Slice PASS",
            "passed": duplicate_pass,
            "source": f"reports/current/{DUPLICATE_GATE}",
            "evidence": str((duplicate_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "m5a_metadata_detector_slice_pass",
            "label": "M5a Metadata Detector Slice PASS",
            "passed": metadata_pass,
            "source": f"reports/current/{METADATA_GATE}",
            "evidence": str((metadata_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "m5a_data_quality_report_ran",
            "label": "M5a Data Quality Report vollstaendig ausgefuehrt",
            "passed": dq_completed,
            "source": f"reports/current/{DATA_QUALITY_REPORT}",
            "evidence": dq_state,
        },
        {
            "id": "partial_pass_duplicate_and_metadata",
            "label": "Duplicate PASS + Metadata PASS = PARTIAL_PASS",
            "passed": partial_pass,
            "source": f"reports/current/{DUPLICATE_GATE}, reports/current/{METADATA_GATE}",
            "evidence": "true" if partial_pass else "false",
        },
        {
            "id": "full_pass_requires_completed_run",
            "label": "Gesamt-PASS nur bei vollstaendigem Data Quality Run",
            "passed": dq_completed,
            "source": f"reports/current/{DATA_QUALITY_REPORT}",
            "evidence": dq_state,
        },
        {
            "id": "report_integrity_supports_no_invalid_json",
            "label": "report_integrity_pre_m5a bestaetigt keine invalid JSON Reports",
            "passed": no_invalid_json,
            "source": f"reports/current/{REPORT_INTEGRITY}",
            "evidence": "reports_current_json_valid=true" if no_invalid_json else "reports_current_json_valid=false",
        },
        {
            "id": "documentation_truth_lint_pass",
            "label": "documentation_truth_lint ist PASS",
            "passed": doc_lint_pass,
            "source": f"reports/current/{DOC_TRUTH_LINT}",
            "evidence": "PASS" if doc_lint_pass else "NOT_PASS",
        },
        {
            "id": "report_integrity_gate_pass",
            "label": "report_integrity_pre_m5a ist PASS",
            "passed": report_integrity_pass,
            "source": f"reports/current/{REPORT_INTEGRITY}",
            "evidence": "PASS" if report_integrity_pass else "NOT_PASS",
        },
    ]

    passed = sum(1 for item in criteria if item["passed"])
    failed = len(criteria) - passed

    return {
        "report_schema_version": 1,
        "report_name": "m5a_data_quality_gate",
        "gate": "m5a_data_quality_gate",
        "generated_by": "gate_validator",
        "timestamp": now,
        "environment": "local",
        "report_type": "gate",
        "status": status,
        "result": status,
        "collected": len(criteria),
        "passed": passed,
        "failed": failed,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "blockers": blockers,
        "source_command": "python scripts/generate_m5a_data_quality_gate.py",
        "decision": {
            "go_no_go": go_no_go,
            "result": go_no_go,
            "m5a_gate_passed": status == "PASS",
            "m5a_gate_partial_pass": status == "PARTIAL_PASS",
            "m5a_start_gate_pass": start_pass,
            "required_slices_all_pass": partial_pass,
            "data_quality_report_state": dq_state,
            "global_m5_release_allowed": False,
            "no_invalid_json_reports": no_invalid_json,
        },
        "inputs": {
            "start_gate": f"reports/current/{START_GATE}",
            "duplicate_slice_gate": f"reports/current/{DUPLICATE_GATE}",
            "metadata_slice_gate": f"reports/current/{METADATA_GATE}",
            "data_quality_report": f"reports/current/{DATA_QUALITY_REPORT}",
            "documentation_truth_lint": f"reports/current/{DOC_TRUTH_LINT}",
            "report_integrity_pre_m5a": f"reports/current/{REPORT_INTEGRITY}",
        },
        "criteria": criteria,
        "summary": {
            "rule": "Duplicate PASS + Metadata PASS => PARTIAL_PASS; Gesamt-PASS nur bei vollstaendigem Data Quality Run; invalid JSON oder NOT_RUN => BLOCKED; keine globale M5-Freigabe.",
            "overall_m5a_data_quality_pass": status == "PASS",
        },
    }


def write_gate_report(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp_path.write_text(text, encoding="utf-8")

    # Post-write validation before rename.
    parsed = json.loads(tmp_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Generated gate payload must be a JSON object")

    tmp_path.replace(output_path)


def main() -> int:
    payload = build_gate_report()
    output = CURRENT_DIR / OUTPUT_GATE
    write_gate_report(payload, output)
    print(f"m5a_data_quality_gate = {payload['decision']['go_no_go']} (status={payload['status']})")
    print(f"Wrote: {output}")
    return int(payload.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
