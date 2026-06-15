from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import (
    AnalysisCompareDocumentMissingApiError,
    AnalysisJobInvalidStateApiError,
    AnalysisJobNotFoundApiError,
    AnalysisResultNotReadyApiError,
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
    CompareRequest,
    CreateAnalysisJobRequest,
    SummarizeRequest,
)
from app.services.analysis.analysis_stub_engine import (
    AnalysisComparisonProvider,
    AnalysisProvider,
    DeterministicAnalysisStubEngine,
)
from app.services.analysis.approval_service import AnalysisApprovalAuditRecorder, AnalysisApprovalService


class AnalysisJobService:
    def __init__(
        self,
        session: Session,
        *,
        approval_audit_recorder: AnalysisApprovalAuditRecorder | None = None,
    ) -> None:
        self._session = session
        self._approval_audit_recorder = approval_audit_recorder

    def create_job(
        self,
        *,
        workspace_id: str,
        user_id: str,
        source_document_ids: list[str],
        analysis_type: str,
        prompt: str,
    ) -> AnalysisJob:
        document_ids = _deduplicate(source_document_ids)
        documents = [_require_document(self._session, workspace_id, document_id) for document_id in document_ids]

        now = _now()
        job = AnalysisJob(
            id=str(uuid4()),
            workspace_id=workspace_id,
            status="pending",
            analysis_type=analysis_type.strip(),
            prompt=prompt.strip(),
            created_by=user_id,
            created_at=now,
            started_at=None,
            finished_at=None,
            error_code=None,
            error_message=None,
        )
        job.source_document_ids = [document.id for document in documents]
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
    ) -> tuple[list[AnalysisJob], int]:
        query = select(AnalysisJob).where(AnalysisJob.workspace_id == workspace_id)
        if status is not None:
            query = query.where(AnalysisJob.status == status)

        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        jobs = self._session.scalars(
            query.order_by(AnalysisJob.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return jobs, total

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
        _require_status(job, allowed={"pending", "running", "completed"}, action="run")

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
        _require_status(job, allowed={"pending", "running"}, action="fail")

        job.status = "failed"
        job.finished_at = _now()
        job.error_code = error_code
        job.error_message = error_message
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def approve_job(self, *, workspace_id: str, user_id: str, job_id: str) -> AnalysisJob:
        return AnalysisApprovalService(
            self._session,
            audit_recorder=self._approval_audit_recorder,
        ).approve_job(workspace_id=workspace_id, user_id=user_id, job_id=job_id)


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
        _require_status(job, allowed={"pending", "running"}, action="compare")

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


class AnalysisResultService:
    def __init__(self, session: Session, *, provider: AnalysisProvider | None = None) -> None:
        self._session = session
        self._provider = provider or DeterministicAnalysisStubEngine(session)

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
        _require_status(job, allowed={"running", "completed"}, action="create_result")

        now = _now()
        documents = [_require_document(self._session, workspace_id, document_id) for document_id in job.source_document_ids]
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
        result.confidence = float(payload["confidence"])
        result.created_at = now
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


class AnalysisService:
    def __init__(
        self,
        session: Session,
        *,
        provider: AnalysisProvider | None = None,
        approval_audit_recorder: AnalysisApprovalAuditRecorder | None = None,
    ) -> None:
        self._session = session
        self.job_service = AnalysisJobService(session, approval_audit_recorder=approval_audit_recorder)
        self.comparison_service = AnalysisComparisonService(session)
        self.result_service = AnalysisResultService(session, provider=provider)

    def list_jobs(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        status: str | None,
    ) -> AnalysisJobListResponse:
        jobs, total = self.job_service.list_jobs(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        return AnalysisJobListResponse(
            items=[_job_to_list_item(job) for job in jobs],
            total=total,
            limit=limit,
            offset=offset,
        )

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
        )
        return _job_to_response(job)

    def get_job(self, *, workspace_id: str, job_id: str) -> AnalysisJobResponse:
        return _job_to_response(self.job_service.get_job(workspace_id=workspace_id, job_id=job_id))

    def compare_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        request: CompareRequest,
    ) -> AnalysisJobResponse:
        job = self.job_service.get_job(workspace_id=workspace_id, job_id=job_id)
        _require_status(job, allowed={"pending"}, action="compare")
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
        if request.decision != "approved":
            raise AnalysisJobInvalidStateApiError(details={"decision": request.decision})
        return _job_to_response(
            self.job_service.approve_job(workspace_id=workspace_id, user_id=user_id, job_id=job_id)
        )

    def get_result(self, *, workspace_id: str, job_id: str) -> AnalysisResultSchema:
        return _result_to_schema(self.result_service.get_result(workspace_id=workspace_id, job_id=job_id))


def _job_to_list_item(job: AnalysisJob) -> AnalysisJobListItem:
    return AnalysisJobListItem(
        id=job.id,
        workspace_id=job.workspace_id,
        source_document_ids=job.source_document_ids,
        status=job.status,
        analysis_type=job.analysis_type,
        prompt=job.prompt,
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
        suggestions=[_suggestion_to_schema(suggestion) for suggestion in job.suggestions],
    )


def _result_to_schema(result: AnalysisResult) -> AnalysisResultSchema:
    return AnalysisResultSchema(
        id=result.id,
        job_id=result.job_id,
        summary=result.summary,
        key_points=list(result.key_points),
        suggested_tags=list(result.suggested_tags),
        suggested_topics=list(result.suggested_topics),
        confidence=float(result.confidence),
        created_at=result.created_at,
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


def _require_status(job: AnalysisJob, *, allowed: set[str], action: str) -> None:
    if job.status not in allowed:
        raise AnalysisJobInvalidStateApiError(
            details={"current_status": job.status, "allowed_statuses": sorted(allowed), "action": action}
        )


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _now() -> datetime:
    return datetime.now(UTC)
