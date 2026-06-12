"""Observability Tests für Drift Detection.

Prüft:
1. drift_run_started wird emittiert
2. drift_run_completed wird emittiert
3. drift_run_failed wird emittiert
4. findings_count wird in completed-Payload erfasst
5. critical_findings_count wird in completed-Payload erfasst
6. drift_run_duration_ms wird in completed-Payload erfasst
7. correlation_id im Payload vorhanden
8. workspace_id im Payload vorhanden
9. drift_run_id im Payload vorhanden
10. Kein Dokument-Inhalt in Logs (PROHIBIT-PII)
11. Keine Credentials in Logs (PROHIBIT-CRED)
12. drift_run_span: failed-Fall emittiert drift_run_failed
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# sys.modules patches
# ---------------------------------------------------------------------------
sys.modules.setdefault("psycopg", MagicMock())
sys.modules.setdefault("pydantic_settings", MagicMock())
sys.modules.setdefault("app.services.auth", MagicMock())
sys.modules.setdefault("app.core.database", MagicMock())

# Minimal schema stub so observability.logging import succeeds
_schema_mock = MagicMock()
sys.modules.setdefault("app.schemas.observability", _schema_mock)

from app.observability import drift_metrics as dm
from app.observability.logging import metrics_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RUN_ID = "run-obs-001"
WS_ID = "ws-obs-001"
CORR_ID = "corr-obs-001"

FORBIDDEN_CONTENT_KEYS = {
    "content", "chunk_text", "document_title", "filename",
    "path", "query", "quote_preview", "text", "token",
    "password", "secret", "credential", "api_key",
}


def _captured_payload(mock_logger) -> dict:
    """Extract the observability payload from the last event_logger call."""
    call = mock_logger.call_args_list[-1]
    extra = call.kwargs.get("extra") or (call.args[1] if len(call.args) > 1 else {})
    return extra.get("observability", {})


# ---------------------------------------------------------------------------
# 1. drift_run_started emittiert
# ---------------------------------------------------------------------------

class TestDriftRunStarted:
    def test_emits_started_event(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_started(drift_run_id=RUN_ID, workspace_id=WS_ID, correlation_id=CORR_ID)
            assert mock_log.called
            payload = _captured_payload(mock_log)
            assert payload["event"] == dm.METRIC_DRIFT_RUN_STARTED

    def test_registry_records_started(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "info"):
            dm.record_drift_run_started(drift_run_id=RUN_ID, workspace_id=WS_ID)
        snap = metrics_registry.snapshot()
        assert snap.get("drift_run_started.started", 0) >= 1


# ---------------------------------------------------------------------------
# 2. drift_run_completed emittiert
# ---------------------------------------------------------------------------

class TestDriftRunCompleted:
    def test_emits_completed_event(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=123.4, findings_count=5, critical_findings_count=1,
                correlation_id=CORR_ID,
            )
            payload = _captured_payload(mock_log)
            assert payload["event"] == dm.METRIC_DRIFT_RUN_COMPLETED

    def test_registry_records_completed(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "info"):
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=100.0, findings_count=3, critical_findings_count=0,
            )
        snap = metrics_registry.snapshot()
        assert snap.get("drift_run_completed.completed", 0) >= 1


# ---------------------------------------------------------------------------
# 3. drift_run_failed emittiert
# ---------------------------------------------------------------------------

class TestDriftRunFailed:
    def test_emits_failed_event(self):
        with patch.object(dm.event_logger, "warning") as mock_log:
            dm.record_drift_run_failed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                error_code="DB_ERROR", correlation_id=CORR_ID,
            )
            payload = _captured_payload(mock_log)
            assert payload["event"] == dm.METRIC_DRIFT_RUN_FAILED

    def test_registry_records_failed(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "warning"):
            dm.record_drift_run_failed(
                drift_run_id=RUN_ID, workspace_id=WS_ID, error_code="CONFIG_ERROR",
            )
        snap = metrics_registry.snapshot()
        assert snap.get("drift_run_failed.failed", 0) >= 1


# ---------------------------------------------------------------------------
# 4. findings_count in Payload
# ---------------------------------------------------------------------------

class TestFindingsCount:
    def test_findings_count_in_completed_payload(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=50.0, findings_count=7, critical_findings_count=2,
            )
            payload = _captured_payload(mock_log)
            assert payload["findings_count"] == 7

    def test_findings_count_registered(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "info"):
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=50.0, findings_count=7, critical_findings_count=2,
            )
        snap = metrics_registry.snapshot()
        assert snap.get("findings_count.recorded", 0) >= 1


# ---------------------------------------------------------------------------
# 5. critical_findings_count in Payload
# ---------------------------------------------------------------------------

class TestCriticalFindingsCount:
    def test_critical_count_in_payload(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=50.0, findings_count=7, critical_findings_count=3,
            )
            payload = _captured_payload(mock_log)
            assert payload["critical_findings_count"] == 3

    def test_critical_count_registered(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "info"):
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=50.0, findings_count=7, critical_findings_count=3,
            )
        snap = metrics_registry.snapshot()
        assert snap.get("critical_findings_count.recorded", 0) >= 1


# ---------------------------------------------------------------------------
# 6. drift_run_duration_ms in Payload
# ---------------------------------------------------------------------------

class TestDriftRunDuration:
    def test_duration_in_payload(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=456.78, findings_count=0, critical_findings_count=0,
            )
            payload = _captured_payload(mock_log)
            assert payload["duration_ms"] == pytest.approx(456.78, abs=0.01)

    def test_duration_registered(self):
        metrics_registry.reset()
        with patch.object(dm.event_logger, "info"):
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=10.0, findings_count=0, critical_findings_count=0,
            )
        snap = metrics_registry.snapshot()
        assert snap.get("drift_run_duration_ms.recorded", 0) >= 1


# ---------------------------------------------------------------------------
# 7. correlation_id im Payload
# ---------------------------------------------------------------------------

class TestCorrelationId:
    def test_correlation_id_in_started_payload(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_started(
                drift_run_id=RUN_ID, workspace_id=WS_ID, correlation_id="corr-xyz"
            )
            payload = _captured_payload(mock_log)
            assert payload.get("correlation_id") == "corr-xyz"


# ---------------------------------------------------------------------------
# 8. workspace_id im Payload
# ---------------------------------------------------------------------------

class TestWorkspaceId:
    def test_workspace_id_in_started_payload(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_started(drift_run_id=RUN_ID, workspace_id="ws-check-123")
            payload = _captured_payload(mock_log)
            assert payload.get("workspace_id") == "ws-check-123"


# ---------------------------------------------------------------------------
# 9. drift_run_id im Payload
# ---------------------------------------------------------------------------

class TestDriftRunId:
    def test_run_id_in_started_payload(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_started(drift_run_id="run-check-456", workspace_id=WS_ID)
            payload = _captured_payload(mock_log)
            assert payload.get("drift_run_id") == "run-check-456"


# ---------------------------------------------------------------------------
# 10. Kein Dokument-Inhalt in Logs
# ---------------------------------------------------------------------------

class TestNoDocumentContent:
    def test_safe_payload_excludes_content_keys(self):
        payload = dm._safe_payload(
            drift_run_id=RUN_ID,
            workspace_id=WS_ID,
            # forbidden key — should be excluded
            content="some document text",
            chunk_text="chunk body",
        )
        for forbidden in FORBIDDEN_CONTENT_KEYS:
            assert forbidden not in payload, f"Forbidden key '{forbidden}' leaked into payload"

    def test_started_payload_has_no_content(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_started(drift_run_id=RUN_ID, workspace_id=WS_ID)
            payload = _captured_payload(mock_log)
        for forbidden in {"content", "chunk_text", "document_title", "text"}:
            assert forbidden not in payload


# ---------------------------------------------------------------------------
# 11. Keine Credentials in Logs
# ---------------------------------------------------------------------------

class TestNoCredentials:
    def test_safe_payload_excludes_credential_keys(self):
        payload = dm._safe_payload(
            drift_run_id=RUN_ID,
            workspace_id=WS_ID,
            token="secret-token-xyz",
            password="super-secret",
            api_key="key-abc",
        )
        for cred_key in {"token", "password", "secret", "credential", "api_key"}:
            assert cred_key not in payload

    def test_completed_payload_has_no_credentials(self):
        with patch.object(dm.event_logger, "info") as mock_log:
            dm.record_drift_run_completed(
                drift_run_id=RUN_ID, workspace_id=WS_ID,
                duration_ms=10.0, findings_count=0, critical_findings_count=0,
            )
            payload = _captured_payload(mock_log)
        for cred_key in {"token", "password", "secret", "credential", "api_key"}:
            assert cred_key not in payload


# ---------------------------------------------------------------------------
# 12. drift_run_span: Fehlerfall emittiert drift_run_failed
# ---------------------------------------------------------------------------

class TestDriftRunSpan:
    def test_span_emits_started_on_enter(self):
        with patch.object(dm, "record_drift_run_started") as mock_started, \
             patch.object(dm, "record_drift_run_completed"):
            with dm.drift_run_span(drift_run_id=RUN_ID, workspace_id=WS_ID):
                pass
            mock_started.assert_called_once()

    def test_span_emits_failed_on_exception(self):
        with patch.object(dm, "record_drift_run_started"), \
             patch.object(dm, "record_drift_run_failed") as mock_failed:
            with pytest.raises(RuntimeError):
                with dm.drift_run_span(drift_run_id=RUN_ID, workspace_id=WS_ID):
                    raise RuntimeError("boom")
            mock_failed.assert_called_once()
            call_kwargs = mock_failed.call_args.kwargs
            assert call_kwargs["error_code"] == "UNHANDLED_EXCEPTION"
            assert "duration_ms" in call_kwargs
