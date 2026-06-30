"""Final analysis data model.

Revision ID: 20260612_0021
Revises: 20260611_0020
Create Date: 2026-06-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612_0021"
down_revision: str | None = "20260611_0020"
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _archive_legacy_analysis_tables() -> None:
    """Free the analysis_results name while preserving the legacy model."""
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "analysis_results" not in tables:
        return

    columns = {column["name"] for column in sa.inspect(bind).get_columns("analysis_results")}
    if "analysis_group_id" not in columns:
        raise RuntimeError("analysis_results exists but is not the expected legacy table")
    if "analysis_results_legacy" in tables:
        raise RuntimeError("analysis_results_legacy already exists")

    # The final model adds an index with this name in revision 0023. Index
    # names are schema-global in PostgreSQL, so remove the legacy index while
    # the archived table is unused and restore it on downgrade.
    op.drop_index("ix_analysis_results_status", table_name="analysis_results")
    op.rename_table("analysis_results", "analysis_results_legacy")

    if "analysis_result_sources" in tables:
        if "analysis_result_sources_legacy" in tables:
            raise RuntimeError("analysis_result_sources_legacy already exists")
        op.rename_table("analysis_result_sources", "analysis_result_sources_legacy")


def _restore_legacy_analysis_tables() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "analysis_results_legacy" not in tables:
        return

    op.rename_table("analysis_results_legacy", "analysis_results")
    op.create_index("ix_analysis_results_status", "analysis_results", ["status"])

    if "analysis_result_sources_legacy" in tables:
        op.rename_table("analysis_result_sources_legacy", "analysis_result_sources")


def upgrade() -> None:
    _archive_legacy_analysis_tables()

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("analysis_type", sa.String(length=64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_jobs"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_analysis_jobs_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_analysis_jobs_created_by", ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('pending','running','completed','failed','approved')", name="ck_analysis_jobs_status"),
        sa.CheckConstraint("length(trim(analysis_type)) > 0", name="ck_analysis_jobs_analysis_type_not_blank"),
        sa.CheckConstraint("length(trim(prompt)) > 0", name="ck_analysis_jobs_prompt_not_blank"),
    )
    op.create_index("ix_analysis_jobs_workspace_id", "analysis_jobs", ["workspace_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"])

    op.create_table(
        "analysis_job_source_documents",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("job_id", "document_id", name="pk_analysis_job_source_documents"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], name="fk_analysis_job_source_documents_job_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_analysis_job_source_documents_document_id", ondelete="RESTRICT"),
        sa.UniqueConstraint("job_id", "position", name="uq_analysis_job_source_documents_job_position"),
        sa.CheckConstraint("position >= 0", name="ck_analysis_job_source_documents_position_non_negative"),
    )
    op.create_index(
        "ix_analysis_job_source_documents_document_id",
        "analysis_job_source_documents",
        ["document_id"],
    )

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_points", json_type, nullable=False),
        sa.Column("suggested_tags", json_type, nullable=False),
        sa.Column("suggested_topics", json_type, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_results"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], name="fk_analysis_results_job_id", ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_analysis_results_job_id"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_analysis_results_confidence_range"),
    )
    op.create_index("ix_analysis_results_created_at", "analysis_results", ["created_at"])

    op.create_table(
        "analysis_comparisons",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("overlaps", json_type, nullable=False),
        sa.Column("differences", json_type, nullable=False),
        sa.Column("suggested_merge", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_comparisons"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], name="fk_analysis_comparisons_job_id", ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_analysis_comparisons_job_id"),
    )
    op.create_index("ix_analysis_comparisons_created_at", "analysis_comparisons", ["created_at"])

    op.create_table(
        "analysis_comparison_documents",
        sa.Column("comparison_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("comparison_id", "document_id", name="pk_analysis_comparison_documents"),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["analysis_comparisons.id"],
            name="fk_analysis_comparison_documents_comparison_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_analysis_comparison_documents_document_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("comparison_id", "position", name="uq_analysis_comparison_documents_comparison_position"),
        sa.CheckConstraint("position >= 0", name="ck_analysis_comparison_documents_position_non_negative"),
    )
    op.create_index(
        "ix_analysis_comparison_documents_document_id",
        "analysis_comparison_documents",
        ["document_id"],
    )

    op.create_table(
        "analysis_suggestions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("suggestion_type", sa.String(length=64), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_suggestions"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], name="fk_analysis_suggestions_job_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_analysis_suggestions_approved_by", ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('pending','running','completed','failed','approved')", name="ck_analysis_suggestions_status"),
        sa.CheckConstraint(
            "(status = 'approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL) "
            "OR (status != 'approved' AND approved_by IS NULL AND approved_at IS NULL)",
            name="ck_analysis_suggestions_approval_metadata",
        ),
        sa.CheckConstraint("length(trim(suggestion_type)) > 0", name="ck_analysis_suggestions_type_not_blank"),
    )
    op.create_index("ix_analysis_suggestions_status", "analysis_suggestions", ["status"])


def downgrade() -> None:
    op.drop_table("analysis_suggestions")
    op.drop_table("analysis_comparison_documents")
    op.drop_table("analysis_comparisons")
    op.drop_table("analysis_results")
    op.drop_table("analysis_job_source_documents")
    op.drop_table("analysis_jobs")
    _restore_legacy_analysis_tables()
