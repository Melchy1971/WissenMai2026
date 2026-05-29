import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Lock

import psycopg
import pytest
from alembic import command
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.auth import hash_password, hash_token
from app.services.documents.import_persistence_service import DocumentImportPersistenceService
from tests.integration.test_migrations import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, make_alembic_config, psycopg_url


SESSION_TOKEN = "integration-session-token"


def require_test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL duplicate race test")
    return database_url


def seed_auth_context(database_url: str) -> None:
    created = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    with psycopg.connect(psycopg_url(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update users
                set login = %s,
                    password_hash = %s,
                    is_active = true
                where id = %s
                """,
                ("default-user", hash_password("secret-password", salt="integrationsalt"), DEFAULT_USER_ID),
            )
            cursor.execute("delete from auth_sessions where user_id = %s", (DEFAULT_USER_ID,))
            cursor.execute("delete from workspace_memberships where user_id = %s", (DEFAULT_USER_ID,))
            cursor.execute(
                """
                insert into workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at)
                values (%s, %s, %s, %s, %s, %s)
                """,
                ("membership-integration-1", DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, "owner", created, created),
            )
            cursor.execute(
                """
                insert into auth_sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "integration-session-1",
                    DEFAULT_USER_ID,
                    hash_token(SESSION_TOKEN),
                    datetime(2036, 5, 2, 10, 0, tzinfo=UTC),
                    created,
                    created,
                    None,
                ),
            )
        connection.commit()


def make_client() -> TestClient:
    return TestClient(
        app,
        headers={
            "Authorization": f"Bearer {SESSION_TOKEN}",
            "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
        },
    )


@pytest.mark.postgres
@pytest.mark.m4b_upload_queue_truth
def test_parallel_duplicate_imports_create_single_document(monkeypatch) -> None:
    test_database_url = require_test_database_url()
    monkeypatch.setattr(settings, "database_url", test_database_url)
    config = make_alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    original_fetch_existing = DocumentImportPersistenceService._fetch_existing
    barrier = Barrier(2)
    lock = Lock()
    empty_fetch_count = 0

    def wait_after_initial_empty_fetch(self, connection, *, workspace_id, content_hash):
        nonlocal empty_fetch_count
        existing = original_fetch_existing(
            self,
            connection,
            workspace_id=workspace_id,
            content_hash=content_hash,
        )
        if existing is None:
            with lock:
                empty_fetch_count += 1
                should_wait = empty_fetch_count <= 2
            if should_wait:
                barrier.wait(timeout=10)
        return existing

    monkeypatch.setattr(
        DocumentImportPersistenceService,
        "_fetch_existing",
        wait_after_initial_empty_fetch,
    )

    try:
        seed_auth_context(test_database_url)

        def post_document() -> dict:
            client = make_client()
            response = client.post(
                "/documents/import",
                files={"file": ("race.txt", b"# Race\n\nSame content\n", "text/plain")},
            )
            assert response.status_code == 202
            job_id = response.json()["id"]

            job_response = client.get(f"/documents/import-jobs/{job_id}")
            assert job_response.status_code == 200
            payload = job_response.json()
            assert payload["status"] == "completed"
            return payload["result"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            payloads = list(executor.map(lambda _: post_document(), range(2)))

        assert {payload["document_id"] for payload in payloads}
        assert len({payload["document_id"] for payload in payloads}) == 1
        assert sorted(payload["import_status"] for payload in payloads) == ["chunked", "duplicate"]
        assert sum(1 for payload in payloads if payload["duplicate_of_document_id"] is None) == 1
        assert sum(1 for payload in payloads if payload["duplicate_of_document_id"] == payload["document_id"]) == 1

        with psycopg.connect(psycopg_url(test_database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select count(*) from documents")
                assert cursor.fetchone() == (1,)

                cursor.execute("select count(*) from document_versions")
                assert cursor.fetchone() == (1,)

                cursor.execute("select count(*) from document_chunks")
                assert cursor.fetchone() == (1,)
    finally:
        command.downgrade(config, "base")
