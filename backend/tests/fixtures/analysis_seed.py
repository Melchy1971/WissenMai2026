"""Seed helpers for analysis job / result tests.

Import into conftest or test files:

    from tests.fixtures.analysis_seed import make_analysis_job, make_analysis_result

All helpers operate on a SQLAlchemy Session and flush (not commit) by default
so the test transaction can be rolled back cleanly.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisJob, AnalysisResult


# ── Default UUIDs for deterministic test data ─────────────────────────────────
JOB_ID_QUEUED     = "a0000000-0000-0000-0000-000000000001"
JOB_ID_RUNNING    = "a0000000-0000-0000-0000-000000000002"
JOB_ID_COMPLETED  = "a0000000-0000-0000-0000-000000000003"
JOB_ID_FAILED     = "a0000000-0000-0000-0000-000000000004"
JOB_ID_CANCELLED  = "a0000000-0000-0000-0000-000000000005"
RESULT_ID_DRAFT   = "b0000000-0000-0000-0000-000000000001"
RESULT_ID_REVIEW  = "b0000000-0000-0000-0000-000000000002"
RESULT_ID_APPROVED= "b0000000-0000-0000-0000-000000000003"
RESULT_ID_REJECTED= "b0000000-0000-0000-0000-000000000004"


def _now() -> datetime:
    return datetime.now(UTC)


def make_analysis_job(
    session: Session,
    *,
    workspace_id: str,
    created_by: str,
    document_ids: list[str],
    job_id: str | None = None,
    status: str = "queued",
    source_type: str = "DOCUMENTS",
    analysis_type: str = "summary",
    prompt: str = "Fasse die Dokumente zusammen.",
    provider: str | None = "ollama",
    model: str | None = "llama3",
    flush: bool = True,
) -> AnalysisJob:
    job = AnalysisJob(
        id=job_id or str(uuid4()),
        workspace_id=workspace_id,
        status=status,
        analysis_type=analysis_type,
        source_type=source_type,
        source_ids=document_ids,
        prompt=prompt,
        provider=provider,
        model=model,
        created_by=created_by,
        created_at=_now(),
    )
    job.source_document_ids = document_ids
    session.add(job)
    if flush:
        session.flush()
    return job


def make_analysis_result(
    session: Session,
    *,
    job: AnalysisJob,
    result_id: str | None = None,
    title: str = "Analyseergebnis",
    summary: str = "Zusammenfassung der Dokumente.",
    content_markdown: str = "## Ergebnis\n\nDas ist das Ergebnis.",
    sources: list[dict] | None = None,
    confidence: float | None = 0.85,
    status: str = "draft",
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    flush: bool = True,
) -> AnalysisResult:
    if sources is None:
        sources = [
            {"kind": "document", "id": sid, "title": f"Dokument {i+1}", "excerpt": None}
            for i, sid in enumerate(job.source_document_ids[:3])
        ]
    result = AnalysisResult(
        id=result_id or str(uuid4()),
        job_id=job.id,
        title=title,
        summary=summary,
        content_markdown=content_markdown,
        key_points=["Punkt 1", "Punkt 2"],
        suggested_tags=["analyse", "zusammenfassung"],
        suggested_topics=[],
        sources=sources,
        confidence=confidence,
        status=status,
        approved_by=approved_by,
        approved_at=approved_at,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(result)
    if flush:
        session.flush()
    # Update denormalized backpointer
    job.result_id = result.id
    if flush:
        session.flush()
    return result


# ── Scenario builders (complete state combinations) ───────────────────────────

def seed_queued_job(session: Session, workspace_id: str, created_by: str, doc_ids: list[str]) -> AnalysisJob:
    return make_analysis_job(session, workspace_id=workspace_id, created_by=created_by,
                             document_ids=doc_ids, job_id=JOB_ID_QUEUED, status="queued")


def seed_running_job(session: Session, workspace_id: str, created_by: str, doc_ids: list[str]) -> AnalysisJob:
    job = make_analysis_job(session, workspace_id=workspace_id, created_by=created_by,
                            document_ids=doc_ids, job_id=JOB_ID_RUNNING, status="running", flush=False)
    job.started_at = _now()
    session.flush()
    return job


def seed_completed_job_with_result(
    session: Session, workspace_id: str, created_by: str, doc_ids: list[str]
) -> tuple[AnalysisJob, AnalysisResult]:
    now = _now()
    job = make_analysis_job(session, workspace_id=workspace_id, created_by=created_by,
                            document_ids=doc_ids, job_id=JOB_ID_COMPLETED, status="completed", flush=False)
    job.started_at = now
    job.finished_at = now
    session.flush()
    result = make_analysis_result(session, job=job, result_id=RESULT_ID_DRAFT, status="draft")
    return job, result


def seed_failed_job(session: Session, workspace_id: str, created_by: str, doc_ids: list[str]) -> AnalysisJob:
    job = make_analysis_job(session, workspace_id=workspace_id, created_by=created_by,
                            document_ids=doc_ids, job_id=JOB_ID_FAILED, status="failed", flush=False)
    now = _now()
    job.started_at = now
    job.finished_at = now
    job.error_code = "PROVIDER_TIMEOUT"
    job.error_message = "Provider hat nicht innerhalb von 60s geantwortet."
    session.flush()
    return job


def seed_cancelled_job(session: Session, workspace_id: str, created_by: str, doc_ids: list[str]) -> AnalysisJob:
    job = make_analysis_job(session, workspace_id=workspace_id, created_by=created_by,
                            document_ids=doc_ids, job_id=JOB_ID_CANCELLED, status="cancelled", flush=False)
    job.finished_at = _now()
    session.flush()
    return job
