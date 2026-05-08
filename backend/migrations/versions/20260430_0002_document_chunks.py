"""document chunks

Revision ID: 20260430_0002
Revises: 20260430_0001
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260430_0002"
down_revision: str | None = "20260430_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_document_versions_document_id_id",
        "document_versions",
        ["document_id", "id"],
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("document_version_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("anchor", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index_non_negative"),
        sa.CheckConstraint("length(trim(anchor)) > 0", name="ck_document_chunks_anchor_not_blank"),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_document_chunks_content_not_blank"),
        sa.CheckConstraint("length(trim(content_hash)) > 0", name="ck_document_chunks_content_hash_not_blank"),
        sa.CheckConstraint("token_estimate IS NULL OR token_estimate >= 0", name="ck_document_chunks_token_estimate_non_negative"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_document_chunks_document_version_id_document_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "document_version_id"],
            ["document_versions.document_id", "document_versions.id"],
            name="fk_document_chunks_document_version_pair",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("document_version_id", "chunk_index", name="uq_document_chunks_version_chunk_index"),
        sa.UniqueConstraint("document_version_id", "anchor", name="uq_document_chunks_version_anchor"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_document_version_id", "document_chunks", ["document_version_id"])
    op.create_index("ix_document_chunks_content_hash", "document_chunks", ["content_hash"])
    op.create_index("ix_document_chunks_anchor", "document_chunks", ["anchor"])
    op.create_index(
        "ix_document_chunks_metadata",
        "document_chunks",
        ["metadata"],
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_content_fts "
        "ON document_chunks USING gin (to_tsvector('simple', content))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_document_chunks_content_fts")
    op.drop_index("ix_document_chunks_metadata", table_name="document_chunks", postgresql_using="gin")
    op.drop_index("ix_document_chunks_anchor", table_name="document_chunks")
    op.drop_index("ix_document_chunks_content_hash", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_constraint(
        "uq_document_versions_document_id_id",
        "document_versions",
        type_="unique",
    )
