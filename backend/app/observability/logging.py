from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.schemas.observability import ImportEventName, ImportEventStatus, ImportObservabilityEvent


@dataclass(frozen=True)
class ObservabilityContext:
    correlation_id: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None


_context_var: ContextVar[ObservabilityContext] = ContextVar("observability_context", default=ObservabilityContext())


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, str], int] = {}

    def record(self, *, event_name: str, status: str) -> None:
        key = (event_name, status)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {f"{event}.{status}": count for (event, status), count in self._counters.items()}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


metrics_registry = MetricsRegistry()
event_logger = logging.getLogger("app.observability.events")


class StructuredObservabilityFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "observability", None)
        if payload is None:
            return super().format(record)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def configure_structured_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredObservabilityFormatter("%(message)s"))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        return

    for handler in root_logger.handlers:
        if not isinstance(handler.formatter, StructuredObservabilityFormatter):
            handler.setFormatter(StructuredObservabilityFormatter("%(message)s"))


def set_observability_context(*, correlation_id: str | None, workspace_id: str | None = None, user_id: str | None = None):
    return _context_var.set(ObservabilityContext(correlation_id=correlation_id, workspace_id=workspace_id, user_id=user_id))


def bind_observability_context(
    *, correlation_id: str | None = None, workspace_id: str | None = None, user_id: str | None = None
) -> None:
    current = _context_var.get()
    _context_var.set(
        ObservabilityContext(
            correlation_id=correlation_id if correlation_id is not None else current.correlation_id,
            workspace_id=workspace_id if workspace_id is not None else current.workspace_id,
            user_id=user_id if user_id is not None else current.user_id,
        )
    )


def reset_observability_context(token) -> None:
    _context_var.reset(token)


def get_observability_context() -> ObservabilityContext:
    return _context_var.get()


def log_event(
    event_name: str,
    *,
    workspace_id: str | None = None,
    user_id: str | None = None,
    duration_ms: int | None = None,
    status: str,
    error_code: str | None = None,
    correlation_id: str | None = None,
) -> None:
    current = get_observability_context()
    payload = {
        "event_name": event_name,
        "workspace_id": workspace_id if workspace_id is not None else current.workspace_id,
        "user_id": user_id if user_id is not None else current.user_id,
        "duration_ms": duration_ms,
        "status": status,
        "error_code": error_code,
        "correlation_id": correlation_id if correlation_id is not None else current.correlation_id,
    }
    metrics_registry.record(event_name=event_name, status=status)
    event_logger.info("observability_event", extra={"observability": payload})


def log_import_event(
    event_name: ImportEventName,
    *,
    document_id: str | None,
    workspace_id: str | None,
    duration_ms: int | None,
    parser_type: str,
    chunk_count: int,
    status: ImportEventStatus,
    error_code: str | None = None,
    correlation_id: str | None = None,
) -> None:
    current = get_observability_context()
    payload = ImportObservabilityEvent(
        event_name=event_name,
        document_id=document_id,
        workspace_id=workspace_id if workspace_id is not None else current.workspace_id,
        duration_ms=duration_ms,
        parser_type=parser_type,
        chunk_count=chunk_count,
        error_code=error_code,
        correlation_id=correlation_id if correlation_id is not None else current.correlation_id,
        status=status,
    ).model_dump()
    metrics_registry.record(event_name=event_name, status=status)
    event_logger.info("observability_event", extra={"observability": payload})