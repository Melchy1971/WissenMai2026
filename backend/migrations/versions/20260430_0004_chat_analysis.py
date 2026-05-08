"""chat and analysis persistence

Revision ID: 20260430_0004
Revises: 20260430_0003
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260430_0004"
down_revision: str | None = "20260430_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CHAT_ROLES = "'system', 'user', 'assistant'"
BASIS_TYPES = "'knowledge_base', 'general', 'mixed', 'unknown'"
ANALYSIS_STATUSES = "'draft', 'running', 'completed', 'failed', 'committed'"
ANALYSIS_RESULT_TYPES = "'merge', 'compare', 'refine'"


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_chat_sessions_title_not_blank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_chat_sessions_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_chat_sessions_owner_user_id_users",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_chat_sessions_workspace_id", "chat_sessions", ["workspace_id"])
    op.create_index("ix_chat_sessions_owner_user_id", "chat_sessions", ["owner_user_id"])
    op.create_index("ix_chat_sessions_updated_at", "chat_sessions", ["updated_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("message_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("basis_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("message_index >= 0", name="ck_chat_messages_message_index_non_negative"),
        sa.CheckConstraint(f"role in ({CHAT_ROLES})", name="ck_chat_messages_role_allowed"),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_chat_messages_content_not_blank"),
        sa.CheckConstraint(f"basis_type in ({BASIS_TYPES})", name="ck_chat_messages_basis_type_allowed"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name="fk_chat_messages_session_id_chat_sessions",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("session_id", "message_index", name="uq_chat_messages_session_message_index"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_role", "chat_messages", ["role"])
    op.create_index("ix_chat_messages_basis_type", "chat_messages", ["basis_type"])
    op.create_index(
        "ix_chat_messages_source_metadata",
        "chat_messages",
        ["source_metadata"],
        postgresql_using="gin",
    )

    op.create_table(
        "analysis_groups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_analysis_groups_title_not_blank"),
        sa.CheckConstraint(f"status in ({ANALYSIS_STATUSES})", name="ck_analysis_groups_status_allowed"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_analysis_groups_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_analysis_groups_owner_user_id_users",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_analysis_groups_workspace_id", "analysis_groups", ["workspace_id"])
    op.create_index("ix_analysis_groups_owner_user_id", "analysis_groups", ["owner_user_id"])
    op.create_index("ix_analysis_groups_status", "analysis_groups", ["status"])
    op.create_index("ix_analysis_groups_updated_at", "analysis_groups", ["updated_at"])

    op.create_table(
        "analysis_group_documents",
        sa.Column("analysis_group_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("document_version_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["analysis_group_id"],
            ["analysis_groups.id"],
            name="fk_ag_docs_group_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_ag_docs_document_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_ag_docs_document_version_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("analysis_group_id", "document_id", name="pk_analysis_group_documents"),
    )
    op.create_index("ix_analysis_group_documents_document_id", "analysis_group_documents", ["document_id"])
    op.create_index(
        "ix_analysis_group_documents_document_version_id",
        "analysis_group_documents",
        ["document_version_id"],
    )

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_group_id", sa.String(), nullable=False),
        sa.Column("result_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("result_markdown", sa.Text(), nullable=True),
        sa.Column("commit_ref", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(f"result_type in ({ANALYSIS_RESULT_TYPES})", name="ck_analysis_results_type_allowed"),
        sa.CheckConstraint(f"status in ({ANALYSIS_STATUSES})", name="ck_analysis_results_status_allowed"),
        sa.CheckConstraint(
            "result_markdown IS NULL OR length(trim(result_markdown)) > 0",
            name="ck_analysis_results_markdown_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_group_id"],
            ["analysis_groups.id"],
            name="fk_analysis_results_group_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_analysis_results_analysis_group_id", "analysis_results", ["analysis_group_id"])
    op.create_index("ix_analysis_results_type", "analysis_results", ["result_type"])
    op.create_index("ix_analysis_results_status", "analysis_results", ["status"])
    op.create_index("ix_analysis_results_commit_ref", "analysis_results", ["commit_ref"])

    op.create_table(
        "analysis_result_sources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_result_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("document_version_id", sa.String(), nullable=True),
        sa.Column("document_chunk_id", sa.String(), nullable=True),
        sa.Column("anchor", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["analysis_result_id"],
            ["analysis_results.id"],
            name="fk_analysis_sources_result_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_analysis_sources_document_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_analysis_sources_version_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_chunk_id"],
            ["document_chunks.id"],
            name="fk_analysis_sources_chunk_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_analysis_result_sources_analysis_result_id", "analysis_result_sources", ["analysis_result_id"])
    op.create_index("ix_analysis_result_sources_document_id", "analysis_result_sources", ["document_id"])
    op.create_index("ix_analysis_result_sources_document_version_id", "analysis_result_sources", ["document_version_id"])
    op.create_index("ix_analysis_result_sources_document_chunk_id", "analysis_result_sources", ["document_chunk_id"])
    op.create_index("ix_analysis_result_sources_anchor", "analysis_result_sources", ["anchor"])


def downgrade() -> None:
    op.drop_index("ix_analysis_result_sources_anchor", table_name="analysis_result_sources")
    op.drop_index("ix_analysis_result_sources_document_chunk_id", table_name="analysis_result_sources")
    op.drop_index("ix_analysis_result_sources_document_version_id", table_name="analysis_result_sources")
    op.drop_index("ix_analysis_result_sources_document_id", table_name="analysis_result_sources")
    op.drop_index("ix_analysis_result_sources_analysis_result_id", table_name="analysis_result_sources")
    op.drop_table("analysis_result_sources")

    op.drop_index("ix_analysis_results_commit_ref", table_name="analysis_results")
    op.drop_index("ix_analysis_results_status", table_name="analysis_results")
    op.drop_index("ix_analysis_results_type", table_name="analysis_results")
    op.drop_index("ix_analysis_results_analysis_group_id", table_name="analysis_results")
    op.drop_table("analysis_results")

    op.drop_index("ix_analysis_group_documents_document_version_id", table_name="analysis_group_documents")
    op.drop_index("ix_analysis_group_documents_document_id", table_name="analysis_group_documents")
    op.drop_table("analysis_group_documents")

    op.drop_index("ix_analysis_groups_updated_at", table_name="analysis_groups")
    op.drop_index("ix_analysis_groups_status", table_name="analysis_groups")
    op.drop_index("ix_analysis_groups_owner_user_id", table_name="analysis_groups")
    op.drop_index("ix_analysis_groups_workspace_id", table_name="analysis_groups")
    op.drop_table("analysis_groups")

    op.drop_index("ix_chat_messages_source_metadata", table_name="chat_messages", postgresql_using="gin")
    op.drop_index("ix_chat_messages_basis_type", table_name="chat_messages")
    op.drop_index("ix_chat_messages_role", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_owner_user_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_workspace_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
