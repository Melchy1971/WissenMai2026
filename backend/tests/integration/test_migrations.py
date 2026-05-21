import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def make_alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def test_alembic_configuration_is_loadable() -> None:
    config = make_alembic_config()
    script = ScriptDirectory.from_config(config)

    assert script.dir == str(BACKEND_ROOT / "migrations")
    assert script.get_heads()


def test_alembic_revisions_are_unique() -> None:
    script = ScriptDirectory.from_config(make_alembic_config())
    revisions = [revision.revision for revision in script.walk_revisions()]

    assert len(revisions) == len(set(revisions))


@pytest.fixture
def test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL migration integration test")
    return database_url


@pytest.mark.postgres
def test_migrations_upgrade_downgrade_on_test_database(test_database_url, monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", test_database_url)
    config = make_alembic_config()

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    try:
        with psycopg.connect(psycopg_url(test_database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select id, is_default from workspaces where id = %s", (DEFAULT_WORKSPACE_ID,))
                workspace_row = cursor.fetchone()
                assert workspace_row is not None
                assert str(workspace_row[0]) == DEFAULT_WORKSPACE_ID
                assert workspace_row[1] is True

                cursor.execute("select id, is_default from users where id = %s", (DEFAULT_USER_ID,))
                user_row = cursor.fetchone()
                assert user_row is not None
                assert str(user_row[0]) == DEFAULT_USER_ID
                assert user_row[1] is True

                cursor.execute(
                    """
                    insert into tags (id, workspace_id, name, normalized_name)
                    values (%s, %s, %s, %s)
                    """,
                    (
                        "00000000-0000-0000-0000-000000000101",
                        DEFAULT_WORKSPACE_ID,
                        "Alpha",
                        "alpha",
                    ),
                )

        with pytest.raises(psycopg.errors.UniqueViolation):
            with psycopg.connect(psycopg_url(test_database_url)) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        insert into tags (id, workspace_id, name, normalized_name)
                        values (%s, %s, %s, %s)
                        """,
                        (
                            "00000000-0000-0000-0000-000000000102",
                            DEFAULT_WORKSPACE_ID,
                            "Alpha Duplicate",
                            "alpha",
                        ),
                    )
    finally:
        command.downgrade(config, "base")

    with psycopg.connect(psycopg_url(test_database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select to_regclass('public.documents')")
            assert cursor.fetchone() == (None,)


@pytest.mark.postgres
def test_chunk_search_vector_migration_creates_generated_column_and_gin_index(test_database_url, monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", test_database_url)
    config = make_alembic_config()

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    try:
        with psycopg.connect(psycopg_url(test_database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select data_type, generation_expression
                    from information_schema.columns
                    where table_schema = 'public'
                      and table_name = 'document_chunks'
                      and column_name = 'search_vector'
                    """
                )
                column_row = cursor.fetchone()
                assert column_row is not None
                assert column_row[0] == "tsvector"
                # Robustere Prüfung auf Kernbestandteile, tolerant gegenüber Whitespace und expliziten Typen
                expr = column_row[1].replace(" ", "").replace("\n", "")
                assert "to_tsvector('simple'::regconfig,CASEWHENis_searchableTHENCOALESCE(content,''::text)ELSE''::textEND)" in expr

                cursor.execute(
                    """
                    select data_type, column_default, is_nullable
                    from information_schema.columns
                    where table_schema = 'public'
                      and table_name = 'document_chunks'
                      and column_name = 'is_searchable'
                    """
                )
                searchable_row = cursor.fetchone()
                assert searchable_row is not None
                assert searchable_row[0] == "boolean"
                assert searchable_row[2] == "NO"

                cursor.execute(
                    """
                    select pg_get_indexdef(indexrelid)
                    from pg_index
                    where indrelid = 'document_chunks'::regclass
                      and indexrelid = 'ix_document_chunks_search_vector'::regclass
                    """
                )
                index_row = cursor.fetchone()
                assert index_row is not None
                assert "USING gin (search_vector)" in index_row[0]
    finally:
        command.downgrade(config, "base")
