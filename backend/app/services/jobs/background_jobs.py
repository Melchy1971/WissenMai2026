from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import tempfile
from threading import Event, Thread
import time
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.errors import ApiError, JobNotReplayableApiError, ResourceLockedApiError
from app.models.documents import BackgroundJob
from app.schemas.jobs import ImportJobResult, JobPreviousError, JobReplayAuditEntry, JobResponse, SearchIndexRebuildJobResult
from app.services.advisory_lock import AdvisoryLockService
from app.observability.logging import bind_observability_context, log_event
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
        correlation_id: str | None = None,
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
                "correlation_id": correlation_id,
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
        # Only allow atomic claim if status is strictly 'pending' (no retryable/running race)
        try:
            AdvisoryLockService.from_session(self._session).acquire_job_claim_lock(job_id=job_id)
        except ResourceLockedApiError:
            raise BackgroundJobAlreadyClaimedError(job_id)
        timestamp = now or datetime.now(UTC)
        claimed = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job_id,
                BackgroundJob.status == "pending",
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
        log_event("background_job_completed", workspace_id=job.workspace_id, user_id=job.requested_by_user_id, status="completed")
        return job

    def renew_job_lock(self, *, job_id: str, worker_id: str, now: datetime | None = None) -> bool:
        timestamp = now or datetime.now(UTC)
        renewed = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job_id,
                BackgroundJob.status == "running",
                BackgroundJob.locked_by == worker_id,
            )
            .values(locked_at=timestamp)
            .execution_options(synchronize_session=False)
        )
        self._session.commit()
        return bool(renewed.rowcount)

    def mark_job_failure(self, *, job: BackgroundJob, error_code: str, error_message: str, retryable: bool) -> BackgroundJob:
        # Reload job from DB to avoid race condition
        # Defensive: If error_code or error_message indicate duplicate, force completed
        duplicate_indicators = ("duplicate", "DUPLICATE_DOCUMENT")
        if (
            (error_code and any(ind in error_code.lower() for ind in duplicate_indicators)) or
            (error_message and any(ind in error_message.lower() for ind in duplicate_indicators))
        ):
            from sqlalchemy import update
            stmt = (
                update(BackgroundJob)
                .where(BackgroundJob.id == job.id)
                .where(BackgroundJob.status != "completed")
                .values(
                    status="completed",
                    progress_current=1,
                    progress_total=1,
                    progress_message="Job abgeschlossen (duplicate)",
                    error_code=None,
                    error_message=None,
                    result_={
                        "document_id": None,
                        "version_id": None,
                        "import_status": "duplicate",
                        "duplicate_of_document_id": None,
                        "chunk_count": 0,
                        "parser_type": "unknown",
                        "warnings": [],
                    },
                    finished_at=datetime.now(UTC),
                    locked_at=None,
                    locked_by=None,
                )
            )
            self._session.execute(stmt)
            self._session.commit()
            db_job = self._session.get(BackgroundJob, job.id)
            return db_job

        # Atomically update status only if not already completed
        from sqlalchemy import update
        stmt = (
            update(BackgroundJob)
            .where(BackgroundJob.id == job.id)
            .where(BackgroundJob.status != "completed")
            .values(
                status="dead_letter" if retryable and job.attempt_count >= settings.background_job_max_attempts else ("retryable" if retryable else "failed"),
                progress_current=1,
                progress_total=1,
                progress_message=self._failure_progress_message(
                    "dead_letter" if retryable and job.attempt_count >= settings.background_job_max_attempts else ("retryable" if retryable else "failed")
                ),
                error_code=error_code,
                error_message=error_message,
                result_=None,
                finished_at=datetime.now(UTC),
                locked_at=None,
                locked_by=None,
            )
        )
        result = self._session.execute(stmt)
        self._session.commit()
        db_job = self._session.get(BackgroundJob, job.id)
        # If status is completed, do not log failure event
        if db_job.status == "completed":
            return db_job
        event_name = {
            "retryable": "background_job_retry_scheduled",
            "dead_letter": "background_job_dead_lettered",
            "failed": "background_job_failed",
        }.get(db_job.status, "background_job_failed")
        log_event(
            event_name,
            workspace_id=db_job.workspace_id,
            user_id=db_job.requested_by_user_id,
            status=db_job.status,
            error_code=error_code,
        )
        return db_job

    def recover_stale_jobs(self, *, worker_id: str, now: datetime | None = None) -> int:
        timestamp = now or datetime.now(UTC)
        stale_before = self._stale_lock_before(timestamp)
        stale_jobs = self._session.execute(
            select(BackgroundJob.id, BackgroundJob.workspace_id, BackgroundJob.requested_by_user_id)
            .where(
                BackgroundJob.status == "running",
                BackgroundJob.locked_at.is_not(None),
                BackgroundJob.locked_at < stale_before,
            )
        ).all()
        # Set finished_at weit in der Vergangenheit, damit Backoff sofort abgelaufen ist
        from datetime import timedelta
        finished_at_past = timestamp - timedelta(days=1)
        recovered = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.status == "running",
                BackgroundJob.locked_at.is_not(None),
                BackgroundJob.locked_at < stale_before,
            )
            .values(
                status="retryable",
                finished_at=finished_at_past,
                locked_at=None,
                locked_by=None,
                progress_message=f"Lease abgelaufen; Recovery durch {worker_id}",
                error_code="WORKER_RECOVERY_REQUIRED",
                error_message="Worker lease expired before completion",
            )
            .execution_options(synchronize_session=False)
        )
        self._session.commit()
        for stale_job in stale_jobs:
            bind_observability_context(correlation_id=f"job-{stale_job.id}", workspace_id=stale_job.workspace_id, user_id=stale_job.requested_by_user_id)
            log_event(
                "background_job_recovered",
                workspace_id=stale_job.workspace_id,
                user_id=stale_job.requested_by_user_id,
                status="retryable",
                error_code="WORKER_RECOVERY_REQUIRED",
            )
        return int(recovered.rowcount or 0)

    def _stale_lock_before(self, timestamp: datetime) -> datetime:
        from datetime import timedelta

        return timestamp - timedelta(seconds=settings.background_job_lock_timeout_seconds)

    def _backoff_before(self, timestamp: datetime) -> datetime:
        from datetime import timedelta

        return timestamp - timedelta(seconds=settings.background_job_retry_backoff_seconds)

    def _failure_progress_message(self, status: str) -> str:
        if status == "retryable":
            return "Job fehlgeschlagen, Retry geplant"
        if status == "dead_letter":
            return "Job in Dead Letter verschoben"
        return "Job fehlgeschlagen"

    def replay_job(self, *, job_id: str, replayed_by_user_id: str) -> BackgroundJob:
        try:
            AdvisoryLockService.from_session(self._session).acquire_job_replay_lock(job_id=job_id)
        except ResourceLockedApiError:
            raise
        job = self._session.get(BackgroundJob, job_id)
        if job is None:
            raise BackgroundJobNotFoundError(job_id)
        if job.status not in ("dead_letter", "retryable"):
            raise JobNotReplayableApiError(
                message=f"Job {job_id!r} is in status {job.status!r} and cannot be replayed; only dead_letter and retryable jobs are eligible",
                details={"job_id": job_id, "current_status": job.status},
            )
        previous_error_code = job.error_code
        previous_error_message = job.error_message
        replayed_at = datetime.now(UTC)
        payload = dict(job.payload_ or {}) if isinstance(job.payload_, dict) else {}
        replay_history = list(payload.get("replay_history") or [])
        replay_event = {
            "previous_error_code": previous_error_code,
            "previous_error_message": previous_error_message,
            "replayed_at": replayed_at.isoformat(),
            "replayed_by_user_id": replayed_by_user_id,
        }
        replay_history.append(replay_event)
        payload["replay_history"] = replay_history
        payload["previous_error"] = replay_event
        payload["last_replayed_at"] = replay_event["replayed_at"]
        payload["last_replayed_by_user_id"] = replayed_by_user_id
        job.status = "pending"
        job.error_code = None
        job.error_message = None
        job.progress_message = f"Replay angefordert durch {replayed_by_user_id}"
        job.started_at = None
        job.finished_at = None
        job.locked_at = None
        job.locked_by = None
        job.payload_ = payload
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        log_event(
            "background_job_replayed",
            workspace_id=job.workspace_id,
            user_id=replayed_by_user_id,
            status="pending",
        )
        return job

    def enqueue_search_index_rebuild_job(
        self,
        *,
        workspace_id: str,
        requested_by_user_id: str | None,
        target_workspace_id: str | None,
        correlation_id: str | None = None,
    ) -> BackgroundJob:
        now = datetime.now(UTC)
        job = BackgroundJob(
            id=str(uuid4()),
            job_type="search_index_rebuild",
            status="pending",
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            payload_={"target_workspace_id": target_workspace_id, "correlation_id": correlation_id},
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
        payload = job.payload_ if isinstance(job.payload_, dict) else {}
        parsed_result = None
        if result is not None:
            if job.job_type == "document_import":
                parsed_result = ImportJobResult(**result)
            elif job.job_type == "search_index_rebuild":
                parsed_result = SearchIndexRebuildJobResult(**result)
        previous_error = self._parse_previous_error(payload)
        replay_history = self._parse_replay_history(payload)
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
            previous_error=previous_error,
            replay_history=replay_history,
            result=parsed_result,
        )

    def _parse_previous_error(self, payload: dict) -> JobPreviousError | None:
        raw_previous_error = payload.get("previous_error")
        if not isinstance(raw_previous_error, dict):
            return None
        replayed_at = raw_previous_error.get("replayed_at")
        if not isinstance(replayed_at, str):
            return None
        return JobPreviousError(
            previous_error_code=raw_previous_error.get("previous_error_code") if isinstance(raw_previous_error.get("previous_error_code"), str) or raw_previous_error.get("previous_error_code") is None else None,
            previous_error_message=raw_previous_error.get("previous_error_message") if isinstance(raw_previous_error.get("previous_error_message"), str) or raw_previous_error.get("previous_error_message") is None else None,
            replayed_at=datetime.fromisoformat(replayed_at),
            replayed_by_user_id=raw_previous_error.get("replayed_by_user_id") if isinstance(raw_previous_error.get("replayed_by_user_id"), str) or raw_previous_error.get("replayed_by_user_id") is None else None,
        )

    def _parse_replay_history(self, payload: dict) -> list[JobReplayAuditEntry]:
        raw_history = payload.get("replay_history")
        if not isinstance(raw_history, list):
            return []
        entries: list[JobReplayAuditEntry] = []
        for entry in raw_history:
            if not isinstance(entry, dict):
                continue
            replayed_at = entry.get("replayed_at")
            if not isinstance(replayed_at, str):
                continue
            entries.append(
                JobReplayAuditEntry(
                    previous_error_code=entry.get("previous_error_code") if isinstance(entry.get("previous_error_code"), str) or entry.get("previous_error_code") is None else None,
                    previous_error_message=entry.get("previous_error_message") if isinstance(entry.get("previous_error_message"), str) or entry.get("previous_error_message") is None else None,
                    replayed_at=datetime.fromisoformat(replayed_at),
                    replayed_by_user_id=entry.get("replayed_by_user_id") if isinstance(entry.get("replayed_by_user_id"), str) or entry.get("replayed_by_user_id") is None else None,
                )
            )
        return entries

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
        bind_observability_context(
            correlation_id=_job_correlation_id(job, payload),
            workspace_id=job.workspace_id,
            user_id=job.requested_by_user_id,
        )
        temp_file_path = str(payload.get("temp_file_path") or "")
        filename = str(payload.get("filename") or "untitled")
        mime_type = str(payload.get("mime_type") or "application/octet-stream")

        try:
            heartbeat_stop = Event()
            heartbeat = _start_job_heartbeat(bind or get_engine(), job_id=job.id, worker_id="import-worker", stop_event=heartbeat_stop)
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
            # Move duplicate handling before any error handling
            if result.get("import_status") == "duplicate":
                job.status = "completed"
                job.error_code = None
                job.error_message = None
                job.progress_message = "Job abgeschlossen (duplicate)"
                service.mark_job_completed(job=job, result=result)
                if temp_file_path:
                    try:
                        os.remove(temp_file_path)
                    except FileNotFoundError:
                        pass
                return
            service.mark_job_completed(job=job, result=result)
            if temp_file_path:
                try:
                    os.remove(temp_file_path)
                except FileNotFoundError:
                    pass
        except ApiError as exc:
            duplicate_codes = {"duplicate", "DUPLICATE_DOCUMENT"}
            if getattr(exc, 'code', None) in duplicate_codes:
                job.status = "completed"
                service.mark_job_completed(job=job, result={
                    "document_id": None,
                    "version_id": None,
                    "import_status": "duplicate",
                    "duplicate_of_document_id": None,
                    "chunk_count": 0,
                    "parser_type": "unknown",
                    "warnings": [],
                })
            else:
                retryable = _is_retryable_import_error(exc.code)
                service.mark_job_failure(job=job, error_code=exc.code, error_message=exc.message, retryable=retryable)
        except Exception as exc:
            # Defensive: If the exception message or args indicate a duplicate, treat as completed
            duplicate_indicators = ("duplicate", "DUPLICATE_DOCUMENT")
            msg = str(exc)
            if any(ind in msg for ind in duplicate_indicators):
                job.status = "completed"
                service.mark_job_completed(job=job, result={
                    "document_id": None,
                    "version_id": None,
                    "import_status": "duplicate",
                    "duplicate_of_document_id": None,
                    "chunk_count": 0,
                    "parser_type": "unknown",
                    "warnings": [],
                })
            else:
                service.mark_job_failure(
                    job=job,
                    error_code="IMPORT_FAILED",
                    error_message="Document import failed",
                    retryable=True,
                )
        finally:
            if 'heartbeat_stop' in locals():
                heartbeat_stop.set()
            if 'heartbeat' in locals():
                heartbeat.join(timeout=1)


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
        bind_observability_context(
            correlation_id=_job_correlation_id(job, payload),
            workspace_id=job.workspace_id,
            user_id=job.requested_by_user_id,
        )
        target_workspace_id = payload.get("target_workspace_id")

        try:
            heartbeat_stop = Event()
            heartbeat = _start_job_heartbeat(bind or get_engine(), job_id=job.id, worker_id="search-index-worker", stop_event=heartbeat_stop)
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
        finally:
            if 'heartbeat_stop' in locals():
                heartbeat_stop.set()
            if 'heartbeat' in locals():
                heartbeat.join(timeout=1)


def _is_retryable_import_error(error_code: str | None) -> bool:
    return (error_code or "").upper() in {"SERVICE_UNAVAILABLE", "IMPORT_FAILED", "FILE_READ_FAILED"}


def _driver_connection(session: Session):
    sql_connection = session.connection()
    proxied_connection = getattr(sql_connection, "connection", None)
    driver_connection = getattr(proxied_connection, "driver_connection", None)
    return driver_connection


def _start_job_heartbeat(bind: Engine, *, job_id: str, worker_id: str, stop_event: Event) -> Thread:
    heartbeat = Thread(target=_heartbeat_job_lock, args=(bind, job_id, worker_id, stop_event), daemon=True)
    heartbeat.start()
    return heartbeat


def _job_correlation_id(job: BackgroundJob, payload: dict[str, object]) -> str:
    correlation_id = payload.get("correlation_id")
    if isinstance(correlation_id, str) and correlation_id.strip():
        return correlation_id.strip()
    return f"job-{job.id}"


def _heartbeat_job_lock(bind: Engine, job_id: str, worker_id: str, stop_event: Event) -> None:
    interval_seconds = max(1, settings.background_job_heartbeat_interval_seconds)
    while not stop_event.wait(interval_seconds):
        try:
            with Session(bind) as session:
                renewed = BackgroundJobService.from_session(session).renew_job_lock(job_id=job_id, worker_id=worker_id)
                if not renewed:
                    return
        except Exception:
            return