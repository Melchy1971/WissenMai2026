from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
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
    TruthIds,
    make_truth_ids,
)


pytestmark = pytest.mark.postgres_truth

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class PostgresTruthPreflightError(RuntimeError):
    pass


REQUIRED_TABLES = {
    "workspaces",
    "users",
    "workspace_memberships",
    "auth_sessions",
    "documents",
    "document_versions",
    "document_chunks",
    "chat_sessions",
    "chat_messages",
    "chat_citations",
    "background_jobs",
}


REQUIRED_CONSTRAINTS = (
    ("documents", "uq_documents_workspace_content_hash", "u", "content_hash unique"),
    ("documents", "ck_documents_lifecycle_status_allowed", "c", "lifecycle_status check"),
    ("chat_citations", "ck_chat_citations_source_status_allowed", "c", "source_status check"),
    ("background_jobs", "ck_background_jobs_status_allowed", "c", "queue status check"),
)

_PREFLIGHTED_DATABASE_URL: str | None = None


def pytest_collection_modifyitems(items):
    for item in items:
        if "postgres_truth" in str(item.fspath):
            item.add_marker(pytest.mark.postgres_truth)


def pytest_collection_finish(session: pytest.Session) -> None:
    if any("postgres_truth" in str(item.fspath) for item in session.items):
        try:
            _ensure_postgres_truth_preflight(_database_url())
        except PostgresTruthPreflightError as exc:
            pytest.exit(str(exc), returncode=1)


def _database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        raise PostgresTruthPreflightError(
            "postgres_truth preflight failed: TEST_DATABASE_URL is not set. "
            "Configure a reachable PostgreSQL test database; skips are not allowed for postgres_truth."
        )
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


def _alembic_heads() -> set[str]:
    return set(ScriptDirectory.from_config(_alembic_config()).get_heads())


def _ensure_postgres_truth_preflight(database_url: str) -> None:
    global _PREFLIGHTED_DATABASE_URL

    if _PREFLIGHTED_DATABASE_URL == database_url:
        return
    _preflight_postgres_truth_state(database_url)
    _PREFLIGHTED_DATABASE_URL = database_url


def _preflight_postgres_truth_state(database_url: str) -> None:
    errors: list[str] = []
    raw_url = _psycopg_url(database_url)

    try:
        with psycopg.connect(raw_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select 1")
                cursor.fetchone()
                _preflight_alembic_state(cursor, errors)
                _preflight_required_tables(cursor, errors)
                _preflight_required_constraints(cursor, errors)
    except PostgresTruthPreflightError:
        raise
    except Exception as exc:
        raise PostgresTruthPreflightError(
            "postgres_truth preflight failed: database is not reachable via TEST_DATABASE_URL "
            f"({exc.__class__.__name__}: {exc})."
        ) from exc

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise PostgresTruthPreflightError(f"postgres_truth preflight failed:\n{details}")


def _preflight_alembic_state(cursor, errors: list[str]) -> None:
    cursor.execute("select to_regclass('public.alembic_version')")
    if cursor.fetchone()[0] is None:
        errors.append("Alembic state missing: table public.alembic_version does not exist.")
        return

    cursor.execute("select version_num from alembic_version")
    current = {row[0] for row in cursor.fetchall()}
    heads = _alembic_heads()
    if current != heads:
        errors.append(
            "Alembic state mismatch: "
            f"current={sorted(current) or ['<empty>']} head={sorted(heads)}. "
            "Run alembic upgrade head before postgres_truth."
        )


def _preflight_required_tables(cursor, errors: list[str]) -> None:
    cursor.execute(
        """
        select table_name
        from information_schema.tables
        where table_schema = 'public'
          and table_type = 'BASE TABLE'
        """
    )
    existing = {row[0] for row in cursor.fetchall()}
    missing = sorted(REQUIRED_TABLES - existing)
    if missing:
        errors.append(f"Required tables missing: {', '.join(missing)}.")


def _preflight_required_constraints(cursor, errors: list[str]) -> None:
    cursor.execute(
        """
        select cls.relname, con.conname, con.contype
        from pg_constraint con
        join pg_class cls on cls.oid = con.conrelid
        join pg_namespace ns on ns.oid = cls.relnamespace
        where ns.nspname = 'public'
        """
    )
    existing = {(table, name): constraint_type for table, name, constraint_type in cursor.fetchall()}
    missing: list[str] = []
    wrong_type: list[str] = []
    for table, name, expected_type, label in REQUIRED_CONSTRAINTS:
        actual_type = existing.get((table, name))
        if actual_type is None:
            missing.append(f"{label} ({table}.{name})")
        elif actual_type != expected_type:
            wrong_type.append(f"{label} ({table}.{name}) expected type {expected_type}, got {actual_type}")
    if missing:
        errors.append(f"Required constraints missing: {', '.join(missing)}.")
    if wrong_type:
        errors.append(f"Required constraints have wrong type: {', '.join(wrong_type)}.")


@pytest.fixture(scope="session")
def postgres_truth_database_url() -> str:
    return _database_url()


@pytest.fixture(scope="session", autouse=True)
def postgres_truth_schema(postgres_truth_database_url: str) -> Iterator[None]:
    _ensure_postgres_truth_preflight(postgres_truth_database_url)
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
        if transaction.is_active:
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
def truth_ids(request: pytest.FixtureRequest) -> TruthIds:
    return make_truth_ids(request.node.nodeid)


@pytest.fixture
def truth_seed(postgres_truth_database_url: str, truth_ids: TruthIds) -> dict[str, str]:
    created = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into workspaces (id, name, is_default, created_at)
                values (%s::uuid, %s, false, %s), (%s::uuid, %s, false, %s)
                """,
                (
                    truth_ids.workspace_id,
                    f"Truth Workspace {truth_ids.slug}",
                    created,
                    truth_ids.other_workspace_id,
                    f"Truth Other Workspace {truth_ids.slug}",
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
                    truth_ids.user_id,
                    f"Truth User {truth_ids.slug}",
                    f"truth-user-{truth_ids.slug}",
                    hash_password("secret-password", salt=f"truthsalt-{truth_ids.namespace}"),
                    created,
                    truth_ids.other_user_id,
                    f"Truth Other User {truth_ids.slug}",
                    f"truth-other-user-{truth_ids.slug}",
                    hash_password("secret-password", salt=f"truthsalt2-{truth_ids.namespace}"),
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
                    truth_ids.membership_id,
                    truth_ids.workspace_id,
                    truth_ids.user_id,
                    created,
                    created,
                    truth_ids.other_membership_id,
                    truth_ids.other_workspace_id,
                    truth_ids.other_user_id,
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
                    truth_ids.session_id,
                    truth_ids.user_id,
                    hash_token(truth_ids.session_token),
                    datetime(2036, 5, 7, 10, 0, tzinfo=UTC),
                    created,
                    created,
                    truth_ids.other_session_id,
                    truth_ids.other_user_id,
                    hash_token(truth_ids.other_session_token),
                    datetime(2036, 5, 7, 10, 0, tzinfo=UTC),
                    created,
                    created,
                ),
            )
        connection.commit()
    return {
        "workspace_id": truth_ids.workspace_id,
        "other_workspace_id": truth_ids.other_workspace_id,
        "user_id": truth_ids.user_id,
        "other_user_id": truth_ids.other_user_id,
        "token": truth_ids.session_token,
        "other_token": truth_ids.other_session_token,
        "ids": truth_ids,
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
            cursor.execute(
                """
                delete from document_chunks
                where id::text like 'f4000000-%'
                   or document_id in (
                       select id from documents where workspace_id::text like 'f1000000-%'
                   )
                   or document_version_id in (
                       select v.id
                       from document_versions v
                       join documents d on d.id = v.document_id
                       where d.workspace_id::text like 'f1000000-%'
                   )
                """
            )
            cursor.execute("update documents set current_version_id = null where workspace_id::text like 'f1000000-%'")
            cursor.execute(
                """
                delete from document_versions
                where id::text like 'f5000000-%'
                   or document_id in (
                       select id from documents where workspace_id::text like 'f1000000-%'
                   )
                """
            )
            cursor.execute("delete from documents where id::text like 'f3000000-%' or workspace_id::text like 'f1000000-%'")
            cursor.execute("delete from auth_sessions where id like 'truth-%'")
            cursor.execute("delete from workspace_memberships where id like 'truth-%'")
            cursor.execute("delete from users where id::text like 'f2000000-%'")
            cursor.execute("delete from workspaces where id::text like 'f1000000-%'")
        connection.commit()
