"""exclude non-active chunks from full text search index

Revision ID: 20260506_0012
Revises: 20260504_0011
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260506_0012"
down_revision: str | None = "20260505_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEARCH_VECTOR_INDEX = "ix_document_chunks_search_vector"
SEARCH_VECTOR_COLUMN = "search_vector"
SEARCHABLE_COLUMN = "is_searchable"


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        _upgrade_postgresql()
        return

    if dialect_name == "sqlite":
        _upgrade_sqlite()
        return

    raise RuntimeError(f"Unsupported database dialect for chunk searchability migration: {dialect_name}")


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        _downgrade_postgresql()
        return

    if dialect_name == "sqlite":
        _downgrade_sqlite()
        return

    raise RuntimeError(f"Unsupported database dialect for chunk searchability migration: {dialect_name}")


def _upgrade_postgresql() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(SEARCHABLE_COLUMN, sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.execute(
        "UPDATE document_chunks AS chunk "
        "SET is_searchable = EXISTS ("
        "SELECT 1 FROM documents AS document "
        "WHERE document.id = chunk.document_id AND document.lifecycle_status = 'active'"
        ")"
    )
    op.execute(f"DROP INDEX IF EXISTS {SEARCH_VECTOR_INDEX}")
    op.execute(
        "ALTER TABLE document_chunks "
        f"DROP COLUMN IF EXISTS {SEARCH_VECTOR_COLUMN}"
    )
    op.execute(
        "ALTER TABLE document_chunks "
        f"ADD COLUMN {SEARCH_VECTOR_COLUMN} tsvector "
        "GENERATED ALWAYS AS ("
        "to_tsvector('simple', CASE WHEN is_searchable THEN coalesce(content, '') ELSE '' END)"
        ") STORED"
    )
    op.execute(
        f"CREATE INDEX {SEARCH_VECTOR_INDEX} "
        "ON document_chunks USING gin (search_vector)"
    )


def _downgrade_postgresql() -> None:
    op.execute(f"DROP INDEX IF EXISTS {SEARCH_VECTOR_INDEX}")
    op.execute(
        "ALTER TABLE document_chunks "
        f"DROP COLUMN IF EXISTS {SEARCH_VECTOR_COLUMN}"
    )
    op.execute(
        "ALTER TABLE document_chunks "
        f"DROP COLUMN IF EXISTS {SEARCHABLE_COLUMN}"
    )
    op.execute(
        "ALTER TABLE document_chunks "
        f"ADD COLUMN {SEARCH_VECTOR_COLUMN} tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED"
    )
    op.execute(
        f"CREATE INDEX {SEARCH_VECTOR_INDEX} "
        "ON document_chunks USING gin (search_vector)"
    )


def _upgrade_sqlite() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(SEARCHABLE_COLUMN, sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(
        "UPDATE document_chunks "
        "SET is_searchable = 1, "
        "search_vector = CASE WHEN is_searchable THEN content ELSE '' END"
    )


def _downgrade_sqlite() -> None:
    op.drop_column("document_chunks", SEARCHABLE_COLUMN)
