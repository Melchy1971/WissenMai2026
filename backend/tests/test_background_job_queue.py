from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import tempfile

import pytest

from app.core.config import settings
from app.core.errors import ParserFailedApiError
from app.models.documents import BackgroundJob
from app.observability.logging import event_logger, metrics_registry
from app.services.jobs.background_jobs import (
    BackgroundJobAlreadyClaimedError,
    BackgroundJobService,
    process_import_job,
    process_search_index_rebuild_job,
)


def make_job(*, status: str = "pending", attempt_count: int = 0, locked_at=None, locked_by=None) -> BackgroundJob:
    now = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    return BackgroundJob(
        id="job-queue-1",
        job_type="document_import",
        status=status,
        workspace_id="00000000-0000-0000-0000-000000000001",
        requested_by_user_id="00000000-0000-0000-0000-000000000001",
        payload_={"filename": "queue.txt", "mime_type": "text/plain", "temp_file_path": ""},
        result_=None,
        progress_current=0,
        progress_total=1,
        progress_message=None,
        error_code=None,
        error_message=None,
        attempt_count=attempt_count,
        locked_at=locked_at,
        locked_by=locked_by,
        created_at=now,
        started_at=None,
        finished_at=None,
    )


def make_search_job(*, status: str = "pending", attempt_count: int = 0, locked_at=None, locked_by=None) -> BackgroundJob:
    now = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    return BackgroundJob(
        id="job-search-1",
        job_type="search_index_rebuild",
        status=status,
        workspace_id="00000000-0000-0000-0000-000000000001",
        requested_by_user_id="00000000-0000-0000-0000-000000000001",
        payload_={"target_workspace_id": "00000000-0000-0000-0000-000000000001"},
        result_=None,
        progress_current=0,
        progress_total=1,
        progress_message=None,
        error_code=None,
        error_message=None,
        attempt_count=attempt_count,
        locked_at=locked_at,
        locked_by=locked_by,
        created_at=now,
        started_at=None,
        finished_at=None,
    )


def test_claim_job_is_deterministic_and_allows_only_one_worker(db_session) -> None:
    job = make_job()
    db_session.add(job)
    db_session.commit()

    first_service = BackgroundJobService.from_session(db_session)
    claimed = first_service.claim_job(job_id=job.id, worker_id="worker-a")

    assert claimed.status == "running"
    assert claimed.locked_by == "worker-a"
    assert claimed.attempt_count == 1

    second_service = BackgroundJobService.from_session(db_session)
    with pytest.raises(BackgroundJobAlreadyClaimedError):
        second_service.claim_job(job_id=job.id, worker_id="worker-b")


def test_recover_stale_running_job_marks_it_retryable(db_session) -> None:
    stale_at = datetime.now(UTC) - timedelta(seconds=settings.background_job_lock_timeout_seconds + 5)
    job = make_job(status="running", attempt_count=1, locked_at=stale_at, locked_by="worker-a")
    db_session.add(job)
    db_session.commit()

    service = BackgroundJobService.from_session(db_session)
    recovered = service.recover_stale_jobs(worker_id="worker-b")

    refreshed = db_session.get(BackgroundJob, job.id)
    assert recovered == 1
    assert refreshed is not None
    assert refreshed.status == "retryable"
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert refreshed.error_code == "WORKER_RECOVERY_REQUIRED"


def test_recover_stale_running_job_emits_recovery_observability(db_session, caplog) -> None:
    stale_at = datetime.now(UTC) - timedelta(seconds=settings.background_job_lock_timeout_seconds + 5)
    job = make_job(status="running", attempt_count=1, locked_at=stale_at, locked_by="worker-a")
    db_session.add(job)
    db_session.commit()
    metrics_registry.reset()

    with caplog.at_level("INFO", logger="app.observability.events"):
        recovered = BackgroundJobService.from_session(db_session).recover_stale_jobs(worker_id="worker-b")

    assert recovered == 1
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert observability_records[-1]["event_name"] == "background_job_recovered"
    assert observability_records[-1]["workspace_id"] == job.workspace_id
    assert observability_records[-1]["status"] == "retryable"
    assert observability_records[-1]["error_code"] == "WORKER_RECOVERY_REQUIRED"
    assert observability_records[-1]["correlation_id"] == f"job-{job.id}"
    snapshot = metrics_registry.snapshot()
    assert snapshot["background_job_recovered.retryable"] == 1


def test_renew_job_lock_prevents_slow_worker_from_being_recovered(db_session) -> None:
    claimed_at = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    renewed_at = claimed_at + timedelta(seconds=settings.background_job_lock_timeout_seconds - 1)
    recovery_check_at = claimed_at + timedelta(seconds=settings.background_job_lock_timeout_seconds + 1)
    job = make_job(status="running", attempt_count=1, locked_at=claimed_at, locked_by="worker-a")
    db_session.add(job)
    db_session.commit()

    service = BackgroundJobService.from_session(db_session)
    renewed = service.renew_job_lock(job_id=job.id, worker_id="worker-a", now=renewed_at)
    recovered = service.recover_stale_jobs(worker_id="worker-b", now=recovery_check_at)

    refreshed = db_session.get(BackgroundJob, job.id)
    assert renewed is True
    assert recovered == 0
    assert refreshed is not None
    assert refreshed.status == "running"
    assert refreshed.locked_by == "worker-a"
    assert refreshed.locked_at is not None
    assert refreshed.locked_at.replace(tzinfo=UTC) == renewed_at


def test_renew_job_lock_rejects_wrong_worker(db_session) -> None:
    job = make_job(status="running", attempt_count=1, locked_at=datetime.now(UTC), locked_by="worker-a")
    db_session.add(job)
    db_session.commit()

    service = BackgroundJobService.from_session(db_session)
    renewed = service.renew_job_lock(job_id=job.id, worker_id="worker-b")

    refreshed = db_session.get(BackgroundJob, job.id)
    assert renewed is False
    assert refreshed is not None
    assert refreshed.locked_by == "worker-a"


def test_process_import_job_marks_generic_failure_retryable_and_keeps_payload_for_recovery(db_session, monkeypatch, tmp_path) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "queue.txt"
        temp_file.write_bytes(b"queue payload")
        job = make_job()
        job.payload_ = {"filename": "queue.txt", "mime_type": "text/plain", "temp_file_path": str(temp_file)}
        db_session.add(job)
        db_session.commit()

        class CrashingImportExecutor:
            def execute(self, **_kwargs):
                raise RuntimeError("chunking crashed")

        monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", CrashingImportExecutor)

        process_import_job(job.id, db_session.connection())

        db_session.expire_all()
        refreshed = db_session.get(BackgroundJob, job.id)
        assert refreshed is not None
        assert refreshed.status == "retryable"
        assert refreshed.error_code == "IMPORT_FAILED"
        assert Path(refreshed.payload_["temp_file_path"]).exists() is True


def test_process_import_job_retry_is_observable_with_job_correlation(db_session, monkeypatch, caplog) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "queue.txt"
        temp_file.write_bytes(b"queue payload")
        job = make_job()
        job.payload_ = {
            "filename": "queue.txt",
            "mime_type": "text/plain",
            "temp_file_path": str(temp_file),
            "correlation_id": "corr-import-1",
        }
        db_session.add(job)
        db_session.commit()
        metrics_registry.reset()

        class CrashingImportExecutor:
            def execute(self, **_kwargs):
                raise RuntimeError("chunking crashed")

        monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", CrashingImportExecutor)

        event_logger.disabled = False
        event_logger.propagate = True
        caplog.clear()
        with caplog.at_level("INFO", logger="app.observability.events"):
            process_import_job(job.id, db_session.connection())

        observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
        assert observability_records[-1]["event_name"] == "background_job_retry_scheduled"
        assert observability_records[-1]["workspace_id"] == job.workspace_id
        assert observability_records[-1]["status"] == "retryable"
        assert observability_records[-1]["error_code"] == "IMPORT_FAILED"
        assert observability_records[-1]["correlation_id"] == "corr-import-1"
        snapshot = metrics_registry.snapshot()
        assert snapshot["background_job_retry_scheduled.retryable"] == 1


def test_process_import_job_marks_parser_crash_as_terminal_failure_without_duplicate_rows(db_session, monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "parser-crash.txt"
        temp_file.write_bytes(b"parser payload")
        job = make_job()
        job.payload_ = {
            "filename": "parser-crash.txt",
            "mime_type": "text/plain",
            "temp_file_path": str(temp_file),
        }
        db_session.add(job)
        db_session.commit()

        class CrashingImportExecutor:
            def execute(self, **_kwargs):
                raise ParserFailedApiError(message="parser crashed irrecoverably")

        monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", CrashingImportExecutor)

        process_import_job(job.id, db_session.connection())

        db_session.expire_all()
        refreshed = db_session.get(BackgroundJob, job.id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.error_code == "PARSER_FAILED"
        assert refreshed.attempt_count == 1
        assert Path(refreshed.payload_["temp_file_path"]).exists() is True


def test_process_import_job_recovers_retryable_job_without_job_loss(db_session, monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "queue-retry.txt"
        temp_file.write_bytes(b"queue payload")
        job = make_job(status="retryable", attempt_count=1)
        job.payload_ = {"filename": "queue-retry.txt", "mime_type": "text/plain", "temp_file_path": str(temp_file)}
        db_session.add(job)
        db_session.commit()

        class SuccessfulImportExecutor:
            def execute(self, **_kwargs):
                return {
                    "document_id": "doc-1",
                    "version_id": "ver-1",
                    "import_status": "chunked",
                    "duplicate_of_document_id": None,
                    "chunk_count": 1,
                    "parser_type": "txt-parser",
                    "warnings": [],
                }

        monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", SuccessfulImportExecutor)

        process_import_job(job.id, db_session.connection())

        db_session.expire_all()
        refreshed = db_session.get(BackgroundJob, job.id)
        assert refreshed is not None
        assert refreshed.status == "completed"
        assert refreshed.result_["document_id"] == "doc-1"
        assert Path(str(temp_file)).exists() is False


def test_process_import_job_moves_exhausted_retryable_job_to_dead_letter(db_session, monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "queue-dead.txt"
        temp_file.write_bytes(b"queue payload")
        job = make_job(status="retryable", attempt_count=settings.background_job_max_attempts - 1)
        job.payload_ = {"filename": "queue-dead.txt", "mime_type": "text/plain", "temp_file_path": str(temp_file)}
        db_session.add(job)
        db_session.commit()

        class CrashingImportExecutor:
            def execute(self, **_kwargs):
                raise RuntimeError("database connection aborted")

        monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", CrashingImportExecutor)

        process_import_job(job.id, db_session.connection())

        db_session.expire_all()
        refreshed = db_session.get(BackgroundJob, job.id)
        assert refreshed is not None
        assert refreshed.status == "dead_letter"
        assert refreshed.error_code == "IMPORT_FAILED"
        assert Path(refreshed.payload_["temp_file_path"]).exists() is True


def test_process_search_index_rebuild_job_marks_failure_retryable_without_lifecycle_drift(db_session, monkeypatch) -> None:
    job = make_search_job()
    db_session.add(job)
    db_session.commit()

    class CrashingRebuildService:
        @classmethod
        def from_session(cls, _session):
            return cls()

        def rebuild_search_index(self, **_kwargs):
            raise RuntimeError("index rebuild crashed")

    monkeypatch.setattr("app.services.jobs.background_jobs.SearchIndexRebuildService", CrashingRebuildService)

    process_search_index_rebuild_job(job.id, db_session.connection())

    db_session.expire_all()
    refreshed = db_session.get(BackgroundJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "retryable"
    assert refreshed.error_code == "SERVICE_UNAVAILABLE"


def test_process_search_index_rebuild_job_moves_exhausted_retry_to_dead_letter(db_session, monkeypatch) -> None:
    job = make_search_job(status="retryable", attempt_count=settings.background_job_max_attempts - 1)
    db_session.add(job)
    db_session.commit()

    class CrashingRebuildService:
        @classmethod
        def from_session(cls, _session):
            return cls()

        def rebuild_search_index(self, **_kwargs):
            raise RuntimeError("index rebuild crashed")

    monkeypatch.setattr("app.services.jobs.background_jobs.SearchIndexRebuildService", CrashingRebuildService)

    process_search_index_rebuild_job(job.id, db_session.connection())

    db_session.expire_all()
    refreshed = db_session.get(BackgroundJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "dead_letter"
    assert refreshed.error_code == "SERVICE_UNAVAILABLE"


def test_replay_dead_letter_preserves_previous_error_cause_and_audit(db_session) -> None:
    job = make_job(status="dead_letter", attempt_count=settings.background_job_max_attempts)
    job.error_code = "IMPORT_FAILED"
    job.error_message = "database connection aborted"
    db_session.add(job)
    db_session.commit()

    replayed = BackgroundJobService.from_session(db_session).replay_job(job_id=job.id, replayed_by_user_id="admin-1")
    response = BackgroundJobService.from_session(db_session).to_response(replayed)

    assert replayed.status == "pending"
    assert replayed.error_code is None
    assert replayed.error_message is None
    assert response.previous_error is not None
    assert response.previous_error.previous_error_code == "IMPORT_FAILED"
    assert response.previous_error.previous_error_message == "database connection aborted"
    assert response.previous_error.replayed_by_user_id == "admin-1"
    assert len(response.replay_history) == 1
    assert response.replay_history[0].previous_error_code == "IMPORT_FAILED"


def test_replay_retryable_preserves_previous_error_cause_and_audit(db_session) -> None:
    job = make_job(status="retryable", attempt_count=1)
    job.error_code = "SERVICE_UNAVAILABLE"
    job.error_message = "temporary parser outage"
    db_session.add(job)
    db_session.commit()

    replayed = BackgroundJobService.from_session(db_session).replay_job(job_id=job.id, replayed_by_user_id="admin-2")
    response = BackgroundJobService.from_session(db_session).to_response(replayed)

    assert replayed.status == "pending"
    assert response.previous_error is not None
    assert response.previous_error.previous_error_code == "SERVICE_UNAVAILABLE"
    assert response.previous_error.previous_error_message == "temporary parser outage"
    assert response.replay_history[0].replayed_by_user_id == "admin-2"


def test_parallel_replay_only_succeeds_once(db_session) -> None:
    job = make_job(status="dead_letter", attempt_count=settings.background_job_max_attempts)
    job.error_code = "IMPORT_FAILED"
    job.error_message = "irrecoverable"
    db_session.add(job)
    db_session.commit()

    service = BackgroundJobService.from_session(db_session)
    replayed = service.replay_job(job_id=job.id, replayed_by_user_id="admin-1")
    assert replayed.status == "pending"

    with pytest.raises(Exception):
        service.replay_job(job_id=job.id, replayed_by_user_id="admin-2")


def test_replay_audit_is_visible_in_job_response(db_session) -> None:
    job = make_search_job(status="retryable", attempt_count=2)
    job.error_code = "SERVICE_UNAVAILABLE"
    job.error_message = "index rebuild crashed"
    db_session.add(job)
    db_session.commit()

    service = BackgroundJobService.from_session(db_session)
    service.replay_job(job_id=job.id, replayed_by_user_id="admin-3")
    refreshed = service.get_job(job.id)
    response = service.to_response(refreshed)

    assert response.previous_error is not None
    assert response.previous_error.previous_error_code == "SERVICE_UNAVAILABLE"
    assert response.previous_error.replayed_by_user_id == "admin-3"
    assert response.replay_history
    assert response.replay_history[0].previous_error_message == "index rebuild crashed"
