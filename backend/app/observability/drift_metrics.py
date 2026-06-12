"""Drift Detection Observability.

Metriken und strukturiertes Logging für Drift Detection Runs.

Constraints (PROHIBIT-02, PROHIBIT-06):
    Kein Inhalt von Dokumenten, keine Credentials in Logs.
    Alle Felder: correlation_id, workspace_id, drift_run_id.

Metriken:
    drift_run_started
    drift_run_completed
    drift_run_failed
    findings_count
    critical_findings_count
    drift_run_duration_ms
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator

from app.observability.logging import (
    event_logger,
    get_observability_context,
    metrics_registry,
)

_drift_logger = logging.getLogger("app.observability.drift")

# ---------------------------------------------------------------------------
# Metric names
# ---------------------------------------------------------------------------

METRIC_DRIFT_RUN_STARTED = "drift_run_started"
METRIC_DRIFT_RUN_COMPLETED = "drift_run_completed"
METRIC_DRIFT_RUN_FAILED = "drift_run_failed"
METRIC_FINDINGS_COUNT = "findings_count"
METRIC_CRITICAL_FINDINGS_COUNT = "critical_findings_count"
METRIC_DRIFT_RUN_DURATION_MS = "drift_run_duration_ms"

# ---------------------------------------------------------------------------
# Safe field list — no document content, no credentials
# ---------------------------------------------------------------------------

_SAFE_FIELDS = frozenset({
    "correlation_id",
    "workspace_id",
    "drift_run_id",
    "status",
    "duration_ms",
    "findings_count",
    "critical_findings_count",
    "error_code",
    "detector_names",
})


def _safe_payload(**kwargs) -> dict:
    """Strip any key not in the safe-field allowlist."""
    ctx = get_observability_context()
    base = {
        "correlation_id": ctx.correlation_id,
        "workspace_id": ctx.workspace_id,
    }
    base.update({k: v for k, v in kwargs.items() if k in _SAFE_FIELDS})
    return base


# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------

def record_drift_run_started(
    *,
    drift_run_id: str,
    workspace_id: str,
    correlation_id: str | None = None,
) -> None:
    """Emit drift_run_started metric + log event."""
    payload = _safe_payload(
        drift_run_id=drift_run_id,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        status="started",
    )
    payload["event"] = METRIC_DRIFT_RUN_STARTED
    metrics_registry.record(event_name=METRIC_DRIFT_RUN_STARTED, status="started")
    event_logger.info(METRIC_DRIFT_RUN_STARTED, extra={"observability": payload})


def record_drift_run_completed(
    *,
    drift_run_id: str,
    workspace_id: str,
    duration_ms: float,
    findings_count: int,
    critical_findings_count: int,
    correlation_id: str | None = None,
) -> None:
    """Emit drift_run_completed + findings + critical_findings + duration metrics."""
    payload = _safe_payload(
        drift_run_id=drift_run_id,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        status="completed",
        duration_ms=round(duration_ms, 2),
        findings_count=findings_count,
        critical_findings_count=critical_findings_count,
    )
    payload["event"] = METRIC_DRIFT_RUN_COMPLETED
    metrics_registry.record(event_name=METRIC_DRIFT_RUN_COMPLETED, status="completed")
    metrics_registry.record(event_name=METRIC_FINDINGS_COUNT, status="recorded")
    metrics_registry.record(event_name=METRIC_CRITICAL_FINDINGS_COUNT, status="recorded")
    metrics_registry.record(event_name=METRIC_DRIFT_RUN_DURATION_MS, status="recorded")
    event_logger.info(METRIC_DRIFT_RUN_COMPLETED, extra={"observability": payload})


def record_drift_run_failed(
    *,
    drift_run_id: str,
    workspace_id: str,
    error_code: str,
    duration_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Emit drift_run_failed metric + log event."""
    payload = _safe_payload(
        drift_run_id=drift_run_id,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        status="failed",
        error_code=error_code,
    )
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    payload["event"] = METRIC_DRIFT_RUN_FAILED
    metrics_registry.record(event_name=METRIC_DRIFT_RUN_FAILED, status="failed")
    event_logger.warning(METRIC_DRIFT_RUN_FAILED, extra={"observability": payload})


# ---------------------------------------------------------------------------
# Context manager for instrumented runs
# ---------------------------------------------------------------------------

@contextmanager
def drift_run_span(
    *,
    drift_run_id: str,
    workspace_id: str,
    correlation_id: str | None = None,
) -> Generator[None, None, None]:
    """Context manager that emits started/completed/failed automatically."""
    record_drift_run_started(
        drift_run_id=drift_run_id,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
    )
    t0 = time.perf_counter()
    try:
        yield
        duration_ms = (time.perf_counter() - t0) * 1000
        # Caller must call record_drift_run_completed with findings counts;
        # the span only handles timing for failed case automatically.
    except Exception:
        duration_ms = (time.perf_counter() - t0) * 1000
        record_drift_run_failed(
            drift_run_id=drift_run_id,
            workspace_id=workspace_id,
            error_code="UNHANDLED_EXCEPTION",
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        raise
