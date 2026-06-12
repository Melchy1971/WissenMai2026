"""Drift Persistence Layer — SQLAlchemy Models.

Tables: drift_runs, drift_findings, drift_snapshots.

Design constraints:
- workspace scoped: every table carries workspace_id FK
- audit fields: created_at on all tables; updated_at on drift_runs
- FK constraints: drift_findings and drift_snapshots -> drift_runs (CASCADE)
- no data mutation outside Drift tables: no FK to documents, chunks, or versions
  (entity_id is a plain String to stay read-only and schema-independent)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .documents import Base


# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------

DRIFT_FINDING_TYPES = (
    "DOCUMENT_DRIFT",
    "METADATA_DRIFT",
    "LIFECYCLE_DRIFT",
    "SOURCE_STATUS_DRIFT",
    "RETRIEVAL_DRIFT",
)

DRIFT_RUN_STATUS_VALUES = ("pending", "running", "completed", "failed", "cancelled")

DRIFT_SEVERITY_VALUES = ("info", "warning", "error", "critical")

DRIFT_SNAPSHOT_TYPES = ("pre_run", "post_run", "baseline", "delta")


# ---------------------------------------------------------------------------
# drift_runs
# ---------------------------------------------------------------------------

class DriftRun(Base):
    """One execution of the drift detection pipeline for a workspace."""

    __tablename__ = "drift_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_drift_runs_status",
        ),
        Index("ix_drift_runs_workspace_id", "workspace_id"),
        Index("ix_drift_runs_status", "status"),
        Index("ix_drift_runs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
    )
    triggered_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="user_id or 'system'",
    )
    detector_names: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Ordered list of detector class names that were registered for this run.",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_findings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    findings: Mapped[list[DriftFinding]] = relationship(
        "DriftFinding",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    snapshots: Mapped[list[DriftSnapshot]] = relationship(
        "DriftSnapshot",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# drift_findings
# ---------------------------------------------------------------------------

class DriftFinding(Base):
    """A single drift finding produced by a detector during a DriftRun."""

    __tablename__ = "drift_findings"
    __table_args__ = (
        CheckConstraint(
            "finding_type IN ("
            "'DOCUMENT_DRIFT','METADATA_DRIFT','LIFECYCLE_DRIFT',"
            "'SOURCE_STATUS_DRIFT','RETRIEVAL_DRIFT'"
            ")",
            name="ck_drift_findings_finding_type",
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name="ck_drift_findings_severity",
        ),
        Index("ix_drift_findings_run_id", "run_id"),
        Index("ix_drift_findings_workspace_id", "workspace_id"),
        Index("ix_drift_findings_finding_type", "finding_type"),
        Index("ix_drift_findings_severity", "severity"),
        Index("ix_drift_findings_entity_id", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("drift_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="e.g. 'document', 'version', 'chunk'",
    )
    entity_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="ID of the affected entity. Plain String — no FK to preserve read-only semantics.",
    )
    detail: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Detector-specific context. Schema defined in drift_schema.json.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    run: Mapped[DriftRun] = relationship(
        "DriftRun",
        back_populates="findings",
    )


# ---------------------------------------------------------------------------
# drift_snapshots
# ---------------------------------------------------------------------------

class DriftSnapshot(Base):
    """Workspace state snapshot captured before or after a DriftRun."""

    __tablename__ = "drift_snapshots"
    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ('pre_run', 'post_run', 'baseline', 'delta')",
            name="ck_drift_snapshots_snapshot_type",
        ),
        Index("ix_drift_snapshots_run_id", "run_id"),
        Index("ix_drift_snapshots_workspace_id", "workspace_id"),
        Index("ix_drift_snapshots_snapshot_type", "snapshot_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("drift_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    entity_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Serialised workspace state at snapshot time.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    run: Mapped[DriftRun] = relationship(
        "DriftRun",
        back_populates="snapshots",
    )
