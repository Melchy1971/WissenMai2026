from datetime import UTC, datetime
from typing import Annotated, Any, Iterator

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import RequestAuthContext, require_workspace_admin, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import (
    AdminActionNotImplementedApiError,
    ApiError,
    BackupValidationFailedApiError,
    BackgroundJobNotFoundApiError,
    DiagnosticsFailedApiError,
    ForbiddenApiError,
    JobNotReplayableApiError,
    ReindexConstraintViolationApiError,
    ReplayFailedApiError,
    ResourceLockedApiError,
)
from app.db.session import get_session
from app.schemas.admin import (
    BackupVerificationRequest,
    BackupVerificationResponse,
    CitationLongevityReport,
    CleanupGovernanceReport,
    CleanupGovernanceRequest,
    DiagnosticsResponse,
    QueueAgingReport,
    ReindexGovernanceReport,
    ReindexGovernanceRequest,
    SearchIndexDriftReportResponse,
    SearchIndexInconsistencyReportResponse,
)
from app.schemas.jobs import JobResponse
from app.services.backup_restore import BackupRestoreError, BackupRestoreService
from app.services.citation_longevity_service import CitationLongevityAuditService
from app.services.diagnostics import DiagnosticsService
from app.services.queue_aging_service import QueueAgingService
from app.services.cleanup_governance import CleanupGovernanceService
from app.services.m5_cleanup import CleanupConfig
from app.services.reindex_governance import ReindexGovernanceService, ReindexGovernanceViolation
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


def get_backup_restore_service() -> Iterator[BackupRestoreService]:
    try:
        yield BackupRestoreService()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_citation_longevity_service() -> Iterator[CitationLongevityAuditService]:
    try:
        for session in get_session():
            yield CitationLongevityAuditService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_reindex_governance_service() -> Iterator[ReindexGovernanceService]:
    try:
        for session in get_session():
            yield ReindexGovernanceService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_queue_aging_service() -> Iterator[QueueAgingService]:
    try:
        for session in get_session():
            yield QueueAgingService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_cleanup_governance_service() -> Iterator[CleanupGovernanceService]:
    try:
        for session in get_session():
            yield CleanupGovernanceService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


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


@router.post("/backup/verify", response_model=BackupVerificationResponse)
def verify_backup(
    payload: BackupVerificationRequest,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[BackupRestoreService, Depends(get_backup_restore_service)],
) -> BackupVerificationResponse:
    del auth_context
    try:
        result = service.verify_backup(input_dir=payload.input_dir)
        checked_at = result.get("checked_at")
        if isinstance(checked_at, str):
            result = dict(result)
            result["checked_at"] = datetime.fromisoformat(checked_at)
        return BackupVerificationResponse.model_validate(result)
    except BackupRestoreError as exc:
        raise BackupValidationFailedApiError(details={"message": str(exc), "input_dir": payload.input_dir}) from exc


@router.get("/queue/aging", response_model=QueueAgingReport)
def get_queue_aging(
    auth_context: Annotated[RequestAuthContext, Depends(require_diagnostics_admin)],
    service: Annotated[QueueAgingService, Depends(get_queue_aging_service)],
) -> QueueAgingReport:
    report = service.get_aging_report(workspace_id=auth_context.workspace_id)
    return QueueAgingReport.model_validate(report)


@router.get("/citations/longevity", response_model=CitationLongevityReport)
def get_citation_longevity(
    auth_context: Annotated[RequestAuthContext, Depends(require_diagnostics_admin)],
    service: Annotated[CitationLongevityAuditService, Depends(get_citation_longevity_service)],
) -> CitationLongevityReport:
    report = service.get_longevity_report(workspace_id=auth_context.workspace_id)
    return CitationLongevityReport.model_validate(report)


@router.post("/reindex/governed", response_model=ReindexGovernanceReport)
def run_governed_reindex(
    payload: ReindexGovernanceRequest,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[ReindexGovernanceService, Depends(get_reindex_governance_service)],
) -> ReindexGovernanceReport:
    try:
        report = service.run_governed_reindex(
            reindex_type=payload.reindex_type,
            workspace_id=payload.workspace_id,
            document_id=payload.document_id,
            correlation_id=payload.correlation_id,
            reason=payload.reason,
        )
        return ReindexGovernanceReport.model_validate(report)
    except ReindexGovernanceViolation as exc:
        raise ReindexConstraintViolationApiError(details={"message": str(exc)}) from exc


@router.post("/cleanup/governed", response_model=CleanupGovernanceReport)
def run_governed_cleanup(
    payload: CleanupGovernanceRequest,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[CleanupGovernanceService, Depends(get_cleanup_governance_service)],
) -> CleanupGovernanceReport:
    config = CleanupConfig(
        retention_days=payload.retention_days,
        workspace_id=payload.workspace_id,
        now=datetime.now(UTC),
    )
    result = service.run_governed_cleanup(
        config=config,
        dry_run_only=payload.dry_run_only,
        correlation_id=payload.correlation_id,
    )
    return CleanupGovernanceReport.model_validate(result)


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
