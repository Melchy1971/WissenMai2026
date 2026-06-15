"""Workspace-scoped read-only Dashboard V3 endpoints."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.dashboard import (
    DashboardActivityResponse,
    DashboardAnalysisResponse,
    DashboardImportsResponse,
    DashboardQualityResponse,
    DashboardSummary,
    DashboardTopicsResponse,
)
from app.services.dashboard_service import DashboardSummaryService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_dashboard_summary_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> DashboardSummaryService:
    return DashboardSummaryService(session)


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    ctx: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DashboardSummaryService, Depends(get_dashboard_summary_service)],
) -> DashboardSummary:
    return service.get_summary(workspace_id=ctx.workspace_id)


@router.get("/activity", response_model=DashboardActivityResponse)
def dashboard_activity(
    ctx: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DashboardSummaryService, Depends(get_dashboard_summary_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardActivityResponse:
    return service.list_activity(workspace_id=ctx.workspace_id, limit=limit)


@router.get("/imports", response_model=DashboardImportsResponse)
def dashboard_imports(
    ctx: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DashboardSummaryService, Depends(get_dashboard_summary_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardImportsResponse:
    return service.list_imports(workspace_id=ctx.workspace_id, limit=limit)


@router.get("/analysis", response_model=DashboardAnalysisResponse)
def dashboard_analysis(
    ctx: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DashboardSummaryService, Depends(get_dashboard_summary_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardAnalysisResponse:
    return service.list_analysis(workspace_id=ctx.workspace_id, limit=limit)


@router.get("/quality", response_model=DashboardQualityResponse)
def dashboard_quality(
    ctx: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DashboardSummaryService, Depends(get_dashboard_summary_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardQualityResponse:
    return service.list_quality(workspace_id=ctx.workspace_id, limit=limit)


@router.get("/topics", response_model=DashboardTopicsResponse)
def dashboard_topics(
    ctx: Annotated[AuthContext, Depends(require_workspace_member)],
    service: Annotated[DashboardSummaryService, Depends(get_dashboard_summary_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> DashboardTopicsResponse:
    return service.list_topics(workspace_id=ctx.workspace_id, limit=limit)
