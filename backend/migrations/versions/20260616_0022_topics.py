"""topics, topic_documents, topic_tags

Revision ID: 20260616_0022
Revises: 20260612_0021
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260616_0022"
down_revision: str | None = "20260612_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("slug", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status in ('draft', 'review', 'approved', 'archived')",
            name="ck_topics_status_allowed",
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_topics_title_not_blank"),
        sa.CheckConstraint("length(trim(slug)) > 0", name="ck_topics_slug_not_blank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_topics_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_topics_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_topics_approved_by_users",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_topics_workspace_slug"),
    )
    op.create_index("ix_topics_workspace_id", "topics", ["workspace_id"])
    op.create_index("ix_topics_status", "topics", ["status"])
    op.create_index("ix_topics_created_by", "topics", ["created_by"])
    op.create_index("ix_topics_created_at", "topics", ["created_at"])
    op.create_index("ix_topics_workspace_status", "topics", ["workspace_id", "status"])

    op.create_table(
        "topic_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("topic_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False, server_default="related"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "relation_type in ('primary', 'related', 'reference')",
            name="ck_topic_documents_relation_type_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name="fk_topic_documents_topic_id_topics",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_topic_documents_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("topic_id", "document_id", name="uq_topic_documents_topic_document"),
    )
    op.create_index("ix_topic_documents_topic_id", "topic_documents", ["topic_id"])
    op.create_index("ix_topic_documents_document_id", "topic_documents", ["document_id"])
    op.create_index("ix_topic_documents_relation_type", "topic_documents", ["relation_type"])

    op.create_table(
        "topic_tags",
        sa.Column("topic_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("tag_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name="fk_topic_tags_topic_id_topics",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name="fk_topic_tags_tag_id_tags",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("topic_id", "tag_id", name="uq_topic_tags_topic_tag"),
    )
    op.create_index("ix_topic_tags_topic_id", "topic_tags", ["topic_id"])
    op.create_index("ix_topic_tags_tag_id", "topic_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_topic_tags_tag_id", "topic_tags")
    op.drop_index("ix_topic_tags_topic_id", "topic_tags")
    op.drop_table("topic_tags")

    op.drop_index("ix_topic_documents_relation_type", "topic_documents")
    op.drop_index("ix_topic_documents_document_id", "topic_documents")
    op.drop_index("ix_topic_documents_topic_id", "topic_documents")
    op.drop_table("topic_documents")

    op.drop_index("ix_topics_workspace_status", "topics")
    op.drop_index("ix_topics_created_at", "topics")
    op.drop_index("ix_topics_created_by", "topics")
    op.drop_index("ix_topics_status", "topics")
    op.drop_index("ix_topics_workspace_id", "topics")
    op.drop_table("topics")
