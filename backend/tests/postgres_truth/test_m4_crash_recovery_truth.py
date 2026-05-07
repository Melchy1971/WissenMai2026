from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.jobs.background_jobs import BackgroundJobService
from tests.integration.test_migrations import psycopg_url
from tests.postgres_truth.crash_matrix import load_crash_consistency_matrix
from tests.postgres_truth.support import TRUTH_USER_ID, TRUTH_WORKSPACE_ID


pytestmark = pytest.mark.postgres_truth

CRASH_JOB_ID = "truth-job-crash-import-1"
CRASH_DUPLICATE_JOB_ID_1 = "truth-job-crash-duplicate-1"
CRASH_DUPLICATE_JOB_ID_2 = "truth-job-crash-duplicate-2"
CRASH_REINDEX_JOB_ID = "truth-job-crash-reindex-1"


@pytest.mark.m4b_gate
def test_backend_process_kill_during_import_leaves_retryable_job_and_no_orphan_rows(
    postgres_truth_database_url: str,
    truth_session: Session,
    tmp_path: Path,
) -> None:
    temp_file = tmp_path / "truth-crash-import.txt"
    temp_file.write_bytes(b"# Truth\n\ncrash recovery import payload\n")

    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'pending', :workspace_id, :user_id, cast(:payload as jsonb), null,
                0, 1, 'pending', null, null,
                0, null, null, :created_at, null, null
            )
            """
        ),
        {
            "id": CRASH_JOB_ID,
            "workspace_id": TRUTH_WORKSPACE_ID,
            "user_id": TRUTH_USER_ID,
            "payload": json.dumps(
                {
                    "filename": "truth-crash-import.txt",
                    "mime_type": "text/plain",
                    "temp_file_path": str(temp_file),
                }
            ),
            "created_at": datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
        },
    )
    truth_session.commit()

    signal_file = tmp_path / "worker-ready.signal"
    worker_script = Path(__file__).with_name("crash_import_worker.py")
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = postgres_truth_database_url
    env["CRASH_JOB_ID"] = CRASH_JOB_ID
    env["CRASH_SIGNAL_FILE"] = str(signal_file)

    worker = subprocess.Popen(
        [sys.executable, str(worker_script)],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
    )
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not signal_file.exists():
            time.sleep(0.1)
        assert signal_file.exists(), "worker did not reach crash point in time"
    finally:
        worker.kill()
        worker.wait(timeout=10)

    recovered = BackgroundJobService.from_session(truth_session).recover_stale_jobs(
        worker_id="truth-crash-recovery",
        now=datetime.now(UTC).replace(year=2026, month=5, day=7, hour=13, minute=0),
    )
    assert recovered == 1

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=TRUTH_WORKSPACE_ID)
    assert matrix.background_jobs_running == 0
    assert matrix.background_jobs_retryable >= 1
    assert matrix.orphan_documents_without_version == 0
    assert matrix.orphan_versions_without_document == 0
    assert matrix.orphan_chunks_without_document == 0
    assert matrix.orphan_chunks_without_version == 0
    assert matrix.duplicate_versions_per_number == 0
    assert matrix.duplicate_chunks_per_index == 0


@pytest.mark.m4c_gate
def test_sql_crash_matrix_detects_no_stale_lifecycle_index_in_truth_workspace(
    postgres_truth_database_url: str,
    truth_session: Session,
) -> None:
    truth_session.execute(
        text(
            """
            insert into documents (
                id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at
            ) values (
                'f3000000-0000-0000-0000-000000000099'::uuid,
                :workspace_id::uuid,
                :user_id::uuid,
                null,
                'Crash Matrix',
                'upload',
                'text/plain',
                'truth-crash-matrix-hash',
                'pending',
                'active',
                null,
                null,
                now(),
                now()
            )
            on conflict do nothing
            """
        ),
        {"workspace_id": TRUTH_WORKSPACE_ID, "user_id": TRUTH_USER_ID},
    )
    truth_session.commit()

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=TRUTH_WORKSPACE_ID)
    assert matrix.orphan_documents_without_version == 0
    assert matrix.orphan_versions_without_document == 0
    assert matrix.orphan_chunks_without_document == 0
    assert matrix.orphan_chunks_without_version == 0
    assert matrix.duplicate_versions_per_number == 0
    assert matrix.duplicate_chunks_per_index == 0
    assert matrix.stale_archived_searchable_chunks == 0
    assert matrix.stale_deleted_searchable_chunks == 0


@pytest.mark.m4b_gate
def test_backend_http_process_kill_during_upload_leaves_no_partial_db_rows(
    postgres_truth_database_url: str,
    tmp_path: Path,
) -> None:
    signal_file = tmp_path / "server-ready.signal"
    temp_file = tmp_path / "upload-temp.bin"
    port = "8765"
    server_script = Path(__file__).with_name("crash_api_server.py")
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = postgres_truth_database_url
    env["DATABASE_URL"] = postgres_truth_database_url
    env["CRASH_SIGNAL_FILE"] = str(signal_file)
    env["CRASH_TEMP_FILE"] = str(temp_file)
    env["CRASH_SERVER_PORT"] = port

    server = subprocess.Popen([sys.executable, str(server_script)], cwd=str(Path(__file__).resolve().parents[2]), env=env)
    try:
        deadline = time.time() + 15
        client_error = None
        with httpx.Client(timeout=5.0) as client:
            request_started = False
            while time.time() < deadline and not signal_file.exists():
                if not request_started:
                    request_started = True
                    try:
                        client.post(
                            f"http://127.0.0.1:{port}/documents/import",
                            headers={
                                "Authorization": "Bearer postgres-truth-session-token",
                                "X-Workspace-Id": TRUTH_WORKSPACE_ID,
                            },
                            files={"file": ("truth-http-crash.txt", b"# Truth\n\nHTTP upload crash\n", "text/plain")},
                        )
                    except Exception as exc:  # pragma: no cover - expected once process is killed
                        client_error = exc
                time.sleep(0.1)
            assert signal_file.exists(), "server did not reach upload crash point in time"
        assert client_error is None or isinstance(client_error, Exception)
    finally:
        server.kill()
        server.wait(timeout=10)

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=TRUTH_WORKSPACE_ID)
    assert matrix.orphan_documents_without_version == 0
    assert matrix.orphan_versions_without_document == 0
    assert matrix.orphan_chunks_without_document == 0
    assert matrix.orphan_chunks_without_version == 0


@pytest.mark.m4b_gate
def test_duplicate_import_worker_crash_recovery_avoids_duplicate_versions_and_chunks(
    postgres_truth_database_url: str,
    truth_session: Session,
    tmp_path: Path,
) -> None:
    temp_file = tmp_path / "truth-duplicate-crash.txt"
    temp_file.write_bytes(b"# Truth\n\nduplicate crash content\n")

    for job_id in (CRASH_DUPLICATE_JOB_ID_1, CRASH_DUPLICATE_JOB_ID_2):
        truth_session.execute(
            text(
                """
                insert into background_jobs (
                    id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                    progress_current, progress_total, progress_message, error_code, error_message,
                    attempt_count, locked_at, locked_by, created_at, started_at, finished_at
                ) values (
                    :id, 'document_import', 'pending', :workspace_id, :user_id, cast(:payload as jsonb), null,
                    0, 1, 'pending', null, null,
                    0, null, null, now(), null, null
                )
                """
            ),
            {
                "id": job_id,
                "workspace_id": TRUTH_WORKSPACE_ID,
                "user_id": TRUTH_USER_ID,
                "payload": json.dumps(
                    {
                        "filename": "truth-duplicate-crash.txt",
                        "mime_type": "text/plain",
                        "temp_file_path": str(temp_file),
                    }
                ),
            },
        )
    truth_session.commit()

    signal_file = tmp_path / "duplicate-worker-ready.signal"
    worker_script = Path(__file__).with_name("crash_import_worker.py")
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = postgres_truth_database_url
    env["CRASH_JOB_ID"] = CRASH_DUPLICATE_JOB_ID_1
    env["CRASH_SIGNAL_FILE"] = str(signal_file)
    worker = subprocess.Popen([sys.executable, str(worker_script)], cwd=str(Path(__file__).resolve().parents[2]), env=env)
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not signal_file.exists():
            time.sleep(0.1)
        assert signal_file.exists(), "duplicate worker did not reach crash point in time"
    finally:
        worker.kill()
        worker.wait(timeout=10)

    recovered = BackgroundJobService.from_session(truth_session).recover_stale_jobs(
        worker_id="truth-duplicate-recovery",
        now=datetime.now(UTC).replace(year=2026, month=5, day=7, hour=14, minute=0),
    )
    assert recovered >= 1

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=TRUTH_WORKSPACE_ID)
    assert matrix.duplicate_versions_per_number == 0
    assert matrix.duplicate_chunks_per_index == 0
    assert matrix.orphan_documents_without_version == 0
    assert matrix.orphan_chunks_without_document == 0


@pytest.mark.m4c_gate
def test_reindex_worker_crash_recovery_leaves_retryable_job_without_lifecycle_drift(
    postgres_truth_database_url: str,
    truth_session: Session,
    tmp_path: Path,
) -> None:
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'search_index_rebuild', 'pending', :workspace_id, :user_id, cast(:payload as jsonb), null,
                0, 1, 'pending', null, null,
                0, null, null, now(), null, null
            )
            """
        ),
        {
            "id": CRASH_REINDEX_JOB_ID,
            "workspace_id": TRUTH_WORKSPACE_ID,
            "user_id": TRUTH_USER_ID,
            "payload": json.dumps({"target_workspace_id": TRUTH_WORKSPACE_ID}),
        },
    )
    truth_session.commit()

    signal_file = tmp_path / "reindex-worker-ready.signal"
    worker_script = Path(__file__).with_name("crash_reindex_worker.py")
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = postgres_truth_database_url
    env["CRASH_JOB_ID"] = CRASH_REINDEX_JOB_ID
    env["CRASH_SIGNAL_FILE"] = str(signal_file)
    worker = subprocess.Popen([sys.executable, str(worker_script)], cwd=str(Path(__file__).resolve().parents[2]), env=env)
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not signal_file.exists():
            time.sleep(0.1)
        assert signal_file.exists(), "reindex worker did not reach crash point in time"
    finally:
        worker.kill()
        worker.wait(timeout=10)

    recovered = BackgroundJobService.from_session(truth_session).recover_stale_jobs(
        worker_id="truth-reindex-recovery",
        now=datetime.now(UTC).replace(year=2026, month=5, day=7, hour=15, minute=0),
    )
    assert recovered >= 1

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=TRUTH_WORKSPACE_ID)
    assert matrix.background_jobs_running == 0
    assert matrix.background_jobs_retryable >= 1
    assert matrix.stale_archived_searchable_chunks == 0
    assert matrix.stale_deleted_searchable_chunks == 0