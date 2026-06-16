"""REST API for Analysis Jobs and Results.

Endpoints (v2):
  GET    /analysis/jobs                           list_analysis_jobs
  POST   /analysis/jobs                           create_analysis_job
  GET    /analysis/jobs/{job_id}                  get_analysis_job
  POST   /analysis/jobs/{job_id}/cancel           cancel_analysis_job
  POST   /analysis/jobs/{job_id}/retry            retry_analysis_job
  POST   /analysis/jobs/{job_id}/compare          compare_analysis_job  (legacy)
  POST   /analysis/jobs/{job_id}/summarize        summarize_analysis_job (legacy)
  POST   /analysis/jobs/{job_id}/approve          approve_analysis_job  (legacy)
  GET    /analysis/jobs/{job_id}/result           get_result_by_job     (legacy)

  GET    /analysis/results/{result_id}            get_analysis_result
  PATCH  /analysis/results/{result_id}            update_analysis_result
  POST   /analysis/results/{result_id}/review     mark_result_for_review
  POST   /analysis/results/{result_id}/approve    approve_analysis_result
  POST   /analysis/results/{result_id}/reject     reject_analysis_result

Pagination: limit (1–100, default 20), offset (≥0, default 0).
Status filter: ?status=<value>  Source type filter: ?source_type=<value>
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_admin, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import (
    AnalysisConfirmRequiredApiError,
    AnalysisResultInvalidStateApiError,
    AnalysisResultNotFoundApiError,
    AnalysisRetryLimitExceededApiError,
    AnalysisSourceRequiredApiError,
    ApiError,
)
from app.db.session import get_session
from app.models.analysis import ANALYSIS_JOB_SOURCE_TYPE_VALUES, ANALYSIS_JOB_STATUS_VALUES
from app.schemas.analysis import (
    AnalysisJobListResponse,
    AnalysisJobResponse,
    AnalysisResult as AnalysisResultSchema,
    ApproveRequest,
    ApproveResultRequest,
    CompareRequest,
    CreateAnalysisJobRequest,
    ImportAnalysisResultResponse,
    MarkForReviewRequest,
    RejectResultRequest,
    SummarizeRequest,
    UpdateAnalysisResultRequest,
)
from app.services.analysis.service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ── Dependencies ──────────────────────────────────────────────────────────────

def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_analysis_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AnalysisService:
    return AnalysisService(session)


# ── Job endpoints ─────────────────────────────────────────────────────────────

@router.get(
    "/jobs",
    response_model=AnalysisJobListResponse,
    summary="List analysis jobs",
    responses={
        200: {"description": "Paginated job list"},
        422: {"description": "Invalid status or source_type filter value"},
    },
)
def list_analysis_jobs(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by job status")
    ] = None,
    source_type: Annotated[
        str | None, Query(description="Filter by source type (DOCUMENTS, TOPIC, SEARCH_RESULT)")
    ] = None,
) -> AnalysisJobListResponse:
    if status_filter is not None and status_filter not in ANALYSIS_JOB_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {list(ANALYSIS_JOB_STATUS_VALUES)}",
        )
    if source_type is not None and source_type not in ANALYSIS_JOB_SOURCE_TYPE_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid source_type. Allowed: {list(ANALYSIS_JOB_SOURCE_TYPE_VALUES)}",
        )
    return service.list_jobs(
        workspace_id=auth.workspace_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        source_type=source_type,
    )


@router.post(
    "/jobs",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create analysis job",
    responses={
        201: {"description": "Job created"},
        422: {"description": "source_document_ids required or invalid payload"},
    },
)
def create_analysis_job(
    request: CreateAnalysisJobRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    try:
        return service.create_job(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            request=request,
        )
    except AnalysisSourceRequiredApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/jobs/{job_id}",
    response_model=AnalysisJobResponse,
    summary="Get analysis job",
    responses={
        200: {"description": "Job with nested result, comparison, suggestions"},
        404: {"description": "Job not found"},
    },
)
def get_analysis_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.get_job(workspace_id=auth.workspace_id, job_id=job_id)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=AnalysisJobResponse,
    summary="Cancel analysis job",
    responses={
        200: {"description": "Job cancelled"},
        404: {"description": "Job not found"},
        409: {"description": "Job is in a terminal state and cannot be cancelled"},
    },
)
def cancel_analysis_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    from app.core.errors import AnalysisJobInvalidStateApiError
    try:
        return service.cancel_job(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            job_id=job_id,
        )
    except AnalysisJobInvalidStateApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/jobs/{job_id}/retry",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Retry failed or cancelled analysis job",
    responses={
        201: {"description": "New queued job created"},
        404: {"description": "Job not found"},
        409: {"description": "Job is not retryable or retry limit exceeded"},
    },
)
def retry_analysis_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    from app.core.errors import AnalysisJobInvalidStateApiError
    try:
        return service.retry_job(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            job_id=job_id,
        )
    except (AnalysisRetryLimitExceededApiError, AnalysisJobInvalidStateApiError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# ── Result endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/results/{result_id}",
    response_model=AnalysisResultSchema,
    summary="Get analysis result by ID",
    responses={
        200: {"description": "Analysis result"},
        404: {"description": "Result not found or not in caller's workspace"},
    },
)
def get_analysis_result(
    result_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResultSchema:
    try:
        return service.get_result_by_id(
            workspace_id=auth.workspace_id,
            result_id=result_id,
        )
    except AnalysisResultNotFoundApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch(
    "/results/{result_id}",
    response_model=AnalysisResultSchema,
    summary="Update analysis result (draft or review only)",
    responses={
        200: {"description": "Updated result"},
        404: {"description": "Result not found"},
        409: {"description": "Result is not in an editable state (approved or rejected)"},
    },
)
def update_analysis_result(
    result_id: str,
    request: UpdateAnalysisResultRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResultSchema:
    try:
        return service.update_result(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            result_id=result_id,
            request=request,
        )
    except (AnalysisResultNotFoundApiError, AnalysisResultInvalidStateApiError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/results/{result_id}/review",
    response_model=AnalysisResultSchema,
    summary="Mark result for review (draft → review)",
    responses={
        200: {"description": "Result marked for review"},
        404: {"description": "Result not found"},
        409: {"description": "Result is not in draft status"},
    },
)
def mark_result_for_review(
    result_id: str,
    request: MarkForReviewRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResultSchema:
    try:
        return service.mark_result_for_review(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            result_id=result_id,
            request=request,
        )
    except (AnalysisResultNotFoundApiError, AnalysisResultInvalidStateApiError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/results/{result_id}/approve",
    response_model=AnalysisResultSchema,
    summary="Approve analysis result (review → approved). Requires confirm=true.",
    responses={
        200: {"description": "Result approved"},
        404: {"description": "Result not found"},
        409: {"description": "Result is not in review status"},
        422: {"description": "confirm must be true"},
    },
)
def approve_analysis_result(
    result_id: str,
    request: ApproveResultRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResultSchema:
    try:
        return service.approve_result(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            actor_role=auth.role,
            result_id=result_id,
            request=request,
        )
    except AnalysisConfirmRequiredApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except (AnalysisResultNotFoundApiError, AnalysisResultInvalidStateApiError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/results/{result_id}/reject",
    response_model=AnalysisResultSchema,
    summary="Reject analysis result (review → rejected)",
    responses={
        200: {"description": "Result rejected"},
        404: {"description": "Result not found"},
        409: {"description": "Result is not in review status"},
        422: {"description": "reason is required"},
    },
)
def reject_analysis_result(
    result_id: str,
    request: RejectResultRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResultSchema:
    try:
        return service.reject_result(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            actor_role=auth.role,
            result_id=result_id,
            request=request,
        )
    except (AnalysisResultNotFoundApiError, AnalysisResultInvalidStateApiError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc



@router.post(
    "/results/{result_id}/import",
    response_model=ImportAnalysisResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Import approved analysis result into knowledge base",
    responses={
        200: {"description": "Import summary: topics and tags created/linked, documents tagged"},
        404: {"description": "Result not found"},
        409: {"description": "Result is not approved — import blocked"},
    },
)
def import_analysis_result(
    result_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> ImportAnalysisResultResponse:
    try:
        stats = service.import_result(
            workspace_id=auth.workspace_id,
            user_id=auth.user_id,
            result_id=result_id,
        )
        return ImportAnalysisResultResponse(
            result_id=stats.result_id,
            tags_created=stats.tags_created,
            tags_found=stats.tags_found,
            document_tags_applied=stats.document_tags_applied,
            topics_created=stats.topics_created,
            topics_found=stats.topics_found,
            topic_docs_attached=stats.topic_docs_attached,
            topic_tags_applied=stats.topic_tags_applied,
            source_document_count=stats.source_document_count,
        )
    except AnalysisResultNotFoundApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except AnalysisResultInvalidStateApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# ── Legacy endpoints (backward compat) ───────────────────────────────────────

@router.post(
    "/jobs/{job_id}/compare",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[Legacy] Compare job with existing documents",
    tags=["analysis", "legacy"],
)
def compare_analysis_job(
    job_id: str,
    request: CompareRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.compare_job(workspace_id=auth.workspace_id, job_id=job_id, request=request)


@router.post(
    "/jobs/{job_id}/summarize",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[Legacy] Summarize job",
    tags=["analysis", "legacy"],
)
def summarize_analysis_job(
    job_id: str,
    request: SummarizeRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.summarize_job(workspace_id=auth.workspace_id, job_id=job_id, request=request)


@router.post(
    "/jobs/{job_id}/approve",
    response_model=AnalysisJobResponse,
    summary="[Legacy] Approve job (job-level approval)",
    tags=["analysis", "legacy"],
)
def approve_analysis_job(
    job_id: str,
    request: ApproveRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.approve_job(
        workspace_id=auth.workspace_id,
        user_id=auth.user_id,
        job_id=job_id,
        request=request,
    )


@router.get(
    "/jobs/{job_id}/result",
    response_model=AnalysisResultSchema,
    summary="[Legacy] Get result by job ID",
    tags=["analysis", "legacy"],
)
def get_result_by_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResultSchema:
    retur