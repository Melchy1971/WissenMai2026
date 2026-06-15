from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_admin, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError
from app.db.session import get_session
from app.models.analysis import ANALYSIS_JOB_STATUS_VALUES
from app.schemas.analysis import (
    AnalysisJobListResponse,
    AnalysisJobResponse,
    AnalysisResult,
    ApproveRequest,
    CompareRequest,
    CreateAnalysisJobRequest,
    SummarizeRequest,
)
from app.services.analysis.service import AnalysisService


router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_analysis_service(session: Annotated[Session, Depends(get_db_session)]) -> AnalysisService:
    return AnalysisService(session)


@router.get("/jobs", response_model=AnalysisJobListResponse)
def list_analysis_jobs(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> AnalysisJobListResponse:
    if status_filter is not None and status_filter not in ANALYSIS_JOB_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {ANALYSIS_JOB_STATUS_VALUES}",
        )
    return service.list_jobs(
        workspace_id=auth.workspace_id,
        limit=limit,
        offset=offset,
        status=status_filter,
    )


@router.post("/jobs", response_model=AnalysisJobResponse, status_code=status.HTTP_201_CREATED)
def create_analysis_job(
    request: CreateAnalysisJobRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.create_job(workspace_id=auth.workspace_id, user_id=auth.user_id, request=request)


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.get_job(workspace_id=auth.workspace_id, job_id=job_id)


@router.post("/jobs/{job_id}/compare", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def compare_analysis_job(
    job_id: str,
    request: CompareRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.compare_job(workspace_id=auth.workspace_id, job_id=job_id, request=request)


@router.post("/jobs/{job_id}/summarize", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def summarize_analysis_job(
    job_id: str,
    request: SummarizeRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisJobResponse:
    return service.summarize_job(workspace_id=auth.workspace_id, job_id=job_id, request=request)


@router.post("/jobs/{job_id}/approve", response_model=AnalysisJobResponse)
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


@router.get("/jobs/{job_id}/result", response_model=AnalysisResult)
def get_analysis_result(
    job_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResult:
    return service.get_result(workspace_id=auth.workspace_id, job_id=job_id)
