from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


CHILD_BLOCKING_STATUSES = {"BLOCKED", "INVALID", "STALE"}
CHILD_FAIL_STATUSES = {"FAIL", "FAILED"}
PARENT_BLOCKING_STATUSES = {"BLOCKED", "MISSING", "INVALID", "STALE"}


@dataclass(frozen=True)
class ChildGateReference:
    child_gate_id: str
    report: str
    accepted_statuses: tuple[str, ...] = ("PASS",)
    required_decision: str | None = None
    counter_validation: str = "not_required"
    optional_true_fields: tuple[str, ...] = ()
    min_quality_score: float | None = None

    @classmethod
    def from_spec(cls, child_gate_id: str, spec: dict[str, Any]) -> "ChildGateReference":
        accepted_statuses = tuple(
            str(value) for value in spec.get("accepted_statuses", ["PASS"])
        )
        optional_true_fields = tuple(
            str(value) for value in spec.get("optional_true_fields", [])
        )
        min_quality_score = spec.get("min_quality_score")
        return cls(
            child_gate_id=child_gate_id,
            report=str(spec.get("report") or ""),
            accepted_statuses=accepted_statuses,
            required_decision=spec.get("required_decision"),
            counter_validation=str(spec.get("counter_validation") or "not_required"),
            optional_true_fields=optional_true_fields,
            min_quality_score=(
                float(min_quality_score)
                if isinstance(min_quality_score, (int, float))
                else None
            ),
        )


@dataclass(frozen=True)
class GateDefinition:
    parent_gate_id: str
    mandatory_children: tuple[ChildGateReference, ...]
    hierarchy_source: str | None = None


@dataclass(frozen=True)
class GateDecisionTrace:
    parent_gate: str
    rule: str
    evaluated_children: list[dict[str, Any]]
    blocking_children: list[str]
    failing_children: list[str]
    final_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_gate": self.parent_gate,
            "rule": self.rule,
            "evaluated_children": self.evaluated_children,
            "blocking_children": self.blocking_children,
            "failing_children": self.failing_children,
            "final_status": self.final_status,
        }


@dataclass(frozen=True)
class GateResult:
    parent_gate: str
    status: str
    child_results: dict[str, dict[str, Any]]
    blockers: list[dict[str, Any]]
    decision_trace: GateDecisionTrace
    collected: int
    passed: int
    failed: int
    errors: int = 0
    skipped: int = 0
    manual_override_allowed: bool = False

    @property
    def exit_code(self) -> int:
        return 0 if self.status == "PASS" else 1


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def nested(payload: dict[str, Any], key_path: str) -> Any:
    current: Any = payload
    for key in key_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def status_values(report: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("status", "result"):
        value = report.get(key)
        if isinstance(value, str) and value:
            values.add(_normalize_status(value))
    for key_path in ("decision.go_no_go", "decision.result"):
        value = nested(report, key_path)
        if isinstance(value, str) and value:
            values.add(_normalize_status(value))
    return values


def evaluate_gate(
    definition: GateDefinition,
    child_inputs: dict[str, dict[str, Any]],
    *,
    now: datetime,
    max_report_age_hours: int | None,
) -> GateResult:
    child_results: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, Any]] = []

    for reference in definition.mandatory_children:
        child_id = reference.child_gate_id
        child_input = child_inputs.get(child_id, {})
        report = child_input.get("report")
        error = child_input.get("error")

        if error is not None or report is None:
            status, child_blockers = _input_error_blockers(child_id, error)
            child_result: dict[str, Any] = {
                "child_gate_id": child_id,
                "report": reference.report,
                "validation_status": status,
                "blockers": child_blockers,
            }
        else:
            status, child_blockers = validate_child_report(
                reference,
                report,
                now=now,
                max_report_age_hours=max_report_age_hours,
            )
            child_result = {
                "child_gate_id": child_id,
                "report": reference.report,
                "validation_status": status,
                "report_status": report.get("status"),
                "report_result": report.get("result"),
                "decision": nested(report, "decision.go_no_go"),
                "timestamp": report.get("timestamp") or report.get("generated_at"),
                "generated_by": report.get("generated_by"),
                "collected": report.get("collected"),
                "report_type": report.get("report_type"),
                "blockers": child_blockers,
            }

        child_results[child_id] = child_result
        if child_result["validation_status"] != "PASS":
            blockers.append({
                "id": child_id,
                "child_gate_id": child_id,
                "severity": "blocking",
                "reason": "; ".join(child_result["blockers"]),
            })

    status = parent_status(child_results)
    return GateResult(
        parent_gate=definition.parent_gate_id,
        status=status,
        child_results=child_results,
        blockers=blockers,
        decision_trace=decision_trace(definition.parent_gate_id, child_results, status),
        collected=len(definition.mandatory_children),
        passed=sum(1 for item in child_results.values() if item["validation_status"] == "PASS"),
        failed=len(blockers),
    )


def validate_child_report(
    reference: ChildGateReference,
    report: dict[str, Any],
    *,
    now: datetime,
    max_report_age_hours: int | None,
) -> tuple[str, list[str]]:
    child_id = reference.child_gate_id
    report_name = Path(reference.report).name
    accepted_statuses = {_normalize_status(value) for value in reference.accepted_statuses}
    statuses = status_values(report)
    blockers: list[str] = []

    blocking_statuses = statuses & CHILD_BLOCKING_STATUSES
    if blocking_statuses:
        return "BLOCKED", [f"{child_id}: child status is blocking ({sorted(blocking_statuses)})"]

    failing_statuses = statuses & CHILD_FAIL_STATUSES
    if failing_statuses:
        return "FAIL", [f"{child_id}: child status is FAIL ({sorted(failing_statuses)})"]

    if statuses.isdisjoint(accepted_statuses):
        blockers.append(
            f"{child_id}: status/result must be one of {sorted(accepted_statuses)}, got {sorted(statuses)}"
        )

    invalid_blockers: list[str] = []
    if not report.get("generated_by"):
        invalid_blockers.append(f"{child_id}: generated_by must be set")

    timestamp = parse_timestamp(report.get("timestamp") or report.get("generated_at"))
    if timestamp is None:
        return "STALE", [f"{child_id}: timestamp must be machine-readable"]

    collected = _as_int(report.get("collected"))
    if not _is_supporting_report(report) and (collected is None or collected <= 0):
        invalid_blockers.append(
            f"{child_id}: passing child report requires collected > 0 or report_type=supporting"
        )

    if invalid_blockers:
        return "INVALID", invalid_blockers

    if reference.required_decision is not None:
        decision = nested(report, "decision.go_no_go")
        if _normalize_status(decision) != _normalize_status(reference.required_decision):
            blockers.append(f"{child_id}: decision.go_no_go must be {reference.required_decision}")

    counter_required = reference.counter_validation == "required"
    blockers.extend(_counter_blockers(report_name, report, required=counter_required))

    summary_errors = nested(report, "summary.errors")
    if isinstance(summary_errors, int) and summary_errors != 0:
        blockers.append(f"{child_id}: summary.errors must be 0")

    if report.get("failed_tests") not in ([], None):
        blockers.append(f"{child_id}: failed_tests must be empty")
    if report.get("blockers") not in ([], None):
        blockers.append(f"{child_id}: blockers must be empty")

    for field in reference.optional_true_fields:
        if field in report and report.get(field) is not True:
            blockers.append(f"{child_id}: {field} must be true when present")

    if reference.min_quality_score is not None:
        score = report.get("quality_score")
        if not isinstance(score, (int, float)) or score < reference.min_quality_score:
            blockers.append(f"{child_id}: quality_score must be >= {reference.min_quality_score:g}")

    if max_report_age_hours is not None and now - timestamp > timedelta(hours=max_report_age_hours):
        return "STALE", [f"{child_id}: report is older than {max_report_age_hours} hours"]

    return ("PASS" if not blockers else "FAIL"), blockers


def parent_status(child_results: dict[str, dict[str, Any]]) -> str:
    statuses = {str(item["validation_status"]) for item in child_results.values()}
    if statuses & PARENT_BLOCKING_STATUSES:
        return "BLOCKED"
    if "FAIL" in statuses:
        return "FAIL"
    return "PASS"


def decision_trace(
    parent_gate_id: str,
    child_results: dict[str, dict[str, Any]],
    status: str,
) -> GateDecisionTrace:
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
    return GateDecisionTrace(
        parent_gate=parent_gate_id,
        rule=(
            "Missing child, invalid child JSON, child BLOCKED/INVALID/STALE, or invalid PASS evidence "
            "=> parent BLOCKED; child FAIL => parent FAIL; all mandatory child gates must PASS; "
            "manual override is not allowed."
        ),
        evaluated_children=evaluated_children,
        blocking_children=[
            item["child_gate_id"]
            for item in evaluated_children
            if item["validation_status"] in PARENT_BLOCKING_STATUSES
        ],
        failing_children=[
            item["child_gate_id"]
            for item in evaluated_children
            if item["validation_status"] == "FAIL"
        ],
        final_status=status,
    )


def _input_error_blockers(child_id: str, error: Any) -> tuple[str, list[str]]:
    if error in (None, "missing"):
        return "MISSING", [f"{child_id}: missing"]

    error_text = str(error)
    if error_text.startswith("blocked:"):
        return "BLOCKED", [error_text.removeprefix("blocked:").strip()]
    if error_text.startswith("invalid:"):
        return "INVALID", [f"{child_id}: {error_text.removeprefix('invalid:').strip()}"]
    return "INVALID", [f"{child_id}: {error_text}"]


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


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _is_supporting_report(report: dict[str, Any]) -> bool:
    return str(report.get("report_type") or "").lower() == "supporting"


def _normalize_status(value: Any) -> str:
    return str(value).upper().replace("-", "_")
