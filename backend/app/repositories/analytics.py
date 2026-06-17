"""Analytics Snapshot Repository (PRI-4 Dashboard Drift Analytics).

All read/write operations for analytics_snapshots and analytics_metrics.

Rules enforced here:
- Snapshots are INSERT-only. No UPDATE method exists.
- get_latest_snapshot returns the most recent record per snapshot_type.
- list_snapshots supports pagination, type filter, status filter.
- Missing data (empty result) is signalled by returning None, not by
  synthesising a PASS record — callers must treat None as WARNING.
- No UUID values are included in returned dataclasses (use label/key fields
  for display). UUIDs are internal database keys only.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsMetric, AnalyticsSnapshot

# ---------------------------------------------------------------------------
# Status priority order (higher index = higher priority)
# ---------------------------------------------------------------------------

_STATUS_PRIORITY: dict[str, int] = {
    "PASS": 0,
    "WARNING": 1,
    "FAIL": 2,
    "BLOCKED": 3,
}

SnapshotType = Literal[
    "PRODUCT_MATURITY",
    "GOLD_PATH",
    "RELEASE_GATE",
    "TEST_COVERAGE",
    "ID_LEAK_AUDIT",
    "SECURITY_AUDIT",
]

StatusValue = Literal["PASS", "WARNING", "FAIL", "BLOCKED"]


# ---------------------------------------------------------------------------
# Dataclass records (immutable, returned to service layer)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotRecord:
    """Returned by get_latest_snapshot and list_snapshots. No UUIDs exposed."""
    id: str  # internal only — never render as primary UI text
    snapshot_type: str
    score: float | None
    status: str
    payload: dict | None
    created_at: datetime
    created_by: str | None
    workspace_id: str | None


@dataclass(frozen=True)
class MetricRecord:
    """One row in the DriftDetailPage metrics table."""
    id: str
    metric_key: str
    metric_label: str
    metric_value: str
    metric_unit: str | None
    threshold_warning: float | None
    threshold_fail: float | None
    status: str
    created_at: datetime


@dataclass(frozen=True)
class SnapshotListPage:
    items: list[SnapshotRecord]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Writes (INSERT only — no UPDATE)
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        snapshot_type: SnapshotType,
        status: StatusValue,
        *,
        score: float | None = None,
        payload: dict | None = None,
        created_by: str | None = None,
        workspace_id: str | None = None,
    ) -> SnapshotRecord:
        """Insert a new immutable snapshot. Returns the created record."""
        if payload:
            _assert_no_secrets(payload)

        now = datetime.now(tz=timezone.utc)
        row = AnalyticsSnapshot(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            snapshot_type=snapshot_type,
            score=score,
            status=status,
            payload=payload,
            created_at=now,
            created_by=created_by,
        )
        self._session.add(row)
        self._session.flush()
        return _to_snapshot_record(row)

    def create_metrics(
        self,
        snapshot_id: str,
        metrics: list[dict],
    ) -> list[MetricRecord]:
        """Insert multiple metrics for a snapshot. Returns created records.

        Each dict in `metrics` must have keys:
            metric_key, metric_label, metric_value, status
        Optional: metric_unit, threshold_warning, threshold_fail
        """
        now = datetime.now(tz=timezone.utc)
        rows: list[AnalyticsMetric] = []
        for m in metrics:
            row = AnalyticsMetric(
                id=str(uuid.uuid4()),
                snapshot_id=snapshot_id,
                metric_key=m["metric_key"],
                metric_label=m["metric_label"],
                metric_value=str(m["metric_value"]),
                metric_unit=m.get("metric_unit"),
                threshold_warning=m.get("threshold_warning"),
                threshold_fail=m.get("threshold_fail"),
                status=m["status"],
                created_at=now,
            )
            rows.append(row)
            self._session.add(row)
        self._session.flush()
        return [_to_metric_record(r) for r in rows]

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_latest_snapshot(
        self,
        snapshot_type: SnapshotType,
        workspace_id: str | None = None,
    ) -> SnapshotRecord | None:
        """Return the most recent snapshot for the given type.

        Returns None if no snapshot exists yet — callers must treat this as
        WARNING (missing data is not PASS).
        """
        stmt = (
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.snapshot_type == snapshot_type)
            .order_by(desc(AnalyticsSnapshot.created_at))
            .limit(1)
        )
        if workspace_id is not None:
            stmt = stmt.where(AnalyticsSnapshot.workspace_id == workspace_id)

        row = self._session.execute(stmt).scalar_one_or_none()
        return _to_snapshot_record(row) if row else None

    def list_snapshots(
        self,
        *,
        snapshot_type: SnapshotType | None = None,
        status: StatusValue | None = None,
        workspace_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SnapshotListPage:
        """Paginated list of snapshots, newest first. Supports type + status filters."""
        conditions = []
        if snapshot_type:
            conditions.append(AnalyticsSnapshot.snapshot_type == snapshot_type)
        if status:
            conditions.append(AnalyticsSnapshot.status == status)
        if workspace_id is not None:
            conditions.append(AnalyticsSnapshot.workspace_id == workspace_id)

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count()).select_from(AnalyticsSnapshot).where(where_clause)
        total: int = self._session.execute(count_stmt).scalar_one()

        offset = (page - 1) * page_size
        rows_stmt = (
            select(AnalyticsSnapshot)
            .where(where_clause)
            .order_by(desc(AnalyticsSnapshot.created_at))
            .offset(offset)
            .limit(page_size)
        )
        rows = list(self._session.execute(rows_stmt).scalars())
        return SnapshotListPage(
            items=[_to_snapshot_record(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_snapshot_by_id(self, snapshot_id: str) -> SnapshotRecord | None:
        """Return a single snapshot by internal ID. Returns None if not found."""
        row = self._session.get(AnalyticsSnapshot, snapshot_id)
        return _to_snapshot_record(row) if row else None

    def get_snapshot_metrics(self, snapshot_id: str) -> list[MetricRecord]:
        """Return all metrics for a snapshot, ordered by metric_key."""
        stmt = (
            select(AnalyticsMetric)
            .where(AnalyticsMetric.snapshot_id == snapshot_id)
            .order_by(AnalyticsMetric.metric_key)
        )
        rows = list(self._session.execute(stmt).scalars())
        return [_to_metric_record(r) for r in rows]

    def get_all_latest_snapshots(self) -> dict[str, SnapshotRecord | None]:
        """Return the latest snapshot for every known type.

        Used by DriftService to build the Dashboard overview.
        Missing types map to None (caller must treat as WARNING).
        """
        result: dict[str, SnapshotRecord | None] = {t: None for t in (
            "PRODUCT_MATURITY",
            "GOLD_PATH",
            "RELEASE_GATE",
            "TEST_COVERAGE",
            "ID_LEAK_AUDIT",
            "SECURITY_AUDIT",
        )}
        # Subquery: max created_at per type
        subq = (
            select(
                AnalyticsSnapshot.snapshot_type,
                func.max(AnalyticsSnapshot.created_at).label("max_created"),
            )
            .group_by(AnalyticsSnapshot.snapshot_type)
            .subquery()
        )
        stmt = select(AnalyticsSnapshot).join(
            subq,
            and_(
                AnalyticsSnapshot.snapshot_type == subq.c.snapshot_type,
                AnalyticsSnapshot.created_at == subq.c.max_created,
            ),
        )
        for row in self._session.execute(stmt).scalars():
            result[row.snapshot_type] = _to_snapshot_record(row)
        return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_snapshot_record(row: AnalyticsSnapshot) -> SnapshotRecord:
    return SnapshotRecord(
        id=row.id,
        snapshot_type=row.snapshot_type,
        score=row.score,
        status=row.status,
        payload=row.payload,
        created_at=row.created_at,
        created_by=row.created_by,
        workspace_id=row.workspace_id,
    )


def _to_metric_record(row: AnalyticsMetric) -> MetricRecord:
    return MetricRecord(
        id=row.id,
        metric_key=row.metric_key,
        metric_label=row.metric_label,
        metric_value=row.metric_value,
        metric_unit=row.metric_unit,
        threshold_warning=row.threshold_warning,
        threshold_fail=row.threshold_fail,
        status=row.status,
        created_at=row.created_at,
    )


_SECRET_KEYS = frozenset({
    "auth_token", "auth_tokens", "api_key", "api_keys",
    "session", "sessions", "password", "secret", "secret_key",
    "private_key", "token", "bearer",
})


def _assert_no_secrets(payload: dict, path: str = "") -> None:
    """Raise ValueError if payload contains secret field names.

    Checked recursively. Prevents secret data from being stored in snapshot
    payload column (PROHIBIT rule from export security constraints).
    """
    for key, value in payload.items():
        full_key = f"{path}.{key}" if path else key
        if key.lower() in _SECRET_KEYS or key.lower().startswith("secret_"):
            raise ValueError(
                f"Snapshot payload contains forbidden field '{full_key}'. "
                "Secrets must not be stored in analytics_snapshots.payload."
            )
        if isinstance(value, dict):
            _assert_no_secrets(value, full_key)
