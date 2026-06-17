"""ExportService unit tests.

Covers: Export Markdown, Export JSON, Export PDF (stub), invalid source,
Draft Analysis blockiert, fehlende Datei, Download nach Completed.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.errors import (
    ExportFileNotFoundApiError,
    ExportJobInvalidStateApiError,
    ExportJobNotFoundApiError,
    ExportSourceNotApprovedApiError,
    ExportSourceNotFoundApiError,
    ExportTemplateNotFoundApiError,
)
from app.models.analysis import AnalysisResult
from app.models.export import ExportJob, ExportTemplate
from app.services.export.service import ExportService, _normalize_filename
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID

pytestmark = pytest.mark.unit_fast

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESULT_ID = "result-approved-001"
DRAFT_RESULT_ID = "result-draft-001"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(UTC)


def _make_approved_result(db_session: Session, result_id: str = RESULT_ID) -> AnalysisResult:
    result = AnalysisResult(
        id=result_id,
        job_id="job-001",
        summary="Summary text",
        key_points=["Point A", "Point B"],
        suggested_tags=["tag1", "tag2"],
        suggested_topics=["Topic X"],
        confidence=0.85,
        status="approved",
        approved_by=DEFAULT_USER_ID,
        approved_at=_now(),
        created_at=_now(),
    )
    db_session.add(result)
    db_session.flush()
    return result


def _make_draft_result(db_session: Session) -> AnalysisResult:
    result = AnalysisResult(
        id=DRAFT_RESULT_ID,
        job_id="job-002",
        summary="Draft summary",
        key_points=[],
        suggested_tags=[],
        suggested_topics=[],
        confidence=0.5,
        status="draft",
        approved_by=None,
        approved_at=None,
        created_at=_now(),
    )
    db_session.add(result)
    db_session.flush()
    return result


def _stub_renderer(format_: str = "MARKDOWN") -> MagicMock:
    renderer = MagicMock()
    renderer.render.return_value = b"rendered content"
    return renderer


def _make_service(
    db_session: Session,
    *,
    renderer=None,
    tmp_path: Path | None = None,
) -> ExportService:
    return ExportService(
        db_session,
        renderer=renderer or _stub_renderer(),
        export_root=tmp_path or Path("/tmp/export-test"),
    )


# ---------------------------------------------------------------------------
# _normalize_filename
# ---------------------------------------------------------------------------

def test_normalize_filename_strips_unsafe_chars() -> None:
    assert _normalize_filename("my report!", "MARKDOWN") == "my_report_.md"


def test_normalize_filename_enforces_extension() -> None:
    result = _normalize_filename("report.txt", "PDF")
    assert result.endswith(".pdf")


def test_normalize_filename_fallback() -> None:
    assert _normalize_filename("", "JSON") == "export.json"


# ---------------------------------------------------------------------------
# createExportJob — approved analysis result
# ---------------------------------------------------------------------------

def test_create_export_job_approved_result(db_session: Session) -> None:
    _make_approved_result(db_session)
    service = _make_service(db_session)
    record = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="my_export",
    )
    assert record.status == "QUEUED"
    assert record.export_format == "MARKDOWN"
    assert record.file_name == "my_export.md"
    assert record.file_path is None


def test_create_export_job_sets_workspace_and_creator(db_session: Session) -> None:
    _make_approved_result(db_session)
    service = _make_service(db_session)
    record = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="JSON",
        file_name="export",
        created_by=DEFAULT_USER_ID,
    )
    assert record.workspace_id == DEFAULT_WORKSPACE_ID
    assert record.created_by == DEFAULT_USER_ID


# ---------------------------------------------------------------------------
# createExportJob — Draft Analysis blockiert (approved-only guard)
# ---------------------------------------------------------------------------

def test_create_export_job_blocks_draft_analysis(db_session: Session) -> None:
    _make_draft_result(db_session)
    service = _make_service(db_session)
    with pytest.raises(ExportSourceNotApprovedApiError):
        service.create_export_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            source_type="ANALYSIS_RESULT",
            source_ids=[DRAFT_RESULT_ID],
            export_format="PDF",
            file_name="draft_export",
        )


def test_create_export_job_blocks_review_status(db_session: Session) -> None:
    result = _make_draft_result(db_session)
    result.status = "review"
    db_session.flush()
    service = _make_service(db_session)
    with pytest.raises(ExportSourceNotApprovedApiError):
        service.create_export_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            source_type="ANALYSIS_RESULT",
            source_ids=[DRAFT_RESULT_ID],
            export_format="MARKDOWN",
            file_name="review_export",
        )


def test_create_export_job_blocks_unknown_result(db_session: Session) -> None:
    service = _make_service(db_session)
    with pytest.raises(ExportSourceNotFoundApiError):
        service.create_export_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            source_type="ANALYSIS_RESULT",
            source_ids=["nonexistent-result"],
            export_format="MARKDOWN",
            file_name="missing",
        )


# ---------------------------------------------------------------------------
# Export Markdown
# ---------------------------------------------------------------------------

def test_export_markdown(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    renderer = MagicMock()
    renderer.render.return_value = b"# My Export\n\nSummary text"
    service = _make_service(db_session, renderer=renderer, tmp_path=tmp_path)

    job_record = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="my_export",
    )
    completed = service.start_export_job(job_record.id)

    assert completed.status == "COMPLETED"
    assert completed.file_path is not None
    renderer.render.assert_called_once()
    call_kwargs = renderer.render.call_args.kwargs
    assert call_kwargs["export_format"] == "MARKDOWN"
    assert "results" in call_kwargs["content"]


# ---------------------------------------------------------------------------
# Export JSON
# ---------------------------------------------------------------------------

def test_export_json(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    captured: list[dict] = []

    class JsonCapturingRenderer:
        def render(self, *, content: dict, export_format: str) -> bytes:
            captured.append(content)
            return json.dumps(content, default=str).encode()

    service = _make_service(db_session, renderer=JsonCapturingRenderer(), tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="JSON",
        file_name="export",
    )
    completed = service.start_export_job(job.id)
    assert completed.status == "COMPLETED"
    assert len(captured) == 1
    content = captured[0]
    # No technical UUIDs in content keys
    assert "id" not in content
    assert "results" in content
    result = content["results"][0]
    assert result["summary"] == "Summary text"


# ---------------------------------------------------------------------------
# Export PDF (renderer stub)
# ---------------------------------------------------------------------------

def test_export_pdf_calls_renderer(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    renderer = MagicMock()
    renderer.render.return_value = b"%PDF-1.4 stub"
    service = _make_service(db_session, renderer=renderer, tmp_path=tmp_path)

    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="PDF",
        file_name="report",
    )
    completed = service.start_export_job(job.id)
    assert completed.status == "COMPLETED"
    assert renderer.render.call_args.kwargs["export_format"] == "PDF"


# ---------------------------------------------------------------------------
# Download nach Completed
# ---------------------------------------------------------------------------

def test_download_export_file_after_completed(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    renderer = MagicMock()
    renderer.render.return_value = b"file content bytes"
    service = _make_service(db_session, renderer=renderer, tmp_path=tmp_path)

    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="download_me",
    )
    service.start_export_job(job.id)
    file_bytes, file_name = service.download_export_file(job.id)

    assert file_bytes == b"file content bytes"
    assert file_name.endswith(".md")


def test_download_fails_when_not_completed(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    service = _make_service(db_session, tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="pending_job",
    )
    # Job is still QUEUED — no file yet
    with pytest.raises(ExportFileNotFoundApiError):
        service.download_export_file(job.id)


# ---------------------------------------------------------------------------
# fehlende Datei
# ---------------------------------------------------------------------------

def test_download_fails_when_file_physically_missing(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    renderer = MagicMock()
    renderer.render.return_value = b"bytes"
    service = _make_service(db_session, renderer=renderer, tmp_path=tmp_path)

    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="JSON",
        file_name="will_be_deleted",
    )
    service.start_export_job(job.id)
    # Physically remove the file
    completed = service.get_export_job(job.id)
    (tmp_path / completed.file_path).unlink()

    with pytest.raises(ExportFileNotFoundApiError):
        service.download_export_file(job.id)


# ---------------------------------------------------------------------------
# cancelExportJob / retryExportJob
# ---------------------------------------------------------------------------

def test_cancel_queued_job(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    service = _make_service(db_session, tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="cancel_me",
    )
    cancelled = service.cancel_export_job(job.id)
    assert cancelled.status == "CANCELLED"


def test_cancel_completed_job_raises(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    renderer = MagicMock()
    renderer.render.return_value = b"done"
    service = _make_service(db_session, renderer=renderer, tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="completed_job",
    )
    service.start_export_job(job.id)
    with pytest.raises(ExportJobInvalidStateApiError):
        service.cancel_export_job(job.id)


def test_retry_failed_job_creates_new_job(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    failing_renderer = MagicMock()
    failing_renderer.render.side_effect = RuntimeError("render failed")
    service = _make_service(db_session, renderer=failing_renderer, tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="retry_me",
    )
    with pytest.raises(RuntimeError):
        service.start_export_job(job.id)

    failed = service.get_export_job(job.id)
    assert failed.status == "FAILED"

    retry_job = service.retry_export_job(job.id)
    assert retry_job.status == "QUEUED"
    assert retry_job.id != job.id
    assert retry_job.export_format == "MARKDOWN"


def test_retry_queued_job_raises(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    service = _make_service(db_session, tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="JSON",
        file_name="not_failed",
    )
    with pytest.raises(ExportJobInvalidStateApiError):
        service.retry_export_job(job.id)


# ---------------------------------------------------------------------------
# getExportJob / listExportJobs
# ---------------------------------------------------------------------------

def test_get_export_job_not_found(db_session: Session, tmp_path: Path) -> None:
    service = _make_service(db_session, tmp_path=tmp_path)
    with pytest.raises(ExportJobNotFoundApiError):
        service.get_export_job("nonexistent")


def test_list_export_jobs_empty(db_session: Session, tmp_path: Path) -> None:
    service = _make_service(db_session, tmp_path=tmp_path)
    jobs, total = service.list_export_jobs()
    assert jobs == []
    assert total == 0


def test_list_export_jobs_filters_by_format(db_session: Session, tmp_path: Path) -> None:
    r1 = _make_approved_result(db_session, "r-md")
    r2 = _make_approved_result(db_session, "r-json")

    service = _make_service(db_session, tmp_path=tmp_path)
    service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=["r-md"],
        export_format="MARKDOWN",
        file_name="md_export",
    )
    service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=["r-json"],
        export_format="JSON",
        file_name="json_export",
    )
    jobs, total = service.list_export_jobs(export_format="MARKDOWN")
    assert total == 1
    assert jobs[0].export_format == "MARKDOWN"


# ---------------------------------------------------------------------------
# deleteExportFile
# ---------------------------------------------------------------------------

def test_delete_export_file_clears_path(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    renderer = MagicMock()
    renderer.render.return_value = b"content"
    service = _make_service(db_session, renderer=renderer, tmp_path=tmp_path)

    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="MARKDOWN",
        file_name="delete_me",
    )
    service.start_export_job(job.id)
    service.delete_export_file(job.id)

    record = service.get_export_job(job.id)
    assert record.file_path is None
    assert record.status == "COMPLETED"  # job record retained


def test_delete_export_file_idempotent_when_no_file(db_session: Session, tmp_path: Path) -> None:
    _make_approved_result(db_session)
    service = _make_service(db_session, tmp_path=tmp_path)
    job = service.create_export_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        source_type="ANALYSIS_RESULT",
        source_ids=[RESULT_ID],
        export_format="JSON",
        file_name="no_file",
    )
    # QUEUED job has no file — should not raise
    service.delete_export_file(job.id)
    record = service.get_export_job(job.id)
    assert record.file_path is None


# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------

def test_create_and_list_templates(db_session: Session, tmp_path: Path) -> None:
    service = _make_service(db_session, tmp_path=tmp_path)
    tmpl = service.create_template(name="Default PDF", export_format="PDF", is_default=True)
    assert tmpl.name == "Default PDF"
    assert tmpl.is_default is True

    templates = service.list_templates(export_format="PDF")
    assert len(templates) == 1
    assert templates[0].name == "Default PDF"


def test_delete_template_not_found_raises(db_session: Session, tmp_path: Path) -> None:
    service = _make_service(db_session, tmp_path=tmp_path)
    with pytest.raises(ExportTemplateNotFoundApiError):
        service.delete_template("nonexistent")


def test_update_template_not_found_raises(db_session: Session, tmp_path: Path) -> None:
    service = _make_service(db_session, tmp_path=tmp_path)
    with pytest.raises(ExportTemplateNotFoundApiError):
        service.update_template("nonexistent", name="new name")
