"""Extended Health Check — GET /health/ready und /health/components.

Komponenten-Checks: Database, Provider, Filesystem, Metrics, Job Queue,
Reports, Storage. Status UP / DEGRADED / DOWN.
Eingebunden in main.py über health_router (bestehend).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(tags=["health"])

StatusValue = Literal["UP", "DEGRADED", "DOWN"]

_PROCESS_START = time.time()
_APP_VERSION = settings.app_version


def _db_check() -> dict:
    try:
        from app.core.database import check_database_connection
        check_database_connection()
        return {"status": "UP", "detail": "connection ok"}
    except Exception as exc:
        return {"status": "DOWN", "detail": str(exc)[:120]}


def _filesystem_check() -> dict:
    """Prüft ob Upload-Verzeichnis les- und schreibbar ist."""
    try:
        upload_dir = settings.original_file_store_dir or "uploads"
        if not os.path.isdir(upload_dir):
            return {"status": "DEGRADED", "detail": f"{upload_dir} nicht vorhanden"}
        test_path = os.path.join(upload_dir, ".healthcheck")
        with open(test_path, "w") as f:
            f.write("ok")
        os.remove(test_path)
        return {"status": "UP", "detail": f"{upload_dir} les- und schreibbar"}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": str(exc)[:120]}


def _metrics_check() -> dict:
    try:
        from app.observability.prometheus_metrics import _PROMETHEUS_AVAILABLE
        if _PROMETHEUS_AVAILABLE:
            return {"status": "UP", "detail": "prometheus_client verfügbar"}
        return {"status": "DEGRADED", "detail": "prometheus_client nicht installiert"}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": str(exc)[:80]}


def _job_queue_check() -> dict:
    """Prüft Anzahl der hängenden Jobs via psycopg."""
    try:
        from app.core.database import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, COUNT(*) FROM background_jobs GROUP BY status"
                )
                rows = cur.fetchall()
        counts = {row[0]: row[1] for row in rows}
        running = counts.get("running", 0)
        pending = counts.get("pending", 0)
        status: StatusValue = "UP"
        if running > 10:
            status = "DEGRADED"
        if running > 50:
            status = "DOWN"
        return {"status": status, "detail": f"running={running}, pending={pending}"}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": str(exc)[:80]}


def _storage_check() -> dict:
    """Prüft Disk-Nutzung."""
    try:
        import psutil
        disk = psutil.disk_usage("/")
        pct = disk.percent
        status: StatusValue = "UP"
        if pct > 80:
            status = "DEGRADED"
        if pct > 90:
            status = "DOWN"
        return {"status": status, "detail": f"{pct:.1f}% used"}
    except ImportError:
        return {"status": "DEGRADED", "detail": "psutil nicht installiert"}
    except Exception as exc:
        return {"status": "DEGRADED", "detail": str(exc)[:80]}


def _reports_check() -> dict:
    """Prüft ob reports/current/ erreichbar ist."""
    reports_dir = "reports/current"
    if os.path.isdir(reports_dir):
        return {"status": "UP", "detail": f"{reports_dir} vorhanden"}
    return {"status": "DEGRADED", "detail": f"{reports_dir} nicht gefunden"}


def _provider_check() -> dict:
    """Stub: Provider-Erreichbarkeit. Ohne Live-Anfrage."""
    return {"status": "UP", "detail": "provider check skipped (no live ping in health)"}


def _aggregate_status(components: dict[str, dict]) -> StatusValue:
    statuses = [c.get("status", "DOWN") for c in components.values()]
    if "DOWN" in statuses:
        return "DOWN"
    if "DEGRADED" in statuses:
        return "DEGRADED"
    return "UP"


@router.get("/health/ready")
def health_ready() -> JSONResponse:
    """Readiness-Check: alle Komponenten."""
    components = {
        "database": _db_check(),
        "filesystem": _filesystem_check(),
        "metrics": _metrics_check(),
        "storage": _storage_check(),
        "reports": _reports_check(),
        "job_queue": _job_queue_check(),
        "provider": _provider_check(),
    }
    overall = _aggregate_status(components)
    payload = {
        "status": overall,
        "version": _APP_VERSION,
        "uptime_seconds": round(time.time() - _PROCESS_START, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }
    status_code = 200 if overall != "DOWN" else 503
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/health/live")
def health_live() -> dict:
    """Liveness-Check: nur Prozess läuft."""
    return {
        "status": "UP",
        "version": _APP_VERSION,
        "uptime_seconds": round(time.time() - _PROCESS_START, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
