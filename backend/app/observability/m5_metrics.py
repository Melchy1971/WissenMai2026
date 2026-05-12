from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.observability.logging import event_logger, get_observability_context, metrics_registry


AggregationScope = Literal["workspace", "global"]
MetricKind = Literal["gauge", "counter", "rate", "trend"]


@dataclass(frozen=True)
class M5MetricDefinition:
    name: str
    kind: MetricKind
    unit: str
    aggregation_scope: AggregationScope
    window: str
    description: str
    source: str
    warning_threshold: str
    critical_threshold: str


M5_METRIC_DEFINITIONS: tuple[M5MetricDefinition, ...] = (
    M5MetricDefinition(
        name="m5_queue_backlog_age_seconds",
        kind="gauge",
        unit="seconds",
        aggregation_scope="workspace",
        window="current,p95,max",
        description="Age of the oldest pending, running, retryable or dead_letter queue job.",
        source="background_jobs.created_at/claimed_at/updated_at grouped by workspace and status",
        warning_threshold="oldest_running > timeout or p95 > 900",
        critical_threshold="oldest_running > 2*timeout or max > 3600",
    ),
    M5MetricDefinition(
        name="m5_retry_frequency",
        kind="rate",
        unit="retries_per_hour",
        aggregation_scope="workspace",
        window="1h,24h,7d",
        description="Retry attempts per time window by job type and final status.",
        source="background_jobs retry metadata and queue transition audit events",
        warning_threshold="> 5 retries/hour for one workspace",
        critical_threshold="retry rate increasing for 3 consecutive windows or dead_letter growth",
    ),
    M5MetricDefinition(
        name="m5_drift_score",
        kind="gauge",
        unit="score",
        aggregation_scope="workspace",
        window="current,24h trend,7d trend",
        description="Weighted drift score from index, lifecycle, citation, queue, backup and data quality checks.",
        source="drift reports, entropy audit and diagnostics",
        warning_threshold="> 0 outside a maintenance window",
        critical_threshold="persistent > 0 after repair or any cross-workspace drift",
    ),
    M5MetricDefinition(
        name="m5_retrieval_quality_trend",
        kind="trend",
        unit="score_delta",
        aggregation_scope="global",
        window="latest,7d,30d",
        description="Trend of Precision@K, Recall@K, MRR, citation completeness and insufficient_context accuracy.",
        source="reports/m5_retrieval/latest.json and versioned benchmark reports",
        warning_threshold="any metric below warning threshold or negative 7d trend",
        critical_threshold="threshold breach for search/chat recall, citation completeness or lifecycle violations",
    ),
    M5MetricDefinition(
        name="m5_backup_freshness_seconds",
        kind="gauge",
        unit="seconds",
        aggregation_scope="global",
        window="current",
        description="Age of the latest verified backup or restore-capable backup artifact.",
        source="backup manifest, verify-backup report and restore truth report",
        warning_threshold="> 6 days",
        critical_threshold="> 7 days or latest verify-backup failed",
    ),
    M5MetricDefinition(
        name="m5_restore_success_rate",
        kind="rate",
        unit="ratio",
        aggregation_scope="global",
        window="7d,30d",
        description="Successful restore validations divided by attempted restore validations.",
        source="backup restore reports and restore truth reports",
        warning_threshold="< 1.0 in 30d",
        critical_threshold="latest restore verification failed",
    ),
    M5MetricDefinition(
        name="m5_cleanup_impact",
        kind="gauge",
        unit="entities",
        aggregation_scope="workspace",
        window="dry_run,current,7d trend",
        description="Dry-run candidate, protected and blocked entity counts for cleanup plans.",
        source="cleanup dry-run and entropy audit reports",
        warning_threshold="blocked_count > 0 or unexpected candidate growth",
        critical_threshold="destructive plan without verified backup or protected citation impact",
    ),
    M5MetricDefinition(
        name="m5_orphan_growth_rate",
        kind="rate",
        unit="orphans_per_day",
        aggregation_scope="workspace",
        window="24h,7d,30d",
        description="Growth rate of orphan chunks, versions, files, citations or index entries.",
        source="data quality probes, entropy audit and diagnostics",
        warning_threshold="> 0 for one window",
        critical_threshold="persistent > 0 or any orphan touching historical citations",
    ),
)

ALLOWED_DIMENSIONS = {
    "job_type",
    "job_status",
    "drift_type",
    "metric_source",
    "operation",
    "result",
    "window",
}

SENSITIVE_DIMENSIONS = {
    "content",
    "chunk_text",
    "document_title",
    "filename",
    "path",
    "query",
    "quote_preview",
    "text",
    "token",
    "user_id",
}


def metric_names() -> set[str]:
    return {definition.name for definition in M5_METRIC_DEFINITIONS}


def build_m5_metric_payload(
    *,
    metric_name: str,
    value: int | float,
    status: str,
    workspace_id: str | None = None,
    aggregation_scope: AggregationScope | None = None,
    window: str | None = None,
    dimensions: dict[str, str | int | float | bool] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    definition = _definition(metric_name)
    effective_scope = aggregation_scope or definition.aggregation_scope
    if effective_scope == "workspace" and not workspace_id:
        current = get_observability_context()
        workspace_id = current.workspace_id
    sanitized_dimensions = _sanitize_dimensions(dimensions or {})
    current = get_observability_context()
    return {
        "event_name": "m5_metric_observed",
        "metric_name": metric_name,
        "value": value,
        "unit": definition.unit,
        "kind": definition.kind,
        "aggregation_scope": effective_scope,
        "workspace_id": workspace_id if effective_scope == "workspace" else None,
        "window": window or definition.window,
        "status": status,
        "dimensions": sanitized_dimensions,
        "correlation_id": correlation_id if correlation_id is not None else current.correlation_id,
    }


def log_m5_metric(
    *,
    metric_name: str,
    value: int | float,
    status: str,
    workspace_id: str | None = None,
    aggregation_scope: AggregationScope | None = None,
    window: str | None = None,
    dimensions: dict[str, str | int | float | bool] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    payload = build_m5_metric_payload(
        metric_name=metric_name,
        value=value,
        status=status,
        workspace_id=workspace_id,
        aggregation_scope=aggregation_scope,
        window=window,
        dimensions=dimensions,
        correlation_id=correlation_id,
    )
    metrics_registry.record(event_name=payload["metric_name"], status=status)
    event_logger.info("m5_metric_observed", extra={"observability": payload})
    return payload


def _definition(metric_name: str) -> M5MetricDefinition:
    for definition in M5_METRIC_DEFINITIONS:
        if definition.name == metric_name:
            return definition
    raise ValueError(f"Unknown M5 metric: {metric_name}")


def _sanitize_dimensions(dimensions: dict[str, str | int | float | bool]) -> dict[str, str | int | float | bool]:
    sanitized: dict[str, str | int | float | bool] = {}
    for key, value in dimensions.items():
        if key in SENSITIVE_DIMENSIONS:
            raise ValueError(f"Sensitive M5 metric dimension is not allowed: {key}")
        if key not in ALLOWED_DIMENSIONS:
            raise ValueError(f"Unsupported M5 metric dimension: {key}")
        sanitized[key] = value
    return sanitized
