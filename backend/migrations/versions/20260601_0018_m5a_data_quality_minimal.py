"""M5a Data Quality — Minimal Migration.

Creates data_quality_runs and data_quality_findings with all required
fields, FK constraints, and indexes.

Deferred (not in this migration):
  - data_quality_metrics
  - data_quality_snapshots

Supersedes orphaned migration 20260529_0017 (down_revision=None).

Revision ID: 20260601_0018
Revises: 20260508_0014
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260601_0018"
down_revision: str | None = "20260508_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum type ────────────────────────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dq_finding_type') THEN
                CREATE TYPE dq_finding_type AS ENUM (
                    'DUPLICATE_DOCUMENT',
                    'DUPLICATE_CONTENT',
                    'EMPTY_DOCUMENT',
                    'EMPTY_CHUNK',
                    'ORPHAN_CHUNK',
                    'ORPHAN_VERSION',
                    'MISSING_METADATA',
                    'INVALID_SOURCE_STATUS',
                    'INVALID_LIFECYCLE',
                    'RETRIEVAL_RISK'
                );
            END IF;
        END
        $$;
    """)

    # ── data_quality_runs ────────────────────────────────────────────────────
    op.create_table(
        "data_quality_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_findings", sa.Integer, nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column(
            "created_by",
            sa.String,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_dq_runs_status",
        ),
    )
    op.create_index("ix_dq_runs_workspace_id", "data_quality_runs", ["workspace_id"])
    op.create_index("ix_dq_runs_status", "data_quality_runs", ["status"])

    # ── data_quality_findings ────────────────────────────────────────────────
    op.create_table(
        "data_quality_findings",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "run_id",
            sa.String,
            sa.ForeignKey("data_quality_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_type",
            pg.ENUM(
                'DUPLICATE_DOCUMENT',
                'DUPLICATE_CONTENT',
                'EMPTY_DOCUMENT',
                'EMPTY_CHUNK',
                'ORPHAN_CHUNK',
                'ORPHAN_VERSION',
                'MISSING_METADATA',
                'INVALID_SOURCE_STATUS',
                'INVALID_LIFECYCLE',
                'RETRIEVAL_RISK',
                name="dq_finding_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("document_id", sa.String, nullable=True),
        sa.Column("version_id", sa.String, nullable=True),
        sa.Column("chunk_id", sa.String, nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("remediation", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "severity IN ('error', 'warning', 'info')",
            name="ck_dq_findings_severity",
        ),
    )
    op.create_index("ix_dq_findings_run_id", "data_quality_findings", ["run_id"])
    op.create_index("ix_dq_findings_workspace_id", "data_quality_findings", ["workspace_id"])
    op.create_index("ix_dq_findings_severity", "data_quality_findings", ["severity"])
    op.create_index("ix_dq_findings_finding_type", "data_quality_findings", ["finding_type"])


def downgrade() -> None:
    op.drop_index("ix_dq_findings_finding_type", table_name="data_quality_findings")
    op.drop_index("ix_dq_findings_severity", table_name="data_quality_findings")
    op.drop_index("ix_dq_findings_workspace_id", table_name="data_quality_findings")
    op.drop_index("ix_dq_findings_run_id", table_name="data_quality_findings")
    op.drop_table("data_quality_findings")

    op.drop_index("ix_dq_runs_status", table_name="data_quality_runs")
    op.drop_index("ix_dq_runs_workspace_id", table_name="data_quality_runs")
    op.drop_table("data_quality_runs")

    op.execute("DROP TYPE IF EXISTS dq_finding_type")
