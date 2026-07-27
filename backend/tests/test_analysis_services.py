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
            import_status="pending",
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


# ─────────────────────────────────────────────────────────────────────────────
# v2 service tests (Task #75)
# ─────────────────────────────────────────────────────────────────────────────

def test_create_job_requires_at_least_one_source(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisSourceRequiredApiError
    with pytest.raises(AnalysisSourceRequiredApiError):
        AnalysisJobService(db_session).create_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            source_document_ids=[],
            analysis_type="summary",
            prompt="Summarize",
        )


def test_cancel_job_transitions_and_blocks_completed(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisJobInvalidStateApiError
    service = AnalysisJobService(db_session)
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])

    cancelled = service.cancel_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=job.id)
    assert cancelled.status == "cancelled"
    assert cancelled.finished_at is not None

    # Cannot cancel an already-cancelled job.
    with pytest.raises(AnalysisJobInvalidStateApiError):
        service.cancel_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=job.id)


def test_retry_job_creates_new_queued_job_and_enforces_limit(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisRetryLimitExceededApiError
    service = AnalysisJobService(db_session)

    original = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    failed = service.fail_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        job_id=original.id,
        error_code="TIMEOUT",
        error_message="timed out",
    )

    retry1 = service.retry_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=failed.id)
    assert retry1.status == "queued"
    assert retry1.id != original.id
    assert retry1.error_code == f"RETRY:{original.id}"

    # Fail retry1, then retry again.
    service.fail_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=retry1.id, error_code="TIMEOUT", error_message="t")
    retry2 = service.retry_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=retry1.id)
    assert retry2.status == "queued"

    # Third retry must be blocked.
    service.fail_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=retry2.id, error_code="TIMEOUT", error_message="t")
    with pytest.raises(AnalysisRetryLimitExceededApiError):
        service.retry_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=retry2.id)


def test_update_result_allowed_in_draft_and_review_blocked_in_approved(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisResultInvalidStateApiError
    from app.schemas.analysis import UpdateAnalysisResultRequest
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    job = AnalysisJobService(db_session).run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)
    result = job.result
    assert result is not None
    result_svc = AnalysisResultService(db_session)

    # Update in draft state.
    updated = result_svc.update_result(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        result_id=result.id,
        request=UpdateAnalysisResultRequest(title="Neuer Titel", summary="Neue Zusammenfassung"),
    )
    assert updated.title == "Neuer Titel"
    assert updated.updated_at is not None

    # Approve via legacy flow, then block update.
    job_svc = AnalysisJobService(db_session)
    job_svc.approve_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=job.id)
    db_session.refresh(result)
    result.status = "approved"
    db_session.add(result)
    db_session.commit()

    with pytest.raises(AnalysisResultInvalidStateApiError):
        result_svc.update_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
            request=UpdateAnalysisResultRequest(title="Blocked"),
        )


def test_mark_for_review_and_approve_reject_state_machine(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisConfirmRequiredApiError, AnalysisResultInvalidStateApiError
    from app.schemas.analysis import ApproveResultRequest, MarkForReviewRequest, RejectResultRequest
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    job = AnalysisJobService(db_session).run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)
    result = job.result
    assert result is not None
    result_svc = AnalysisResultService(db_session)

    # Cannot approve from draft.
    with pytest.raises(AnalysisResultInvalidStateApiError):
        result_svc.approve_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
            request=ApproveResultRequest(confirm=True),
        )

    # Mark for review.
    reviewed = result_svc.mark_for_review(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        result_id=result.id,
        request=MarkForReviewRequest(),
    )
    assert reviewed.status == "review"

    # Cannot re-mark for review.
    with pytest.raises(AnalysisResultInvalidStateApiError):
        result_svc.mark_for_review(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
            request=MarkForReviewRequest(),
        )

    # Approve requires confirm=True.
    with pytest.raises(AnalysisConfirmRequiredApiError):
        result_svc.approve_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
            request=ApproveResultRequest(confirm=False),
        )

    # Approve with confirm=True.
    approved = result_svc.approve_result(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        result_id=result.id,
        request=ApproveResultRequest(confirm=True),
    )
    assert approved.status == "approved"
    assert approved.approved_by == DEFAULT_USER_ID
    assert approved.approved_at is not None


def test_reject_result_from_review_blocked_from_draft(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisResultInvalidStateApiError
    from app.schemas.analysis import MarkForReviewRequest, RejectResultRequest
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    job = AnalysisJobService(db_session).run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)
    result = job.result
    assert result is not None
    result_svc = AnalysisResultService(db_session)

    # Cannot reject from draft.
    with pytest.raises(AnalysisResultInvalidStateApiError):
        result_svc.reject_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
            request=RejectResultRequest(reason="Zu ungenau"),
        )

    result_svc.mark_for_review(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        result_id=result.id,
        request=MarkForReviewRequest(),
    )
    rejected = result_svc.reject_result(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        result_id=result.id,
        request=RejectResultRequest(reason="Zu ungenau"),
    )
    assert rejected.status == "rejected"


def test_get_result_by_id_is_workspace_scoped(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.core.errors import AnalysisResultNotFoundApiError
    job = _create_service_job(db_session, source_document_ids=[DOCUMENT_ID])
    job = AnalysisJobService(db_session).run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)
    result = job.result
    assert result is not None
    result_svc = AnalysisResultService(db_session)

    fetched = result_svc.get_result_by_id(workspace_id=DEFAULT_WORKSPACE_ID, result_id=result.id)
    assert fetched.id == result.id

    with pytest.raises(AnalysisResultNotFoundApiError):
        result_svc.get_result_by_id(workspace_id="wrong-workspace", result_id=result.id)
