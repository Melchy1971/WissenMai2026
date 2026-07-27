from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .documents import Base


# Preferred status set (v2). Legacy values "pending" / "approved" remain valid
# for backward compatibility with existing rows and stub engine.
ANALYSIS_JOB_STATUS_VALUES = (
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
    # legacy
    "pending",
    "approved",
)

ANALYSIS_JOB_SOURCE_TYPE_VALUES = ("DOCUMENTS", "TOPIC", "SEARCH_RESULT")

ANALYSIS_RESULT_STATUS_VALUES = ("draft", "review", "approved", "rejected")

ANALYSIS_SUGGESTION_STATUS_VALUES = (
    "pending", "running", "completed", "failed", "approved",
)

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class AnalysisJobSourceDocument(Base):
    __tablename__ = "analysis_job_source_documents"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_analysis_job_source_documents_position_non_negative"),
        UniqueConstraint("job_id", "position", name="uq_analysis_job_source_documents_job_position"),
        Index("ix_analysis_job_source_documents_document_id", "document_id"),
    )

    job_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class AnalysisComparisonDocument(Base):
    __tablename__ = "analysis_comparison_documents"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_analysis_comparison_documents_position_non_negative"),
        UniqueConstraint("comparison_id", "position", name="uq_analysis_comparison_documents_comparison_position"),
        Index("ix_analysis_comparison_documents_document_id", "document_id"),
    )

    comparison_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_comparisons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','completed','failed','cancelled','pending','approved')",
            name="ck_analysis_jobs_status",
        ),
        CheckConstraint(
            "source_type IS NULL OR source_type IN ('DOCUMENTS','TOPIC','SEARCH_RESULT')",
            name="ck_analysis_jobs_source_type",
        ),
        CheckConstraint("length(trim(analysis_type)) > 0", name="ck_analysis_jobs_analysis_type_not_blank"),
        CheckConstraint("length(trim(prompt)) > 0", name="ck_analysis_jobs_prompt_not_blank"),
        Index("ix_analysis_jobs_workspace_id", "workspace_id"),
        Index("ix_analysis_jobs_status", "status"),
        Index("ix_analysis_jobs_created_at", "created_at"),
        Index("ix_analysis_jobs_source_type", "source_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    analysis_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_ids: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document_links: Mapped[list[AnalysisJobSourceDocument]] = relationship(
        cascade="all, delete-orphan",
        order_by=AnalysisJobSourceDocument.position,
    )
    result: Mapped["AnalysisResult | None"] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    comparison: Mapped["AnalysisComparison | None"] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    suggestions: Mapped[list["AnalysisSuggestion"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AnalysisSuggestion.id",
    )

    @property
    def source_document_ids(self) -> list[str]:
        return [link.document_id for link in self.source_document_links]

    @source_document_ids.setter
    def source_document_ids(self, document_ids: list[str]) -> None:
        self.source_document_links = [
            AnalysisJobSourceDocument(document_id=document_id, position=index)
            for index, document_id in enumerate(document_ids)
        ]


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_analysis_results_confidence_range"),
        CheckConstraint(
            "status IN ('draft','review','approved','rejected')",
            name="ck_analysis_results_status",
        ),
        CheckConstraint(
            "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL) "
            "OR (status != 'approved' AND approved_by IS NULL AND approved_at IS NULL)",
            name="ck_analysis_results_approval_metadata",
        ),
        UniqueConstraint("job_id", name="uq_analysis_results_job_id"),
        Index("ix_analysis_results_created_at", "created_at"),
        Index("ix_analysis_results_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    suggested_tags: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    suggested_topics: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[AnalysisJob] = relationship(back_populates="result")


class AnalysisComparison(Base):
    __tablename__ = "analysis_comparisons"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_analysis_comparisons_job_id"),
        Index("ix_analysis_comparisons_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    overlaps: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    differences: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    suggested_merge: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job: Mapped[AnalysisJob] = relationship(back_populates="comparison")
    compared_document_links: Mapped[list[AnalysisComparisonDocument]] = relationship(
        cascade="all, delete-orphan",
        order_by=AnalysisComparisonDocument.position,
    )

    @property
    def compared_document_ids(self) -> list[str]:
        return [link.document_id for link in self.compared_document_links]

    @compared_document_ids.setter
    def compared_document_ids(self, document_ids: list[str]) -> None:
        self.compared_document_links = [
            AnalysisComparisonDocument(document_id=document_id, position=index)
            for index, document_id in enumerate(document_ids)
        ]


class AnalysisSuggestion(Base):
    __tablename__ = "analysis_suggestions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','completed','failed','approved')",
            name="ck_analysis_suggestions_status",
        ),
        CheckConstraint(
            "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL) "
            "OR (status != 'approved' AND approved_by IS NULL AND approved_at IS NULL)",
            name="ck_analysis_suggestions_approval_metadata",
        ),
        CheckConstraint("length(trim(suggestion_type)) > 0", name="ck_analysis_suggestions_type_not_blank"),
        Index("ix_analysis_suggestions_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    suggestion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[AnalysisJob] = relationship(back_populates="suggestions")
