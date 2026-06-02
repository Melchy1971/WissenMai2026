"""M5a Data Quality — SQLAlchemy Models (Minimal).

In scope:  data_quality_runs, data_quality_findings
Deferred:  data_quality_metrics, data_quality_snapshots
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .documents import Base


# ---------------------------------------------------------------------------
# Allowed values (referenced by CheckConstraints and Enum)
# ---------------------------------------------------------------------------

FINDING_TYPE_VALUES = (
    "DUPLICATE_DOCUMENT",
    "DUPLICATE_CONTENT",
    "EMPTY_DOCUMENT",
    "EMPTY_CHUNK",
    "ORPHAN_CHUNK",
    "ORPHAN_VERSION",
    "ORPHAN_CITATION",
    "ORPHAN_FINDING",
    "MISSING_METADATA",
    "INVALID_SOURCE_STATUS",
    "INVALID_LIFECYCLE",
    "RETRIEVAL_RISK",
)

RUN_STATUS_VALUES = ("pending", "running", "completed", "failed")
SEVERITY_VALUES = ("error", "warning", "info")


# ---------------------------------------------------------------------------
# data_quality_runs
# ---------------------------------------------------------------------------

class DataQualityRun(Base):
    __tablename__ = "data_quality_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_dq_runs_status",
        ),
        Index("ix_dq_runs_workspace_id", "workspace_id"),
        Index("ix_dq_runs_status", "status"),
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
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_findings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    findings: Mapped[list[DataQualityFinding]] = relationship(
        "DataQualityFinding",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# data_quality_findings
# ---------------------------------------------------------------------------

class DataQualityFinding(Base):
    __tablename__ = "data_quality_findings"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('error', 'warning', 'info')",
            name="ck_dq_findings_severity",
        ),
        Index("ix_dq_findings_run_id", "run_id"),
        Index("ix_dq_findings_workspace_id", "workspace_id"),
        Index("ix_dq_findings_severity", "severity"),
        Index("ix_dq_findings_finding_type", "finding_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("data_quality_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(
        Enum(*FINDING_TYPE_VALUES, name="dq_finding_type"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    run: Mapped[DataQualityRun] = relationship(
        "DataQualityRun",
        back_populates="findings",
    )
