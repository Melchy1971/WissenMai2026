"""Schema-Truth fuer die Migrationen 0028/0029 und den ORM-Migrations-Abgleich.

Zwei Teile:

1. ``test_orm_matches_migration_chain`` laeuft ohne Datenbank. Er spielt die
   Alembic-Kette gegen ein reines Schemamodell durch und vergleicht sie mit den
   ORM-Metadaten. Damit faellt jede neue Drift zwischen Modell und Migration im
   normalen Testlauf auf, nicht erst auf der echten DB.
2. Die ``@pytest.mark.postgres``-Tests fahren die echte Kette hoch und pruefen
   die Invarianten dort, wo sie gelten: auf PostgreSQL. Ohne
   ``TEST_DATABASE_URL`` werden sie uebersprungen.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

# Schema-Integritaet ist Backend-Stabilisierungs-Truth: bricht sie, ist jede
# Aussage ueber Persistenz wertlos.
pytestmark = pytest.mark.m4_truth

BACKEND_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = BACKEND_ROOT / "migrations" / "versions"

# Tabellen, die Migration 0028 entfernt.
DROPPED_TABLES = (
    "analysis_group_documents",
    "analysis_groups",
    "analysis_result_sources_legacy",
    "analysis_results_legacy",
)

# Audit-Log der Datenreparatur aus 20260504_0010. Wird von der Anwendung nie
# gelesen; ein ORM-Modell waere reines Rauschen. Bewusst ohne Modell und bewusst
# nicht gedroppt (siehe Migration 20260726_0028).
TABLES_WITHOUT_ORM_MODEL = {"migration_document_repairs"}

# Bewusste, dokumentierte Abweichungen zwischen ORM und Migrationskette.
KNOWN_ORM_GAPS = {
    # Nur PostgreSQL: nutzt jsonb-Operatoren, in SQLite nicht darstellbar.
    ("document_chunks", "check", "ck_document_chunks_source_anchor_normalized"),
    # Per Raw-SQL angelegt (Migration 20260504_0011), fuer Alembic unsichtbar.
    ("document_chunks", "column", "search_vector"),
}


def make_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture
def test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL schema truth test")
    return database_url


# ---------------------------------------------------------------------------
# 1. ORM vs. Migrationskette (ohne Datenbank)
# ---------------------------------------------------------------------------


def _load_migration_modules() -> dict[str, object]:
    mods: dict[str, object] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"_schema_truth_{path.stem}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        mods[module.revision] = module
    return mods


def _linear_order(mods: dict[str, object]) -> list[str]:
    children: dict[str, list[str]] = {}
    root: str | None = None
    for rev, module in mods.items():
        down = getattr(module, "down_revision", None)
        if down is None:
            assert root is None, "Mehr als eine Wurzel-Revision"
            root = rev
        else:
            children.setdefault(down, []).append(rev)
    assert root is not None, "Keine Wurzel-Revision gefunden"

    order: list[str] = []
    current: str | None = root
    while current is not None:
        order.append(current)
        following = children.get(current, [])
        assert len(following) <= 1, f"Branch in der Migrationskette bei {current}: {following}"
        current = following[0] if following else None

    unreachable = set(mods) - set(order)
    assert not unreachable, f"Nicht erreichbare Revisionen: {sorted(unreachable)}"
    return order


def _replay_chain() -> dict[str, dict]:
    """Spielt die Kette gegen ein Schemamodell durch und liefert das Zielschema."""
    from tests.integration._schema_replay import replay

    mods = _load_migration_modules()
    return replay(mods, _linear_order(mods))


def test_migration_chain_is_linear_and_complete() -> None:
    mods = _load_migration_modules()
    order = _linear_order(mods)
    assert order[-1] == "20260726_0029", f"Unerwarteter Head: {order[-1]}"


def test_orm_matches_migration_chain() -> None:
    schema = _replay_chain()

    import app.models.analysis  # noqa: F401
    import app.models.analytics  # noqa: F401
    import app.models.data_quality  # noqa: F401
    import app.models.drift  # noqa: F401
    import app.models.export  # noqa: F401
    import app.models.topics  # noqa: F401
    from app.models.documents import Base

    problems: list[str] = []

    orm_tables = set(Base.metadata.tables)
    missing_models = set(schema) - orm_tables - TABLES_WITHOUT_ORM_MODEL
    if missing_models:
        problems.append(f"Tabellen ohne ORM-Modell: {sorted(missing_models)}")
    phantom_tables = orm_tables - set(schema)
    if phantom_tables:
        problems.append(f"ORM-Modelle ohne Migration: {sorted(phantom_tables)}")

    for name in sorted(orm_tables & set(schema)):
        table = Base.metadata.tables[name]
        mig = schema[name]

        orm_columns = set(table.columns.keys())
        for column in sorted(set(mig["columns"]) - orm_columns):
            problems.append(f"{name}: Spalte {column} fehlt im ORM")
        for column in sorted(orm_columns - set(mig["columns"])):
            if (name, "column", column) in KNOWN_ORM_GAPS:
                continue
            problems.append(f"{name}: Spalte {column} fehlt in der Migration")

        orm_checks = {
            c.name for c in table.constraints if isinstance(c, sa.CheckConstraint) and c.name
        }
        for check in sorted(set(mig["checks"]) - orm_checks):
            if (name, "check", check) in KNOWN_ORM_GAPS:
                continue
            problems.append(f"{name}: Check {check} fehlt im ORM")

        orm_uniques = {
            c.name for c in table.constraints if isinstance(c, sa.UniqueConstraint) and c.name
        }
        orm_unique_indexes = {ix.name for ix in table.indexes if ix.unique}
        for unique in sorted(set(mig["uniques"])):
            if unique in (None, "null"):
                continue
            if unique not in orm_uniques and unique not in orm_unique_indexes:
                problems.append(f"{name}: Unique {unique} fehlt im ORM")

        orm_indexes = {ix.name for ix in table.indexes}
        for index in sorted(set(mig["indexes"]) - orm_indexes):
            problems.append(f"{name}: Index {index} fehlt im ORM")

    assert not problems, "ORM weicht von der Migrationskette ab:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# 2. Invarianten auf echter PostgreSQL
# ---------------------------------------------------------------------------


@pytest.mark.postgres
def test_dead_tables_are_gone_after_upgrade(test_database_url) -> None:
    import psycopg

    command.upgrade(make_alembic_config(test_database_url), "head")
    with psycopg.connect(psycopg_url(test_database_url)) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = ANY(%s)",
            (list(DROPPED_TABLES),),
        )
        remaining = [row[0] for row in cursor.fetchall()]
    assert remaining == [], f"Migration 0028 hat diese Tabellen nicht entfernt: {remaining}"


@pytest.mark.postgres
def test_migration_document_repairs_is_preserved(test_database_url) -> None:
    """Das Audit-Log der Datenreparatur darf NICHT mitgeloescht werden."""
    import psycopg

    command.upgrade(make_alembic_config(test_database_url), "head")
    with psycopg.connect(psycopg_url(test_database_url)) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT to_regclass('public.migration_document_repairs')")
        assert cursor.fetchone()[0] is not None


@pytest.mark.postgres
def test_background_jobs_accepts_cancelled(test_database_url) -> None:
    import psycopg

    command.upgrade(make_alembic_config(test_database_url), "head")
    with psycopg.connect(psycopg_url(test_database_url)) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO background_jobs "
            "(id, job_type, status, workspace_id, payload, progress_current, progress_total, "
            " attempt_count, created_at) "
            "VALUES ('truth-cancelled', 'document_import', 'cancelled', "
            "'00000000-0000-0000-0000-000000000001', '{}', 0, 1, 0, now())"
        )
        cursor.execute("SELECT status FROM background_jobs WHERE id = 'truth-cancelled'")
        assert cursor.fetchone()[0] == "cancelled"
        connection.rollback()


@pytest.mark.postgres
@pytest.mark.parametrize(
    ("statement", "constraint"),
    [
        (
            "INSERT INTO workspaces (id, name, is_default, kind, created_at) "
            "VALUES ('truth-ws-1', 'X', false, 'team', now())",
            "ck_workspaces_kind_allowed",
        ),
        (
            "INSERT INTO workspaces (id, name, is_default, kind, created_at) "
            "VALUES ('truth-ws-2', 'X', false, 'shared', now())",
            "ck_workspaces_kind_default_consistency",
        ),
        (
            "INSERT INTO workspaces (id, name, is_default, kind, created_at) "
            "VALUES ('truth-ws-3', '   ', false, 'private', now())",
            "ck_workspaces_name_not_blank",
        ),
        (
            "INSERT INTO documents "
            "(id, workspace_id, owner_user_id, title, source_type, content_hash, "
            " import_status, lifecycle_status, created_at, updated_at) "
            "VALUES ('truth-doc-1', '00000000-0000-0000-0000-000000000001', "
            "'00000000-0000-0000-0000-000000000001', 'T', 'upload', 'h1', "
            "'chunked', 'active', now(), now())",
            "ck_documents_readable_status_requires_current_version",
        ),
        (
            "INSERT INTO documents "
            "(id, workspace_id, owner_user_id, title, source_type, content_hash, "
            " import_status, lifecycle_status, created_at, updated_at) "
            "VALUES ('truth-doc-2', '00000000-0000-0000-0000-000000000001', "
            "'00000000-0000-0000-0000-000000000001', 'T', 'upload', 'h2', "
            "'pending', 'pending', now(), now())",
            "ck_documents_lifecycle_status_allowed",
        ),
    ],
)
def test_constraints_reject_invalid_rows(test_database_url, statement, constraint) -> None:
    import psycopg

    command.upgrade(make_alembic_config(test_database_url), "head")
    with psycopg.connect(psycopg_url(test_database_url)) as connection:
        cursor = connection.cursor()
        with pytest.raises(psycopg.errors.CheckViolation) as excinfo:
            cursor.execute(statement)
        assert constraint in str(excinfo.value)
        connection.rollback()


@pytest.mark.postgres
def test_downgrade_and_upgrade_round_trip(test_database_url) -> None:
    """0029 -> 0027 -> head laeuft durch und stellt denselben Head wieder her."""
    import psycopg

    config = make_alembic_config(test_database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "20260724_0027")
    command.upgrade(config, "head")

    with psycopg.connect(psycopg_url(test_database_url)) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone()[0] == "20260726_0029"


if __name__ == "__main__":  # pragma: no cover - manueller Direktaufruf
    sys.exit(pytest.main([__file__, "-v"]))
