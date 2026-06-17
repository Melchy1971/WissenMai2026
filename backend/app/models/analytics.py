"""Analytics Snapshot Models — Dashboard Drift Analytics (PRI-4).

Separate from the M5b DriftRun/DriftFinding/DriftSnapshot layer, which handles
workspace-level document drift detection. This layer captures immutable product
quality snapshots used by the Dashboard Drift Analytics widgets.

Tables: analytics_snapshots, analytics_metrics.

Design constraints:
- Snapshots are immutable: no UPDATE after INSERT (enforced by repository).
- workspace_id is nullable: global snapshots (e.g. product maturity) have no workspace scope.
- Status priority (descending): BLOCKED > FAIL > WARNING > PASS.
- Missing data → WARNING (not PASS).
- analytics_metrics carries per-snapshot threshold data for detail views.
- No technical IDs exposed in service/API layer output.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .documents import Base


# ---------------------------------------------------------------------------
# Allowed values (authoritative)
# ---------------------------------------------------------------------------

ANALYTICS_SNAPSHOT_TYPES = (
    "PRODUCT_MATURITY",
    "GOLD_PATH",
    "RELEASE_GATE",
    "TEST_COVERAGE",
    "ID_LEAK_AUDIT",
    "SECURITY_AUDIT",
)

ANALYTICS_STATUS_VALUES = ("PASS", "WARNING", "FAIL", "BLOCKED")


# ---------------------------------------------------------------------------
# AnalyticsSnapshot
# ---------------------------------------------------------------------------

class AnalyticsSnapshot(Base):
    """Immutable product quality snapshot for one analytics dimension.

    One record per (snapshotType, createdAt) pair. The latest record per type
    is the authoritative current state for Dashboard widgets.

    Score is nullable: some types (e.g. SECURITY_AUDIT) have no numeric score,
    only a status.
    """

    __tablename__ = "analytics_snapshots"
    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ("
            "'PRODUCT_MATURITY','GOLD_PATH','RELEASE_GATE',"
            "'TEST_COVERAGE','ID_LEAK_AUDIT','SECURITY_AUDIT'"
            ")",
            name="ck_analytics_snapshots_snapshot_type",
        ),
        CheckConstraint(
            "status IN ('PASS','WARNING','FAIL','BLOCKED')",
            name="ck_analytics_snapshots_status",
        ),
        # Fast lookup: latest snapshot per type
        Index("ix_analytics_snapshots_type", "snapshot_type"),
        # Filter by status for overview queries
        Index("ix_analytics_snapshots_status", "status"),
        # Time-ordered queries for history / trend views
        Index("ix_analytics_snapshots_created_at", "created_at"),
        # Composite: most common query pattern (latest by type)
        Index("ix_analytics_snapshots_type_created", "snapshot_type", "created_at"),
        # Workspace-scoped queries (nullable — NULL = global)
        Index("ix_analytics_snapshots_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)

    workspace_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for global snapshots (product maturity, gold path, etc.)",
    )

    snapshot_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="One of ANALYTICS_SNAPSHOT_TYPES.",
    )

    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Numeric score where applicable (0–100). NULL for non-numeric types.",
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="PASS|WARNING|FAIL|BLOCKED. BLOCKED takes priority over all others.",
    )

    payload: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment=(
            "Full snapshot payload from source report. "
            "Must not contain auth_tokens, api_keys, sessions, or secret_* fields. "
            "Must not contain UUIDs as primary display values."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Immutable — set at INSERT, never modified.",
    )

    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="user login or 'system'. No UUID stored here.",
    )

    metrics: Mapped[list[AnalyticsMetric]] = relationship(
        "AnalyticsMetric",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# AnalyticsMetric
# ---------------------------------------------------------------------------

class AnalyticsMetric(Base):
    """Individual metric within an AnalyticsSnapshot.

    Used by DriftDetailPage to render the metrics table with threshold indicators.
    One snapshot can have 0..N metrics. Metrics are also immutable (parent-owned).
    """

    __tablename__ = "analytics_metrics"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PASS','WARNING','FAIL','BLOCKED')",
            name="ck_analytics_metrics_status",
        ),
        Index("ix_analytics_metrics_snapshot_id", "snapshot_id"),
        Index("ix_analytics_metrics_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)

    snapshot_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analytics_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    metric_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Machine-readable key, e.g. 'gold_path_pass_count'. Never shown as-is in UI.",
    )

    metric_label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable label for display in DriftDetailPage metrics table.",
    )

    metric_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="String representation of the value (numbers, percentages, counts).",
    )

    metric_unit: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Optional unit, e.g. '%', 'Schritte', 'Dateien'. NULL if unitless.",
    )

    threshold_warning: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Value at which status becomes WARNING. NULL if no threshold defined.",
    )

    threshold_fail: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Value at which status becomes FAIL. NULL if no threshold defined.",
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="PASS|WARNING|FAIL|BLOCKED — derived from value vs thresholds.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    snapshot: Mapped[AnalyticsSnapshot] = relationship(
        "AnalyticsSnapshot",
        back_populates="metrics",
    )
