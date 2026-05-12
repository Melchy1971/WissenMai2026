import pytest

from app.observability import m5_metrics


def test_m5_metric_definitions_cover_required_metrics() -> None:
    assert m5_metrics.metric_names() == {
        "m5_queue_backlog_age_seconds",
        "m5_retry_frequency",
        "m5_drift_score",
        "m5_retrieval_quality_trend",
        "m5_backup_freshness_seconds",
        "m5_restore_success_rate",
        "m5_cleanup_impact",
        "m5_orphan_growth_rate",
    }


def test_m5_metric_payload_uses_workspace_scope_without_sensitive_fields() -> None:
    payload = m5_metrics.build_m5_metric_payload(
        metric_name="m5_queue_backlog_age_seconds",
        value=120,
        status="ok",
        workspace_id="workspace-1",
        dimensions={"job_status": "running", "window": "current"},
    )

    assert payload["event_name"] == "m5_metric_observed"
    assert payload["workspace_id"] == "workspace-1"
    assert payload["aggregation_scope"] == "workspace"
    assert payload["dimensions"] == {"job_status": "running", "window": "current"}
    assert "user_id" not in payload


def test_m5_metric_payload_removes_workspace_for_global_metrics() -> None:
    payload = m5_metrics.build_m5_metric_payload(
        metric_name="m5_backup_freshness_seconds",
        value=3600,
        status="ok",
        workspace_id="workspace-1",
    )

    assert payload["aggregation_scope"] == "global"
    assert payload["workspace_id"] is None


def test_m5_metric_dimensions_reject_sensitive_content() -> None:
    with pytest.raises(ValueError, match="Sensitive M5 metric dimension"):
        m5_metrics.build_m5_metric_payload(
            metric_name="m5_retrieval_quality_trend",
            value=0.98,
            status="ok",
            dimensions={"query": "Was steht im Dokument?"},
        )
