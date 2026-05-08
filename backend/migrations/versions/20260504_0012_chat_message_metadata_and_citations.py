"""align chat persistence with rag citations

Revision ID: 20260504_0012
Revises: 20260504_0011
Create Date: 2026-05-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260504_0012"
down_revision: str | None = "20260504_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_type():
    return sa.String()


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    chat_message_columns = {column["name"] for column in inspector.get_columns("chat_messages")}

    if "source_metadata" in chat_message_columns and "metadata" not in chat_message_columns:
        op.alter_column("chat_messages", "source_metadata", new_column_name="metadata")

    existing_indexes = {index["name"] for index in inspector.get_indexes("chat_messages")}
    if "ix_chat_messages_source_metadata" in existing_indexes:
        op.drop_index("ix_chat_messages_source_metadata", table_name="chat_messages")
    if "ix_chat_messages_metadata" not in existing_indexes:
        if bind.dialect.name == "postgresql":
            op.create_index("ix_chat_messages_metadata", "chat_messages", ["metadata"], postgresql_using="gin")
        else:
            op.create_index("ix_chat_messages_metadata", "chat_messages", ["metadata"])

    existing_tables = set(inspector.get_table_names())
    if "chat_citations" not in existing_tables:
        op.create_table(
            "chat_citations",
            sa.Column("id", _id_type(), primary_key=True),
            sa.Column("message_id", _id_type(), nullable=False),
            sa.Column("chunk_id", _id_type(), nullable=False),
            sa.Column("document_id", _id_type(), nullable=False),
            sa.Column("source_anchor", _json_type(), nullable=False),
            sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], name="fk_chat_citations_message_id", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], name="fk_chat_citations_chunk_id", ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_chat_citations_document_id", ondelete="RESTRICT"),
        )
        op.create_index("ix_chat_citations_message_id", "chat_citations", ["message_id"])
        op.create_index("ix_chat_citations_chunk_id", "chat_citations", ["chunk_id"])
        op.create_index("ix_chat_citations_document_id", "chat_citations", ["document_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "chat_citations" in existing_tables:
        op.drop_index("ix_chat_citations_document_id", table_name="chat_citations")
        op.drop_index("ix_chat_citations_chunk_id", table_name="chat_citations")
        op.drop_index("ix_chat_citations_message_id", table_name="chat_citations")
        op.drop_table("chat_citations")

    existing_indexes = {index["name"] for index in inspector.get_indexes("chat_messages")}
    if "ix_chat_messages_metadata" in existing_indexes:
        op.drop_index("ix_chat_messages_metadata", table_name="chat_messages")

    chat_message_columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    if "metadata" in chat_message_columns and "source_metadata" not in chat_message_columns:
        op.alter_column("chat_messages", "metadata", new_column_name="source_metadata")
        if bind.dialect.name == "postgresql":
            op.create_index("ix_chat_messages_source_metadata", "chat_messages", ["source_metadata"], postgresql_using="gin")
        else:
            op.create_index("ix_chat_messages_source_metadata", "chat_messages", ["source_metadata"])