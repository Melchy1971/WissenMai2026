from typing import Annotated, Iterator

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import RequestAuthContext, require_workspace_admin, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import (
    AdminActionNotImplementedApiError,
    ApiError,
    BackgroundJobNotFoundApiError,
    DiagnosticsFailedApiError,
    ForbiddenApiError,
    JobNotReplayableApiError,
    ReplayFailedApiError,
    ResourceLockedApiError,
)
from app.db.session import get_session
from app.schemas.admin import DiagnosticsResponse, SearchIndexDriftReportResponse, SearchIndexInconsistencyReportResponse
from app.schemas.jobs import JobResponse
from app.services.diagnostics import DiagnosticsService
from app.services.search_index_service import SearchIndexRebuildService
from app.services.jobs.background_jobs import BackgroundJobNotFoundError, BackgroundJobService


router = APIRouter(prefix="/admin", tags=["admin"])


def get_background_job_service() -> Iterator[BackgroundJobService]:
    try:
        for session in get_session():
            yield BackgroundJobService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_search_index_service() -> Iterator[SearchIndexRebuildService]:
    try:
        for session in get_session():
            yield SearchIndexRebuildService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_diagnostics_service() -> Iterator[DiagnosticsService]:
    try:
        for session in get_session():
            yield DiagnosticsService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise DiagnosticsFailedApiError(details={"failed_check": "database"}) from exc


def require_diagnostics_admin(
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_member)],
) -> RequestAuthContext:
    if auth_context.role not in {"owner", "admin"}:
        raise ForbiddenApiError()
    return auth_context


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def get_diagnostics(
    auth_context: Annotated[RequestAuthContext, Depends(require_diagnostics_admin)],
    service: Annotated[DiagnosticsService, Depends(get_diagnostics_service)],
) -> DiagnosticsResponse:
    try:
        return service.get_diagnostics(workspace_id=auth_context.workspace_id)
    except DiagnosticsFailedApiError:
        raise
    except Exception as exc:
        raise DiagnosticsFailedApiError(details={"failed_check": "diagnostics"}) from exc


@router.post("/search-index/rebuild", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def rebuild_search_index(
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
) -> None:
    raise AdminActionNotImplementedApiError(
        message="Search index rebuild is disabled until M4a, M4b and M4c gates are complete",
        details={
            "action": "search_index_rebuild",
            "scope": "M4d read-only diagnostics",
            "required_gates": ["M4a", "M4b", "M4c"],
        },
    )


@router.get("/search-index/inconsistencies", response_model=SearchIndexInconsistencyReportResponse)
def get_search_index_inconsistencies(
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[SearchIndexRebuildService, Depends(get_search_index_service)],
) -> SearchIndexInconsistencyReportResponse:
    return SearchIndexInconsistencyReportResponse.model_validate(
        service.inspect_inconsistencies(workspace_id=auth_context.workspace_id)
    )


@router.get("/search-index/drift", response_model=SearchIndexDriftReportResponse)
def get_search_index_drift(
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[SearchIndexRebuildService, Depends(get_search_index_service)],
) -> SearchIndexDriftReportResponse:
    return SearchIndexDriftReportResponse.model_validate(
        service.inspect_drift(workspace_id=auth_context.workspace_id)
    )


@router.post("/jobs/{job_id}/replay", response_model=JobResponse)
def replay_job(
    job_id: str,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[BackgroundJobService, Depends(get_background_job_service)],
) -> JobResponse:
    try:
        existing_job = service.get_job(job_id)
        if existing_job.workspace_id != auth_context.workspace_id:
            raise BackgroundJobNotFoundError(job_id)
        job = service.replay_job(job_id=job_id, replayed_by_user_id=auth_context.user_id)
        return service.to_response(job)
    except BackgroundJobNotFoundError:
        raise BackgroundJobNotFoundApiError(details={"job_id": job_id})
    except JobNotReplayableApiError:
        raise
    except ResourceLockedApiError:
        raise
    except Exception as exc:
        raise ReplayFailedApiError(details={"job_id": job_id}) from exc
