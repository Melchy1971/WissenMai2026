from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.jobs.background_jobs import BackgroundJobService
from tests.integration.test_migrations import psycopg_url
from tests.postgres_truth.crash_matrix import load_crash_consistency_matrix
from tests.postgres_truth.support import TruthIds


pytestmark = pytest.mark.postgres_truth

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _crash_subprocess_env(postgres_truth_database_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = postgres_truth_database_url
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(BACKEND_ROOT) if not pythonpath else f"{BACKEND_ROOT}{os.pathsep}{pythonpath}"
    return env


def _sa_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _insert_crash_job(
    database_url: str,
    *,
    job_id: str,
    job_type: str,
    workspace_id: str,
    user_id: str,
    payload: dict,
    created_at: datetime | None = None,
) -> None:
    with psycopg.connect(psycopg_url(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into background_jobs (
                    id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                    progress_current, progress_total, progress_message, error_code, error_message,
                    attempt_count, locked_at, locked_by, created_at, started_at, finished_at
                ) values (
                    %s, %s, 'pending', %s, %s, %s, null,
                    0, 1, 'pending', null, null,
                    0, null, null, coalesce(%s, now()), null, null
                )
                """,
                (
                    job_id,
                    job_type,
                    workspace_id,
                    user_id,
                    Jsonb(payload),
                    created_at,
                ),
            )
        connection.commit()


def _recover_stale_jobs(database_url: str, *, worker_id: str) -> int:
    engine = create_engine(_sa_url(database_url), pool_pre_ping=True)
    try:
        with Session(engine) as session:
            return BackgroundJobService.from_session(session).recover_stale_jobs(
                worker_id=worker_id,
                now=datetime.now(UTC) + timedelta(hours=1),
            )
    finally:
        engine.dispose()


@pytest.mark.m4b_gate
def test_backend_process_kill_during_import_leaves_retryable_job_and_no_orphan_rows(
    postgres_truth_database_url: str,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    tmp_path: Path,
) -> None:
    temp_file = tmp_path / "truth-crash-import.txt"
    temp_file.write_bytes(b"# Truth\n\ncrash recovery import payload\n")
    job_id = truth_ids.job_id("crash-import")

    _insert_crash_job(
        postgres_truth_database_url,
        job_id=job_id,
        job_type="document_import",
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        payload={
            "filename": "truth-crash-import.txt",
            "mime_type": "text/plain",
            "temp_file_path": str(temp_file),
        },
        created_at=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
    )

    signal_file = tmp_path / "worker-ready.signal"
    worker_script = Path(__file__).with_name("crash_import_worker.py")
    env = _crash_subprocess_env(postgres_truth_database_url)
    env["CRASH_JOB_ID"] = job_id
    env["CRASH_SIGNAL_FILE"] = str(signal_file)

    worker = subprocess.Popen(
        [sys.executable, str(worker_script)],
        cwd=str(BACKEND_ROOT),
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

    recovered = _recover_stale_jobs(postgres_truth_database_url, worker_id="truth-crash-recovery")
    assert recovered == 1

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=truth_seed["workspace_id"])
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
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    crash_doc_id = truth_ids.document_id("crash-matrix")
    truth_session.execute(
        text(
            """
            insert into documents (
                id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at
            ) values (
                cast(:document_id as uuid),
                cast(:workspace_id as uuid),
                cast(:user_id as uuid),
                null,
                'Crash Matrix',
                'upload',
                'text/plain',
                    :content_hash,
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
        {
            "document_id": crash_doc_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "content_hash": truth_ids.content_hash("crash-matrix"),
        },
    )
    truth_session.commit()

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=truth_seed["workspace_id"])
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
    truth_seed: dict[str, str],
    tmp_path: Path,
) -> None:
    signal_file = tmp_path / "server-ready.signal"
    temp_file = tmp_path / "upload-temp.bin"
    port = "8765"
    server_script = Path(__file__).with_name("crash_api_server.py")
    env = _crash_subprocess_env(postgres_truth_database_url)
    env["DATABASE_URL"] = postgres_truth_database_url
    env["CRASH_SIGNAL_FILE"] = str(signal_file)
    env["CRASH_TEMP_FILE"] = str(temp_file)
    env["CRASH_SERVER_PORT"] = port

    server = subprocess.Popen([sys.executable, str(server_script)], cwd=str(BACKEND_ROOT), env=env)
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
                                "Authorization": f"Bearer {truth_seed['token']}",
                                "X-Workspace-Id": truth_seed["workspace_id"],
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

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=truth_seed["workspace_id"])
    assert matrix.orphan_documents_without_version == 0
    assert matrix.orphan_versions_without_document == 0
    assert matrix.orphan_chunks_without_document == 0
    assert matrix.orphan_chunks_without_version == 0


@pytest.mark.m4b_gate
def test_duplicate_import_worker_crash_recovery_avoids_duplicate_versions_and_chunks(
    postgres_truth_database_url: str,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    tmp_path: Path,
) -> None:
    temp_file = tmp_path / "truth-duplicate-crash.txt"
    temp_file.write_bytes(b"# Truth\n\nduplicate crash content\n")
    duplicate_job_id_1 = truth_ids.job_id("crash-duplicate-1")
    duplicate_job_id_2 = truth_ids.job_id("crash-duplicate-2")

    for job_id in (duplicate_job_id_1, duplicate_job_id_2):
        _insert_crash_job(
            postgres_truth_database_url,
            job_id=job_id,
            job_type="document_import",
            workspace_id=truth_seed["workspace_id"],
            user_id=truth_seed["user_id"],
            payload={
                "filename": "truth-duplicate-crash.txt",
                "mime_type": "text/plain",
                "temp_file_path": str(temp_file),
            },
        )

    signal_file = tmp_path / "duplicate-worker-ready.signal"
    worker_script = Path(__file__).with_name("crash_import_worker.py")
    env = _crash_subprocess_env(postgres_truth_database_url)
    env["CRASH_JOB_ID"] = duplicate_job_id_1
    env["CRASH_SIGNAL_FILE"] = str(signal_file)
    worker = subprocess.Popen([sys.executable, str(worker_script)], cwd=str(BACKEND_ROOT), env=env)
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not signal_file.exists():
            time.sleep(0.1)
        assert signal_file.exists(), "duplicate worker did not reach crash point in time"
    finally:
        worker.kill()
        worker.wait(timeout=10)

    recovered = _recover_stale_jobs(postgres_truth_database_url, worker_id="truth-duplicate-recovery")
    assert recovered >= 1

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=truth_seed["workspace_id"])
    assert matrix.duplicate_versions_per_number == 0
    assert matrix.duplicate_chunks_per_index == 0
    assert matrix.orphan_documents_without_version == 0
    assert matrix.orphan_chunks_without_document == 0


@pytest.mark.m4c_gate
def test_reindex_worker_crash_recovery_leaves_retryable_job_without_lifecycle_drift(
    postgres_truth_database_url: str,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    tmp_path: Path,
) -> None:
    reindex_job_id = truth_ids.job_id("crash-reindex")
    _insert_crash_job(
        postgres_truth_database_url,
        job_id=reindex_job_id,
        job_type="search_index_rebuild",
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        payload={"target_workspace_id": truth_seed["workspace_id"]},
    )

    signal_file = tmp_path / "reindex-worker-ready.signal"
    worker_script = Path(__file__).with_name("crash_reindex_worker.py")
    env = _crash_subprocess_env(postgres_truth_database_url)
    env["CRASH_JOB_ID"] = reindex_job_id
    env["CRASH_SIGNAL_FILE"] = str(signal_file)
    worker = subprocess.Popen([sys.executable, str(worker_script)], cwd=str(BACKEND_ROOT), env=env)
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not signal_file.exists():
            time.sleep(0.1)
        assert signal_file.exists(), "reindex worker did not reach crash point in time"
    finally:
        worker.kill()
        worker.wait(timeout=10)

    recovered = _recover_stale_jobs(postgres_truth_database_url, worker_id="truth-reindex-recovery")
    assert recovered >= 1

    matrix = load_crash_consistency_matrix(psycopg_url(postgres_truth_database_url), workspace_id=truth_seed["workspace_id"])
    assert matrix.background_jobs_running == 0
    assert matrix.background_jobs_retryable >= 1
    assert matrix.stale_archived_searchable_chunks == 0
    assert matrix.stale_deleted_searchable_chunks == 0
