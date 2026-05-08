"""persist historical chat citation snapshots

Revision ID: 20260506_0013
Revises: 20260506_0012
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260506_0013"
down_revision: str | None = "20260506_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_type():
    return sa.String()


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.add_column("chat_citations", sa.Column("document_title", sa.String(length=500), nullable=True))
    op.add_column("chat_citations", sa.Column("quote_preview", sa.Text(), nullable=True))
    op.add_column(
        "chat_citations",
        sa.Column("source_status", sa.String(length=32), nullable=False, server_default="active"),
    )

    with op.batch_alter_table("chat_citations") as batch_op:
        batch_op.alter_column("chunk_id", existing_type=_id_type(), nullable=True)

    if dialect_name == "postgresql":
        op.drop_constraint("fk_chat_citations_chunk_id", "chat_citations", type_="foreignkey")
        op.create_foreign_key(
            "fk_chat_citations_chunk_id",
            "chat_citations",
            "document_chunks",
            ["chunk_id"],
            ["id"],
            ondelete="SET NULL",
        )
    else:
        with op.batch_alter_table("chat_citations") as batch_op:
            batch_op.drop_constraint("fk_chat_citations_chunk_id", type_="foreignkey")
            batch_op.create_foreign_key(
                "fk_chat_citations_chunk_id",
                "document_chunks",
                ["chunk_id"],
                ["id"],
                ondelete="SET NULL",
            )

    op.execute(
        "UPDATE chat_citations AS citation "
        "SET document_title = COALESCE(document.title, 'Unknown document'), "
        "quote_preview = COALESCE(SUBSTR("
        "(SELECT content FROM document_chunks WHERE id = citation.chunk_id LIMIT 1)"
        ", 1, 300), 'Historical citation unavailable'), "
        "source_status = COALESCE(document.lifecycle_status, 'unknown') "
        "FROM documents AS document "
        "WHERE citation.document_id = document.id"
    )
    op.execute(
        "UPDATE chat_citations "
        "SET document_title = COALESCE(document_title, 'Unknown document'), "
        "quote_preview = COALESCE(quote_preview, 'Historical citation unavailable')"
    )

    with op.batch_alter_table("chat_citations") as batch_op:
        batch_op.alter_column("document_title", existing_type=sa.String(length=500), nullable=False)
        batch_op.alter_column("quote_preview", existing_type=sa.Text(), nullable=False)
        batch_op.create_check_constraint(
            "ck_chat_citations_source_status_allowed",
            "source_status in ('active', 'archived', 'deleted', 'unknown')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    with op.batch_alter_table("chat_citations") as batch_op:
        batch_op.drop_constraint("ck_chat_citations_source_status_allowed", type_="check")

    if dialect_name == "postgresql":
        op.drop_constraint("fk_chat_citations_chunk_id", "chat_citations", type_="foreignkey")
        op.create_foreign_key(
            "fk_chat_citations_chunk_id",
            "chat_citations",
            "document_chunks",
            ["chunk_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    else:
        with op.batch_alter_table("chat_citations") as batch_op:
            batch_op.drop_constraint("fk_chat_citations_chunk_id", type_="foreignkey")
            batch_op.create_foreign_key(
                "fk_chat_citations_chunk_id",
                "document_chunks",
                ["chunk_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    with op.batch_alter_table("chat_citations") as batch_op:
        batch_op.alter_column("chunk_id", existing_type=_id_type(), nullable=False)

    op.drop_column("chat_citations", "source_status")
    op.drop_column("chat_citations", "quote_preview")
    op.drop_column("chat_citations", "document_title")
