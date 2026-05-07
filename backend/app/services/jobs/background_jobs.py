from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.errors import ApiError
from app.models.documents import BackgroundJob
from app.schemas.jobs import ImportJobResult, JobResponse, SearchIndexRebuildJobResult
from app.services.documents.import_executor import ImportExecutor
from app.services.search_index_service import SearchIndexRebuildService


class BackgroundJobNotFoundError(LookupError):
    pass


class BackgroundJobAlreadyClaimedError(RuntimeError):
    pass


class BackgroundJobService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "BackgroundJobService":
        return cls(session)

    def enqueue_import_job(
        self,
        *,
        workspace_id: str,
        requested_by_user_id: str,
        filename: str,
        mime_type: str,
        temp_file_path: str,
    ) -> BackgroundJob:
        now = datetime.now(UTC)
        job = BackgroundJob(
            id=str(uuid4()),
            job_type="document_import",
            status="pending",
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            payload_={
                "filename": filename,
                "mime_type": mime_type,
                "temp_file_path": temp_file_path,
            },
            result_=None,
            progress_current=0,
            progress_total=1,
            progress_message="Import wartet auf Verarbeitung",
            error_code=None,
            error_message=None,
            attempt_count=0,
            locked_at=None,
            locked_by=None,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_job(self, job_id: str) -> BackgroundJob:
        job = self._session.get(BackgroundJob, job_id)
        if job is None:
            raise BackgroundJobNotFoundError(job_id)
        return job

    def claim_job(self, *, job_id: str, worker_id: str, now: datetime | None = None) -> BackgroundJob:
        timestamp = now or datetime.now(UTC)
        stale_before = self._stale_lock_before(timestamp)
        claimed = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job_id,
                or_(
                    BackgroundJob.status.in_(("pending", "retryable")),
                    and_(
                        BackgroundJob.status == "running",
                        BackgroundJob.locked_at.is_not(None),
                        BackgroundJob.locked_at < stale_before,
                    ),
                ),
            )
            .values(
                status="running",
                started_at=timestamp,
                finished_at=None,
                locked_at=timestamp,
                locked_by=worker_id,
                progress_current=0,
                progress_total=1,
                progress_message="Job wird verarbeitet",
                error_code=None,
                error_message=None,
                attempt_count=BackgroundJob.attempt_count + 1,
            )
            .execution_options(synchronize_session=False)
        )
        self._session.commit()
        if not claimed.rowcount:
            raise BackgroundJobAlreadyClaimedError(job_id)
        return self.get_job(job_id)

    def mark_job_completed(self, *, job: BackgroundJob, result: dict) -> BackgroundJob:
        job.status = "completed"
        job.progress_current = 1
        job.progress_total = 1
        job.progress_message = "Job abgeschlossen"
        job.result_ = result
        job.error_code = None
        job.error_message = None
        job.finished_at = datetime.now(UTC)
        job.locked_at = None
        job.locked_by = None
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def mark_job_failure(self, *, job: BackgroundJob, error_code: str, error_message: str, retryable: bool) -> BackgroundJob:
        terminal_attempt = job.attempt_count >= settings.background_job_max_attempts
        job.status = "dead_letter" if retryable and terminal_attempt else ("retryable" if retryable else "failed")
        job.progress_current = 1
        job.progress_total = 1
        job.progress_message = self._failure_progress_message(job.status)
        job.error_code = error_code
        job.error_message = error_message
        job.result_ = None
        job.finished_at = datetime.now(UTC)
        job.locked_at = None
        job.locked_by = None
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def recover_stale_jobs(self, *, worker_id: str, now: datetime | None = None) -> int:
        timestamp = now or datetime.now(UTC)
        stale_before = self._stale_lock_before(timestamp)
        recovered = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.status == "running",
                BackgroundJob.locked_at.is_not(None),
                BackgroundJob.locked_at < stale_before,
            )
            .values(
                status="retryable",
                finished_at=timestamp,
                locked_at=None,
                locked_by=None,
                progress_message=f"Lease abgelaufen; Recovery durch {worker_id}",
                error_code="WORKER_RECOVERY_REQUIRED",
                error_message="Worker lease expired before completion",
            )
            .execution_options(synchronize_session=False)
        )
        self._session.commit()
        return int(recovered.rowcount or 0)

    def _stale_lock_before(self, timestamp: datetime) -> datetime:
        from datetime import timedelta

        return timestamp - timedelta(seconds=settings.background_job_lock_timeout_seconds)

    def _failure_progress_message(self, status: str) -> str:
        if status == "retryable":
            return "Job fehlgeschlagen, Retry geplant"
        if status == "dead_letter":
            return "Job in Dead Letter verschoben"
        return "Job fehlgeschlagen"

    def enqueue_search_index_rebuild_job(
        self,
        *,
        workspace_id: str,
        requested_by_user_id: str | None,
        target_workspace_id: str | None,
    ) -> BackgroundJob:
        now = datetime.now(UTC)
        job = BackgroundJob(
            id=str(uuid4()),
            job_type="search_index_rebuild",
            status="pending",
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            payload_={"target_workspace_id": target_workspace_id},
            result_=None,
            progress_current=0,
            progress_total=1,
            progress_message="Rebuild wartet auf Verarbeitung",
            error_code=None,
            error_message=None,
            attempt_count=0,
            locked_at=None,
            locked_by=None,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def to_response(self, job: BackgroundJob) -> JobResponse:
        result = job.result_ if isinstance(job.result_, dict) else None
        parsed_result = None
        if result is not None:
            if job.job_type == "document_import":
                parsed_result = ImportJobResult(**result)
            elif job.job_type == "search_index_rebuild":
                parsed_result = SearchIndexRebuildJobResult(**result)
        return JobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            workspace_id=job.workspace_id,
            requested_by_user_id=job.requested_by_user_id,
            filename=str(job.payload_.get("filename")) if isinstance(job.payload_, dict) else None,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            progress_current=job.progress_current,
            progress_total=job.progress_total,
            progress_message=job.progress_message,
            error_code=job.error_code,
            error_message=job.error_message,
            result=parsed_result,
        )

    @staticmethod
    def create_temp_upload_file(*, filename: str, source_bytes: bytes) -> str:
        temp_root = Path(settings.import_jobs_temp_dir or (Path(tempfile.gettempdir()) / "wissensbasis-import-jobs"))
        temp_root.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, dir=temp_root, prefix="import-job-", suffix=suffix) as handle:
            handle.write(source_bytes)
            return handle.name


def process_import_job(job_id: str, bind: Engine | None = None) -> None:
    from sqlalchemy.orm import Session as SqlAlchemySession
    from app.db.session import get_engine

    with SqlAlchemySession(bind or get_engine()) as session:
        service = BackgroundJobService.from_session(session)
        try:
            job = service.claim_job(job_id=job_id, worker_id="import-worker")
        except (BackgroundJobNotFoundError, BackgroundJobAlreadyClaimedError):
            return

        if job.job_type != "document_import":
            return

        payload = job.payload_ if isinstance(job.payload_, dict) else {}
        temp_file_path = str(payload.get("temp_file_path") or "")
        filename = str(payload.get("filename") or "untitled")
        mime_type = str(payload.get("mime_type") or "application/octet-stream")

        try:
            source_bytes = Path(temp_file_path).read_bytes()
            driver_connection = _driver_connection(session)
            result = ImportExecutor().execute(
                workspace_id=job.workspace_id,
                user_id=job.requested_by_user_id or "",
                filename=filename,
                mime_type=mime_type,
                source_bytes=source_bytes,
                connection=driver_connection,
            )
            service.mark_job_completed(job=job, result=result)
            if temp_file_path:
                try:
                    os.remove(temp_file_path)
                except FileNotFoundError:
                    pass
        except ApiError as exc:
            retryable = _is_retryable_import_error(exc.code)
            service.mark_job_failure(job=job, error_code=exc.code, error_message=exc.message, retryable=retryable)
        except Exception:
            service.mark_job_failure(
                job=job,
                error_code="IMPORT_FAILED",
                error_message="Document import failed",
                retryable=True,
            )


def process_search_index_rebuild_job(job_id: str, bind: Engine | None = None) -> None:
    from sqlalchemy.orm import Session as SqlAlchemySession
    from app.db.session import get_engine

    with SqlAlchemySession(bind or get_engine()) as session:
        service = BackgroundJobService.from_session(session)
        try:
            job = service.claim_job(job_id=job_id, worker_id="search-index-worker")
        except (BackgroundJobNotFoundError, BackgroundJobAlreadyClaimedError):
            return

        if job.job_type != "search_index_rebuild":
            return

        payload = job.payload_ if isinstance(job.payload_, dict) else {}
        target_workspace_id = payload.get("target_workspace_id")

        try:
            result = SearchIndexRebuildService.from_session(session).rebuild_search_index(workspace_id=target_workspace_id)
            service.mark_job_completed(job=job, result=result)
        except ApiError as exc:
            service.mark_job_failure(job=job, error_code=exc.code, error_message=exc.message, retryable=False)
        except Exception:
            service.mark_job_failure(
                job=job,
                error_code="SERVICE_UNAVAILABLE",
                error_message="Search index rebuild failed",
                retryable=True,
            )


def _is_retryable_import_error(error_code: str | None) -> bool:
    return (error_code or "").upper() in {"SERVICE_UNAVAILABLE", "IMPORT_FAILED", "FILE_READ_FAILED"}


def _driver_connection(session: Session):
    sql_connection = session.connection()
    proxied_connection = getattr(sql_connection, "connection", None)
    driver_connection = getattr(proxied_connection, "driver_connection", None)
    return driver_connection