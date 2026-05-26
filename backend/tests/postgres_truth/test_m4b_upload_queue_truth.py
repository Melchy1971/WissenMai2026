from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import OcrRequiredApiError, ParserFailedApiError
from app.main import app
from app.services.jobs.background_jobs import (
    BackgroundJobAlreadyClaimedError,
    BackgroundJobService,
    process_import_job,
)
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m4b_upload_queue_truth]


def test_m4b_retryable_job_is_not_claimed_before_backoff_expires(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    job_id = truth_ids.job_id("backoff-not-expired")
    now = datetime.now(UTC)
    recently_failed_at = now - timedelta(seconds=5)
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'retryable', :workspace_id, :user_id,
                cast(:payload as jsonb), null,
                1, 1, 'Job fehlgeschlagen, Retry geplant', 'IMPORT_FAILED', 'transient failure',
                1, null, null, :now, :now, :finished_at
            )
            """
        ),
        {
            "id": job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json.dumps({"filename": f"backoff-{truth_ids.slug}.txt", "mime_type": "text/plain", "temp_file_path": "unused"}),
            "now": now,
            "finished_at": recently_failed_at,
        },
    )
    truth_session.commit()

    service = BackgroundJobService.from_session(truth_session)
    with pytest.raises(BackgroundJobAlreadyClaimedError):
        service.claim_job(job_id=job_id, worker_id="backoff-test-worker", now=now)

    row = truth_session.execute(
        text("select status from background_jobs where id = :id"),
        {"id": job_id},
    ).one()
    assert row.status == "retryable", "job must stay retryable when backoff has not yet expired"


def test_m4b_retryable_job_is_claimed_after_backoff_expires(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    job_id = truth_ids.job_id("backoff-expired")
    now = datetime.now(UTC)
    expired_at = now - timedelta(seconds=settings.background_job_retry_backoff_seconds + 10)
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'retryable', :workspace_id, :user_id,
                cast(:payload as jsonb), null,
                1, 1, 'Job fehlgeschlagen, Retry geplant', 'IMPORT_FAILED', 'transient failure',
                1, null, null, :now, :now, :finished_at
            )
            """
        ),
        {
            "id": job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json.dumps({"filename": f"expired-{truth_ids.slug}.txt", "mime_type": "text/plain", "temp_file_path": "unused"}),
            "now": now,
            "finished_at": expired_at,
        },
    )
    truth_session.commit()

    service = BackgroundJobService.from_session(truth_session)
    claimed = service.claim_job(job_id=job_id, worker_id="retry-worker", now=now)

    assert claimed.status == "running"
    assert claimed.attempt_count == 2


def test_m4b_file_too_large_returns_413_and_no_job_created(
    truth_seed: dict[str, str],
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_size_bytes", 1024)
    client = TestClient(
        app,
        headers={
            "Authorization": f"Bearer {truth_seed['token']}",
            "X-Workspace-Id": truth_seed["workspace_id"],
        },
        raise_server_exceptions=False,
    )
    oversized = b"x" * 2048

    response = client.post(
        "/documents/import",
        files={"file": ("oversized.txt", oversized, "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
    count = truth_session.execute(
        text("select count(*) from background_jobs where workspace_id = :workspace_id"),
        {"workspace_id": truth_seed["workspace_id"]},
    ).scalar_one()
    assert count == 0, "no job must be created when upload exceeds size limit"


def test_m4b_ocr_required_error_marks_job_as_failed_not_retryable(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    temp_file = tmp_path / f"ocr-{truth_ids.slug}.pdf"
    temp_file.write_bytes(b"fake pdf bytes")
    job_id = truth_ids.job_id("ocr-required")
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'pending', :workspace_id, :user_id,
                cast(:payload as jsonb), null,
                0, 1, 'pending', null, null,
                0, null, null, now(), null, null
            )
            """
        ),
        {
            "id": job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json.dumps({"filename": f"ocr-{truth_ids.slug}.pdf", "mime_type": "application/pdf", "temp_file_path": str(temp_file)}),
        },
    )
    truth_session.commit()

    class OcrRequiredExecutor:
        def execute(self, **_kwargs):
            raise OcrRequiredApiError(message="OCR required but not configured")

    monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", OcrRequiredExecutor)
    process_import_job(job_id, truth_session.connection())

    row = truth_session.execute(
        text("select status, error_code from background_jobs where id = :id"),
        {"id": job_id},
    ).one()
    assert row.status == "failed", "OCR_REQUIRED is non-retryable: status must be 'failed'"
    assert row.error_code == "OCR_REQUIRED"


def test_m4b_parser_failure_marks_job_as_failed_not_retryable(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    temp_file = tmp_path / f"corrupt-{truth_ids.slug}.docx"
    temp_file.write_bytes(b"not a valid docx")
    job_id = truth_ids.job_id("parser-failed")
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'pending', :workspace_id, :user_id,
                cast(:payload as jsonb), null,
                0, 1, 'pending', null, null,
                0, null, null, now(), null, null
            )
            """
        ),
        {
            "id": job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json.dumps({"filename": f"corrupt-{truth_ids.slug}.docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "temp_file_path": str(temp_file)}),
        },
    )
    truth_session.commit()

    class ParserCrashExecutor:
        def execute(self, **_kwargs):
            raise ParserFailedApiError(message="Document could not be parsed")

    monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", ParserCrashExecutor)
    process_import_job(job_id, truth_session.connection())

    row = truth_session.execute(
        text("select status, error_code from background_jobs where id = :id"),
        {"id": job_id},
    ).one()
    assert row.status == "failed", "PARSER_FAILED is non-retryable: status must be 'failed'"
    assert row.error_code == "PARSER_FAILED"
