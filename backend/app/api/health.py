from fastapi import APIRouter

from app.core.config import settings
from app.core.database import DatabaseConfigurationError, check_database_connection
from app.core.errors import ServiceUnavailableApiError

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@router.get("/health/db")
def database_health() -> dict[str, str]:
    try:
        check_database_connection()
    except DatabaseConfigurationError as exc:
        raise ServiceUnavailableApiError(message=str(exc)) from exc
    except Exception as exc:
        raise ServiceUnavailableApiError(message="Database connection check failed") from exc

    return {"status": "ok"}


@router.get("/health/preflight")
def preflight_health() -> dict:
    """
    Führt alle Preflight-Checks durch und gibt das Ergebnis zurück.
    HTTP 200 wenn alle Checks bestanden (pass oder warn).
    HTTP 503 bei mindestens einem fail.
    """
    from app.services.preflight import PreflightService

    result = PreflightService().run()
    payload = result.as_dict()
    payload["env"] = settings.app_env

    if not result.passed:
        raise ServiceUnavailableApiError(message="Preflight checks failed", detail=payload)

    return payload
