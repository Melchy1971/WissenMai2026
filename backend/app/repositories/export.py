from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.export import (
    ExportJob,
    ExportTemplate,
    EXPORT_JOB_STATUS_VALUES,
    EXPORT_FORMAT_VALUES,
)


# ---------------------------------------------------------------------------
# Immutable records (service layer boundary)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExportJobRecord:
    id: str
    workspace_id: str | None
    status: str
    source_type: str
    source_ids: list | None
    export_format: str
    file_name: str
    file_path: str | None
    error_message: str | None
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class ExportTemplateRecord:
    id: str
    name: str
    export_format: str
    layout_config: dict | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class ExportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Job reads ─────────────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> ExportJob | None:
        return self._session.get(ExportJob, job_id)

    def require_job(self, job_id: str) -> ExportJob:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"ExportJob {job_id!r} not found")
        return job

    def list_jobs(
        self,
        *,
        workspace_id: str | None = None,
        status: str | None = None,
        export_format: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ExportJobRecord], int]:
        stmt = select(ExportJob)
        if workspace_id is not None:
            stmt = stmt.where(ExportJob.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(ExportJob.status == status)
        if export_format is not None:
            stmt = stmt.where(ExportJob.export_format == export_format)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = self._session.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(desc(ExportJob.created_at)).limit(limit).offset(offset)
        jobs = self._session.scalars(stmt).all()
        return [_job_to_record(j) for j in jobs], total

    # ── Job writes ────────────────────────────────────────────────────────────

    def create_job(self, job: ExportJob) -> ExportJob:
        self._session.add(job)
        self._session.flush()
        return job

    def update_job_status(
        self,
        job: ExportJob,
        *,
        status: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        file_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if status not in EXPORT_JOB_STATUS_VALUES:
            raise ValueError(f"Invalid export job status: {status!r}")
        job.status = status
        if started_at is not None:
            job.started_at = started_at
        if finished_at is not None:
            job.finished_at = finished_at
        if file_path is not None:
            job.file_path = file_path
        if error_message is not None:
            job.error_message = error_message
        self._session.flush()

    def clear_job_file(self, job: ExportJob) -> None:
        """Remove stored file reference after physical deletion."""
        job.file_path = None
        self._session.flush()

    # ── Template reads ────────────────────────────────────────────────────────

    def get_template(self, template_id: str) -> ExportTemplate | None:
        return self._session.get(ExportTemplate, template_id)

    def require_template(self, template_id: str) -> ExportTemplate:
        tmpl = self.get_template(template_id)
        if tmpl is None:
            raise KeyError(f"ExportTemplate {template_id!r} not found")
        return tmpl

    def get_default_template(self, export_format: str) -> ExportTemplate | None:
        stmt = (
            select(ExportTemplate)
            .where(ExportTemplate.export_format == export_format)
            .where(ExportTemplate.is_default.is_(True))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def list_templates(
        self,
        *,
        export_format: str | None = None,
    ) -> list[ExportTemplateRecord]:
        stmt = select(ExportTemplate)
        if export_format is not None:
            stmt = stmt.where(ExportTemplate.export_format == export_format)
        stmt = stmt.order_by(ExportTemplate.name)
        templates = self._session.scalars(stmt).all()
        return [_template_to_record(t) for t in templates]

    # ── Template writes ───────────────────────────────────────────────────────

    def create_template(self, template: ExportTemplate) -> ExportTemplate:
        self._session.add(template)
        self._session.flush()
        return template

    def update_template(
        self,
        template: ExportTemplate,
        *,
        name: str | None = None,
        export_format: str | None = None,
        layout_config: dict | None = None,
        updated_at: datetime,
    ) -> None:
        if name is not None:
            template.name = name
        if export_format is not None:
            if export_format not in EXPORT_FORMAT_VALUES:
                raise ValueError(f"Invalid export format: {export_format!r}")
            template.export_format = export_format
        if layout_config is not None:
            template.layout_config = layout_config
        template.updated_at = updated_at
        self._session.flush()

    def set_default_template(
        self,
        template: ExportTemplate,
        *,
        updated_at: datetime,
    ) -> None:
        """Clear existing default for same format, set this one as default."""
        stmt = (
            select(ExportTemplate)
            .where(ExportTemplate.export_format == template.export_format)
            .where(ExportTemplate.is_default.is_(True))
        )
        for existing in self._session.scalars(stmt).all():
            existing.is_default = False
            existing.updated_at = updated_at
        template.is_default = True
        template.updated_at = updated_at
        self._session.flush()

    def delete_template(self, template: ExportTemplate) -> None:
        self._session.delete(template)
        self._session.flush()


# ---------------------------------------------------------------------------
# Private converters
# ---------------------------------------------------------------------------

def _job_to_record(job: ExportJob) -> ExportJobRecord:
    return ExportJobRecord(
        id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        source_type=job.source_type,
        source_ids=job.source_ids,
        export_format=job.export_format,
        file_name=job.file_name,
        file_path=job.file_path,
        error_message=job.error_message,
        created_by=job.created_by,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _template_to_record(template: ExportTemplate) -> ExportTemplateRecord:
    return ExportTemplateRecord(
        id=template.id,
        name=template.name,
        export_format=template.export_format,
        layout_config=template.layout_config,
        is_default=template.is_default,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )
