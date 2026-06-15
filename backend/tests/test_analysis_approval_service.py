from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AnalysisJobInvalidStateApiError
from app.models.analysis import AnalysisComparison
from app.services.analysis.approval_service import (
    ANALYSIS_JOB_APPROVED_AUDIT_EVENT,
    AnalysisApprovalAuditEvent,
    AnalysisApprovalService,
)
from app.services.analysis.service import AnalysisComparisonService, AnalysisJobService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID, OLDER_DOCUMENT_ID

pytestmark = pytest.mark.unit_fast


@dataclass
class RecordingAuditRecorder:
    events: list[AnalysisApprovalAuditEvent] = field(default_factory=list)

    def record(self, event: AnalysisApprovalAuditEvent) -> None:
        self.events.append(event)


def _completed_job(db_session: Session):
    job_service = AnalysisJobService(db_session)
    job = job_service.create_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        source_document_ids=[DOCUMENT_ID, OLDER_DOCUMENT_ID],
        analysis_type="comparison",
        prompt="Compare",
    )
    AnalysisComparisonService(db_session).compare_with_existing(
        workspace_id=DEFAULT_WORKSPACE_ID,
        job_id=job.id,
        compared_document_ids=[OLDER_DOCUMENT_ID],
    )
    return job_service.run_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=job.id)


def test_approval_service_allows_only_completed_jobs(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = AnalysisJobService(db_session).create_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        source_document_ids=[DOCUMENT_ID],
        analysis_type="summary",
        prompt="Summarize",
    )

    with pytest.raises(AnalysisJobInvalidStateApiError):
        AnalysisApprovalService(db_session, audit_recorder=RecordingAuditRecorder()).approve_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            job_id=job.id,
        )


def test_approval_sets_suggestions_to_approved_and_writes_audit_event(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _completed_job(db_session)
    recorder = RecordingAuditRecorder()

    approved = AnalysisApprovalService(db_session, audit_recorder=recorder).approve_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        job_id=job.id,
    )

    assert approved.status == "approved"
    assert approved.suggestions
    assert {suggestion.status for suggestion in approved.suggestions} == {"approved"}
    assert {suggestion.approved_by for suggestion in approved.suggestions} == {DEFAULT_USER_ID}
    assert all(suggestion.approved_at is not None for suggestion in approved.suggestions)
    assert len(recorder.events) == 1
    assert recorder.events[0].action == ANALYSIS_JOB_APPROVED_AUDIT_EVENT
    assert recorder.events[0].actor == DEFAULT_USER_ID
    assert recorder.events[0].workspace_id == DEFAULT_WORKSPACE_ID
    assert recorder.events[0].job_id == job.id
    assert recorder.events[0].suggestion_ids == [suggestion.id for suggestion in approved.suggestions]


def test_approval_does_not_modify_result_or_comparison_payloads(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _completed_job(db_session)
    result_snapshot = {
        "summary": job.result.summary,
        "key_points": list(job.result.key_points),
        "suggested_tags": list(job.result.suggested_tags),
        "suggested_topics": list(job.result.suggested_topics),
        "confidence": job.result.confidence,
    }
    comparison = job.comparison
    assert isinstance(comparison, AnalysisComparison)
    comparison_snapshot = {
        "compared_document_ids": comparison.compared_document_ids,
        "overlaps": list(comparison.overlaps),
        "differences": list(comparison.differences),
        "suggested_merge": comparison.suggested_merge,
    }

    approved = AnalysisApprovalService(db_session, audit_recorder=RecordingAuditRecorder()).approve_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        job_id=job.id,
    )

    assert {
        "summary": approved.result.summary,
        "key_points": list(approved.result.key_points),
        "suggested_tags": list(approved.result.suggested_tags),
        "suggested_topics": list(approved.result.suggested_topics),
        "confidence": approved.result.confidence,
    } == result_snapshot
    assert {
        "compared_document_ids": approved.comparison.compared_document_ids,
        "overlaps": list(approved.comparison.overlaps),
        "differences": list(approved.comparison.differences),
        "suggested_merge": approved.comparison.suggested_merge,
    } == comparison_snapshot


def test_repeated_approve_is_idempotent(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    job = _completed_job(db_session)
    recorder = RecordingAuditRecorder()
    service = AnalysisApprovalService(db_session, audit_recorder=recorder)

    first = service.approve_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=job.id)
    first_approved_at = [suggestion.approved_at for suggestion in first.suggestions]
    second = service.approve_job(workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID, job_id=job.id)

    assert second.status == "approved"
    assert [suggestion.approved_at for suggestion in second.suggestions] == first_approved_at
    assert len(recorder.events) == 1


def test_default_approval_recorder_writes_audit_event(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    from app.api.v1.approvals import get_audit_log

    get_audit_log().clear()
    job = _completed_job(db_session)

    AnalysisApprovalService(db_session).approve_job(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        job_id=job.id,
    )

    events = get_audit_log()
    assert len(events) == 1
    assert events[0]["action"] == ANALYSIS_JOB_APPROVED_AUDIT_EVENT
    assert events[0]["actor"] == DEFAULT_USER_ID
    assert events[0]["resource_id"] == job.id
    assert events[0]["details"]["workspace_id"] == DEFAULT_WORKSPACE_ID
    assert events[0]["details"]["job_id"] == job.id
