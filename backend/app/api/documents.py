from dataclasses import dataclass
from time import perf_counter
from typing import Annotated, Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.core.config import settings
from app.core.database import DatabaseConfigurationError
from app.core.errors import (
    ApiError,
    BackgroundJobNotFoundApiError,
    DocumentAlreadyArchivedApiError,
    DocumentAlreadyDeletedApiError,
    DocumentNotFoundApiError,
    DocumentStateConflictApiError,
    FileTooLargeApiError,
    InvalidLifecycleTransitionApiError,
    InvalidLifecycleStatusApiError,
)
from app.db.session import get_session
from app.observability.logging import bind_observability_context, log_event, log_import_event
from app.schemas.documents import (
    DocumentChunkPreview,
    DocumentDetail,
    DocumentImportRecoveryResponse,
    DocumentLifecycleResponse,
    DocumentListItem,
    DocumentVersionSummary,
)
from app.schemas.jobs import JobResponse
from app.services.documents.import_executor import canonical_mime_type, parser_type_from_mime_type
from app.services.documents.lifecycle_service import (
    DocumentAlreadyArchivedError,
    DocumentAlreadyDeletedError,
    DocumentLifecycleConflictError,
    DocumentLifecycleNotFoundError,
    DocumentLifecycleService,
    InvalidLifecycleTransitionError,
)
from app.services.documents.import_recovery_service import (
    DocumentImportRecoveryConflictError,
    DocumentImportRecoveryNotFoundError,
    DocumentImportRecoveryService,
)
from app.services.documents.read_service import DocumentNotFoundError, DocumentReadService, DocumentStateConflictError
from app.services.jobs.background_jobs import BackgroundJobNotFoundError, BackgroundJobService, process_import_job


router = APIRouter(prefix="/documents", tags=["documents"])
UPLOAD_READ_CHUNK_SIZE = 1024 * 1024


def get_document_read_service() -> Iterator[DocumentReadService]:
    try:
        for session in get_session():
            yield DocumentReadService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_document_lifecycle_service() -> Iterator[DocumentLifecycleService]:
    try:
        for session in get_session():
            yield DocumentLifecycleService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_background_job_service() -> Iterator[BackgroundJobService]:
    try:
        for session in get_session():
            yield BackgroundJobService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_document_import_recovery_service() -> Iterator[DocumentImportRecoveryService]:
    try:
        for session in get_session():
            yield DocumentImportRecoveryService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


async def read_upload_with_size_limit(file: UploadFile, *, max_upload_size_bytes: int) -> bytes:
    chunks: list[bytes] = []
    actual_size_bytes = 0

    while True:
        chunk = await file.read(UPLOAD_READ_CHUNK_SIZE)
        if not chunk:
            break
        actual_size_bytes += len(chunk)
        if actual_size_bytes > max_upload_size_bytes:
            raise FileTooLargeApiError(
                details={
                    "max_upload_size_bytes": max_upload_size_bytes,
                    "actual_size_bytes": actual_size_bytes,
                }
            )
        chunks.append(chunk)

    return b"".join(chunks)


@router.get("", response_model=list[DocumentListItem])
def list_documents(
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentReadService, Depends(get_document_read_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    lifecycle_status: Annotated[str | None, Query()] = None,
    include_archived: bool = False,
) -> list[DocumentListItem]:
    try:
        if lifecycle_status not in {None, "active", "archived", "deleted"}:
            raise InvalidLifecycleStatusApiError(details={"lifecycle_status": lifecycle_status})
        return service.get_documents(
            workspace_id=auth_context.workspace_id,
            limit=limit,
            offset=offset,
            lifecycle_status=lifecycle_status,
            include_archived=include_archived,
        )
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentReadService, Depends(get_document_read_service)],
) -> DocumentDetail:
    try:
        return service.get_document_detail(document_id, workspace_id=auth_context.workspace_id)
    except DocumentNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DocumentStateConflictError as exc:
        raise DocumentStateConflictApiError(message=str(exc), details={"document_id": document_id}) from exc
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


@router.get("/{document_id}/versions", response_model=list[DocumentVersionSummary])
def list_document_versions(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentReadService, Depends(get_document_read_service)],
) -> list[DocumentVersionSummary]:
    try:
        return service.get_versions(document_id, workspace_id=auth_context.workspace_id)
    except DocumentNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkPreview])
def list_document_chunks(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentReadService, Depends(get_document_read_service)],
    limit: Annotated[int | None, Query(ge=1, le=500)] = None,
) -> list[DocumentChunkPreview]:
    try:
        return service.get_chunks(document_id, workspace_id=auth_context.workspace_id, limit=limit)
    except DocumentNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


@router.patch("/{document_id}/archive", response_model=DocumentLifecycleResponse)
def archive_document(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentLifecycleService, Depends(get_document_lifecycle_service)],
) -> DocumentLifecycleResponse:
    try:
        document = service.archive(document_id, workspace_id=auth_context.workspace_id)
    except DocumentLifecycleNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DocumentAlreadyArchivedError as exc:
        raise DocumentAlreadyArchivedApiError(message=str(exc), details={"document_id": document_id}) from exc
    except DocumentAlreadyDeletedError as exc:
        raise DocumentAlreadyDeletedApiError(message=str(exc), details={"document_id": document_id}) from exc
    except InvalidLifecycleTransitionError as exc:
        raise InvalidLifecycleTransitionApiError(message=str(exc), details={"document_id": document_id}) from exc
    except DocumentLifecycleConflictError as exc:
        raise DocumentStateConflictApiError(message=str(exc), details={"document_id": document_id}) from exc
    return DocumentLifecycleResponse(
        document_id=document.id,
        lifecycle_status=document.lifecycle_status,
        archived_at=document.archived_at,
        deleted_at=document.deleted_at,
    )


@router.patch("/{document_id}/restore", response_model=DocumentLifecycleResponse)
def restore_document(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentLifecycleService, Depends(get_document_lifecycle_service)],
) -> DocumentLifecycleResponse:
    try:
        document = service.restore(document_id, workspace_id=auth_context.workspace_id)
    except DocumentLifecycleNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DocumentAlreadyDeletedError as exc:
        raise DocumentAlreadyDeletedApiError(message=str(exc), details={"document_id": document_id}) from exc
    except InvalidLifecycleTransitionError as exc:
        raise InvalidLifecycleTransitionApiError(message=str(exc), details={"document_id": document_id}) from exc
    except DocumentLifecycleConflictError as exc:
        raise DocumentStateConflictApiError(message=str(exc), details={"document_id": document_id}) from exc
    return DocumentLifecycleResponse(
        document_id=document.id,
        lifecycle_status=document.lifecycle_status,
        archived_at=document.archived_at,
        deleted_at=document.deleted_at,
    )


@router.delete("/{document_id}", response_model=DocumentLifecycleResponse)
def delete_document(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentLifecycleService, Depends(get_document_lifecycle_service)],
) -> DocumentLifecycleResponse:
    try:
        document = service.delete(document_id, workspace_id=auth_context.workspace_id)
    except DocumentLifecycleNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DocumentAlreadyDeletedError as exc:
        raise DocumentAlreadyDeletedApiError(message=str(exc), details={"document_id": document_id}) from exc
    except InvalidLifecycleTransitionError as exc:
        raise InvalidLifecycleTransitionApiError(message=str(exc), details={"document_id": document_id}) from exc
    except DocumentLifecycleConflictError as exc:
        raise DocumentStateConflictApiError(message=str(exc), details={"document_id": document_id}) from exc
    return DocumentLifecycleResponse(
        document_id=document.id,
        lifecycle_status=document.lifecycle_status,
        archived_at=document.archived_at,
        deleted_at=document.deleted_at,
    )


@router.post("/{document_id}/retry-import", response_model=DocumentImportRecoveryResponse)
def retry_document_import(
    document_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DocumentImportRecoveryService, Depends(get_document_import_recovery_service)],
) -> DocumentImportRecoveryResponse:
    try:
        result = service.retry_import(document_id=document_id, workspace_id=auth_context.workspace_id)
    except DocumentImportRecoveryNotFoundError as exc:
        raise DocumentNotFoundApiError(details={"document_id": document_id}) from exc
    except DocumentImportRecoveryConflictError as exc:
        raise DocumentStateConflictApiError(message=str(exc), details={"document_id": document_id}) from exc
    return DocumentImportRecoveryResponse.model_validate(result)


@router.post("/import", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)] = None,
    job_service: Annotated[BackgroundJobService, Depends(get_background_job_service)] = None,
) -> JobResponse:
    start_time = perf_counter()
    bind_observability_context(workspace_id=auth_context.workspace_id, user_id=auth_context.user_id)
    filename = file.filename or "untitled"
    mime_type = canonical_mime_type(filename, file.content_type)
    try:
        source_bytes = await read_upload_with_size_limit(file, max_upload_size_bytes=settings.max_upload_size_bytes)
    except FileTooLargeApiError:
        duration_ms = int((perf_counter() - start_time) * 1000)
        log_import_event(
            "import_failed",
            document_id=None,
            workspace_id=auth_context.workspace_id,
            duration_ms=duration_ms,
            parser_type=parser_type_from_mime_type(mime_type),
            chunk_count=0,
            status="failed",
            error_code="FILE_TOO_LARGE",
        )
        raise
    log_import_event(
        "upload_received",
        document_id=None,
        workspace_id=auth_context.workspace_id,
        duration_ms=int((perf_counter() - start_time) * 1000),
        parser_type=parser_type_from_mime_type(mime_type),
        chunk_count=0,
        status="received",
    )
    temp_file_path = BackgroundJobService.create_temp_upload_file(filename=filename, source_bytes=source_bytes)
    job = job_service.enqueue_import_job(
        workspace_id=auth_context.workspace_id,
        requested_by_user_id=auth_context.user_id,
        filename=filename,
        mime_type=mime_type,
        temp_file_path=temp_file_path,
    )
    background_tasks.add_task(process_import_job, job.id, job_service._session.get_bind())
    return job_service.to_response(job)


@router.get("/import-jobs/{job_id}", response_model=JobResponse)
def get_import_job(
    job_id: str,
    auth_context: Annotated[AuthContext, Depends(require_workspace_member)],
    job_service: Annotated[BackgroundJobService, Depends(get_background_job_service)],
) -> JobResponse:
    try:
        job = job_service.get_job(job_id)
        if job.workspace_id != auth_context.workspace_id:
            raise BackgroundJobNotFoundError(job_id)
        return job_service.to_response(job)
    except BackgroundJobNotFoundError as exc:
        raise BackgroundJobNotFoundApiError(details={"job_id": job_id}) from exc
