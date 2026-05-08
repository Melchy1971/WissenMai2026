from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import session as db_session_module
from app.main import app
from app.services.auth import hash_password, hash_token
from tests.postgres_truth.support import (
    TRUTH_OTHER_SESSION_TOKEN,
    TRUTH_OTHER_USER_ID,
    TRUTH_OTHER_WORKSPACE_ID,
    TRUTH_SESSION_TOKEN,
    TRUTH_USER_ID,
    TRUTH_WORKSPACE_ID,
)


pytestmark = pytest.mark.postgres_truth

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(items):
    for item in items:
        if "postgres_truth" in str(item.fspath):
            item.add_marker(pytest.mark.postgres_truth)


def _database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL truth tests")
    return database_url


def _sa_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


@pytest.fixture(scope="session")
def postgres_truth_database_url() -> str:
    return _database_url()


@pytest.fixture(scope="session", autouse=True)
def postgres_truth_schema(postgres_truth_database_url: str) -> Iterator[None]:
    settings.database_url = postgres_truth_database_url
    db_session_module._engine = None
    # Migration errors are intentionally not caught: they fail the truth suite.
    command.upgrade(_alembic_config(), "head")
    yield
    db_session_module._engine = None


@pytest.fixture
def postgres_truth_engine(postgres_truth_database_url: str) -> Iterator[Engine]:
    engine = create_engine(_sa_url(postgres_truth_database_url), pool_pre_ping=True)
    original_engine = db_session_module._engine
    db_session_module._engine = engine
    try:
        yield engine
    finally:
        db_session_module._engine = original_engine
        engine.dispose()


@pytest.fixture
def truth_connection(postgres_truth_engine: Engine) -> Iterator[Connection]:
    connection = postgres_truth_engine.connect()
    transaction = connection.begin()
    original_engine = db_session_module._engine
    db_session_module._engine = connection
    try:
        yield connection
    finally:
        db_session_module._engine = original_engine
        transaction.rollback()
        connection.close()


@pytest.fixture
def truth_session(truth_connection: Connection) -> Iterator[Session]:
    with Session(truth_connection) as session:
        yield session


@pytest.fixture(autouse=True)
def truth_cleanup(postgres_truth_database_url: str) -> Iterator[None]:
    _cleanup_truth_rows(postgres_truth_database_url)
    yield
    _cleanup_truth_rows(postgres_truth_database_url)


@pytest.fixture
def truth_seed(postgres_truth_database_url: str) -> dict[str, str]:
    created = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into workspaces (id, name, is_default, created_at)
                values (%s::uuid, %s, false, %s), (%s::uuid, %s, false, %s)
                """,
                (
                    TRUTH_WORKSPACE_ID,
                    "Truth Workspace",
                    created,
                    TRUTH_OTHER_WORKSPACE_ID,
                    "Truth Other Workspace",
                    created,
                ),
            )
            cursor.execute(
                """
                insert into users (id, display_name, login, password_hash, is_active, is_default, created_at)
                values
                    (%s::uuid, %s, %s, %s, true, false, %s),
                    (%s::uuid, %s, %s, %s, true, false, %s)
                """,
                (
                    TRUTH_USER_ID,
                    "Truth User",
                    "truth-user",
                    hash_password("secret-password", salt="truthsalt"),
                    created,
                    TRUTH_OTHER_USER_ID,
                    "Truth Other User",
                    "truth-other-user",
                    hash_password("secret-password", salt="truthsalt2"),
                    created,
                ),
            )
            cursor.execute(
                """
                insert into workspace_memberships (id, workspace_id, user_id, role, created_at, updated_at)
                values
                    (%s, %s::uuid, %s::uuid, 'owner', %s, %s),
                    (%s, %s::uuid, %s::uuid, 'owner', %s, %s)
                """,
                (
                    "truth-membership-1",
                    TRUTH_WORKSPACE_ID,
                    TRUTH_USER_ID,
                    created,
                    created,
                    "truth-membership-2",
                    TRUTH_OTHER_WORKSPACE_ID,
                    TRUTH_OTHER_USER_ID,
                    created,
                    created,
                ),
            )
            cursor.execute(
                """
                insert into auth_sessions
                    (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
                values
                    (%s, %s::uuid, %s, %s, %s, %s, null),
                    (%s, %s::uuid, %s, %s, %s, %s, null)
                """,
                (
                    "truth-session-1",
                    TRUTH_USER_ID,
                    hash_token(TRUTH_SESSION_TOKEN),
                    datetime(2036, 5, 7, 10, 0, tzinfo=UTC),
                    created,
                    created,
                    "truth-session-2",
                    TRUTH_OTHER_USER_ID,
                    hash_token(TRUTH_OTHER_SESSION_TOKEN),
                    datetime(2036, 5, 7, 10, 0, tzinfo=UTC),
                    created,
                    created,
                ),
            )
        connection.commit()
    return {
        "workspace_id": TRUTH_WORKSPACE_ID,
        "other_workspace_id": TRUTH_OTHER_WORKSPACE_ID,
        "user_id": TRUTH_USER_ID,
        "token": TRUTH_SESSION_TOKEN,
        "other_token": TRUTH_OTHER_SESSION_TOKEN,
    }


@pytest.fixture
def truth_client(truth_seed: dict[str, str], truth_connection: Connection) -> TestClient:
    return TestClient(
        app,
        headers={
            "Authorization": f"Bearer {truth_seed['token']}",
            "X-Workspace-Id": truth_seed["workspace_id"],
        },
    )


def _cleanup_truth_rows(database_url: str) -> None:
    with psycopg.connect(_psycopg_url(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from chat_citations where id::text like 'truth-%'")
            cursor.execute("delete from chat_messages where id::text like 'truth-%'")
            cursor.execute("delete from chat_sessions where id::text like 'truth-%'")
            cursor.execute("delete from background_jobs where id like 'truth-%' or workspace_id::text like 'f1000000-%'")
            cursor.execute("delete from document_chunks where id::text like 'f4000000-%'")
            cursor.execute("update documents set current_version_id = null where id::text like 'f3000000-%'")
            cursor.execute("delete from document_versions where id::text like 'f5000000-%'")
            cursor.execute("delete from documents where id::text like 'f3000000-%'")
            cursor.execute("delete from auth_sessions where id like 'truth-%'")
            cursor.execute("delete from workspace_memberships where id like 'truth-%'")
            cursor.execute("delete from users where id::text like 'f2000000-%'")
            cursor.execute("delete from workspaces where id::text like 'f1000000-%'")
        connection.commit()
