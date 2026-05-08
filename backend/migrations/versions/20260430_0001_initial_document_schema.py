"""initial document schema

Revision ID: 20260430_0001
Revises:
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260430_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_workspaces_name_not_blank"),
    )
    op.create_index(
        "ux_workspaces_single_default",
        "workspaces",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(display_name)) > 0", name="ck_users_display_name_not_blank"),
    )
    op.create_index(
        "ux_users_single_default",
        "users",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    workspaces = sa.table(
        "workspaces",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_default", sa.Boolean()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("is_default", sa.Boolean()),
    )
    op.bulk_insert(
        workspaces,
        [{"id": DEFAULT_WORKSPACE_ID, "name": "Default Workspace", "is_default": True}],
    )
    op.bulk_insert(
        users,
        [{"id": DEFAULT_USER_ID, "display_name": "Default User", "is_default": True}],
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("current_version_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_documents_title_not_blank"),
        sa.CheckConstraint("length(trim(source_type)) > 0", name="ck_documents_source_type_not_blank"),
        sa.CheckConstraint("length(trim(content_hash)) > 0", name="ck_documents_content_hash_not_blank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_documents_workspace_id_workspaces",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_documents_owner_user_id_users",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_documents_owner_user_id", "documents", ["owner_user_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("normalized_markdown", sa.Text(), nullable=False),
        sa.Column("markdown_hash", sa.String(length=128), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ki_provider", sa.String(length=128), nullable=True),
        sa.Column("ki_model", sa.String(length=128), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("version_number > 0", name="ck_document_versions_version_number_positive"),
        sa.CheckConstraint("length(trim(markdown_hash)) > 0", name="ck_document_versions_markdown_hash_not_blank"),
        sa.CheckConstraint("length(trim(parser_version)) > 0", name="ck_document_versions_parser_version_not_blank"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_versions_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_document_version_number"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_markdown_hash", "document_versions", ["markdown_hash"])
    op.create_index("ix_document_versions_created_at", "document_versions", ["created_at"])

    op.create_foreign_key(
        "fk_documents_current_version_id_document_versions",
        "documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_current_version_id", "documents", ["current_version_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_current_version_id", table_name="documents")
    op.drop_constraint(
        "fk_documents_current_version_id_document_versions",
        "documents",
        type_="foreignkey",
    )

    op.drop_index("ix_document_versions_created_at", table_name="document_versions")
    op.drop_index("ix_document_versions_markdown_hash", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_index("ix_documents_owner_user_id", table_name="documents")
    op.drop_index("ix_documents_workspace_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ux_users_single_default", table_name="users")
    op.drop_table("users")

    op.drop_index("ux_workspaces_single_default", table_name="workspaces")
    op.drop_table("workspaces")
