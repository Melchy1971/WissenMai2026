from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AnalysisJobInvalidStateApiError, AnalysisJobNotFoundApiError, DocumentNotFoundApiError
from app.models.analysis import AnalysisJob
from app.models.documents import Document, Workspace
from app.services.analysis.service import AnalysisComparisonService, AnalysisJobService, AnalysisResultService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID, OLDER_DOCUMENT_ID

pytestmark = pytest.mark.unit_fast


def _create_service_job(db_session: Session, *, source_document_ids: list[str] | None = None) -> AnalysisJob:
    return AnalysisJobService(db_session).create_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        source_document_ids=source_document_ids or [DOCUMENT_ID, OLDER_DOCUMENT_ID],
        analysis_type="comparison",
        prompt="Compare contracts",
    )


def _add_other_workspace_document(db_session: Session) -> str:
    now = datetime.now(UTC)
    workspace_id = "analysis-services-other-workspace"
    document_id = "analysis-services-other-document"
    db_session.add(Workspace(id=workspace_id, name="Other", is_default=False, created_at=now))
    db_session.add(
        Document(
            id=document_id,
            workspace_id=workspace_id,
            owner_user_id=DEFAULT_USER_ID,
            current_version_id=None,
            title="Other workspace document",
            source_type="upload",
            mime_type="text/plain",
            content_hash="analysis-services-other-document-hash",
            import_status="parsed",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    return document_id


def test_job_service_create_get_and_list_are_workspace_scoped(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    service = AnalysisJobService(db_session)
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])

    fetched = service.get_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)
    jobs, total = service.list_jobs(workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0, status=None)

    assert fetched.id == job.id
    assert total == 1
    assert [item.id for item in jobs] == [job.id]
    with pytest.raises(AnalysisJobNotFoundApiError):
        service.get_job(workspace_id="wrong-workspace", job_id=job.id)


def test_job_service_rejects_foreign_workspace_documents(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    foreign_document_id = _add_other_workspace_document(db_session)

    with pytest.raises(DocumentNotFoundApiError):
        AnalysisJobService(db_session).create_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            source_document_ids=[foreign_document_id],
            analysis_type="summary",
            prompt="Summarize",
        )


def test_run_and_fail_validate_status_transitions(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    service = AnalysisJobService(db_session)
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])

    failed = service.fail_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        job_id=job.id,
        error_code="PROVIDER_ERROR",
        error_message="Provider failed",
    )
    assert failed.status == "failed"
    assert failed.error_code == "PROVIDER_ERROR"

    with pytest.raises(AnalysisJobInvalidStateApiError):
        service.run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)


def test_result_service_create_and_get_result_are_workspace_scoped(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    job.status = "running"
    db_session.add(job)
    db_session.commit()
    result_service = AnalysisResultService(db_session)

    result = result_service.create_result(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)

    job.status = "completed"
    job.finished_at = datetime.now(UTC)
    db_session.add(job)
    db_session.commit()

    assert result.summary
    assert result_service.get_result(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id).id == result.id
    with pytest.raises(AnalysisJobNotFoundApiError):
        result_service.get_result(workspace_id="wrong-workspace", job_id=job.id)


def test_result_service_rejects_pending_jobs(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])

    with pytest.raises(AnalysisJobInvalidStateApiError):
        AnalysisResultService(db_session).create_result(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)


def test_comparison_service_blocks_foreign_workspace_documents(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    foreign_document_id = _add_other_workspace_document(db_session)

    with pytest.raises(DocumentNotFoundApiError):
        AnalysisComparisonService(db_session).compare_with_existing(
            workspace_id=DEFAULT_WORKSPACE_ID,
            job_id=job.id,
            compared_document_ids=[foreign_document_id],
        )


def test_comparison_service_create_and_get_comparison(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _create_service_job(db_session)
    service = AnalysisComparisonService(db_session)

    comparison = service.compare_with_existing(
        workspace_id=DEFAULT_WORKSPACE_ID,
        job_id=job.id,
        compared_document_ids=[OLDER_DOCUMENT_ID],
    )

    assert comparison.compared_document_ids == [OLDER_DOCUMENT_ID]
    assert service.get_comparison(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id).id == comparison.id
    with pytest.raises(AnalysisJobNotFoundApiError):
        service.get_comparison(workspace_id="wrong-workspace", job_id=job.id)


def test_approve_job_is_idempotent_and_never_approves_without_result(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    service = AnalysisJobService(db_session)
    pending_job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])

    with pytest.raises(AnalysisJobInvalidStateApiError):
        service.approve_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=pending_job.id)

    completed = service.run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=pending_job.id)
    approved = service.approve_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=completed.id)
    approved_again = service.approve_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=completed.id)

    assert approved.status == "approved"
    assert approved_again.status == "approved"
    assert [item.approved_by for item in approved_again.suggestions] == [DEFAULT_USER_ID]
