"""Create export_jobs and export_templates tables.

Adds: export_jobs (id, workspace_id, status, source_type, source_ids,
      export_format, file_name, file_path, error_message, created_by,
      created_at, started_at, finished_at).
Adds: export_templates (id, name, export_format, layout_config, is_default,
      created_at, updated_at).

Revision ID: 20260616_0024
Revises: 20260616_0023
Create Date: 2026-06-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260616_0024"
down_revision: str | None = "20260616_0023"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- export_jobs ---
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="QUEUED"),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ids", json_type, nullable=True),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_export_jobs"),
        sa.CheckConstraint(
            "status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')",
            name="ck_export_jobs_status",
        ),
        sa.CheckConstraint(
            "source_type IN ('SEARCH_RESULT','ANALYSIS_RESULT','TOPIC','DOCUMENT_COLLECTION')",
            name="ck_export_jobs_source_type",
        ),
        sa.CheckConstraint(
            "export_format IN ('MARKDOWN','JSON','PDF')",
            name="ck_export_jobs_export_format",
        ),
        sa.CheckConstraint(
            "length(trim(file_name)) > 0",
            name="ck_export_jobs_file_name_not_blank",
        ),
    )
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])
    op.create_index("ix_export_jobs_source_type", "export_jobs", ["source_type"])
    op.create_index("ix_export_jobs_export_format", "export_jobs", ["export_format"])
    op.create_index("ix_export_jobs_created_at", "export_jobs", ["created_at"])
    op.create_index("ix_export_jobs_workspace_id", "export_jobs", ["workspace_id"])

    # --- export_templates ---
    op.create_table(
        "export_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("layout_config", json_type, nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_export_templates"),
        sa.UniqueConstraint("name", name="uq_export_templates_name"),
        sa.CheckConstraint(
            "export_format IN ('MARKDOWN','JSON','PDF')",
            name="ck_export_templates_export_format",
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_export_templates_name_not_blank",
        ),
    )
    op.create_index("ix_export_templates_export_format", "export_templates", ["export_format"])
    op.create_index("ix_export_templates_is_default", "export_templates", ["is_default"])


def downgrade() -> None:
    op.drop_index("ix_export_templates_is_default", table_name="export_templates")
    op.drop_index("ix_export_templates_export_format", table_name="export_templates")
    op.drop_table("export_templates")

    op.drop_index("ix_export_jobs_workspace_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_created_at", table_name="export_jobs")
    op.drop_index("ix_export_jobs_export_format", table_name="export_jobs")
    op.drop_index("ix_export_jobs_source_type", table_name="export_jobs")
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_table("export_jobs")
