"""Test seed data for Export Center contract tests."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.export import ExportJob, ExportTemplate
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID

# Fixed IDs for predictable assertions
JOB_ID_QUEUED = "export-job-queued-0001"
JOB_ID_RUNNING = "export-job-running-001"
JOB_ID_COMPLETED = "export-job-completed-1"
JOB_ID_FAILED = "export-job-failed-0001"
JOB_ID_CANCELLED = "export-job-cancelled-1"
TEMPLATE_ID_DEFAULT = "export-tmpl-default-1"
RESULT_ID_APPROVED = "analysis-result-apprv1"


def _now() -> datetime:
    return datetime.now(UTC)


def make_approved_result(result_id: str = RESULT_ID_APPROVED) -> AnalysisResult:
    now = _now()
    return AnalysisResult(
        id=result_id,
        job_id=str(uuid4()),
        summary="Approved result summary",
        key_points=["Point 1", "Point 2"],
        suggested_tags=["tag-a"],
        suggested_topics=["Topic A"],
        confidence=0.9,
        status="approved",
        approved_by=DEFAULT_USER_ID,
        approved_at=now,
        created_at=now,
    )


def make_export_job(
    job_id: str,
    *,
    status: str = "QUEUED",
    export_format: str = "MARKDOWN",
    source_ids: list[str] | None = None,
    file_path: str | None = None,
    error_message: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> ExportJob:
    now = _now()
    return ExportJob(
        id=job_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        status=status,
        source_type="ANALYSIS_RESULT",
        source_ids=source_ids or [RESULT_ID_APPROVED],
        export_format=export_format,
        file_name=f"export_{status.lower()}.{export_format.lower()}",
        file_path=file_path,
        error_message=error_message,
        created_by=DEFAULT_USER_ID,
        created_at=now,
        started_at=started_at,
        finished_at=finished_at,
    )


def make_export_template(
    template_id: str = TEMPLATE_ID_DEFAULT,
    *,
    name: str = "Standard PDF",
    export_format: str = "PDF",
    is_default: bool = True,
) -> ExportTemplate:
    now = _now()
    return ExportTemplate(
        id=template_id,
        name=name,
        export_format=export_format,
        layout_config={"font_size": 10},
        is_default=is_default,
        created_at=now,
        updated_at=now,
    )


def seed_queued_job(session: Session) -> ExportJob:
    result = make_approved_result()
    session.add(result)
    job = make_export_job(JOB_ID_QUEUED, status="QUEUED")
    session.add(job)
    session.flush()
    return job


def seed_completed_job(session: Session, *, file_path: str = "some-job-id/export.md") -> ExportJob:
    result = make_approved_result()
    session.add(result)
    now = _now()
    job = make_export_job(
        JOB_ID_COMPLETED,
        status="COMPLETED",
        file_path=file_path,
        started_at=now,
        finished_at=now,
    )
    session.add(job)
    session.flush()
    return job


def seed_failed_job(session: Session) -> ExportJob:
    result = make_approved_result()
    session.add(result)
    now = _now()
    job = make_export_job(
        JOB_ID_FAILED,
        status="FAILED",
        error_message="Render failed: out of memory",
        started_at=now,
        finished_at=now,
    )
    session.add(job)
    session.flush()
    return job


def seed_cancelled_job(session: Session) -> ExportJob:
    result = make_approved_result()
    session.add(result)
    job = make_export_job(JOB_ID_CANCELLED, status="CANCELLED")
    session.add(job)
    session.flush()
    return job


def seed_default_template(session: Session) -> ExportTemplate:
    tmpl = make_export_template()
    session.add(tmpl)
    session.flush()
    return tmpl
