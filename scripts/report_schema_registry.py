from __future__ import annotations

from dataclasses import dataclass
from typing import Any


COMMON_REQUIRED_FIELDS = (
    "report_schema_version",
    "report_name",
    "generated_by",
    "timestamp",
    "status",
)

COMMON_FIELD_TYPES: dict[str, tuple[type, ...]] = {
    "report_schema_version": (int,),
    "report_name": (str,),
    "generated_by": (str,),
    "timestamp": (str,),
    "status": (str,),
    "report_type": (str,),
    "schema": (str,),
    "schema_name": (str,),
    "report_kind": (str,),
    "environment": (str,),
    "source_command": (str,),
    "commit_hash": (str,),
    "notes": (str, list),
}


@dataclass(frozen=True)
class ReportSchema:
    name: str
    required_fields: tuple[str, ...]
    field_types: dict[str, tuple[type, ...]]
    allowed_fields: frozenset[str]
    status_values: frozenset[str]

    def type_names(self, field: str) -> tuple[str, ...]:
        return tuple(value.__name__ for value in self.field_types[field])


def _schema(
    name: str,
    *,
    extra_required: tuple[str, ...] = (),
    extra_types: dict[str, tuple[type, ...]] | None = None,
    extra_allowed: tuple[str, ...] = (),
    status_values: tuple[str, ...] = ("PASS", "FAIL", "BLOCKED"),
) -> ReportSchema:
    field_types = dict(COMMON_FIELD_TYPES)
    field_types.update(extra_types or {})
    required_fields = tuple(dict.fromkeys((*COMMON_REQUIRED_FIELDS, *extra_required)))
    allowed_fields = frozenset((*field_types.keys(), *required_fields, *extra_allowed))
    return ReportSchema(
        name=name,
        required_fields=required_fields,
        field_types=field_types,
        allowed_fields=allowed_fields,
        status_values=frozenset(status_values),
    )


REPORT_SCHEMAS: dict[str, ReportSchema] = {
    "gate_report": _schema(
        "gate_report",
        extra_required=("gate", "collected", "passed", "failed", "errors", "skipped", "exit_code", "blockers"),
        extra_types={
            "gate": (str,),
            "result": (str,),
            "decision": (dict,),
            "collected": (int,),
            "passed": (int,),
            "failed": (int,),
            "errors": (int,),
            "skipped": (int,),
            "exit_code": (int,),
            "blockers": (list,),
            "warnings": (list,),
            "quality_score": (int, float),
            "failed_tests": (list,),
            "gate_decision_trace": (dict,),
            "parent_gate_validation": (dict,),
            "no_manual_override": (bool,),
        },
        extra_allowed=(
            "alembic",
            "ambiguous_truth_tests",
            "api_base_url",
            "approved_stale_required_reports",
            "archive_actions",
            "archive_target",
            "assessment",
            "auth_me",
            "authority",
            "blocker_details",
            "blocking",
            "blocking_gates",
            "changes_since_last_run",
            "checks",
            "child_gates",
            "cleanup_log",
            "clear_decision",
            "components",
            "conditions",
            "credentials",
            "criteria",
            "current_scope_validation",
            "database_url",
            "database_url_set",
            "decisions",
            "deferred",
            "dependency_graph",
            "diagnostic_blockers",
            "documentation_lint",
            "errors_list",
            "evaluation_basis",
            "evaluated_reports",
            "evaluation_rules",
            "evidence_from",
            "evidence_timestamp",
            "finding_type",
            "findings",
            "finished_at",
            "fixes",
            "frontend",
            "frontend_base_url",
            "gate_rules",
            "gate_status",
            "gates",
            "generated_from",
            "health",
            "implementation",
            "implementation_blockers",
            "inputs",
            "invalid_reports",
            "issue",
            "known_limitation_assessment",
            "known_limitations",
            "limitations",
            "login",
            "m3a_impact",
            "m3a_release_candidate",
            "m4_backend_release_candidate",
            "m4_impact",
            "m4e_operations_release",
            "m5_implementation_dependency",
            "marker",
            "marker_policy",
            "missing_gates",
            "missing_or_invalid_artifacts",
            "moved",
            "name",
            "non_blocking",
            "note",
            "open",
            "operations_release_status",
            "parent_gate",
            "passed_checks",
            "phase_status",
            "policy",
            "preconditions",
            "preflight",
            "pytest_exit_code",
            "quality_score",
            "re_evaluated_at",
            "release_candidate",
            "remaining_errors",
            "repair_path",
            "repair_actions",
            "report_format_version",
            "required_set",
            "report_source_policy",
            "required_actions_before_m5a",
            "required_gates",
            "rule",
            "rules",
            "run_id",
            "run_status",
            "scope",
            "scope_definition",
            "score",
            "score_pct",
            "score_threshold",
            "seed",
            "source_file",
            "sprint",
            "stale_guard",
            "started_at",
            "status_generation_engine",
            "summary",
            "test_database_url_set",
            "test_module",
            "threshold_pct",
            "total_checks",
            "total_findings",
            "unmarked_truth_tests",
            "validation_summary",
            "version",
            "workspace_id",
            "mandatory_children",
            "child_results",
            "hierarchy_source",
            "report_dir",
            "generated_at",
        ),
        status_values=("PASS", "FAIL", "BLOCKED", "DRAFT", "PREPARED"),
    ),
    "supporting_report": _schema(
        "supporting_report",
        extra_types={
            "result": (str,),
            "summary": (dict,),
            "metrics": (dict,),
            "findings": (list,),
            "blockers": (list,),
            "warnings": (list,),
            "quality_score": (int, float),
            "collected": (int,),
            "passed": (int,),
            "failed": (int,),
            "errors": (int,),
            "skipped": (int,),
            "exit_code": (int,),
        },
        extra_allowed=(
            "analyzed_report",
            "analyzed_report_status",
            "analyzed_report_timestamp",
            "archive_policy",
            "authority",
            "blocker_analysis",
            "changes",
            "classification_taxonomy",
            "current_workspace_counts",
            "decision",
            "decisions",
            "duplicate_findings",
            "findings_by_severity",
            "findings_by_type",
            "finished_at",
            "fixes",
            "generated_at",
            "inputs",
            "known_risks",
            "lifecycle_findings",
            "m5a_snapshot",
            "m5b_input",
            "masterplan_source",
            "metadata_findings",
            "orphan_findings",
            "policy",
            "post_fix_gate_forecast",
            "required_fix_sequence",
            "run_id",
            "scope",
            "scope_definition",
            "score_explanation",
            "secondary_source",
            "secondary_source_status",
            "secondary_source_timestamp",
            "source_status_findings",
            "started_at",
            "total_documents",
            "total_findings",
            "validation",
            "workspace_id",
        ),
        status_values=("PASS", "FAIL", "BLOCKED", "COMPLETED", "INFO", "WARN"),
    ),
    "diagnostic_report": _schema(
        "diagnostic_report",
        extra_types={
            "result": (str,),
            "checks": (list,),
            "diagnostics": (dict,),
            "collected": (int,),
            "passed": (int,),
            "failed": (int,),
            "errors": (int, list),
            "skipped": (int,),
            "warnings": (list,),
            "blockers": (list,),
            "exit_code": (int,),
            "summary": (dict,),
        },
        extra_allowed=(
            "blocker_tests",
            "blocking_gates",
            "child_gates",
            "conditions",
            "decision",
            "entries",
            "gate",
            "generated_at",
            "invalid_sources",
            "inputs",
            "lock",
            "missing_gates",
            "next_allowed_phase",
            "open_blockers_for_next_phase",
            "policy",
            "queue_recovery_fixes",
            "required_actions_before_m5a",
            "required_actions_before_m5b",
            "scope",
            "source_file",
            "sprint",
            "validation_summary",
        ),
        status_values=("PASS", "FAIL", "BLOCKED", "INFO", "WARN", "READY_FOR_M5B"),
    ),
    "status_report": _schema(
        "status_report",
        extra_types={
            "result": (str,),
            "decision": (dict, str),
            "summary": (dict,),
            "architecture": (dict,),
            "inputs": (dict,),
            "layer": (str,),
            "measurements": (list,),
            "methodology": (dict,),
            "quality_score": (int, float),
            "progress": (int, float),
            "recommendations": (list,),
            "overall_progress_percent": (int, float),
            "next_phase": (str,),
            "blockers": (list,),
            "warnings": (list,),
            "parent_gate_statuses": (dict,),
            "release_allowed": (bool,),
            "status_layer": (dict,),
            "collected": (int,),
            "passed": (int,),
            "failed": (int,),
            "errors": (int,),
            "skipped": (int,),
            "exit_code": (int,),
        },
        extra_allowed=(
            "api",
            "architecture",
            "archive_target",
            "archived",
            "assessment",
            "authority",
            "blocking",
            "decisions",
            "dashboard",
            "deferred",
            "detectors",
            "documentation_lint",
            "evaluation_basis",
            "findings_model",
            "fixes",
            "gate",
            "gate_criteria_summary",
            "gate_decision",
            "gate_score",
            "gate_hierarchy",
            "generated_at",
            "generated_from",
            "input_integrity_issues",
            "inputs",
            "issue",
            "known_limitations",
            "limitations",
            "m5",
            "m5a_gate_logic",
            "m3a_release_candidate",
            "m4_backend_release_candidate",
            "m4e_operations_release",
            "marker_policy",
            "milestone",
            "milestone_name",
            "milestones",
            "moved",
            "no_action_required",
            "non_blocking",
            "note",
            "open",
            "overall",
            "overall_m5a_data_quality_pass",
            "parent_gate_validations",
            "phases",
            "progress_model",
            "quality_score_model",
            "quality_score_threshold",
            "report_contradictions",
            "retained_required",
            "residual_risks",
            "scope_definition",
            "sections",
            "source_inputs",
            "trigger",
        ),
        status_values=("PASS", "FAIL", "BLOCKED", "INFO", "DRAFT", "PARTIAL_PASS", "WARN"),
    ),
}


REPORT_TYPE_TO_SCHEMA = {
    "gate": "gate_report",
    "supporting": "supporting_report",
    "diagnostic": "diagnostic_report",
    "status": "status_report",
    "informational": "status_report",
    "baseline_validation": "supporting_report",
    "matrix": "diagnostic_report",
    "validation": "diagnostic_report",
}


def get_schema(name: str) -> ReportSchema:
    try:
        return REPORT_SCHEMAS[name]
    except KeyError as exc:
        raise KeyError(f"unknown report schema: {name}") from exc


def schema_names() -> tuple[str, ...]:
    return tuple(REPORT_SCHEMAS)


def match_schema(payload: dict[str, Any]) -> ReportSchema | None:
    explicit = payload.get("schema") or payload.get("schema_name") or payload.get("report_kind")
    if isinstance(explicit, str) and explicit in REPORT_SCHEMAS:
        return REPORT_SCHEMAS[explicit]

    report_type = payload.get("report_type")
    if isinstance(report_type, str):
        schema_name = REPORT_TYPE_TO_SCHEMA.get(report_type.lower())
        if schema_name is not None:
            return REPORT_SCHEMAS[schema_name]

    report_name = payload.get("report_name")
    if isinstance(report_name, str) and (
        report_name.endswith("_assessment") or report_name.endswith("_completion_report")
    ):
        return REPORT_SCHEMAS["status_report"]
    if isinstance(report_name, str) and report_name.endswith("_status"):
        return REPORT_SCHEMAS["status_report"]
    if "gate" in payload or (isinstance(report_name, str) and report_name.endswith("_gate")):
        return REPORT_SCHEMAS["gate_report"]
    if "diagnostics" in payload or "checks" in payload:
        return REPORT_SCHEMAS["diagnostic_report"]
    if "summary" in payload or "metrics" in payload or "findings" in payload:
        return REPORT_SCHEMAS["supporting_report"]
    return None
