"""categories and additive tags

Revision ID: 20260430_0003
Revises: 20260430_0002
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260430_0003"
down_revision: str | None = "20260430_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_categories_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_categories_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("workspace_id", "name", name="uq_categories_workspace_name"),
    )
    op.create_index("ix_categories_workspace_id", "categories", ["workspace_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_tags_name_not_blank"),
        sa.CheckConstraint("length(trim(normalized_name)) > 0", name="ck_tags_normalized_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_tags_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("workspace_id", "normalized_name", name="uq_tags_workspace_normalized_name"),
    )
    op.create_index("ix_tags_workspace_id", "tags", ["workspace_id"])
    op.create_index("ix_tags_normalized_name", "tags", ["normalized_name"])

    op.create_table(
        "document_tags",
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("source in ('manual', 'ki', 'import')", name="ck_document_tags_source_allowed"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_document_tags_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_tags_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name="fk_document_tags_tag_id_tags",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_document_tags_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("document_id", "tag_id", "source", name="pk_document_tags"),
    )
    op.create_index("ix_document_tags_document_id", "document_tags", ["document_id"])
    op.create_index("ix_document_tags_tag_id", "document_tags", ["tag_id"])
    op.create_index("ix_document_tags_source", "document_tags", ["source"])
    op.create_index("ix_document_tags_created_by_user_id", "document_tags", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_document_tags_created_by_user_id", table_name="document_tags")
    op.drop_index("ix_document_tags_source", table_name="document_tags")
    op.drop_index("ix_document_tags_tag_id", table_name="document_tags")
    op.drop_index("ix_document_tags_document_id", table_name="document_tags")
    op.drop_table("document_tags")

    op.drop_index("ix_tags_normalized_name", table_name="tags")
    op.drop_index("ix_tags_workspace_id", table_name="tags")
    op.drop_table("tags")

    op.drop_index("ix_categories_workspace_id", table_name="categories")
    op.drop_table("categories")
