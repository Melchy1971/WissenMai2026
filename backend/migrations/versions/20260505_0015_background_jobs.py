"""background jobs

Revision ID: 20260505_0015
Revises: 20260505_0014
Create Date: 2026-05-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260505_0015"
down_revision: str | None = "20260505_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("requested_by_user_id", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("progress_message", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "job_type in ('document_import', 'search_index_rebuild')",
            name="ck_background_jobs_job_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'retryable', 'failed', 'dead_letter')",
            name="ck_background_jobs_status_allowed",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_background_jobs_attempt_count_non_negative"),
    )
    op.create_index("ix_background_jobs_status_created_at", "background_jobs", ["status", "created_at"])
    op.create_index(
        "ix_background_jobs_workspace_job_type_created_at",
        "background_jobs",
        ["workspace_id", "job_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_background_jobs_workspace_job_type_created_at", table_name="background_jobs")
    op.drop_index("ix_background_jobs_status_created_at", table_name="background_jobs")
    op.drop_table("background_jobs")