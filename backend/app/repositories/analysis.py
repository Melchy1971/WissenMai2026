from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.analysis import (
    AnalysisJob,
    AnalysisResult,
    AnalysisJobSourceDocument,
    ANALYSIS_JOB_STATUS_VALUES,
    ANALYSIS_JOB_SOURCE_TYPE_VALUES,
    ANALYSIS_RESULT_STATUS_VALUES,
)


# ---------------------------------------------------------------------------
# Immutable records (service layer boundary)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AnalysisJobRecord:
    id: str
    workspace_id: str | None
    status: str
    analysis_type: str
    source_type: str | None
    source_ids: list | None
    source_document_ids: list[str]
    prompt: str
    provider: str | None
    model: str | None
    result_id: str | None
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class AnalysisResultRecord:
    id: str
    job_id: str
    title: str | None
    summary: str
    content_markdown: str | None
    key_points: list
    suggested_tags: list
    suggested_topics: list
    sources: list | None
    confidence: float | None
    status: str
    approved_at: datetime | None
    approved_by: str | None
    created_at: datetime
    updated_at: datetime | None


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Job reads ─────────────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> AnalysisJob | None:
        return self._session.get(AnalysisJob, job_id)

    def require_job(self, job_id: str) -> AnalysisJob:
        """Return job or raise KeyError (caller maps to API error)."""
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"AnalysisJob {job_id!r} not found")
        return job

    def list_jobs(
        self,
        *,
        workspace_id: str,
        status: str | None = None,
        source_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AnalysisJobRecord], int]:
        stmt = select(AnalysisJob).where(AnalysisJob.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(AnalysisJob.status == status)
        if source_type is not None:
            stmt = stmt.where(AnalysisJob.source_type == source_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = self._session.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(desc(AnalysisJob.created_at)).limit(limit).offset(offset)
        jobs = self._session.scalars(stmt).all()
        return [_job_to_record(j) for j in jobs], total

    # ── Job writes ────────────────────────────────────────────────────────────

    def create_job(self, job: AnalysisJob) -> AnalysisJob:
        self._session.add(job)
        self._session.flush()
        return job

    def update_job_status(
        self,
        job: AnalysisJob,
        *,
        status: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if status not in ANALYSIS_JOB_STATUS_VALUES:
            raise ValueError(f"Invalid status: {status!r}")
        job.status = status
        if started_at is not None:
            job.started_at = started_at
        if finished_at is not None:
            job.finished_at = finished_at
        if error_code is not None:
            job.error_code = error_code
        if error_message is not None:
            job.error_message = error_message
        self._session.flush()

    def set_job_result_id(self, job: AnalysisJob, result_id: str) -> None:
        """Denormalized backpointer — set after result is persisted."""
        job.result_id = result_id
        self._session.flush()

    def count_retries(self, original_job_id: str) -> int:
        """Count jobs that retry original_job_id (stored as error_code prefix)."""
        stmt = select(func.count(AnalysisJob.id)).where(
            AnalysisJob.error_code == f"RETRY:{original_job_id}"
        )
        return self._session.execute(stmt).scalar_one()

    # ── Result reads ──────────────────────────────────────────────────────────

    def get_result(self, result_id: str) -> AnalysisResult | None:
        return self._session.get(AnalysisResult, result_id)

    def get_result_by_job(self, job_id: str) -> AnalysisResult | None:
        stmt = select(AnalysisResult).where(AnalysisResult.job_id == job_id)
        return self._session.scalars(stmt).first()

    def require_result(self, result_id: str) -> AnalysisResult:
        result = self.get_result(result_id)
        if result is None:
            raise KeyError(f"AnalysisResult {result_id!r} not found")
        return result

    # ── Result writes ─────────────────────────────────────────────────────────

    def create_result(self, result: AnalysisResult) -> AnalysisResult:
        self._session.add(result)
        self._session.flush()
        return result

    def update_result(
        self,
        result: AnalysisResult,
        *,
        title: str | None = None,
        summary: str | None = None,
        content_markdown: str | None = None,
        sources: list | None = None,
        updated_at: datetime,
    ) -> None:
        if title is not None:
            result.title = title
        if summary is not None:
            result.summary = summary
        if content_markdown is not None:
            result.content_markdown = content_markdown
        if sources is not None:
            result.sources = sources
        result.updated_at = updated_at
        self._session.flush()

    def set_result_status(
        self,
        result: AnalysisResult,
        *,
        status: str,
        approved_by: str | None = None,
        approved_at: datetime | None = None,
        updated_at: datetime,
    ) -> None:
        if status not in ANALYSIS_RESULT_STATUS_VALUES:
            raise ValueError(f"Invalid result status: {status!r}")
        result.status = status
        result.approved_by = approved_by
        result.approved_at = approved_at
        result.updated_at = updated_at
        self._session.flush()

    # ── Source document helpers ───────────────────────────────────────────────

    def get_source_document_ids(self, job_id: str) -> list[str]:
        stmt = (
            select(AnalysisJobSourceDocument.document_id)
            .where(AnalysisJobSourceDocument.job_id == job_id)
            .order_by(AnalysisJobSourceDocument.position)
        )
        return list(self._session.scalars(stmt).all())

    # ── Aggregate / reporting ─────────────────────────────────────────────────

    def count_jobs_by_status(self, workspace_id: str) -> dict[str, int]:
        stmt = (
            select(AnalysisJob.status, func.count(AnalysisJob.id))
            .where(AnalysisJob.workspace_id == workspace_id)
            .group_by(AnalysisJob.status)
        )
        return {row[0]: row[1] for row in self._session.execute(stmt).all()}


# ---------------------------------------------------------------------------
# Internal mappers
# ---------------------------------------------------------------------------

def _job_to_record(job: AnalysisJob) -> AnalysisJobRecord:
    return AnalysisJobRecord(
        id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        analysis_type=job.analysis_type,
        source_type=job.source_type,
        source_ids=job.source_ids,
        source_document_ids=job.source_document_ids,
        prompt=job.prompt,
        provider=job.provider,
        model=job.model,
        result_id=job.result_id,
        created_by=job.created_by,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )


def result_to_record(result: AnalysisResult) -> AnalysisResultRecord:
    return AnalysisResultRecord(
        id=result.id,
        job_id=result.job_id,
        title=result.title,
        summary=result.summary,
        content_markdown=result.content_markdown,
        key_points=result.key_points,
        suggested_tags=result.suggested_tags,
        suggested_topics=result.suggested_topics,
        sources=result.sources,
        confidence=result.confidence,
        status=result.status,
        approved_at=result.approved_at,
        approved_by=result.approved_by,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )
