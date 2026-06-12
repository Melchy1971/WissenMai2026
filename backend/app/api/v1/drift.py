"""Drift Detection Read-Only API — V1.

All endpoints are read-only (GET only). No POST/PUT/PATCH/DELETE.
No repair actions. No cleanup actions. No auto-reindex.
Auth required. Results are workspace-scoped.

Invariant: Drift Detection darf nur erkennen, nie korrigieren.

Endpoints:
  GET /drift/runs              — paginated run list
  GET /drift/runs/{run_id}     — single run detail with finding counts
  GET /drift/findings          — paginated findings with severity/type filter
  GET /drift/summary           — workspace drift summary
"""
from __future__ import annotations

from collections import Counter
from typing import Annotated, Iterator, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError
from app.db.session import get_session
from app.models.drift import (
    DRIFT_FINDING_TYPES,
    DRIFT_SEVERITY_VALUES,
    DriftFinding,
    DriftRun,
)
from app.schemas.drift import (
    DriftFindingItem,
    DriftFindingListResponse,
    DriftRunDetail,
    DriftRunListResponse,
    DriftRunSummary,
    DriftSummary,
)


router = APIRouter(prefix="/drift", tags=["drift"])

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
# GET /drift/runs
# ---------------------------------------------------------------------------

@router.get("/runs", response_model=DriftRunListResponse)
def list_drift_runs(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> DriftRunListResponse:
    """List drift runs for the authenticated workspace. Newest first."""
    ws_id = auth.workspace_id

    base_q = select(DriftRun).where(DriftRun.workspace_id == ws_id)
    if status_filter is not None:
        base_q = base_q.where(DriftRun.status == status_filter)

    total: int = session.scalar(
        select(func.count()).select_from(base_q.subquery())
    ) or 0

    rows = session.scalars(
        base_q.order_by(DriftRun.created_at.desc()).offset(offset).limit(limit)
    ).all()

    items = [
        DriftRunSummary(
            run_id=r.id,
            workspace_id=r.workspace_id,
            status=r.status,
            triggered_by=r.triggered_by,
            detector_names=r.detector_names,
            started_at=r.started_at,
            completed_at=r.completed_at,
            total_findings=r.total_findings,
            error_message=r.error_message,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return DriftRunListResponse(items=items, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# GET /drift/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}", response_model=DriftRunDetail)
def get_drift_run(
    run_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
) -> DriftRunDetail:
    """Retrieve a single drift run by ID. Workspace-scoped."""
    run = session.scalar(
        select(DriftRun).where(
            DriftRun.id == run_id,
            DriftRun.workspace_id == auth.workspace_id,
        )
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drift run not found")

    # finding counts per type and severity
    type_rows = session.execute(
        select(DriftFinding.finding_type, func.count().label("cnt"))
        .where(DriftFinding.run_id == run_id)
        .group_by(DriftFinding.finding_type)
    ).all()
    sev_rows = session.execute(
        select(DriftFinding.severity, func.count().label("cnt"))
        .where(DriftFinding.run_id == run_id)
        .group_by(DriftFinding.severity)
    ).all()

    return DriftRunDetail(
        run_id=run.id,
        workspace_id=run.workspace_id,
        status=run.status,
        triggered_by=run.triggered_by,
        detector_names=run.detector_names,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_findings=run.total_findings,
        error_message=run.error_message,
        created_at=run.created_at,
        findings_by_type={row.finding_type: row.cnt for row in type_rows},
        findings_by_severity={row.severity: row.cnt for row in sev_rows},
    )


# ---------------------------------------------------------------------------
# GET /drift/findings
# ---------------------------------------------------------------------------

@router.get("/findings", response_model=DriftFindingListResponse)
def list_drift_findings(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=_FINDINGS_MAX_LIMIT)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    run_id: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    finding_type: Annotated[str | None, Query()] = None,
) -> DriftFindingListResponse:
    """List drift findings for the authenticated workspace.

    Filter by run_id, severity (info/warning/error/critical),
    or finding_type (DOCUMENT_DRIFT etc.). Newest first.
    """
    if severity is not None and severity not in DRIFT_SEVERITY_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid severity. Allowed: {DRIFT_SEVERITY_VALUES}",
        )
    if finding_type is not None and finding_type not in DRIFT_FINDING_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid finding_type. Allowed: {DRIFT_FINDING_TYPES}",
        )

    base_q = select(DriftFinding).where(DriftFinding.workspace_id == auth.workspace_id)
    if run_id is not None:
        base_q = base_q.where(DriftFinding.run_id == run_id)
    if severity is not None:
        base_q = base_q.where(DriftFinding.severity == severity)
    if finding_type is not None:
        base_q = base_q.where(DriftFinding.finding_type == finding_type)

    total: int = session.scalar(
        select(func.count()).select_from(base_q.subquery())
    ) or 0

    rows = session.scalars(
        base_q.order_by(DriftFinding.created_at.desc()).offset(offset).limit(limit)
    ).all()

    items = [
        DriftFindingItem(
            finding_id=f.id,
            run_id=f.run_id,
            workspace_id=f.workspace_id,
            finding_type=f.finding_type,
            severity=f.severity,
            entity_type=f.entity_type,
            entity_id=f.entity_id,
            detail=f.detail,
            created_at=f.created_at,
        )
        for f in rows
    ]
    return DriftFindingListResponse(items=items, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# GET /drift/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DriftSummary)
def get_drift_summary(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    session: Annotated[Session, Depends(get_db_session)],
) -> DriftSummary:
    """Workspace drift summary: latest run, total counts, breakdown by type and severity."""
    ws_id = auth.workspace_id

    latest_run = session.scalar(
        select(DriftRun)
        .where(DriftRun.workspace_id == ws_id)
        .order_by(DriftRun.created_at.desc())
        .limit(1)
    )

    total_runs: int = session.scalar(
        select(func.count(DriftRun.id)).where(DriftRun.workspace_id == ws_id)
    ) or 0

    total_findings: int = session.scalar(
        select(func.count(DriftFinding.id)).where(DriftFinding.workspace_id == ws_id)
    ) or 0

    type_rows = session.execute(
        select(DriftFinding.finding_type, func.count().label("cnt"))
        .where(DriftFinding.workspace_id == ws_id)
        .group_by(DriftFinding.finding_type)
    ).all()

    sev_rows = session.execute(
        select(DriftFinding.severity, func.count().label("cnt"))
        .where(DriftFinding.workspace_id == ws_id)
        .group_by(DriftFinding.severity)
    ).all()

    findings_by_type = {row.finding_type: row.cnt for row in type_rows}
    findings_by_severity = {row.severity: row.cnt for row in sev_rows}

    return DriftSummary(
        workspace_id=ws_id,
        latest_run_id=latest_run.id if latest_run else None,
        latest_run_status=latest_run.status if latest_run else None,
        latest_run_completed_at=latest_run.completed_at if latest_run else None,
        total_runs=total_runs,
        total_findings=total_findings,
        findings_by_type=findings_by_type,
        findings_by_severity=findings_by_severity,
        critical_count=findings_by_severity.get("critical", 0),
        error_count=findings_by_severity.get("error", 0),
    )
