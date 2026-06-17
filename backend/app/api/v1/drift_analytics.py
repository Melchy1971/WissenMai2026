"""REST API — Dashboard Drift Analytics (PRI-4).

Endpoints:
  GET  /api/v1/drift/overview                    Dashboard widget overview
  GET  /api/v1/drift/snapshots                   Paginated list (type+status filter)
  GET  /api/v1/drift/snapshots/{id}              Single snapshot detail
  GET  /api/v1/drift/snapshots/{id}/metrics      Metrics for DriftDetailPage
  POST /api/v1/drift/snapshots/recalculate       Trigger recalculation

Auth: All endpoints require workspace_member.
Pagination: page (≥1, default 1), page_size (1–100, default 20).
Filters: ?type=PRODUCT_MATURITY  ?status=BLOCKED

Design rules:
  - No UUIDs returned as primary UI text (SnapshotSummary / OverviewWidget).
  - SnapshotDetail includes internal id for metrics lookup, labelled as non-display.
  - Missing data (no snapshot found) → 200 with null widget, not 404.
  - Recalculate errors per type are isolated and listed in snapshots_failed.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError
from app.db.session import get_session
from app.models.analytics import ANALYTICS_SNAPSHOT_TYPES, ANALYTICS_STATUS_VALUES
from app.repositories.analytics import SnapshotRecord
from app.schemas.analytics import (
    DriftOverviewResponse,
    MetricListResponse,
    MetricResponse,
    OverviewWidget,
    RecalculateResponse,
    SnapshotDetail,
    SnapshotListItem,
    SnapshotListResponse,
)
from app.services.drift_analytics import DriftAnalyticsService

router = APIRouter(prefix="/drift", tags=["drift-analytics"])


# ---------------------------------------------------------------------------
# Labels for overview widgets (no UUIDs, no internal keys as display text)
# ---------------------------------------------------------------------------

_WIDGET_LABELS: dict[str, str] = {
    "PRODUCT_MATURITY": "Produktreife",
    "GOLD_PATH": "Gold Path",
    "RELEASE_GATE": "Release Gate",
    "TEST_COVERAGE": "Test Coverage",
    "ID_LEAK_AUDIT": "Technische ID Prüfung",
    "SECURITY_AUDIT": "Sicherheitsaudit",
}


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_analytics_service(
    session: Annotated[Session, Depends(get_db_session)],
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
) -> DriftAnalyticsService:
    created_by = getattr(auth, "login", None) or getattr(auth, "user_id", "system")
    return DriftAnalyticsService(session, created_by=created_by)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=DriftOverviewResponse)
def get_drift_overview(
    _auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[DriftAnalyticsService, Depends(get_analytics_service)],
) -> DriftOverviewResponse:
    """Return latest snapshot for all 6 analytics types as Dashboard widgets.

    Missing snapshots (no data yet) are returned as None — not a 404.
    The UI must treat None as status=WARNING.
    """
    overview = service.get_overview()

    def _to_widget(snap: SnapshotRecord | None, snap_type: str) -> OverviewWidget | None:
        if snap is None:
            return None
        return OverviewWidget(
            status=snap.status,  # type: ignore[arg-type]
            score=snap.score,
            label=_WIDGET_LABELS.get(snap_type, snap_type),
            last_updated=snap.created_at,
            snapshot_type=snap.snapshot_type,  # type: ignore[arg-type]
        )

    return DriftOverviewResponse(
        product_maturity=_to_widget(overview.product_maturity, "PRODUCT_MATURITY"),
        gold_path=_to_widget(overview.gold_path, "GOLD_PATH"),
        release_gate=_to_widget(overview.release_gate, "RELEASE_GATE"),
        test_coverage=_to_widget(overview.test_coverage, "TEST_COVERAGE"),
        id_leak_audit=_to_widget(overview.id_leak_audit, "ID_LEAK_AUDIT"),
        security_audit=_to_widget(overview.security_audit, "SECURITY_AUDIT"),
        last_updated=overview.last_updated,
        global_status=overview.global_status,  # type: ignore[arg-type]
    )


@router.get("/snapshots", response_model=SnapshotListResponse)
def list_snapshots(
    _auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[DriftAnalyticsService, Depends(get_analytics_service)],
    type_filter: Annotated[str | None, Query(alias="type")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SnapshotListResponse:
    """Paginated list of analytics snapshots, newest first.

    Optional filters: ?type=PRODUCT_MATURITY  ?status=BLOCKED
    """
    if type_filter is not None and type_filter not in ANALYTICS_SNAPSHOT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid type. Allowed: {ANALYTICS_SNAPSHOT_TYPES}",
        )
    if status_filter is not None and status_filter not in ANALYTICS_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {ANALYTICS_STATUS_VALUES}",
        )

    page_result = service.list_snapshots(
        snapshot_type=type_filter,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    return SnapshotListResponse(
        items=[
            SnapshotListItem(
                id=s.id,
                snapshot_type=s.snapshot_type,  # type: ignore[arg-type]
                score=s.score,
                status=s.status,  # type: ignore[arg-type]
                created_at=s.created_at,
                created_by=s.created_by,
            )
            for s in page_result.items
        ],
        total=page_result.total,
        page=page_result.page,
        page_size=page_result.page_size,
    )


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotDetail)
def get_snapshot(
    snapshot_id: str,
    _auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[DriftAnalyticsService, Depends(get_analytics_service)],
) -> SnapshotDetail:
    """Return full detail for one snapshot (used by DriftDetailPage overview section).

    The payload may be large — UI should render it in a collapsible section.
    No UUIDs or secrets in payload (enforced at repository layer).
    """
    snap = service._repo.get_snapshot_by_id(snapshot_id)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot nicht gefunden.",
        )
    return SnapshotDetail(
        id=snap.id,
        snapshot_type=snap.snapshot_type,  # type: ignore[arg-type]
        score=snap.score,
        status=snap.status,  # type: ignore[arg-type]
        payload=snap.payload,
        created_at=snap.created_at,
        created_by=snap.created_by,
    )


@router.get("/snapshots/{snapshot_id}/metrics", response_model=MetricListResponse)
def get_snapshot_metrics(
    snapshot_id: str,
    _auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[DriftAnalyticsService, Depends(get_analytics_service)],
) -> MetricListResponse:
    """Return metrics for one snapshot (DriftDetailPage metrics table).

    Returns 404 if the snapshot itself does not exist.
    Returns empty metrics list if snapshot has no metrics (not an error).
    """
    snap = service._repo.get_snapshot_by_id(snapshot_id)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot nicht gefunden.",
        )

    metrics = service.get_snapshot_metrics(snapshot_id)
    return MetricListResponse(
        snapshot_type=snap.snapshot_type,  # type: ignore[arg-type]
        snapshot_status=snap.status,  # type: ignore[arg-type]
        metrics=[
            MetricResponse(
                metric_key=m.metric_key,
                metric_label=m.metric_label,
                metric_value=m.metric_value,
                metric_unit=m.metric_unit,
                threshold_warning=m.threshold_warning,
                threshold_fail=m.threshold_fail,
                status=m.status,  # type: ignore[arg-type]
                created_at=m.created_at,
            )
            for m in metrics
        ],
    )


@router.post(
    "/snapshots/recalculate",
    response_model=RecalculateResponse,
    status_code=status.HTTP_200_OK,
)
def recalculate_snapshots(
    _auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[DriftAnalyticsService, Depends(get_analytics_service)],
) -> RecalculateResponse:
    """Trigger recalculation of all analytics snapshots from current report files.

    Old snapshots are preserved (append-only). Errors per type are isolated
    and listed in snapshots_failed. A partial result (some failed) is still
    HTTP 200 — the caller must check snapshots_failed.

    Audit note: each recalculate call creates new snapshot rows with
    created_by=current_user and created_at=now. The history is thus complete.
    """
    result = service.recalculate()

    if result.snapshots_failed:
        failed_str = ", ".join(result.snapshots_failed)
        message = (
            f"{result.snapshots_created} Snapshots erstellt. "
            f"Fehlgeschlagen: {failed_str}."
        )
    else:
        message = f"{result.snapshots_created} Snapshots erfolgreich neu berechnet."

    return RecalculateResponse(
        snapshots_created=result.snapshots_created,
        snapshots_failed=result.snapshots_failed,
        global_status=result.global_status,  # type: ignore[arg-type]
        created_at=result.created_at,
        message=message,
    )
