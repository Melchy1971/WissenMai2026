"""REST API for Export Center.

Endpoints:
  GET    /export/jobs                           list_export_jobs
  POST   /export/jobs                           create_export_job
  GET    /export/jobs/{job_id}                  get_export_job
  POST   /export/jobs/{job_id}/start            start_export_job
  POST   /export/jobs/{job_id}/cancel           cancel_export_job
  POST   /export/jobs/{job_id}/retry            retry_export_job
  GET    /export/jobs/{job_id}/download         download_export_file
  DELETE /export/jobs/{job_id}/file             delete_export_file

  GET    /export/templates                      list_export_templates
  POST   /export/templates                      create_export_template
  PUT    /export/templates/{template_id}        update_export_template
  DELETE /export/templates/{template_id}        delete_export_template

Pagination: limit (1–100, default 20), offset (≥0, default 0).
Filter: ?status=<value>  ?format=<value>
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import (
    ApiError,
    ExportFileNotFoundApiError,
    ExportJobInvalidStateApiError,
    ExportJobNotFoundApiError,
    ExportSourceNotApprovedApiError,
    ExportSourceNotFoundApiError,
    ExportTemplateNameConflictApiError,
    ExportTemplateNotFoundApiError,
)
from app.db.session import get_session
from app.models.export import EXPORT_FORMAT_VALUES, EXPORT_JOB_STATUS_VALUES, EXPORT_SOURCE_TYPE_VALUES
from app.schemas.export import (
    CreateExportJobRequest,
    CreateExportTemplateRequest,
    ExportJobListResponse,
    ExportJobResponse,
    ExportTemplateListResponse,
    ExportTemplateResponse,
    UpdateExportTemplateRequest,
)
from app.services.export.service import ExportService
from app.repositories.export import ExportJobRecord, ExportTemplateRecord

router = APIRouter(prefix="/export", tags=["export"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_export_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ExportService:
    return ExportService(session)


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------

def _job_response(record: ExportJobRecord) -> ExportJobResponse:
    return ExportJobResponse(
        id=record.id,
        workspace_id=record.workspace_id,
        status=record.status,  # type: ignore[arg-type]
        source_type=record.source_type,  # type: ignore[arg-type]
        source_ids=list(record.source_ids) if record.source_ids else None,
        export_format=record.export_format,  # type: ignore[arg-type]
        file_name=record.file_name,
        file_path=record.file_path,
        error_message=record.error_message,
        created_by=record.created_by,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )


def _template_response(record: ExportTemplateRecord) -> ExportTemplateResponse:
    return ExportTemplateResponse(
        id=record.id,
        name=record.name,
        export_format=record.export_format,  # type: ignore[arg-type]
        layout_config=record.layout_config,
        is_default=record.is_default,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ---------------------------------------------------------------------------
# Job endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/jobs",
    response_model=ExportJobListResponse,
    summary="List export jobs",
    responses={
        200: {"description": "Paginated export job list"},
        422: {"description": "Invalid filter value"},
    },
)
def list_export_jobs(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by job status")
    ] = None,
    format_filter: Annotated[
        str | None, Query(alias="format", description="Filter by export format")
    ] = None,
) -> ExportJobListResponse:
    if status_filter is not None and status_filter not in EXPORT_JOB_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {list(EXPORT_JOB_STATUS_VALUES)}",
        )
    if format_filter is not None and format_filter not in EXPORT_FORMAT_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid format. Allowed: {list(EXPORT_FORMAT_VALUES)}",
        )
    jobs, total = service.list_export_jobs(
        workspace_id=auth.workspace_id,
        status=status_filter,
        export_format=format_filter,
        limit=limit,
        offset=offset,
    )
    return ExportJobListResponse(
        items=[_job_response(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/jobs",
    response_model=ExportJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create export job",
    responses={
        201: {"description": "Export job created"},
        404: {"description": "Source not found"},
        422: {"description": "Draft analysis cannot be exported"},
    },
)
def create_export_job(
    request: CreateExportJobRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportJobResponse:
    try:
        record = service.create_export_job(
            workspace_id=auth.workspace_id,
            source_type=request.source_type,
            source_ids=list(request.source_ids),
            export_format=request.export_format,
            file_name=request.file_name,
            created_by=auth.user_id,
        )
        return _job_response(record)
    except ExportSourceNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ExportSourceNotApprovedApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc


@router.get(
    "/jobs/{job_id}",
    response_model=ExportJobResponse,
    summary="Get export job",
    responses={
        200: {"description": "Export job"},
        404: {"description": "Job not found"},
    },
)
def get_export_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportJobResponse:
    try:
        return _job_response(service.get_export_job(job_id))
    except ExportJobNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.post(
    "/jobs/{job_id}/start",
    response_model=ExportJobResponse,
    summary="Start export job",
    responses={
        200: {"description": "Job started and completed"},
        404: {"description": "Job not found"},
        409: {"description": "Job not in QUEUED state"},
    },
)
def start_export_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportJobResponse:
    try:
        return _job_response(service.start_export_job(job_id))
    except ExportJobNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ExportJobInvalidStateApiError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ExportSourceNotApprovedApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=ExportJobResponse,
    summary="Cancel export job",
    responses={
        200: {"description": "Job cancelled"},
        404: {"description": "Job not found"},
        409: {"description": "Job cannot be cancelled in current state"},
    },
)
def cancel_export_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportJobResponse:
    try:
        return _job_response(service.cancel_export_job(job_id))
    except ExportJobNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ExportJobInvalidStateApiError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ExportJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Retry export job",
    responses={
        201: {"description": "New queued job created"},
        404: {"description": "Job not found"},
        409: {"description": "Job cannot be retried in current state"},
    },
)
def retry_export_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportJobResponse:
    try:
        return _job_response(service.retry_export_job(job_id))
    except ExportJobNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ExportJobInvalidStateApiError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.get(
    "/jobs/{job_id}/download",
    summary="Download export file",
    response_class=Response,
    responses={
        200: {"description": "File bytes", "content": {"application/octet-stream": {}}},
        404: {"description": "Job not found or file not available"},
    },
)
def download_export_file(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> Response:
    try:
        file_bytes, file_name = service.download_export_file(job_id)
    except ExportJobNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ExportFileNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc

    content_type = _content_type_for(file_name)
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Length": str(len(file_bytes)),
        },
    )


@router.delete(
    "/jobs/{job_id}/file",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete export file",
    responses={
        204: {"description": "File deleted"},
        404: {"description": "Job not found"},
    },
)
def delete_export_file(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> None:
    try:
        service.delete_export_file(job_id)
    except ExportJobNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/templates",
    response_model=ExportTemplateListResponse,
    summary="List export templates",
)
def list_export_templates(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
    format_filter: Annotated[
        str | None, Query(alias="format", description="Filter by export format")
    ] = None,
) -> ExportTemplateListResponse:
    if format_filter is not None and format_filter not in EXPORT_FORMAT_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid format. Allowed: {list(EXPORT_FORMAT_VALUES)}",
        )
    templates = service.list_templates(export_format=format_filter)
    return ExportTemplateListResponse(
        items=[_template_response(t) for t in templates],
        total=len(templates),
    )


@router.post(
    "/templates",
    response_model=ExportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create export template",
    responses={
        201: {"description": "Template created"},
        409: {"description": "Template name already in use"},
    },
)
def create_export_template(
    request: CreateExportTemplateRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportTemplateResponse:
    try:
        record = service.create_template(
            name=request.name,
            export_format=request.export_format,
            layout_config=request.layout_config,
            is_default=request.is_default,
        )
        return _template_response(record)
    except ExportTemplateNameConflictApiError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.put(
    "/templates/{template_id}",
    response_model=ExportTemplateResponse,
    summary="Update export template",
    responses={
        200: {"description": "Template updated"},
        404: {"description": "Template not found"},
        409: {"description": "Name already in use"},
    },
)
def update_export_template(
    template_id: str,
    request: UpdateExportTemplateRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportTemplateResponse:
    try:
        record = service.update_template(
            template_id,
            name=request.name,
            export_format=request.export_format,
            layout_config=request.layout_config,
            is_default=request.is_default,
        )
        return _template_response(record)
    except ExportTemplateNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ExportTemplateNameConflictApiError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete export template",
    responses={
        204: {"description": "Template deleted"},
        404: {"description": "Template not found"},
    },
)
def delete_export_template(
    template_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> None:
    try:
        service.delete_template(template_id)
    except ExportTemplateNotFoundApiError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _content_type_for(file_name: str) -> str:
    if file_name.endswith(".pdf"):
        return "application/pdf"
    if file_name.endswith(".json"):
        return "application/json"
    return "text/markdown; charset=utf-8"
