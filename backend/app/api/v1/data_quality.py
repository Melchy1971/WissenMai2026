"""Data Quality Read-Only API — V1.

All endpoints are read-only. No mutations.
Auth required. Results are scoped to the authenticated workspace.

Endpoints:
  GET /data-quality/runs              — paginated run list
  GET /data-quality/runs/{run_id}     — single run detail
  GET /data-quality/findings          — paginated findings with filters
  GET /data-quality/summary           — workspace quality summary
"""
from __future__ import annotations

from typing import Annotated, Iterator, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError
from app.db.session import get_session
from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.schemas.data_quality import (
    DataQualityFindingItem,
    DataQualityFindingListResponse,
    DataQualityRunDetail,
    DataQualityRunListResponse,
    DataQualityRunSummary,
    DataQualitySummary,
)


router = APIRouter(prefix="/data-quality", tags=["data-quality"])

_FINDINGS_MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /data-quality/runs
# ---------------------------------------------------------------------------

@router.get("/runs", response_model=DataQualityRunListResponse)
def list_runs(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DataQualityRunListResponse:
    wid = auth.workspace_id
    base = select(DataQualityRun).where(DataQualityRun.workspace_id == wid)

    total = session.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    rows = session.scalars(
        base.order_by(DataQualityRun.started_at.desc()).limit(limit).offset(offset)
    ).all()

    return DataQualityRunListResponse(
        items=[_run_to_summary(r) for r in rows],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /data-quality/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}", response_model=DataQualityRunDetail)
def get_run(
    run_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
) -> DataQualityRunDetail:
    run = session.get(DataQualityRun, run_id)
    if run is None or run.workspace_id != auth.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    counts_rows = session.execute(
        select(DataQualityFinding.finding_type, func.count())
        .where(DataQualityFinding.run_id == run_id)
        .group_by(DataQualityFinding.finding_type)
    ).all()
    finding_counts = {row[0]: row[1] for row in counts_rows}

    return DataQualityRunDetail(
        **_run_to_summary(run).model_dump(),
        finding_counts=finding_counts,
    )


# ---------------------------------------------------------------------------
# GET /data-quality/findings
# ---------------------------------------------------------------------------

@router.get("/findings", response_model=DataQualityFindingListResponse)
def list_findings(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
    run_id: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query(pattern="^(error|warning|info)$")] = None,
    finding_type: Annotated[str | None, Query(max_length=64)] = None,
    document_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_FINDINGS_MAX_LIMIT)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DataQualityFindingListResponse:
    wid = auth.workspace_id
    base = select(DataQualityFinding).where(DataQualityFinding.workspace_id == wid)

    if run_id is not None:
        base = base.where(DataQualityFinding.run_id == run_id)
    if severity is not None:
        base = base.where(DataQualityFinding.severity == severity)
    if finding_type is not None:
        base = base.where(DataQualityFinding.finding_type == finding_type)
    if document_id is not None:
        base = base.where(DataQualityFinding.document_id == document_id)

    total = session.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    rows = session.scalars(
        base.order_by(DataQualityFinding.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return DataQualityFindingListResponse(
        items=[_finding_to_item(f) for f in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /data-quality/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DataQualitySummary)
def get_summary(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
) -> DataQualitySummary:
    wid = auth.workspace_id

    total_runs = session.scalar(
        select(func.count(DataQualityRun.id)).where(DataQualityRun.workspace_id == wid)
    ) or 0

    latest_run = session.scalar(
        select(DataQualityRun)
        .where(DataQualityRun.workspace_id == wid)
        .order_by(DataQualityRun.started_at.desc())
        .limit(1)
    )

    total_findings = session.scalar(
        select(func.count(DataQualityFinding.id))
        .where(DataQualityFinding.workspace_id == wid)
    ) or 0

    severity_rows = session.execute(
        select(DataQualityFinding.severity, func.count())
        .where(DataQualityFinding.workspace_id == wid)
        .group_by(DataQualityFinding.severity)
    ).all()
    findings_by_severity = {row[0]: row[1] for row in severity_rows}

    type_rows = session.execute(
        select(DataQualityFinding.finding_type, func.count())
        .where(DataQualityFinding.workspace_id == wid)
        .group_by(DataQualityFinding.finding_type)
    ).all()
    findings_by_type = {row[0]: row[1] for row in type_rows}

    return DataQualitySummary(
        workspace_id=wid,
        latest_run_id=latest_run.id if latest_run else None,
        latest_run_status=latest_run.status if latest_run else None,
        latest_run_at=latest_run.started_at if latest_run else None,
        latest_quality_score=latest_run.quality_score if latest_run else None,
        total_runs=total_runs,
        total_findings=total_findings,
        findings_by_severity=findings_by_severity,
        findings_by_type=findings_by_type,
    )


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------

def _run_to_summary(run: DataQualityRun) -> DataQualityRunSummary:
    return DataQualityRunSummary(
        run_id=run.id,
        workspace_id=run.workspace_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        total_findings=run.total_findings,
        quality_score=run.quality_score,
        created_by=run.created_by,
    )


def _finding_to_item(f: DataQualityFinding) -> DataQualityFindingItem:
    return DataQualityFindingItem(
        finding_id=f.id,
        run_id=f.run_id,
        workspace_id=f.workspace_id,
        finding_type=f.finding_type,
        severity=f.severity,
        document_id=f.document_id,
        version_id=f.version_id,
        chunk_id=f.chunk_id,
        title=f.title,
        description=f.description,
        remediation=f.remediation,
        created_at=f.created_at,
    )
