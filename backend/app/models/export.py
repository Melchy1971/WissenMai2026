from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .documents import Base


EXPORT_JOB_STATUS_VALUES = (
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
)

EXPORT_SOURCE_TYPE_VALUES = (
    "SEARCH_RESULT",
    "ANALYSIS_RESULT",
    "TOPIC",
    "DOCUMENT_COLLECTION",
)

EXPORT_FORMAT_VALUES = (
    "MARKDOWN",
    "JSON",
    "PDF",
)

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')",
            name="ck_export_jobs_status",
        ),
        CheckConstraint(
            "source_type IN ('SEARCH_RESULT','ANALYSIS_RESULT','TOPIC','DOCUMENT_COLLECTION')",
            name="ck_export_jobs_source_type",
        ),
        CheckConstraint(
            "export_format IN ('MARKDOWN','JSON','PDF')",
            name="ck_export_jobs_export_format",
        ),
        CheckConstraint(
            "length(trim(file_name)) > 0",
            name="ck_export_jobs_file_name_not_blank",
        ),
        Index("ix_export_jobs_status", "status"),
        Index("ix_export_jobs_source_type", "source_type"),
        Index("ix_export_jobs_export_format", "export_format"),
        Index("ix_export_jobs_created_at", "created_at"),
        Index("ix_export_jobs_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="QUEUED")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ids: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    export_format: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExportTemplate(Base):
    __tablename__ = "export_templates"
    __table_args__ = (
        CheckConstraint(
            "export_format IN ('MARKDOWN','JSON','PDF')",
            name="ck_export_templates_export_format",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_export_templates_name_not_blank",
        ),
        UniqueConstraint("name", name="uq_export_templates_name"),
        Index("ix_export_templates_export_format", "export_format"),
        Index("ix_export_templates_is_default", "is_default"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    export_format: Mapped[str] = mapped_column(String(16), nullable=False)
    layout_config: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
