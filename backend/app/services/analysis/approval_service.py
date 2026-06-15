from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    AnalysisJobInvalidStateApiError,
    AnalysisJobNotFoundApiError,
    AnalysisResultNotReadyApiError,
)
from app.models.analysis import AnalysisJob


ANALYSIS_JOB_APPROVED_AUDIT_EVENT = "ANALYSIS_JOB_APPROVED"


@dataclass(frozen=True)
class AnalysisApprovalAuditEvent:
    action: str
    actor: str
    workspace_id: str
    job_id: str
    suggestion_ids: list[str]
    approved_at: datetime

    @property
    def details(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "job_id": self.job_id,
            "suggestion_ids": self.suggestion_ids,
            "approved_at": self.approved_at.isoformat(),
        }


class AnalysisApprovalAuditRecorder(Protocol):
    def record(self, event: AnalysisApprovalAuditEvent) -> None:
        ...


class InMemoryAnalysisApprovalAuditRecorder:
    def record(self, event: AnalysisApprovalAuditEvent) -> None:
        from app.api.v1.approvals import _log_audit

        _log_audit(event.action, event.actor, event.job_id, event.details)


class AnalysisApprovalService:
    def __init__(
        self,
        session: Session,
        *,
        audit_recorder: AnalysisApprovalAuditRecorder | None = None,
    ) -> None:
        self._session = session
        self._audit_recorder = audit_recorder or InMemoryAnalysisApprovalAuditRecorder()

    def approve_job(self, *, workspace_id: str, user_id: str, job_id: str) -> AnalysisJob:
        job = self._require_job(workspace_id=workspace_id, job_id=job_id)
        if job.status == "approved":
            return job
        if job.status != "completed":
            raise AnalysisJobInvalidStateApiError(
                details={"current_status": job.status, "required_status": "completed", "action": "approve"}
            )
        if job.result is None:
            raise AnalysisResultNotReadyApiError(
                details={"current_status": job.status, "required_status": "completed"}
            )

        approved_at = datetime.now(UTC)
        approved_suggestion_ids: list[str] = []
        for suggestion in job.suggestions:
            suggestion.status = "approved"
            suggestion.approved_by = user_id
            suggestion.approved_at = approved_at
            approved_suggestion_ids.append(suggestion.id)
            self._session.add(suggestion)

        job.status = "approved"
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)

        self._audit_recorder.record(
            AnalysisApprovalAuditEvent(
                action=ANALYSIS_JOB_APPROVED_AUDIT_EVENT,
                actor=user_id,
                workspace_id=workspace_id,
                job_id=job_id,
                suggestion_ids=approved_suggestion_ids,
                approved_at=approved_at,
            )
        )
        return job

    def _require_job(self, *, workspace_id: str, job_id: str) -> AnalysisJob:
        job = self._session.scalar(
            select(AnalysisJob).where(
                AnalysisJob.id == job_id,
                AnalysisJob.workspace_id == workspace_id,
            )
        )
        if job is None:
            raise AnalysisJobNotFoundApiError(details={"job_id": job_id})
        return job
