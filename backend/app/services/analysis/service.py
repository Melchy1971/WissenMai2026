from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import (
    AnalysisCompareDocumentMissingApiError,
    AnalysisConfirmRequiredApiError,
    AnalysisJobInvalidStateApiError,
    AnalysisJobNotFoundApiError,
    AnalysisResultInvalidStateApiError,
    AnalysisResultNotFoundApiError,
    AnalysisResultNotReadyApiError,
    AnalysisRetryLimitExceededApiError,
    AnalysisSourceRequiredApiError,
    DocumentNotFoundApiError,
)
from app.models.analysis import AnalysisComparison, AnalysisJob, AnalysisResult, AnalysisSuggestion
from app.models.documents import Document
from app.schemas.analysis import (
    AnalysisComparison as AnalysisComparisonSchema,
    AnalysisJobListItem,
    AnalysisJobListResponse,
    AnalysisJobResponse,
    AnalysisResult as AnalysisResultSchema,
    AnalysisSuggestion as AnalysisSuggestionSchema,
    ApproveRequest,
    ApproveResultRequest,
    CompareRequest,
    CreateAnalysisJobRequest,
    MarkForReviewRequest,
    RejectResultRequest,
    SummarizeRequest,
    UpdateAnalysisResultRequest,
)
from app.services.analysis.analysis_stub_engine import (
    AnalysisComparisonProvider,
    AnalysisProvider,
    DeterministicAnalysisStubEngine,
)
from app.services.analysis.approval_service import (
    ANALYSIS_JOB_CANCELLED_AUDIT_EVENT,
    ANALYSIS_JOB_RETRIED_AUDIT_EVENT,
    ANALYSIS_RESULT_APPROVED_AUDIT_EVENT,
    ANALYSIS_RESULT_MARKED_FOR_REVIEW_AUDIT_EVENT,
    ANALYSIS_RESULT_REJECTED_AUDIT_EVENT,
    AnalysisApprovalAuditRecorder,
    AnalysisApprovalService,
    AnalysisResultAuditEvent,
    InMemoryAnalysisApprovalAuditRecorder,
)
from app.services.analysis.approval_policy import (
    AnalysisApprovalPolicy,
    ApprovalContext,
    ApprovalPolicyViolation,
)

_log = logging.getLogger(__name__)

# Maximum number of retries allowed per original job.
RETRY_LIMIT = 2

# ──────────────────────────────────────────────────────────────────────────────
# Job service
# ──────────────────────────────────────────────────────────────────────────────

class AnalysisJobService:
    def __init__(
        self,
        session: Session,
        *,
        approval_audit_recorder: AnalysisApprovalAuditRecorder | None = None,
    ) -> None:
        self._session = session
        self._audit = approval_audit_recorder or InMemoryAnalysisApprovalAuditRecorder()

    def create_job(
        self,
        *,
        workspace_id: str,
        user_id: str,
        source_document_ids: list[str],
        analysis_type: str,
        prompt: str,
        source_type: str | None = None,
        source_ids: list[str] | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> AnalysisJob:
        effective_doc_ids = _deduplicate(source_document_ids)
        effective_source_ids = _deduplicate(source_ids or [])

        # Source obligation: at least one explicit document or source_id.
        if not effective_doc_ids and not effective_source_ids:
            raise AnalysisSourceRequiredApiError(
                details={"workspace_id": workspace_id, "analysis_type": analysis_type}
            )

        documents = [
            _require_document(self._session, workspace_id, doc_id)
            for doc_id in effective_doc_ids
        ]

        now = _now()
        job = AnalysisJob(
            id=str(uuid4()),
            workspace_id=workspace_id,
            status="queued",
            analysis_type=analysis_type.strip(),
            source_type=source_type,
            source_ids=effective_source_ids or None,
            prompt=prompt.strip(),
            provider=provider,
            model=model,
            created_by=user_id,
            created_at=now,
            started_at=None,
            finished_at=None,
            error_code=None,
            error_message=None,
        )
        job.source_document_ids = [doc.id for doc in documents]
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_job(self, *, workspace_id: str, job_id: str) -> AnalysisJob:
        return _require_job(self._session, workspace_id, job_id)

    def list_jobs(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        status: str | None,
        source_type: str | None = None,
    ) -> tuple[list[AnalysisJob], int]:
        query = select(AnalysisJob).where(AnalysisJob.workspace_id == workspace_id)
        if status is not None:
            query = query.where(AnalysisJob.status == status)
        if source_type is not None:
            query = query.where(AnalysisJob.source_type == source_type)

        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        jobs = self._session.scalars(
            query.order_by(AnalysisJob.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return list(jobs), total

    def run_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        prompt: str | None = None,
        max_suggestions: int = 10,
        result_service: AnalysisResultService | None = None,
    ) -> AnalysisJob:
        job = self.get_job(workspace_id=workspace_id, job_id=job_id)
        _require_job_status(job, allowed={"queued", "pending", "running", "completed"}, action="run")

        now = _now()
        job.status = "running"
        job.started_at = job.started_at or now
        self._session.add(job)
        self._session.flush()

        (result_service or AnalysisResultService(self._session)).create_result(
            workspace_id=workspace_id,
            job_id=job_id,
            prompt=prompt or job.prompt,
            max_suggestions=max_suggestions,
            commit=False,
        )
        job.status = "completed"
        job.finished_at = _now()
        job.error_code = None
        job.error_message = None
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def fail_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        error_code: str,
        error_message: str,
    ) -> AnalysisJob:
        job = self.get_job(workspace_id=workspace_id, job_id=job_id)
        _require_job_status(job, allowed={"queued", "pending", "running"}, action="fail")

        job.status = "failed"
        job.finished_at = _now()
        job.error_code = error_code
        job.error_message = error_message
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def cancel_job(self, *, workspace_id: str, user_id: str, job_id: str) -> AnalysisJob:
        job = self.get_job(workspace_id=workspace_id, job_id=job_id)
        _require_job_status(job, allowed={"queued", "pending", "running"}, action="cancel")

        now = _now()
        job.status = "cancelled"
        job.finished_at = now
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)

        self._audit.record_result_event(
            AnalysisResultAuditEvent(
                action=ANALYSIS_JOB_CANCELLED_AUDIT_EVENT,
                actor=user_id,
                workspace_id=workspace_id,
                job_id=job_id,
                result_id="",
                occurred_at=now,
                extra={},
            )
        )
        return job

    def retry_job(self, *, workspace_id: str, user_id: str, job_id: str) -> AnalysisJob:
        original = self.get_job(workspace_id=workspace_id, job_id=job_id)
        _require_job_status(original, allowed={"failed", "cancelled"}, action="retry")

        retry_count = self._count_retries(original.id)
        if retry_count >= RETRY_LIMIT:
            raise AnalysisRetryLimitExceededApiError(
                details={"job_id": job_id, "retry_count": retry_count, "retry_limit": RETRY_LIMIT}
            )

        now = _now()
        retry_job = AnalysisJob(
            id=str(uuid4()),
            workspace_id=workspace_id,
            status="queued",
            analysis_type=original.analysis_type,
            source_type=original.source_type,
            source_ids=list(original.source_ids) if original.source_ids else None,
            prompt=original.prompt,
            provider=original.provider,
            model=original.model,
            created_by=user_id,
            created_at=now,
            # Mark as retry so count_retries can find this job.
            error_code=f"RETRY:{original.id}",
        )
        retry_job.source_document_ids = list(original.source_document_ids)
        self._session.add(retry_job)
        self._session.commit()
        self._session.refresh(retry_job)

        self._audit.record_result_event(
            AnalysisResultAuditEvent(
                action=ANALYSIS_JOB_RETRIED_AUDIT_EVENT,
                actor=user_id,
                workspace_id=workspace_id,
                job_id=retry_job.id,
                result_id="",
                occurred_at=now,
                extra={"original_job_id": original.id, "retry_count": retry_count + 1},
            )
        )
        return retry_job

    def _count_retries(self, original_job_id: str) -> int:
        stmt = select(func.count(AnalysisJob.id)).where(
            AnalysisJob.error_code == f"RETRY:{original_job_id}"
        )
        return self._session.execute(stmt).scalar_one()

    def approve_job(self, *, workspace_id: str, user_id: str, job_id: str) -> AnalysisJob:
        return AnalysisApprovalService(
            self._session,
            audit_recorder=self._audit,
        ).approve_job(workspace_id=workspace_id, user_id=user_id, job_id=job_id)


# ──────────────────────────────────────────────────────────────────────────────
# Comparison service
# ──────────────────────────────────────────────────────────────────────────────

class AnalysisComparisonService:
    def __init__(self, session: Session, *, comparison_provider: AnalysisComparisonProvider | None = None) -> None:
        self._session = session
        self._comparison_provider = comparison_provider or DeterministicAnalysisStubEngine(session)

    def compare_with_existing(
        self,
        *,
        workspace_id: str,
        job_id: str,
        compared_document_ids: list[str] | None = None,
        max_differences: int = 50,
        commit: bool = True,
    ) -> AnalysisComparison:
        job = _require_job(self._session, workspace_id, job_id)
        _require_job_status(job, allowed={"queued", "pending", "running"}, action="compare")

        document_ids = _deduplicate(compared_document_ids or job.source_document_ids[1:])
        if not document_ids:
            raise AnalysisCompareDocumentMissingApiError(details={"job_id": job_id})
        for document_id in document_ids:
            _require_document(self._session, workspace_id, document_id)

        now = _now()
        payload = self._comparison_provider.compare(
            job=job,
            compared_document_ids=document_ids,
            created_at=now,
            max_differences=max_differences,
        )
        comparison = job.comparison or AnalysisComparison(id=str(uuid4()), job_id=job.id)
        comparison.compared_document_ids = list(payload["compared_document_ids"])
        comparison.overlaps = list(payload["overlaps"])
        comparison.differences = list(payload["differences"])
        comparison.suggested_merge = payload.get("suggested_merge")
        comparison.created_at = now
        job.comparison = comparison
        self._session.add(comparison)
        if commit:
            self._session.commit()
            self._session.refresh(comparison)
        return comparison

    def get_comparison(self, *, workspace_id: str, job_id: str) -> AnalysisComparison:
        job = _require_job(self._session, workspace_id, job_id)
        if job.comparison is None:
            raise AnalysisResultNotReadyApiError(
                details={"job_id": job_id, "required_resource": "comparison"}
            )
        return job.comparison


# ──────────────────────────────────────────────────────────────────────────────
# Result service
# ──────────────────────────────────────────────────────────────────────────────

# Status transitions that allow editing result content.
_RESULT_EDITABLE_STATUSES = {"draft", "review"}

class AnalysisResultService:
    def __init__(
        self,
        session: Session,
        *,
        provider: AnalysisProvider | None = None,
        audit_recorder: AnalysisApprovalAuditRecorder | None = None,
    ) -> None:
        self._session = session
        self._provider = provider or DeterministicAnalysisStubEngine(session)
        self._audit = audit_recorder or InMemoryAnalysisApprovalAuditRecorder()

    def create_result(
        self,
        *,
        workspace_id: str,
        job_id: str,
        prompt: str | None = None,
        max_suggestions: int = 10,
        commit: bool = True,
    ) -> AnalysisResult:
        job = _require_job(self._session, workspace_id, job_id)
        _require_job_status(job, allowed={"running", "completed"}, action="create_result")

        now = _now()
        documents = [
            _require_document(self._session, workspace_id, doc_id)
            for doc_id in job.source_document_ids
        ]
        payload = self._provider.build_result(
            job=job,
            documents=documents,
            comparison=_comparison_to_payload(job.comparison) if job.comparison else None,
            prompt=prompt or job.prompt,
            max_suggestions=max_suggestions,
            created_at=now,
        )

        result = job.result or AnalysisResult(id=str(uuid4()), job_id=job.id)
        result.summary = payload["summary"]
        result.key_points = list(payload["key_points"])
        result.suggested_tags = list(payload["suggested_tags"])
        result.suggested_topics = list(payload["suggested_topics"])
        result.confidence = float(payload["confidence"]) if payload.get("confidence") is not None else None
        result.created_at = now
        result.status = "draft"
        job.result = result

        job.suggestions.clear()
        self._session.flush()
        job.suggestions = [
            AnalysisSuggestion(
                id=str(uuid4()),
                job_id=job.id,
                suggestion_type=item["suggestion_type"],
                payload=dict(item["payload"]),
                status="pending",
                approved_by=None,
                approved_at=None,
            )
            for item in payload["suggestions"]
        ]
        self._session.add(result)
        if commit:
            self._session.commit()
            self._session.refresh(result)
        return result

    def get_result(self, *, workspace_id: str, job_id: str) -> AnalysisResult:
        job = _require_job(self._session, workspace_id, job_id)
        if job.status not in {"completed", "approved"} or job.result is None:
            raise AnalysisResultNotReadyApiError(
                details={"current_status": job.status, "required_status": "completed"}
            )
        return job.result

    def get_result_by_id(self, *, workspace_id: str, result_id: str) -> AnalysisResult:
        """Fetch result directly by result_id, workspace-scoped via job JOIN."""
        result = self._session.scalar(
            select(AnalysisResult)
            .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
            .where(
                AnalysisResult.id == result_id,
                AnalysisJob.workspace_id == workspace_id,
            )
        )
        if result is None:
            raise AnalysisResultNotFoundApiError(details={"result_id": result_id})
        return result

    def update_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        result_id: str,
        request: UpdateAnalysisResultRequest,
    ) -> AnalysisResult:
        result = self.get_result_by_id(workspace_id=workspace_id, result_id=result_id)
        if result.status not in _RESULT_EDITABLE_STATUSES:
            raise AnalysisResultInvalidStateApiError(
                details={
                    "result_id": result_id,
                    "current_status": result.status,
                    "editable_statuses": sorted(_RESULT_EDITABLE_STATUSES),
                    "action": "update",
                }
            )
        now = _now()
        if request.title is not None:
            result.title = request.title
        if request.summary is not None:
            result.summary = request.summary
        if request.content_markdown is not None:
            result.content_markdown = request.content_markdown
        if request.sources is not None:
            result.sources = [s.model_dump() for s in request.sources]
        result.updated_at = now
        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)
        return result

    def mark_for_review(
        self,
        *,
        workspace_id: str,
        user_id: str,
        result_id: str,
        request: MarkForReviewRequest,
    ) -> AnalysisResult:
        result = self.get_result_by_id(workspace_id=workspace_id, result_id=result_id)
        if result.status != "draft":
            raise AnalysisResultInvalidStateApiError(
                details={
                    "result_id": result_id,
                    "current_status": result.status,
                    "required_status": "draft",
                    "action": "mark_for_review",
                }
            )
        now = _now()
        result.status = "review"
        result.updated_at = now
        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)

        self._audit.record_result_event(
            AnalysisResultAuditEvent(
                action=ANALYSIS_RESULT_MARKED_FOR_REVIEW_AUDIT_EVENT,
                actor=user_id,
                workspace_id=workspace_id,
                job_id=result.job_id,
                result_id=result_id,
                occurred_at=now,
                extra={"note": request.note},
            )
        )
        return result

    def approve_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        actor_role: str = "admin",
        result_id: str,
        request: ApproveResultRequest,
    ) -> AnalysisResult:
        result = self.get_result_by_id(workspace_id=workspace_id, result_id=result_id)
        job = result.job
        _policy = AnalysisApprovalPolicy()
        _ctx = ApprovalContext(
            action="approve",
            actor_id=user_id,
            actor_role="admin" if actor_role in ("admin", "owner") else "member",  # type: ignore[arg-type]
            workspace_id=workspace_id,
            result_id=result_id,
            result_status=result.status,
            result_workspace=result.job.workspace_id if result.job else workspace_id,
            created_by=job.created_by if job else None,
            job_status=job.status if job else "unknown",
            confirm=request.confirm,
            reject_reason="",
        )
        try:
            _policy.check(_ctx)
        except ApprovalPolicyViolation as exc:
            raise AnalysisResultInvalidStateApiError(
                details={"rule": exc.rule, "detail": exc.detail, "result_id": result_id}
            ) from exc
        now = _now()
        result.status = "approved"
        result.approved_by = user_id
        result.approved_at = now
        result.updated_at = now
        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)

        self._audit.record_result_event(
            AnalysisResultAuditEvent(
                action=ANALYSIS_RESULT_APPROVED_AUDIT_EVENT,
                actor=user_id,
                workspace_id=workspace_id,
                job_id=result.job_id,
                result_id=result_id,
                occurred_at=now,
                extra={"reviewer_note": request.reviewer_note},
            )
        )
        return result

    def reject_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        actor_role: str = "admin",
        result_id: str,
        request: RejectResultRequest,
    ) -> AnalysisResult:
        result = self.get_result_by_id(workspace_id=workspace_id, result_id=result_id)
        job = result.job
        _policy = AnalysisApprovalPolicy()
        _ctx = ApprovalContext(
            action="reject",
            actor_id=user_id,
            actor_role="admin" if actor_role in ("admin", "owner") else "member",  # type: ignore[arg-type]
            workspace_id=workspace_id,
            result_id=result_id,
            result_status=result.status,
            result_workspace=result.job.workspace_id if result.job else workspace_id,
            created_by=job.created_by if job else None,
            job_status=job.status if job else "unknown",
            confirm=False,
            reject_reason=request.reason or "",
        )
        try:
            _policy.check(_ctx)
        except ApprovalPolicyViolation as exc:
            raise AnalysisResultInvalidStateApiError(
                details={"rule": exc.rule, "detail": exc.detail, "result_id": result_id}
            ) from exc
        now = _now()
        result.status = "rejected"
        result.updated_at = now
        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)

        self._audit.record_result_event(
            AnalysisResultAuditEvent(
                action=ANALYSIS_RESULT_REJECTED_AUDIT_EVENT,
                actor=user_id,
                workspace_id=workspace_id,
                job_id=result.job_id,
                result_id=result_id,
                occurred_at=now,
                extra={"reason": request.reason},
            )
        )
        return result


# ──────────────────────────────────────────────────────────────────────────────
# Facade
# ──────────────────────────────────────────────────────────────────────────────

class AnalysisService:
    def __init__(
        self,
        session: Session,
        *,
        provider: AnalysisProvider | None = None,
        approval_audit_recorder: AnalysisApprovalAuditRecorder | None = None,
    ) -> None:
        self._session = session
        _audit = approval_audit_recorder or InMemoryAnalysisApprovalAuditRecorder()
        self.job_service = AnalysisJobService(session, approval_audit_recorder=_audit)
        self.comparison_service = AnalysisComparisonService(session)
        self.result_service = AnalysisResultService(session, provider=provider, audit_recorder=_audit)

    # ── 1. create_job ─────────────────────────────────────────────────────────

    def create_job(
        self,
        *,
        workspace_id: str,
        user_id: str,
        request: CreateAnalysisJobRequest,
    ) -> AnalysisJobResponse:
        job = self.job_service.create_job(
            workspace_id=workspace_id,
            user_id=user_id,
            source_document_ids=request.source_document_ids,
            analysis_type=request.analysis_type,
            prompt=request.prompt,
            source_type=request.source_type,
            source_ids=list(request.source_ids) if request.source_ids else None,
            provider=request.provider,
            model=request.model,
        )
        return _job_to_response(job)

    # ── 2. get_job ────────────────────────────────────────────────────────────

    def get_job(self, *, workspace_id: str, job_id: str) -> AnalysisJobResponse:
        return _job_to_response(self.job_service.get_job(workspace_id=workspace_id, job_id=job_id))

    # ── 3. list_jobs ──────────────────────────────────────────────────────────

    def list_jobs(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        status: str | None,
        source_type: str | None = None,
    ) -> AnalysisJobListResponse:
        jobs, total = self.job_service.list_jobs(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            status=status,
            source_type=source_type,
        )
        return AnalysisJobListResponse(
            items=[_job_to_list_item(job) for job in jobs],
            total=total,
            limit=limit,
            offset=offset,
        )

    # ── 4. cancel_job ─────────────────────────────────────────────────────────

    def cancel_job(
        self, *, workspace_id: str, user_id: str, job_id: str
    ) -> AnalysisJobResponse:
        return _job_to_response(
            self.job_service.cancel_job(workspace_id=workspace_id, user_id=user_id, job_id=job_id)
        )

    # ── 5. retry_job ──────────────────────────────────────────────────────────

    def retry_job(
        self, *, workspace_id: str, user_id: str, job_id: str
    ) -> AnalysisJobResponse:
        return _job_to_response(
            self.job_service.retry_job(workspace_id=workspace_id, user_id=user_id, job_id=job_id)
        )

    # ── 6. update_result ──────────────────────────────────────────────────────

    def update_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        result_id: str,
        request: UpdateAnalysisResultRequest,
    ) -> AnalysisResultSchema:
        return _result_to_schema(
            self.result_service.update_result(
                workspace_id=workspace_id,
                user_id=user_id,
                result_id=result_id,
                request=request,
            )
        )

    # ── 7. mark_result_for_review ─────────────────────────────────────────────

    def mark_result_for_review(
        self,
        *,
        workspace_id: str,
        user_id: str,
        result_id: str,
        request: MarkForReviewRequest,
    ) -> AnalysisResultSchema:
        return _result_to_schema(
            self.result_service.mark_for_review(
                workspace_id=workspace_id,
                user_id=user_id,
                result_id=result_id,
                request=request,
            )
        )

    # ── 8. approve_result ─────────────────────────────────────────────────────

    def approve_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        actor_role: str = "admin",
        result_id: str,
        request: ApproveResultRequest,
    ) -> AnalysisResultSchema:
        return _result_to_schema(
            self.result_service.approve_result(
                workspace_id=workspace_id,
                user_id=user_id,
                actor_role=actor_role,
                result_id=result_id,
                request=request,
            )
        )

    # ── 9. reject_result ──────────────────────────────────────────────────────

    def reject_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        actor_role: str = "admin",
        result_id: str,
        request: RejectResultRequest,
    ) -> AnalysisResultSchema:
        return _result_to_schema(
            self.result_service.reject_result(
                workspace_id=workspace_id,
                user_id=user_id,
                actor_role=actor_role,
                result_id=result_id,
                request=request,
            )
        )

    # ── 10. get_result_by_id ──────────────────────────────────────────────────

    def get_result_by_id(
        self, *, workspace_id: str, result_id: str
    ) -> AnalysisResultSchema:
        return _result_to_schema(
            self.result_service.get_result_by_id(workspace_id=workspace_id, result_id=result_id)
        )

    # ── Legacy facade methods (backward compat) ───────────────────────────────

    def compare_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        request: CompareRequest,
    ) -> AnalysisJobResponse:
        job = self.job_service.get_job(workspace_id=workspace_id, job_id=job_id)
        _require_job_status(job, allowed={"queued", "pending"}, action="compare")
        job.status = "running"
        job.started_at = _now()
        self._session.add(job)
        self._session.flush()
        self.comparison_service.compare_with_existing(
            workspace_id=workspace_id,
            job_id=job_id,
            compared_document_ids=request.compared_document_ids,
            max_differences=request.max_differences,
            commit=False,
        )
        job = self.job_service.run_job(
            workspace_id=workspace_id,
            job_id=job_id,
            max_suggestions=10,
            result_service=self.result_service,
        )
        return _job_to_response(job)

    def summarize_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        request: SummarizeRequest,
    ) -> AnalysisJobResponse:
        job = self.job_service.run_job(
            workspace_id=workspace_id,
            job_id=job_id,
            prompt=request.prompt,
            max_suggestions=request.max_suggestions,
            result_service=self.result_service,
        )
        return _job_to_response(job)

    def approve_job(
        self,
        *,
        workspace_id: str,
        user_id: str,
        job_id: str,
        request: ApproveRequest,
    ) -> AnalysisJobResponse:
        from app.core.errors import AnalysisJobInvalidStateApiError
        if request.decision != "approved":
            raise AnalysisJobInvalidStateApiError(details={"decision": request.decision})
        return _job_to_response(
            self.job_service.approve_job(workspace_id=workspace_id, user_id=user_id, job_id=job_id)
        )

    def get_result(self, *, workspace_id: str, job_id: str) -> AnalysisResultSchema:
        return _result_to_schema(self.result_service.get_result(workspace_id=workspace_id, job_id=job_id))

    def import_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        result_id: str,
    ):  # returns ImportStats — imported inline to avoid circular import
        from app.services.analysis.import_service import AnalysisResultImportService
        svc = AnalysisResultImportService(self._session)
        return svc.import_result(
            workspace_id=workspace_id,
            user_id=user_id,
            result_id=result_id,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Schema mappers
# ──────────────────────────────────────────────────────────────────────────────

def _job_to_list_item(job: AnalysisJob) -> AnalysisJobListItem:
    return AnalysisJobListItem(
        id=job.id,
        workspace_id=job.workspace_id,
        source_document_ids=job.source_document_ids,
        status=job.status,
        analysis_type=job.analysis_type,
        source_type=job.source_type,
        source_ids=list(job.source_ids) if job.source_ids else None,
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


def _job_to_response(job: AnalysisJob) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        **_job_to_list_item(job).model_dump(),
        result=_result_to_schema(job.result) if job.result else None,
        comparison=_comparison_to_schema(job.comparison) if job.comparison else None,
        suggestions=[_suggestion_to_schema(s) for s in job.suggestions],
    )


def _result_to_schema(result: AnalysisResult) -> AnalysisResultSchema:
    from app.schemas.analysis import AnalysisSourceRef
    raw_sources = result.sources
    parsed_sources: list[AnalysisSourceRef] | None = None
    if raw_sources is not None:
        parsed_sources = [
            AnalysisSourceRef(**s) if isinstance(s, dict) else s
            for s in raw_sources
        ]
    return AnalysisResultSchema(
        id=result.id,
        job_id=result.job_id,
        summary=result.summary,
        key_points=list(result.key_points),
        suggested_tags=list(result.suggested_tags),
        suggested_topics=list(result.suggested_topics),
        confidence=result.confidence,
        created_at=result.created_at,
        title=result.title,
        content_markdown=result.content_markdown,
        sources=parsed_sources,
        status=result.status,
        approved_at=result.approved_at,
        approved_by=result.approved_by,
        updated_at=result.updated_at,
    )


def _comparison_to_schema(comparison: AnalysisComparison) -> AnalysisComparisonSchema:
    return AnalysisComparisonSchema(
        id=comparison.id,
        job_id=comparison.job_id,
        compared_document_ids=comparison.compared_document_ids,
        overlaps=list(comparison.overlaps),
        differences=list(comparison.differences),
        suggested_merge=comparison.suggested_merge,
        created_at=comparison.created_at,
    )


def _suggestion_to_schema(suggestion: AnalysisSuggestion) -> AnalysisSuggestionSchema:
    return AnalysisSuggestionSchema(
        id=suggestion.id,
        job_id=suggestion.job_id,
        suggestion_type=suggestion.suggestion_type,
        payload=dict(suggestion.payload),
        status=suggestion.status,
        approved_by=suggestion.approved_by,
        approved_at=suggestion.approved_at,
    )


def _comparison_to_payload(comparison: AnalysisComparison) -> dict:
    return {
        "job_id": comparison.job_id,
        "compared_document_ids": comparison.compared_document_ids,
        "overlaps": list(comparison.overlaps),
        "differences": list(comparison.differences),
        "suggested_merge": comparison.suggested_merge,
        "created_at": comparison.created_at,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _require_job(session: Session, workspace_id: str, job_id: str) -> AnalysisJob:
    job = session.scalar(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.workspace_id == workspace_id,
        )
    )
    if job is None:
        raise AnalysisJobNotFoundApiError(details={"job_id": job_id})
    return job


def _require_document(session: Session, workspace_id: str, document_id: str | None) -> Document:
    document = session.scalar(
        select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id)
    )
    if document is None:
        raise DocumentNotFoundApiError(details={"document_id": document_id})
    return document


def _require_job_status(job: AnalysisJob, *, allowed: set[str], action: str) -> None:
    if job.status not in allowed:
        raise AnalysisJobInvalidStateApiError(
            details={"current_status": job.status, "allowed_statuses": sorted(allowed), "action": action}
        )


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _now() -> datetime:
    return datetime.now(UTC)
