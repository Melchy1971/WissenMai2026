"""Additive v2 fields for analysis_jobs and analysis_results.

Adds: source_type, source_ids, provider, model, result_id to analysis_jobs.
Makes workspace_id and created_by nullable.
Expands status check constraint to include queued / cancelled.

Adds: title, content_markdown, sources, status, approved_at, approved_by,
      updated_at to analysis_results. Makes confidence nullable.

Revision ID: 20260616_0023
Revises: 20260616_0022
Create Date: 2026-06-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260616_0023"
down_revision: str | None = "20260616_0022"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ── analysis_jobs ─────────────────────────────────────────────────────────

    # 1. Drop old status CHECK (name must match migration 0021)
    if is_pg:
        op.drop_constraint("ck_analysis_jobs_status", "analysis_jobs", type_="check")

    # 2. Add expanded status CHECK
    op.create_check_constraint(
        "ck_analysis_jobs_status",
        "analysis_jobs",
        "status IN ('queued','running','completed','failed','cancelled','pending','approved')",
    )

    # 3. Make workspace_id nullable
    op.alter_column("analysis_jobs", "workspace_id", nullable=True, existing_type=sa.String())

    # 4. Make created_by nullable
    op.alter_column("analysis_jobs", "created_by", nullable=True, existing_type=sa.String())

    # 5. New columns
    op.add_column("analysis_jobs", sa.Column("source_type", sa.String(32), nullable=True))
    op.add_column("analysis_jobs", sa.Column("source_ids", json_type, nullable=True))
    op.add_column("analysis_jobs", sa.Column("provider", sa.String(64), nullable=True))
    op.add_column("analysis_jobs", sa.Column("model", sa.String(128), nullable=True))
    op.add_column("analysis_jobs", sa.Column("result_id", sa.String(), nullable=True))

    # 6. source_type CHECK
    op.create_check_constraint(
        "ck_analysis_jobs_source_type",
        "analysis_jobs",
        "source_type IS NULL OR source_type IN ('DOCUMENTS','TOPIC','SEARCH_RESULT')",
    )

    # 7. Index on source_type
    op.create_index("ix_analysis_jobs_source_type", "analysis_jobs", ["source_type"])

    # ── analysis_results ──────────────────────────────────────────────────────

    # 8. Make confidence nullable (was NOT NULL)
    op.alter_column("analysis_results", "confidence", nullable=True, existing_type=sa.Float())

    # 9. New columns
    op.add_column("analysis_results", sa.Column("title", sa.String(255), nullable=True))
    op.add_column("analysis_results", sa.Column("content_markdown", sa.Text(), nullable=True))
    op.add_column("analysis_results", sa.Column("sources", json_type, nullable=True))
    op.add_column(
        "analysis_results",
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
    )
    op.add_column("analysis_results", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("analysis_results", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column("analysis_results", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    # 10. FK for approved_by
    op.create_foreign_key(
        "fk_analysis_results_approved_by",
        "analysis_results",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # 11. Constraints and indexes on analysis_results
    op.create_check_constraint(
        "ck_analysis_results_status",
        "analysis_results",
        "status IN ('draft','review','approved','rejected')",
    )
    op.create_check_constraint(
        "ck_analysis_results_approval_metadata",
        "analysis_results",
        "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL) "
        "OR (status != 'approved' AND approved_by IS NULL AND approved_at IS NULL)",
    )
    op.create_index("ix_analysis_results_status", "analysis_results", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # analysis_results
    op.drop_index("ix_analysis_results_status", "analysis_results")
    if is_pg:
        op.drop_constraint("ck_analysis_results_approval_metadata", "analysis_results", type_="check")
        op.drop_constraint("ck_analysis_results_status", "analysis_results", type_="check")
    op.drop_constraint("fk_analysis_results_approved_by", "analysis_results", type_="foreignkey")
    for col in ("updated_at", "approved_by", "approved_at", "status", "sources", "content_markdown", "title"):
        op.drop_column("analysis_results", col)
    op.alter_column("analysis_results", "confidence", nullable=False, existing_type=sa.Float())

    # analysis_jobs
    op.drop_index("ix_analysis_jobs_source_type", "analysis_jobs")
    if is_pg:
        op.drop_constraint("ck_analysis_jobs_source_type", "analysis_jobs", type_="check")
    for col in ("result_id", "model", "provider", "source_ids", "source_type"):
        op.drop_column("analysis_jobs", col)
    op.alter_column("analysis_jobs", "created_by", nullable=False, existing_type=sa.String())
    op.alter_column("analysis_jobs", "workspace_id", nullable=False, existing_type=sa.String())
    if is_pg:
        op.drop_constraint("ck_analysis_jobs_status", "analysis_jobs", type_="check")
    op.create_check_constraint(
        "ck_analysis_jobs_status",
        "analysis_jobs",
        "status IN ('pending','running','completed','failed','approved')",
    )
