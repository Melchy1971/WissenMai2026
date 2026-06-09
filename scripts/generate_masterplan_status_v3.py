"""Masterplan Status Engine v3.

Derives the current masterplan state from current report artifacts only.
Manual status text and archived/root-level reports are not authority inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from m3a_stale_guard import check_staleness  # noqa: E402
from parent_gate_validator import HIERARCHY_JSON, validate_parent_gate  # noqa: E402
from progress_calculator import calculate_masterplan_progress  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
DEFAULT_OUTPUT_JSON = CURRENT_DIR / "masterplan_status.json"
DEFAULT_OUTPUT_SECTION = REPO_ROOT / "docs" / "generated" / "status_section.md"
DEFAULT_MASTERPLAN = REPO_ROOT / "masterplan.md"

M3A_RC = "m3a_release_candidate.json"
M4_BACKEND_RC = "m4_backend_release_candidate.json"
DOC_LINT = "documentation_truth_lint.json"
KNOWN_LIMITATIONS = "known_limitations.json"
M4E_OPERATIONS_RELEASE = "m4e_operations_release_report.json"
M4E_OPERATIONS_RELEASE_GATE = "m4e_operations_release_gate.json"
M5_GATE_ASSESSMENT = "m5_gate_assessment.json"
M5A_START_GATE = "m5a_start_gate.json"
M5A_DATA_QUALITY_GATE = "m5a_data_quality_gate.json"
M5A_DUPLICATE_DETECTOR_GATE = "m5a_duplicate_detector_gate.json"
M5A_METADATA_DETECTOR_GATE = "m5a_metadata_detector_gate.json"
REPORT_INTEGRITY_V2 = "report_integrity_v2.json"
M5B_START_GATE = "m5b_start_gate.json"
M5B_IMPLEMENTATION_GATE = "m5b_implementation_gate.json"
M5A_PARENT_GATE_NOT_PASSED = "M5A_PARENT_GATE_NOT_PASSED"
RUNTIME_CONNECTIVITY_GATE = "runtime_connectivity_gate.json"
FRONTEND_FULL_SUITE = "frontend_full_suite_staged_report.json"
PREFLIGHT = "report_truth_preflight.json"

SCHEMA_VERSION = 3
M5_STATUSES = (
    "NOT_STARTED",
    "PREPARATION_ALLOWED",
    "PREPARATION_DONE",
    "SLICE_START_ALLOWED",
    "SLICE_IMPLEMENTING",
    "SLICE_GATE_PASSED",
    "M5_IMPLEMENTATION_ALLOWED",
    "BLOCKED",
)


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root must be an object"
    return payload, None


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _decision(report: dict[str, Any] | None) -> str | None:
    if not report:
        return None
    raw_decision = report.get("decision")
    if isinstance(raw_decision, dict):
        raw = raw_decision.get("go_no_go") or raw_decision.get("result")
    else:
        raw = raw_decision
    raw = raw or report.get("go_no_go") or report.get("operations_release_status")
    return str(raw).upper().replace("-", "_") if raw is not None else None


def _is_pass_report(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    status = str(report.get("status") or report.get("result") or "").upper()
    if status in {"STALE", "BLOCKED"}:
        return False
    return (
        status == "PASS"
        and _int_value(report.get("collected")) > 0
        and _int_value(report.get("failed")) == 0
        and _int_value(report.get("errors")) == 0
        and _int_value(report.get("skipped")) == 0
        and _int_value(report.get("exit_code")) == 0
        and (_decision(report) in {None, "GO"})
    )


def _is_go_gate(report: dict[str, Any] | None) -> bool:
    if report is None:
        return False
    return _decision(report) == "GO" or _is_pass_report(report)


def _doc_lint_errors(report: dict[str, Any] | None) -> int:
    if report is None:
        return 1
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return _int_value(summary.get("errors") if "errors" in summary else report.get("errors"))


def _check_m3a_stale(m3a: dict[str, Any] | None, current_dir: Path) -> dict[str, Any] | None:
    def _quick_load(name: str) -> dict[str, Any] | None:
        payload, _ = _load_json(current_dir / name)
        return payload

    def _frontend_completion_evidence() -> dict[str, Any] | None:
        current = _quick_load(FRONTEND_FULL_SUITE)
        if current is not None:
            return current
        stale_guard = m3a.get("stale_guard") if isinstance(m3a, dict) else {}
        input_timestamps = stale_guard.get("input_timestamps") if isinstance(stale_guard, dict) else {}
        timestamp = input_timestamps.get("frontend_full_suite_staged_report") if isinstance(input_timestamps, dict) else None
        return {"timestamp": timestamp} if timestamp else None

    stale_result = check_staleness(
        m3a,
        _frontend_completion_evidence(),
        _quick_load(PREFLIGHT),
        _quick_load(DOC_LINT),
        runtime_connectivity_gate=_quick_load(RUNTIME_CONNECTIVITY_GATE),
    )
    if not stale_result.is_stale:
        return None
    return {
        "id": "m3a_rc_stale",
        "type": "stale_guard",
        "severity": "blocking",
        "detail": (
            "M3a RC is STALE: mandatory input reports are newer than the RC. "
            f"Regenerate with: python scripts/generate_m3a_release_candidate.py "
            f"({stale_result.stale_reason})"
        ),
        "source": f"reports/current/{M3A_RC}",
        "stale_reasons": stale_result.reasons,
    }


def _active_limitations(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    limitations = report.get("limitations", []) if report else []
    if not isinstance(limitations, list):
        return []
    inactive = {"resolved", "closed", "released", "deferred"}
    return [
        item for item in limitations
        if isinstance(item, dict) and str(item.get("status", "open")).lower() not in inactive
    ]


def _gate_list(item: dict[str, Any]) -> list[str]:
    raw = item.get("blockiert_gate", item.get("blocks_gate", []))
    return [str(value) for value in raw] if isinstance(raw, list) else []


def _known_limitations_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    limitations = report.get("limitations", []) if report and isinstance(report.get("limitations"), list) else []
    active = _active_limitations(report)
    blocking = [item for item in active if _gate_list(item)]
    m5_slice = [
        item for item in active
        if any(gate in {"m5_slice_start_gate", "m5_truth_gate"} for gate in _gate_list(item))
    ]
    operations_open = [
        item for item in active
        if not _gate_list(item)
        and ("Operations" in str(item.get("zielphase", "")) or "M4e" in str(item.get("bereich", "")))
    ]
    return {
        "total": len(limitations),
        "active": len(active),
        "blocking": len(blocking),
        "blocking_ids": [str(item.get("id")) for item in blocking],
        "m5_slice_blocking_ids": [str(item.get("id")) for item in m5_slice],
        "operations_explicitly_released": len(operations_open) == 0,
        "operations_open_ids": [str(item.get("id")) for item in operations_open],
    }


def _summary(report: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    if report is None:
        return {"available": False, "error": error}
    return {
        "available": True,
        "report_name": report.get("report_name"),
        "gate": report.get("gate"),
        "status": report.get("status"),
        "result": report.get("result"),
        "decision": _decision(report),
        "collected": report.get("collected"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "errors": report.get("errors"),
        "skipped": report.get("skipped"),
        "exit_code": report.get("exit_code"),
        "timestamp": report.get("timestamp") or report.get("generated_at"),
    }


def _phase(
    phase_id: str,
    label: str,
    *,
    passed: bool,
    decision: str,
    gate_id: str,
    source: str,
    blockers: list[dict[str, Any]],
    phase_status: str | None = None,
    gate_status: str | None = None,
) -> dict[str, Any]:
    return {
        "id": phase_id,
        "label": label,
        "status": phase_status or ("gate_passed" if passed else "blocked"),
        "decision": decision,
        "gate_id": gate_id,
        "gate_status": gate_status or ("PASS" if passed else "FAIL"),
        "source": source,
        "blockers": blockers,
    }


def _invalid_json_blockers(errors: dict[str, str | None]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for name, error in errors.items():
        if error and error != "missing":
            blockers.append({
                "id": f"invalid_{Path(name).stem}",
                "type": "input_integrity",
                "severity": "blocking",
                "detail": f"{name} is not a valid current JSON report: {error}",
                "source": f"reports/current/{name}",
            })
    return blockers


def _assessment_value(report: dict[str, Any] | None, key: str) -> bool | None:
    if not report:
        return None
    assessment = report.get("assessment") if isinstance(report.get("assessment"), dict) else {}
    value = assessment.get(key, report.get(key))
    return value if isinstance(value, bool) else None


def _derive_m5_status(
    *,
    blocked: bool,
    m4e_operations_pass: bool,
    preparation_done: bool,
    slice_start_allowed: bool,
    slice_implementing: bool,
    slice_gate_passed: bool,
) -> str:
    if blocked:
        return "BLOCKED"
    if not m4e_operations_pass:
        return "NOT_STARTED"
    if slice_gate_passed:
        return "SLICE_GATE_PASSED"
    if slice_implementing:
        return "SLICE_IMPLEMENTING"
    if slice_start_allowed:
        return "SLICE_START_ALLOWED"
    if preparation_done:
        return "PREPARATION_DONE"
    return "PREPARATION_ALLOWED"


def _m5a_gate_status(report: dict[str, Any] | None) -> str:
    if report is None:
        return "MISSING"
    value = str(report.get("status") or report.get("result") or "").upper()
    if value in {"PASS", "PARTIAL_PASS", "BLOCKED", "NOT_RUN"}:
        return value
    return "UNKNOWN"


def _parent_validation(parent_gate: str, current_dir: Path, timestamp: str) -> tuple[dict[str, Any], str | None]:
    try:
        return validate_parent_gate(
            parent_gate,
            report_dir=current_dir,
            hierarchy_path=HIERARCHY_JSON,
            timestamp=timestamp,
            max_report_age_hours=None,
        ), None
    except Exception as exc:  # pragma: no cover - defensive report integrity guard
        return {
            "report_name": "parent_gate_validation",
            "generated_by": "gate_validator",
            "parent_gate": parent_gate,
            "status": "BLOCKED",
            "result": "BLOCKED",
            "decision": {"go_no_go": "NO_GO", "manual_override_allowed": False},
            "blockers": [{
                "id": "parent_gate_validator_error",
                "child_gate_id": parent_gate,
                "severity": "blocking",
                "reason": str(exc),
            }],
            "gate_decision_trace": {
                "parent_gate": parent_gate,
                "rule": "Parent gate validation failed; parent remains BLOCKED.",
                "evaluated_children": [],
                "blocking_children": [parent_gate],
                "failing_children": [],
                "final_status": "BLOCKED",
            },
        }, str(exc)


def _parent_status(validation: dict[str, Any]) -> str:
    return str(validation.get("status") or validation.get("result") or "BLOCKED").upper()


def _parent_blockers(validation: dict[str, Any], *, parent_gate: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for blocker in validation.get("blockers", []):
        if not isinstance(blocker, dict):
            continue
        child_gate = str(blocker.get("child_gate_id") or blocker.get("id") or parent_gate)
        reason = str(blocker.get("reason") or blocker.get("detail") or f"{child_gate} blocks {parent_gate}.")
        blockers.append({
            "id": f"{parent_gate}_parent_child_{child_gate}",
            "type": "parent_gate",
            "severity": "blocking",
            "detail": reason,
            "source": "docs/gate_hierarchy.json",
            "child_gate_id": child_gate,
        })
    return blockers


def evaluate(current_dir: Path = CURRENT_DIR, *, timestamp: str | None = None) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(timezone.utc).isoformat()
    m3a, m3a_error = _load_json(current_dir / M3A_RC)
    m4, m4_error = _load_json(current_dir / M4_BACKEND_RC)
    doc_lint, doc_error = _load_json(current_dir / DOC_LINT)
    known, known_error = _load_json(current_dir / KNOWN_LIMITATIONS)
    m4e_ops, m4e_ops_error = _load_json(current_dir / M4E_OPERATIONS_RELEASE)
    m4e_ops_gate, m4e_ops_gate_error = _load_json(current_dir / M4E_OPERATIONS_RELEASE_GATE)
    m5_assessment, m5_assessment_error = _load_json(current_dir / M5_GATE_ASSESSMENT)
    m5a_start, m5a_start_error = _load_json(current_dir / M5A_START_GATE)
    m5a_data_quality, m5a_data_quality_error = _load_json(current_dir / M5A_DATA_QUALITY_GATE)
    m5a_dup_gate, m5a_dup_gate_error = _load_json(current_dir / M5A_DUPLICATE_DETECTOR_GATE)
    m5a_metadata_gate, m5a_metadata_gate_error = _load_json(current_dir / M5A_METADATA_DETECTOR_GATE)
    report_integrity, report_integrity_error = _load_json(current_dir / REPORT_INTEGRITY_V2)
    m5b_start, m5b_start_error = _load_json(current_dir / M5B_START_GATE)
    gate_hierarchy, gate_hierarchy_error = _load_json(HIERARCHY_JSON)
    m3a_parent_validation, m3a_parent_validation_error = _parent_validation("m3a", current_dir, generated_at)
    m4_parent_validation, m4_parent_validation_error = _parent_validation("m4", current_dir, generated_at)
    m5a_parent_validation, m5a_parent_validation_error = _parent_validation("m5a", current_dir, generated_at)

    m3a_stale_blocker = _check_m3a_stale(m3a, current_dir)
    m3a_parent_pass = _parent_status(m3a_parent_validation) == "PASS"
    m4_parent_pass = _parent_status(m4_parent_validation) == "PASS"
    # Masterplan rule-set: parent gates follow mandatory child gates.
    m3a_pass = _is_pass_report(m3a) and m3a_parent_pass and m3a_stale_blocker is None
    m4_pass = _is_pass_report(m4) and m4_parent_pass
    m4e_primary_pass = _is_pass_report(m4e_ops)
    m4e_alt_pass = _is_pass_report(m4e_ops_gate) if m4e_ops_gate else None
    m4e_operations_pass = m4e_primary_pass or bool(m4e_alt_pass)
    doc_errors = _doc_lint_errors(doc_lint)
    known_summary = _known_limitations_summary(known)
    m4e_operations_ready = m4e_operations_pass and known_summary["operations_explicitly_released"]

    integrity_blockers = _invalid_json_blockers({
        M3A_RC: m3a_error,
        M4_BACKEND_RC: m4_error,
        DOC_LINT: doc_error,
        KNOWN_LIMITATIONS: known_error,
        M4E_OPERATIONS_RELEASE: m4e_ops_error,
        M4E_OPERATIONS_RELEASE_GATE: m4e_ops_gate_error,
        M5_GATE_ASSESSMENT: m5_assessment_error,
        M5A_START_GATE: m5a_start_error,
        M5A_DATA_QUALITY_GATE: m5a_data_quality_error,
        M5A_DUPLICATE_DETECTOR_GATE: m5a_dup_gate_error,
        M5A_METADATA_DETECTOR_GATE: m5a_metadata_gate_error,
        REPORT_INTEGRITY_V2: report_integrity_error,
        M5B_START_GATE: m5b_start_error,
        "docs/gate_hierarchy.json": gate_hierarchy_error,
    })

    m5a_start_go = _is_go_gate(m5a_start)
    m5a_gate_status = _m5a_gate_status(m5a_data_quality)
    m5a_parent_status = _parent_status(m5a_parent_validation)
    m5a_parent_pass = m5a_parent_status == "PASS"
    raw_m5a_data_quality_pass = _is_pass_report(m5a_data_quality) and m5a_gate_status == "PASS"
    m5a_data_quality_pass = raw_m5a_data_quality_pass and m5a_parent_pass
    m5a_duplicate_slice_pass = _is_pass_report(m5a_dup_gate)
    m5a_metadata_slice_pass = _is_pass_report(m5a_metadata_gate)
    required_slices_pass = m5a_duplicate_slice_pass and m5a_metadata_slice_pass
    data_quality_report_not_run = m5a_gate_status in {"NOT_RUN", "MISSING"}
    slice_start_allowed = m5a_start_go
    m5a_overall_pass = m5a_parent_pass and m5a_data_quality_pass and not data_quality_report_not_run
    m5a_partial_pass = (
        m5a_parent_pass
        and ((required_slices_pass and not m5a_overall_pass and not data_quality_report_not_run) or m5a_gate_status == "PARTIAL_PASS")
    )
    slice_gate_passed = m5a_overall_pass
    preparation_done = _assessment_value(m5_assessment, "m5_preparation_done") is True
    slice_implementing = m5a_start_go and not m5a_overall_pass

    contradictions: list[dict[str, Any]] = []
    if m4e_ops and m4e_ops_gate and m4e_primary_pass != bool(m4e_alt_pass):
        contradictions.append({
            "id": "m4e_operations_reports_contradict",
            "type": "report_contradiction",
            "severity": "blocking",
            "detail": "m4e_operations_release_report.json and m4e_operations_release_gate.json disagree.",
            "source": f"reports/current/{M4E_OPERATIONS_RELEASE}",
        })
    if _assessment_value(m5_assessment, "m5_preparation_allowed") is True and not m4e_operations_ready:
        contradictions.append({
            "id": "m5_assessment_preparation_contradiction",
            "type": "report_contradiction",
            "severity": "blocking",
            "detail": "m5_gate_assessment allows preparation although M4e Operations is not PASS/GO or still has active Operations limitations.",
            "source": f"reports/current/{M5_GATE_ASSESSMENT}",
        })
    if _assessment_value(m5_assessment, "m5_implementation_allowed") is True and not slice_start_allowed:
        contradictions.append({
            "id": "m5_assessment_implementation_contradiction",
            "type": "report_contradiction",
            "severity": "blocking",
            "detail": "m5_gate_assessment allows implementation without a valid slice start gate.",
            "source": f"reports/current/{M5_GATE_ASSESSMENT}",
        })
    if _assessment_value(m5_assessment, "m5_slice_start_allowed") is True and not slice_start_allowed:
        contradictions.append({
            "id": "m5_assessment_slice_start_contradiction",
            "type": "report_contradiction",
            "severity": "blocking",
            "detail": "m5_gate_assessment allows slice start but slice prerequisites are not met.",
            "source": f"reports/current/{M5_GATE_ASSESSMENT}",
        })
    if raw_m5a_data_quality_pass and not m5a_start_go:
        contradictions.append({
            "id": "m5a_data_quality_without_start_gate",
            "type": "report_contradiction",
            "severity": "blocking",
            "detail": "m5a_data_quality_gate.json is PASS without m5a_start_gate = GO.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        })
    if raw_m5a_data_quality_pass and not required_slices_pass:
        contradictions.append({
            "id": "m5a_data_quality_without_required_slices",
            "type": "report_contradiction",
            "severity": "blocking",
            "detail": "m5a_data_quality_gate.json is PASS although required M5a slice gates are not all PASS.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        })

    m3a_blockers = []
    if m3a_error or not _is_pass_report(m3a):
        m3a_blockers.append({
            "id": "m3a_rc_not_pass",
            "type": "release_candidate",
            "severity": "blocking",
            "detail": f"{M3A_RC} must be PASS/GO and not stale.",
            "source": f"reports/current/{M3A_RC}",
        })
    if m3a_stale_blocker:
        m3a_blockers.append(m3a_stale_blocker)
    if not m3a_parent_pass:
        m3a_blockers.extend(_parent_blockers(m3a_parent_validation, parent_gate="m3a"))

    m4_blockers = []
    if m4_error or not _is_pass_report(m4):
        m4_blockers.append({
        "id": "m4_backend_rc_not_pass",
        "type": "release_candidate",
        "severity": "blocking",
        "detail": f"{M4_BACKEND_RC} must be PASS/GO.",
        "source": f"reports/current/{M4_BACKEND_RC}",
        })
    if not m4_parent_pass:
        m4_blockers.extend(_parent_blockers(m4_parent_validation, parent_gate="m4"))
    doc_blockers = [] if doc_errors == 0 and not doc_error else [{
        "id": "documentation_truth_lint_errors",
        "type": "documentation",
        "severity": "blocking",
        "detail": f"{DOC_LINT} has {doc_errors} error(s) or is unavailable.",
        "source": f"reports/current/{DOC_LINT}",
    }]
    m5_blockers = []
    if not m4e_operations_ready:
        m5_blockers.append({
            "id": "m5_preparation_requires_m4e_operations",
            "type": "dependency",
            "severity": "blocking",
            "detail": "M5 preparation requires M4e Operations PASS/GO and no active Operations limitation.",
            "source": f"reports/current/{M4E_OPERATIONS_RELEASE}",
        })
    m5_blockers.extend(integrity_blockers)
    m5_blockers.extend(contradictions)

    m5a_overall_blockers: list[dict[str, Any]] = []
    if not m5a_start_go:
        m5a_overall_blockers.append({
            "id": "m5a_start_gate_not_go",
            "type": "dependency",
            "severity": "blocking",
            "detail": "M5a overall gate requires m5a_start_gate = GO.",
            "source": f"reports/current/{M5A_START_GATE}",
        })
    if not m5a_duplicate_slice_pass:
        m5a_overall_blockers.append({
            "id": "m5a_duplicate_slice_not_pass",
            "type": "slice_gate",
            "severity": "blocking",
            "detail": "M5a Duplicate Detector slice gate is not PASS.",
            "source": f"reports/current/{M5A_DUPLICATE_DETECTOR_GATE}",
        })
    if not m5a_metadata_slice_pass:
        m5a_overall_blockers.append({
            "id": "m5a_metadata_slice_not_pass",
            "type": "slice_gate",
            "severity": "blocking",
            "detail": "M5a Metadata Detector slice gate is not PASS.",
            "source": f"reports/current/{M5A_METADATA_DETECTOR_GATE}",
        })
    if data_quality_report_not_run:
        m5a_overall_blockers.append({
            "id": "m5a_data_quality_report_not_run",
            "type": "gate",
            "severity": "blocking",
            "detail": "M5a Data Quality report status is NOT_RUN.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        })
    if not m5a_data_quality_pass:
        m5a_overall_blockers.append({
            "id": "m5a_data_quality_gate_not_pass",
            "type": "gate",
            "severity": "blocking",
            "detail": "M5a Data Quality gate is not PASS.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        })
    if not m5a_parent_pass:
        m5a_overall_blockers.extend(_parent_blockers(m5a_parent_validation, parent_gate="m5a"))

    model_blocked = bool(integrity_blockers or contradictions)
    if model_blocked:
        m5a_effective_status = "BLOCKED"
    elif m5a_parent_status in {"BLOCKED", "MISSING", "INVALID", "STALE"}:
        m5a_effective_status = "BLOCKED"
    elif m5a_parent_status == "FAIL":
        m5a_effective_status = "FAIL"
    elif m5a_overall_pass:
        m5a_effective_status = "PASS"
    elif m5a_partial_pass:
        m5a_effective_status = "PARTIAL_PASS"
    else:
        m5a_effective_status = "BLOCKED"
    m5_status = _derive_m5_status(
        blocked=model_blocked,
        m4e_operations_pass=m4e_operations_ready,
        preparation_done=preparation_done,
        slice_start_allowed=slice_start_allowed,
        slice_implementing=slice_implementing,
        slice_gate_passed=slice_gate_passed,
    )
    m5_preparation_allowed = m5_status in {
        "PREPARATION_ALLOWED",
        "PREPARATION_DONE",
        "SLICE_START_ALLOWED",
        "SLICE_IMPLEMENTING",
        "SLICE_GATE_PASSED",
        "M5_IMPLEMENTATION_ALLOWED",
    }
    m5_slice_work_allowed = m5_status in {
        "SLICE_START_ALLOWED",
        "SLICE_IMPLEMENTING",
        "SLICE_GATE_PASSED",
        "M5_IMPLEMENTATION_ALLOWED",
    }

    m5b_status = str((m5b_start or {}).get("status") or (m5b_start or {}).get("result") or "MISSING").upper()
    m5b_prepared = m5a_effective_status == "PASS" and m5b_status == "PREPARED"
    m5b_implementation_gate, m5b_implementation_gate_error = _load_json(current_dir / M5B_IMPLEMENTATION_GATE)
    m5b_implementation_pass = _is_pass_report(m5b_implementation_gate)
    m5b_implementation_allowed = m5b_prepared and m5b_implementation_pass
    m5_implementation_allowed = m5_slice_work_allowed and m5b_implementation_allowed

    # M5 implementation is never globally PASS before M5a overall PASS and a
    # separate M5b implementation gate PASS/GO.
    m5_implementation_global_pass = m5_implementation_allowed and m5a_effective_status == "PASS"
    m5b_blockers: list[dict[str, Any]] = []
    if m5a_effective_status != "PASS":
        m5b_blockers.append({
            "id": M5A_PARENT_GATE_NOT_PASSED,
            "type": "dependency",
            "severity": "blocking",
            "detail": "M5b bleibt BLOCKED bis m5a_data_quality_gate PASS/GO meldet.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        })
    for blocker in (m5b_start or {}).get("blockers", []):
        if isinstance(blocker, dict):
            m5b_blockers.append({
                "id": str(blocker.get("id") or "m5b_start_gate_blocker"),
                "type": "gate",
                "severity": str(blocker.get("severity") or "blocking"),
                "detail": str(blocker.get("reason") or blocker.get("detail") or "m5b_start_gate blocks M5b preparation."),
                "source": str(blocker.get("source") or f"reports/current/{M5B_START_GATE}"),
            })
    m5b_implementation_blockers: list[dict[str, Any]] = []
    if not m5b_implementation_allowed:
        m5b_implementation_blockers.append({
            "id": "M5B_IMPLEMENTATION_GATE_REQUIRED",
            "type": "gate",
            "severity": "blocking",
            "detail": "M5b Implementierung erfordert ein separates m5b_implementation_gate PASS/GO.",
            "source": f"reports/current/{M5B_IMPLEMENTATION_GATE}",
        })
    if m5b_implementation_gate_error and m5b_implementation_gate_error != "missing":
        m5b_implementation_blockers.append({
            "id": "invalid_m5b_implementation_gate",
            "type": "input_integrity",
            "severity": "blocking",
            "detail": f"{M5B_IMPLEMENTATION_GATE} is not valid JSON: {m5b_implementation_gate_error}",
            "source": f"reports/current/{M5B_IMPLEMENTATION_GATE}",
        })

    release_blockers = [*m3a_blockers, *m4_blockers, *doc_blockers, *integrity_blockers, *contradictions]
    if m5a_effective_status != "PASS":
        release_blockers.append({
            "id": "m5a_overall_not_pass",
            "type": "gate",
            "severity": "blocking",
            "detail": "Global release remains blocked until m5a_data_quality_gate is PASS.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        })
    if not m5b_implementation_allowed:
        release_blockers.extend(m5b_implementation_blockers)
    release_allowed = (
        m3a_pass
        and m4_pass
        and m4e_operations_pass
        and doc_errors == 0
        and not integrity_blockers
        and not contradictions
        and m5a_effective_status == "PASS"
        and m5b_implementation_allowed
    )

    overall_status = "pass" if release_allowed else ("partial_pass" if (m3a_pass and m4_pass and m4e_operations_pass and m5a_effective_status == "PARTIAL_PASS") else "blocked")
    if m5_implementation_global_pass:
        m5_implementation_blockers = []
    elif m5a_effective_status != "PASS":
        m5_implementation_blockers = [{
            "id": "m5_implementation_global_not_pass",
            "type": "gate",
            "severity": "blocking",
            "detail": "M5 Implementierung ist nicht global PASS, solange m5a_data_quality_gate nicht PASS ist.",
            "source": f"reports/current/{M5A_DATA_QUALITY_GATE}",
        }]
    else:
        m5_implementation_blockers = m5b_implementation_blockers
    phases = {
        "m3a": _phase("m3a", "M3a Frontend Foundation", passed=m3a_pass, decision="GO" if m3a_pass else "NO_GO", gate_id="m3a_release_candidate_gate", source=f"reports/current/{M3A_RC}", blockers=m3a_blockers),
        "m4": _phase("m4", "M4 Backend", passed=m4_pass, decision="GO" if m4_pass else "NO_GO", gate_id="m4_backend_release_candidate_gate", source=f"reports/current/{M4_BACKEND_RC}", blockers=m4_blockers),
        "m5_preparation": _phase("m5_preparation", "M5 Vorbereitung", passed=m5_preparation_allowed, decision="GO" if m5_preparation_allowed else "NO_GO", gate_id="m5_preparation_gate", source=f"reports/current/{M4E_OPERATIONS_RELEASE}", blockers=[] if m5_preparation_allowed else m5_blockers),
        "m5_implementation": _phase(
            "m5_implementation",
            "M5 Implementierung",
            passed=m5_implementation_global_pass,
            decision="GO" if m5_implementation_global_pass else "NO_GO",
            gate_id="m5_implementation_gate",
            source=f"reports/current/{M5A_START_GATE}",
            blockers=m5_implementation_blockers,
            phase_status="blocked" if not m5_implementation_global_pass else None,
            gate_status="BLOCKED" if not m5_implementation_global_pass else None,
        ),
        "m5a_data_quality": _phase(
            "m5a_data_quality",
            "M5a Data Quality",
            passed=m5a_effective_status == "PASS",
            decision="GO" if m5a_effective_status == "PASS" else "NO_GO",
            gate_id="m5a_data_quality_gate",
            source=f"reports/current/{M5A_DATA_QUALITY_GATE}",
            blockers=[] if m5a_effective_status == "PASS" else [*m5a_overall_blockers, *m5_blockers],
            phase_status="gate_partial_pass" if m5a_effective_status == "PARTIAL_PASS" else None,
            gate_status=m5a_effective_status if m5a_effective_status in {"PASS", "PARTIAL_PASS", "BLOCKED"} else None,
        ),
        "m5b_drift": _phase(
            "m5b_drift",
            "M5b Drift",
            passed=m5b_prepared,
            decision="PREPARED" if m5b_prepared else "NO_GO",
            gate_id="m5b_start_gate",
            source=f"reports/current/{M5B_START_GATE}",
            blockers=[] if m5b_prepared else m5b_blockers,
            phase_status="prepared" if m5b_prepared else "blocked",
            gate_status="PREPARED" if m5b_prepared else m5b_status,
        ),
    }
    progress_model = calculate_masterplan_progress(
        m3a_parent_status=_parent_status(m3a_parent_validation),
        m4_parent_status=_parent_status(m4_parent_validation),
        m5a_parent_status=m5a_parent_status,
        m3a_pass=m3a_pass,
        m4_pass=m4_pass,
        m5_preparation_allowed=m5_preparation_allowed,
        m5a_slice_passes={
            "duplicate_detector": m5a_duplicate_slice_pass,
            "metadata_detector": m5a_metadata_slice_pass,
        },
        m5a_effective_status=m5a_effective_status,
        m5b_prepared=m5b_prepared,
        m5b_implementation_allowed=m5b_implementation_allowed,
        release_allowed=release_allowed,
        documentation_pass=doc_errors == 0,
    )
    progress = progress_model["progress_percent"]
    parent_gate_statuses = {
        "m3a": _parent_status(m3a_parent_validation),
        "m4": _parent_status(m4_parent_validation),
        "m5a": _parent_status(m5a_parent_validation),
    }
    parent_hierarchy_result = (
        "PASS"
        if all(status == "PASS" for status in parent_gate_statuses.values())
        else "BLOCKED"
        if any(status in {"BLOCKED", "MISSING", "INVALID", "STALE"} for status in parent_gate_statuses.values())
        else "FAIL"
    )

    return {
        "report_schema_version": SCHEMA_VERSION,
        "report_name": "masterplan_status",
        "generated_by": "masterplan_status_engine_v3",
        "generated_at": generated_at,
        "timestamp": generated_at,
        "status": overall_status,
        "result": overall_status,
        "authority": {
            "source_of_truth": "reports/current release-candidate and gate artifacts",
            "manual_status_override_allowed": False,
            "engine_version": 3,
            "rule": "M5 uses explicit status values; M4e Operations PASS permits preparation only, while every M5 slice needs its own start gate.",
        },
        "inputs": {"current_reports": {
            M3A_RC: _summary(m3a, m3a_error),
            M4_BACKEND_RC: _summary(m4, m4_error),
            M4E_OPERATIONS_RELEASE: _summary(m4e_ops, m4e_ops_error),
            M4E_OPERATIONS_RELEASE_GATE: _summary(m4e_ops_gate, m4e_ops_gate_error),
            M5_GATE_ASSESSMENT: _summary(m5_assessment, m5_assessment_error),
            M5A_START_GATE: _summary(m5a_start, m5a_start_error),
            M5A_DATA_QUALITY_GATE: _summary(m5a_data_quality, m5a_data_quality_error),
            M5A_DUPLICATE_DETECTOR_GATE: _summary(m5a_dup_gate, m5a_dup_gate_error),
            M5A_METADATA_DETECTOR_GATE: _summary(m5a_metadata_gate, m5a_metadata_gate_error),
            REPORT_INTEGRITY_V2: _summary(report_integrity, report_integrity_error),
            M5B_START_GATE: _summary(m5b_start, m5b_start_error),
            M5B_IMPLEMENTATION_GATE: _summary(m5b_implementation_gate, m5b_implementation_gate_error),
            DOC_LINT: _summary(doc_lint, doc_error),
            KNOWN_LIMITATIONS: {"available": known is not None, "error": known_error, **known_summary},
            "docs/gate_hierarchy.json": {
                "available": gate_hierarchy is not None,
                "error": gate_hierarchy_error,
                "timestamp": (gate_hierarchy or {}).get("timestamp") if gate_hierarchy else None,
                "generated_by": (gate_hierarchy or {}).get("generated_by") if gate_hierarchy else None,
            },
        }},
        "overall": {
            "status": overall_status,
            "progress_percent": progress,
            "release_allowed": release_allowed,
            "blocker_count": len(release_blockers),
        },
        "progress_model": progress_model,
        "m5a_gate_logic": {
            "start_gate": {
                "report": f"reports/current/{M5A_START_GATE}",
                "go": m5a_start_go,
            },
            "slice_gates": {
                "duplicate_detector": {
                    "report": f"reports/current/{M5A_DUPLICATE_DETECTOR_GATE}",
                    "pass": m5a_duplicate_slice_pass,
                },
                "metadata_detector": {
                    "report": f"reports/current/{M5A_METADATA_DETECTOR_GATE}",
                    "pass": m5a_metadata_slice_pass,
                },
            },
            "required_slices_all_pass": required_slices_pass,
            "data_quality_gate": {
                "report": f"reports/current/{M5A_DATA_QUALITY_GATE}",
                "pass": m5a_data_quality_pass,
                "status": m5a_gate_status,
                "effective_status": m5a_effective_status,
                "not_run": data_quality_report_not_run,
            },
            "overall_m5a_pass": m5a_effective_status == "PASS",
            "rule": "M5a ist PARTIAL_PASS oder BLOCKED, solange m5a_data_quality_gate nicht PASS ist; globale M5-Freigabe erst bei M5a PASS.",
        },
        "m5": {
            "status": m5_status,
            "valid_status_values": list(M5_STATUSES),
            "preparation_allowed": m5_preparation_allowed,
            "implementation_allowed": m5_implementation_allowed,
            "implementation_decision": "GO" if m5_implementation_global_pass else "NO_GO",
            "slice_start_allowed": slice_start_allowed,
            "slice_gate_passed": slice_gate_passed,
            "m5a_status": m5a_effective_status,
            "m5b_status": "PREPARED" if m5b_prepared else m5b_status,
            "m5b_implementation_allowed": m5b_implementation_allowed,
            "m5b_implementation_gate_required": True,
            "rule": "M5 Gesamt wird nicht automatisch PASS; M5b PREPARED erfordert M5a Parent-Gate PASS. M5b Implementierung erfordert ein separates M5b Implementation Gate.",
        },
        "documentation_lint": {
            "status": (doc_lint or {}).get("status"),
            "errors": doc_errors,
        },
        "known_limitations": known_summary,
        "input_integrity_issues": integrity_blockers,
        "report_contradictions": contradictions,
        "blockers": release_blockers,
        "parent_gate_validations": {
            "m3a": m3a_parent_validation,
            "m4": m4_parent_validation,
            "m5a": m5a_parent_validation,
            "errors": {
                "m3a": m3a_parent_validation_error,
                "m4": m4_parent_validation_error,
                "m5a": m5a_parent_validation_error,
            },
        },
        "phases": phases,
        "gate_hierarchy": {
            "result": parent_hierarchy_result,
            "source": "docs/gate_hierarchy.json",
            "parent_statuses": parent_gate_statuses,
            "gates": {phase["gate_id"]: {"status": phase["gate_status"], "blockers": [b["detail"] for b in phase["blockers"]]} for phase in phases.values()},
            "m5b_implementation_gate": {
                "status": "PASS" if m5b_implementation_allowed else "BLOCKED",
                "blockers": [blocker["detail"] for blocker in m5b_implementation_blockers],
            },
        },
    }


def render_status_section(payload: dict[str, Any]) -> str:
    overall = payload.get("overall", {})
    lines = [
        "<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->",
        "## Maschinenstatus Masterplan",
        "",
        f"Stand: `{payload.get('generated_at', '-')}`",
        f"Engine: `{payload.get('generated_by', '-')}`",
        "",
        f"Gesamtstatus: `{str(overall.get('status', '-')).upper()}`",
        f"Fortschritt: `{overall.get('progress_percent', 0)}%`",
        f"Release-Freigabe: `{'ja' if overall.get('release_allowed') else 'nein'}`",
        f"Blocker: `{overall.get('blocker_count', 0)}`",
        "",
        "> Dieser Abschnitt ist maschinell generiert. Manuelle Statusaussagen duerfen diesen Status nicht ueberschreiben.",
        "",
        "### Phasen",
        "",
        "| Phase | Status | Entscheidung | Gate | Gate-Status |",
        "|---|---|---|---|---|",
    ]
    for phase in payload.get("phases", {}).values():
        lines.append(
            f"| {phase.get('label', '-')} | `{phase.get('status', '-')}` | `{phase.get('decision', '-')}` | `{phase.get('gate_id', '-')}` | `{phase.get('gate_status', '-')}` |"
        )

    dl = payload.get("inputs", {}).get("current_reports", {}).get(DOC_LINT, {})
    m5 = payload.get("m5", {})
    gate_hierarchy = payload.get("gate_hierarchy", {})
    lines.extend([
        "",
        "### M5 Statusmodell",
        "",
        f"- Status: `{m5.get('status', '-')}`",
        f"- M5a: `{m5.get('m5a_status', '-')}`",
        f"- M5b: `{m5.get('m5b_status', '-')}`",
        f"- Implementierung global: `{m5.get('implementation_decision', 'NO_GO')}`",
        f"- Parent-Gate-Hierarchie: `{gate_hierarchy.get('result', '-')}`",
        "",
        "### Dokumentations-Lint",
        "",
        f"- Ergebnis: `{dl.get('status') or dl.get('result') or '—'}`",
        f"- Errors: `{_int_value(dl.get('errors'))}`  Warnings: `{_int_value(dl.get('warnings'))}`",
        "",
        "### Blocker",
        "",
    ])

    blockers: list[str] = []
    for phase in payload.get("phases", {}).values():
        for blocker in phase.get("blockers", []):
            if not isinstance(blocker, dict):
                continue
            detail = str(blocker.get("detail") or blocker.get("reason") or "")
            source = str(blocker.get("source") or "")
            if detail and source:
                blockers.append(f"{detail} (laut {source})")
            elif detail:
                blockers.append(detail)
    if blockers:
        for blocker in blockers[:20]:
            lines.append(f"- {blocker}")
    else:
        lines.append("- Keine aktiven Blocker.")

    lines.append("")
    lines.append("<!-- END GENERATED MASTERPLAN STATUS v3 -->")
    return "\n".join(lines) + "\n"


def _replace_between_markers(text: str, replacement: str, begin_marker: str, end_marker: str) -> str:
    start = text.find(begin_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        return replacement.strip() + "\n\n" + text
    end += len(end_marker)
    return text[:start] + replacement.strip() + text[end:]


def write_outputs(payload: dict[str, Any], json_path: Path, section_path: Path, masterplan_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    section_path.parent.mkdir(parents=True, exist_ok=True)
    section = render_status_section(payload)
    section_path.write_text(section, encoding="utf-8")

    if masterplan_path.exists():
        masterplan_text = masterplan_path.read_text(encoding="utf-8")
        updated = _replace_between_markers(
            masterplan_text,
            section,
            "<!-- BEGIN GENERATED MASTERPLAN STATUS v3 -->",
            "<!-- END GENERATED MASTERPLAN STATUS v3 -->",
        )
        masterplan_path.write_text(updated, encoding="utf-8")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(CURRENT_DIR / "masterplan_status.json"))
    parser.add_argument("--output-section", default=str(DEFAULT_OUTPUT_SECTION))
    parser.add_argument("--masterplan", default=str(DEFAULT_MASTERPLAN))
    args = parser.parse_args()
    payload = evaluate()
    out = Path(args.output)
    out_section = Path(args.output_section)
    masterplan_path = Path(args.masterplan)
    write_outputs(payload, out, out_section, masterplan_path)
    print(f"masterplan_status generated: {payload['overall']['status']}")
    print(f"progress: {payload['overall']['progress_percent']}%")
    print(f"release_allowed: {payload['overall']['release_allowed']}")
    print(f"Wrote: {out}")
    print(f"Wrote: {out_section}")
    print(f"Updated: {masterplan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
