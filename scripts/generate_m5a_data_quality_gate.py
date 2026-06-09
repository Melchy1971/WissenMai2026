from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.parent_gate_validator import validate_parent_gate
except ModuleNotFoundError:
    from parent_gate_validator import validate_parent_gate


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"

START_GATE = "m5a_start_gate.json"
DUPLICATE_GATE = "m5a_duplicate_detector_gate.json"
METADATA_GATE = "m5a_metadata_detector_gate.json"
LIFECYCLE_GATE = "m5a_lifecycle_integrity_gate.json"
DATA_QUALITY_REPORT = "data_quality_report.json"
DOC_TRUTH_LINT = "documentation_truth_lint.json"
REPORT_INTEGRITY = "report_integrity_v2.json"
CHILD_GATE_MATRIX = "m5a_child_gate_matrix.json"

OUTPUT_GATE = "m5a_data_quality_gate.json"
SCORE_THRESHOLD = 90.0
PARENT_GATE_MAX_REPORT_AGE_HOURS = 168

SOURCE_STATUS_DETECTOR = REPO_ROOT / "backend" / "app" / "services" / "source_status_integrity_detector.py"
ORPHAN_DETECTOR = REPO_ROOT / "backend" / "app" / "services" / "orphan_detector.py"
QUALITY_SCORE_SERVICE = REPO_ROOT / "backend" / "app" / "services" / "quality_score.py"
DATA_QUALITY_API = REPO_ROOT / "backend" / "app" / "api" / "v1" / "data_quality.py"
DATA_QUALITY_DASHBOARD = REPO_ROOT / "frontend" / "src" / "features" / "data-quality" / "DataQualityDashboard.jsx"
RUNNER_FILE = REPO_ROOT / "backend" / "app" / "services" / "data_quality_runner.py"

SOURCE_STATUS_TEST = REPO_ROOT / "backend" / "tests" / "test_source_status_integrity_detector.py"
ORPHAN_TEST = REPO_ROOT / "backend" / "tests" / "test_orphan_detector.py"
QUALITY_SCORE_TEST = REPO_ROOT / "backend" / "tests" / "test_m5a_quality_score.py"
DATA_QUALITY_API_TEST = REPO_ROOT / "backend" / "tests" / "test_data_quality_api.py"
DASHBOARD_TEST = REPO_ROOT / "frontend" / "src" / "tests" / "pages" / "DataQualityPage.test.jsx"


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


def _file_contains(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    try:
        return needle in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _report_has_v2_fields(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    required = (
        "total_documents",
        "duplicate_findings",
        "metadata_findings",
        "lifecycle_findings",
        "source_status_findings",
        "orphan_findings",
        "quality_score",
        "findings_by_severity",
        "findings_by_type",
    )
    return (
        report.get("report_schema_version") == 2
        and all(key in report for key in required)
        and isinstance(report.get("findings_by_severity"), dict)
        and isinstance(report.get("findings_by_type"), dict)
    )


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
        and isinstance(report.get("total_documents"), int)
        and isinstance(report.get("total_findings"), int)
        and isinstance(report.get("quality_score"), int | float)
        and _report_has_v2_fields(report)
        and isinstance(report.get("findings"), list)
        and isinstance(report.get("started_at"), str)
        and isinstance(report.get("finished_at"), str)
    )
    if completed and has_required_fields:
        return "COMPLETED", True

    return "INCOMPLETE", False


def _parent_child_status(parent_validation: dict[str, Any]) -> str:
    child_results = parent_validation.get("child_results")
    if not isinstance(child_results, dict) or not child_results:
        return "BLOCKED"

    statuses = {
        str(item.get("validation_status") or "")
        for item in child_results.values()
        if isinstance(item, dict)
    }
    if statuses & {"BLOCKED", "MISSING", "INVALID", "STALE"}:
        return "BLOCKED"
    if "FAIL" in statuses:
        return "FAIL"
    if statuses == {"PASS"}:
        return "PASS"
    return "BLOCKED"


def _child_gate_trace(
    parent_validation: dict[str, Any],
    matrix: dict[str, Any] | None,
    report_integrity: dict[str, Any] | None,
    status: str,
) -> dict[str, Any]:
    child_results = parent_validation.get("child_results")
    if not isinstance(child_results, dict):
        child_results = {}

    matrix_children = {}
    if isinstance(matrix, dict) and isinstance(matrix.get("child_gates"), list):
        matrix_children = {
            str(item.get("child_gate")): item
            for item in matrix["child_gates"]
            if isinstance(item, dict)
        }

    evaluated_children: list[dict[str, Any]] = []
    for child_id, result in child_results.items():
        if not isinstance(result, dict):
            continue
        validation_status = str(result.get("validation_status") or "INVALID")
        matrix_child = matrix_children.get(str(child_id), {})
        evaluated_children.append({
            "child_gate_id": child_id,
            "report": result.get("report"),
            "matrix_status": matrix_child.get("status"),
            "matrix_blocking": matrix_child.get("blocking"),
            "parent_validation_status": validation_status,
            "report_status": result.get("report_status"),
            "decision": result.get("decision"),
            "generated_by": result.get("generated_by"),
            "timestamp": result.get("timestamp"),
            "collected": result.get("collected"),
            "report_type": result.get("report_type"),
            "effect": (
                "blocks_parent"
                if validation_status in {"BLOCKED", "MISSING", "INVALID", "STALE"}
                else "fails_parent"
                if validation_status == "FAIL"
                else "passes_parent"
            ),
            "blockers": result.get("blockers", []),
        })

    return {
        "parent_gate": "m5a",
        "rule": (
            "PASS iff all child gates PASS. BLOCKED if at least one child gate is "
            "BLOCKED, missing, invalid, or stale. FAIL if no child gate blocks and at least "
            "one child gate is technically FAIL."
        ),
        "inputs": {
            "child_gate_matrix": {
                "source": f"reports/current/{CHILD_GATE_MATRIX}",
                "status": matrix.get("status") if isinstance(matrix, dict) else None,
                "timestamp": matrix.get("timestamp") if isinstance(matrix, dict) else None,
            },
            "report_integrity_v2": {
                "source": f"reports/current/{REPORT_INTEGRITY}",
                "status": report_integrity.get("status") if isinstance(report_integrity, dict) else None,
                "timestamp": report_integrity.get("timestamp") if isinstance(report_integrity, dict) else None,
            },
            "parent_gate_validator": {
                "source": "scripts/parent_gate_validator.py m5a",
                "status": parent_validation.get("status"),
                "timestamp": parent_validation.get("timestamp"),
            },
        },
        "evaluated_children": evaluated_children,
        "blocking_children": [
            item["child_gate_id"]
            for item in evaluated_children
            if item["parent_validation_status"] in {"BLOCKED", "MISSING", "INVALID", "STALE"}
        ],
        "failing_children": [
            item["child_gate_id"]
            for item in evaluated_children
            if item["parent_validation_status"] == "FAIL"
        ],
        "final_status": status,
    }


def build_gate_report(current_dir: Path = CURRENT_DIR, *, timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or datetime.now(UTC).isoformat()
    parent_validation = validate_parent_gate(
        "m5a",
        report_dir=current_dir,
        timestamp=now,
        max_report_age_hours=PARENT_GATE_MAX_REPORT_AGE_HOURS,
    )
    status = _parent_child_status(parent_validation)
    parent_validation_pass = status == "PASS"
    child_gate_count = _int_value(parent_validation.get("collected"), 0)
    child_gates_passed = _int_value(parent_validation.get("passed"), 0)
    child_gates_failed = child_gate_count - child_gates_passed

    start_gate, start_gate_error = _load_json(current_dir / START_GATE)
    duplicate_gate, duplicate_gate_error = _load_json(current_dir / DUPLICATE_GATE)
    metadata_gate, metadata_gate_error = _load_json(current_dir / METADATA_GATE)
    lifecycle_gate, lifecycle_gate_error = _load_json(current_dir / LIFECYCLE_GATE)
    dq_report, dq_report_error = _load_json(current_dir / DATA_QUALITY_REPORT)
    doc_lint, doc_lint_error = _load_json(current_dir / DOC_TRUTH_LINT)
    report_integrity, report_integrity_error = _load_json(current_dir / REPORT_INTEGRITY)
    child_gate_matrix, child_gate_matrix_error = _load_json(current_dir / CHILD_GATE_MATRIX)

    diagnostic_blockers: list[dict[str, Any]] = []

    for report_name, error in (
        (START_GATE, start_gate_error),
        (DUPLICATE_GATE, duplicate_gate_error),
        (METADATA_GATE, metadata_gate_error),
        (LIFECYCLE_GATE, lifecycle_gate_error),
        (DATA_QUALITY_REPORT, dq_report_error),
        (DOC_TRUTH_LINT, doc_lint_error),
        (REPORT_INTEGRITY, report_integrity_error),
        (CHILD_GATE_MATRIX, child_gate_matrix_error),
    ):
        if error:
            diagnostic_blockers.append({
                "id": f"invalid_{Path(report_name).stem}",
                "severity": "blocking",
                "reason": f"Invalid or missing gate input JSON in reports/current/{report_name}: {error}",
            })

    start_pass = _is_pass_gate(start_gate)
    duplicate_pass = _is_pass_gate(duplicate_gate)
    metadata_pass = _is_pass_gate(metadata_gate)
    lifecycle_pass = _is_pass_gate(lifecycle_gate)
    dq_state, dq_completed = _data_quality_report_state(dq_report if dq_report_error is None else None)
    doc_lint_pass = _is_pass_status(doc_lint) and _int_value((doc_lint or {}).get("summary", {}).get("errors"), 0) == 0
    report_integrity_pass = _is_pass_gate(report_integrity)
    no_invalid_json = _criterion_passed(report_integrity, "reports_current_json_valid")
    source_status_pass = (
        SOURCE_STATUS_DETECTOR.exists()
        and SOURCE_STATUS_TEST.exists()
        and _file_contains(RUNNER_FILE, "SourceStatusIntegrityDetector")
    )
    orphan_pass = (
        ORPHAN_DETECTOR.exists()
        and ORPHAN_TEST.exists()
        and _file_contains(RUNNER_FILE, "OrphanObjectDetector")
    )
    score = float((dq_report or {}).get("quality_score") or 0.0)
    quality_score_pass = QUALITY_SCORE_SERVICE.exists() and QUALITY_SCORE_TEST.exists() and score >= SCORE_THRESHOLD
    api_pass = DATA_QUALITY_API.exists() and DATA_QUALITY_API_TEST.exists()
    dashboard_pass = (
        DATA_QUALITY_DASHBOARD.exists()
        and DASHBOARD_TEST.exists()
        and _file_contains(DATA_QUALITY_DASHBOARD, "dq-score-breakdown")
        and _file_contains(DATA_QUALITY_DASHBOARD, "dq-runs-trend")
    )
    report_v2_pass = dq_completed and _report_has_v2_fields(dq_report)

    if dq_state == "NOT_RUN":
        diagnostic_blockers.append({
            "id": "data_quality_report_not_run",
            "severity": "blocking",
            "reason": "M5a Data Quality report is NOT_RUN/missing; gate remains BLOCKED.",
        })
    elif dq_state == "INCOMPLETE":
        diagnostic_blockers.append({
            "id": "data_quality_report_incomplete",
            "severity": "blocking",
            "reason": "M5a Data Quality report is present but not a completed full run.",
        })

    # ---------------------------------------------------------------------------
    # Mandatory precondition gates — failure sets status=BLOCKED, not FAIL.
    # These must appear in criteria so their pass/fail state drives the result.
    # ---------------------------------------------------------------------------
    MANDATORY_GATE_IDS = frozenset({
        "m5a_start_gate_pass",
        "documentation_truth_lint_pass",
        "report_integrity_v2_pass",
        "parent_gate_validation_pass",
    })

    criteria: list[dict[str, Any]] = [
        # --- Mandatory precondition gates ---
        {
            "id": "m5a_start_gate_pass",
            "label": "M5a Start Gate",
            "mandatory": True,
            "passed": start_pass,
            "source": f"reports/current/{START_GATE}",
            "evidence": str((start_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "documentation_truth_lint_pass",
            "label": "Documentation Truth Lint",
            "mandatory": True,
            "passed": doc_lint_pass,
            "source": f"reports/current/{DOC_TRUTH_LINT}",
            "evidence": "PASS" if doc_lint_pass else str((doc_lint or {}).get("status") or "MISSING"),
        },
        {
            "id": "report_integrity_v2_pass",
            "label": "Report Integrity v2",
            "mandatory": True,
            "passed": report_integrity_pass,
            "source": f"reports/current/{REPORT_INTEGRITY}",
            "evidence": str((report_integrity or {}).get("status") or "MISSING"),
        },
        # --- Slice and implementation criteria ---
        {
            "id": "duplicate_detector_pass",
            "label": "Duplicate Detector",
            "passed": duplicate_pass,
            "source": f"reports/current/{DUPLICATE_GATE}",
            "evidence": str((duplicate_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "metadata_detector_pass",
            "label": "Metadata Detector",
            "passed": metadata_pass,
            "source": f"reports/current/{METADATA_GATE}",
            "evidence": str((metadata_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "lifecycle_detector_pass",
            "label": "Lifecycle Detector",
            "passed": lifecycle_pass,
            "source": f"reports/current/{LIFECYCLE_GATE}",
            "evidence": str((lifecycle_gate or {}).get("status") or "MISSING"),
        },
        {
            "id": "source_status_detector_pass",
            "label": "Source Status Detector",
            "passed": source_status_pass,
            "source": "backend/app/services/source_status_integrity_detector.py",
            "evidence": "implemented_and_runner_integrated" if source_status_pass else "missing",
        },
        {
            "id": "orphan_detector_pass",
            "label": "Orphan Detector",
            "passed": orphan_pass,
            "source": "backend/app/services/orphan_detector.py",
            "evidence": "implemented_and_runner_integrated" if orphan_pass else "missing",
        },
        {
            "id": "quality_score_pass",
            "label": "Quality Score",
            "passed": quality_score_pass,
            "source": f"reports/current/{DATA_QUALITY_REPORT}",
            "evidence": f"{score} >= {SCORE_THRESHOLD}",
        },
        {
            "id": "data_quality_api_pass",
            "label": "Data Quality API",
            "passed": api_pass,
            "source": "backend/app/api/v1/data_quality.py",
            "evidence": "api_and_tests_present" if api_pass else "missing",
        },
        {
            "id": "dashboard_pass",
            "label": "Dashboard",
            "passed": dashboard_pass,
            "source": "frontend/src/features/data-quality/DataQualityDashboard.jsx",
            "evidence": "dashboard_widgets_present" if dashboard_pass else "missing_widgets",
        },
        {
            "id": "data_quality_report_v2_pass",
            "label": "Data Quality Report V2",
            "passed": report_v2_pass,
            "source": f"reports/current/{DATA_QUALITY_REPORT}",
            "evidence": f"{dq_state}, schema_version={(dq_report or {}).get('report_schema_version')}",
        },
        {
            "id": "parent_gate_validation_pass",
            "label": "Parent Gate Validator",
            "mandatory": True,
            "passed": parent_validation_pass,
            "source": "docs/gate_hierarchy.json",
            "evidence": parent_validation["status"],
        },
    ]

    passed = sum(1 for item in criteria if item["passed"])
    failed = len(criteria) - passed
    for item in criteria:
        if not item["passed"]:
            diagnostic_blockers.append({
                "id": item["id"],
                "severity": "blocking",
                "reason": f"{item['label']} criterion failed: {item['evidence']}",
                "source": item["source"],
            })
    for parent_blocker in parent_validation["blockers"]:
        diagnostic_blockers.append({
            "id": f"parent_child_{parent_blocker['child_gate_id']}",
            "child_gate_id": parent_blocker["child_gate_id"],
            "severity": "blocking",
            "reason": parent_blocker["reason"],
            "source": "docs/gate_hierarchy.json",
        })

    child_gate_blockers = [
        {
            "id": f"child_gate_{parent_blocker['child_gate_id']}",
            "child_gate_id": parent_blocker["child_gate_id"],
            "severity": "blocking",
            "reason": parent_blocker["reason"],
            "source": "scripts/parent_gate_validator.py",
        }
        for parent_blocker in parent_validation["blockers"]
    ]
    gate_decision_trace = _child_gate_trace(parent_validation, child_gate_matrix, report_integrity, status)
    go_no_go = "GO" if status == "PASS" else "NO_GO"
    gate_score = 100.0 if status == "PASS" else round((child_gates_passed / max(child_gate_count, 1)) * 100.0, 2)

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
        "collected": child_gate_count,
        "passed": child_gates_passed,
        "failed": child_gates_failed,
        "errors": 0,
        "skipped": 0,
        "exit_code": 0 if status == "PASS" else 1,
        "score": gate_score,
        "score_threshold": SCORE_THRESHOLD,
        "blockers": child_gate_blockers,
        "diagnostic_blockers": diagnostic_blockers,
        "source_command": "python scripts/generate_m5a_data_quality_gate.py",
        "decision": {
            "go_no_go": go_no_go,
            "result": go_no_go,
            "m5a_gate_passed": status == "PASS",
            "m5a_gate_partial_pass": False,
            "m5a_start_gate_pass": start_pass,
            "required_slices_all_pass": duplicate_pass and metadata_pass and lifecycle_pass and source_status_pass and orphan_pass,
            "data_quality_report_state": dq_state,
            "quality_score": score,
            "score_threshold": SCORE_THRESHOLD,
            "global_m5_release_allowed": False,
            "no_invalid_json_reports": no_invalid_json,
            "documentation_truth_lint_pass": doc_lint_pass,
            "report_integrity_v2_pass": report_integrity_pass,
            "parent_gate_validation_pass": parent_validation_pass,
            "child_gate_matrix_status": child_gate_matrix.get("status") if isinstance(child_gate_matrix, dict) else None,
        },
        "inputs": {
            "child_gate_matrix": f"reports/current/{CHILD_GATE_MATRIX}",
            "start_gate": f"reports/current/{START_GATE}",
            "duplicate_slice_gate": f"reports/current/{DUPLICATE_GATE}",
            "metadata_slice_gate": f"reports/current/{METADATA_GATE}",
            "lifecycle_slice_gate": f"reports/current/{LIFECYCLE_GATE}",
            "data_quality_report": f"reports/current/{DATA_QUALITY_REPORT}",
            "documentation_truth_lint": f"reports/current/{DOC_TRUTH_LINT}",
            "report_integrity_v2": f"reports/current/{REPORT_INTEGRITY}",
            "gate_hierarchy": "docs/gate_hierarchy.json",
        },
        "criteria": criteria,
        "parent_gate_validation": parent_validation,
        "gate_decision_trace": gate_decision_trace,
        "summary": {
            "rule": (
                "M5a Data Quality Gate status is derived only from child-gate aggregation. "
                "PASS requires every child gate to PASS. BLOCKED is used when at least one "
                "child gate is BLOCKED, missing, invalid, or stale. FAIL is used when no child "
                "blocks and at least one child gate technically FAILs."
            ),
            "mandatory_gate_ids": sorted(MANDATORY_GATE_IDS),
            "parent_gate_id": "m5a",
            "parent_gate_validation_required": True,
            "overall_m5a_data_quality_pass": status == "PASS",
            "child_gates_collected": child_gate_count,
            "child_gates_passed": child_gates_passed,
            "child_gates_failed_or_blocking": child_gates_failed,
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
