"""Prometheus Metrics — GA-OBS-01.

Implementiert /metrics Endpoint und alle Metriken gemäß PRI-7-Anforderungen:
- System: CPU, RAM, Uptime
- HTTP: Request Count, Response Time, Error Count, Status Codes
- Business: Document Count, Topic Count, Analysis Jobs, Export Jobs, Open Reviews
- Provider: Requests, Errors, Duration
- Jobsystem: Running Jobs, Failed Jobs, Queue Length, Retry Count

Verwendung:
    from app.observability.prometheus_metrics import (
        HTTP_REQUEST_COUNT, HTTP_REQUEST_DURATION,
        track_provider_request, update_job_gauges,
    )

Kein prometheus_client-Pflicht-Import in Tests — alles lazy.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager

from app.core.config import settings

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Info, generate_latest,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False


def _noop_counter(*a, **kw):
    class _N:
        def labels(self, **kw): return self
        def inc(self, n=1): pass
    return _N()

def _noop_histogram(*a, **kw):
    class _N:
        def labels(self, **kw): return self
        def observe(self, v): pass
        def time(self): return __import__('contextlib').nullcontext()
    return _N()

def _noop_gauge(*a, **kw):
    class _N:
        def labels(self, **kw): return self
        def set(self, v): pass
        def inc(self, n=1): pass
        def dec(self, n=1): pass
    return _N()


if _PROMETHEUS_AVAILABLE:
    # ── HTTP ──────────────────────────────────────────────────────────────── #
    HTTP_REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    HTTP_REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    HTTP_ERROR_COUNT = Counter(
        "http_errors_total",
        "Total HTTP errors (4xx + 5xx)",
        ["method", "path", "status"],
    )
    APP_INFO = Info("app", "Application build information")

    app_info_labels = {"version": settings.app_version}
    if settings.app_sprint:
        app_info_labels["sprint"] = settings.app_sprint
    APP_INFO.info(app_info_labels)

    # ── System ────────────────────────────────────────────────────────────── #
    SYSTEM_CPU_USAGE = Gauge("system_cpu_usage_percent", "CPU usage in percent")
    SYSTEM_MEMORY_USAGE_MB = Gauge("system_memory_usage_mb", "Memory RSS usage in MB")
    SYSTEM_UPTIME_SECONDS = Gauge("system_uptime_seconds", "Process uptime in seconds")
    SYSTEM_DISK_USAGE_PERCENT = Gauge("system_disk_usage_percent", "Disk usage percent")

    # ── Business ──────────────────────────────────────────────────────────── #
    BUSINESS_DOCUMENTS_TOTAL = Gauge(
        "business_documents_total",
        "Total documents",
        ["lifecycle_status"],
    )
    BUSINESS_TOPICS_TOTAL = Gauge(
        "business_topics_total",
        "Total topics",
    )
    BUSINESS_ANALYSIS_JOBS_TOTAL = Gauge(
        "business_analysis_jobs_total",
        "Analysis jobs by status",
        ["status"],
    )
    BUSINESS_EXPORT_JOBS_TOTAL = Gauge(
        "business_export_jobs_total",
        "Export jobs by status",
        ["status"],
    )
    BUSINESS_OPEN_REVIEWS = Gauge(
        "business_open_reviews_total",
        "Analysis results in review/draft status",
    )

    # ── Provider ──────────────────────────────────────────────────────────── #
    PROVIDER_REQUEST_COUNT = Counter(
        "provider_requests_total",
        "Total provider API requests",
        ["provider"],
    )
    PROVIDER_ERROR_COUNT = Counter(
        "provider_errors_total",
        "Total provider API errors",
        ["provider", "error_type"],
    )
    PROVIDER_REQUEST_DURATION = Histogram(
        "provider_request_duration_seconds",
        "Provider API request duration",
        ["provider"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    # ── Jobsystem ─────────────────────────────────────────────────────────── #
    JOB_RUNNING = Gauge("job_running_total", "Currently running jobs", ["job_type"])
    JOB_FAILED = Counter("job_failed_total", "Total failed jobs", ["job_type"])
    JOB_QUEUE_LENGTH = Gauge("job_queue_length", "Pending jobs in queue", ["job_type"])
    JOB_RETRY_COUNT = Counter("job_retry_total", "Total job retries", ["job_type"])
    JOB_DEAD_LETTER = Gauge("job_dead_letter_total", "Jobs in dead-letter state", ["job_type"])

else:
    # Fallback: no-ops wenn prometheus_client nicht installiert
    HTTP_REQUEST_COUNT = _noop_counter()
    HTTP_REQUEST_DURATION = _noop_histogram()
    HTTP_ERROR_COUNT = _noop_counter()
    APP_INFO = _noop_gauge()
    SYSTEM_CPU_USAGE = _noop_gauge()
    SYSTEM_MEMORY_USAGE_MB = _noop_gauge()
    SYSTEM_UPTIME_SECONDS = _noop_gauge()
    SYSTEM_DISK_USAGE_PERCENT = _noop_gauge()
    BUSINESS_DOCUMENTS_TOTAL = _noop_gauge()
    BUSINESS_TOPICS_TOTAL = _noop_gauge()
    BUSINESS_ANALYSIS_JOBS_TOTAL = _noop_gauge()
    BUSINESS_EXPORT_JOBS_TOTAL = _noop_gauge()
    BUSINESS_OPEN_REVIEWS = _noop_gauge()
    PROVIDER_REQUEST_COUNT = _noop_counter()
    PROVIDER_ERROR_COUNT = _noop_counter()
    PROVIDER_REQUEST_DURATION = _noop_histogram()
    JOB_RUNNING = _noop_gauge()
    JOB_FAILED = _noop_counter()
    JOB_QUEUE_LENGTH = _noop_gauge()
    JOB_RETRY_COUNT = _noop_counter()
    JOB_DEAD_LETTER = _noop_gauge()


# ── System-Metriken aktualisieren ──────────────────────────────────────────── #

_PROCESS_START = time.time()
PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def update_system_metrics() -> None:
    """Aktualisiert CPU/RAM/Uptime/Disk Gauges. Benötigt psutil."""
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        SYSTEM_CPU_USAGE.set(psutil.cpu_percent(interval=None))
        SYSTEM_MEMORY_USAGE_MB.set(proc.memory_info().rss / 1024 / 1024)
        SYSTEM_UPTIME_SECONDS.set(time.time() - _PROCESS_START)
        disk = psutil.disk_usage("/")
        SYSTEM_DISK_USAGE_PERCENT.set(disk.percent)
    except Exception:
        pass


# ── Provider-Helper ────────────────────────────────────────────────────────── #

@contextmanager
def track_provider_request(provider: str):
    """Context-Manager: zählt Provider-Anfragen, misst Duration, tracked Errors."""
    PROVIDER_REQUEST_COUNT.labels(provider=provider).inc()
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        error_type = type(exc).__name__
        PROVIDER_ERROR_COUNT.labels(provider=provider, error_type=error_type).inc()
        raise
    finally:
        PROVIDER_REQUEST_DURATION.labels(provider=provider).observe(
            time.perf_counter() - start
        )


# ── /metrics Endpoint-Handler ──────────────────────────────────────────────── #

def metrics_response():
    """Gibt Prometheus-Text-Format zurück."""
    if not _PROMETHEUS_AVAILABLE:
        return "# prometheus_client not installed\n", PROMETHEUS_CONTENT_TYPE
    update_system_metrics()
    return generate_latest(), PROMETHEUS_CONTENT_TYPE
