"""Drift Persistence Layer.

Creates tables: drift_runs, drift_findings, drift_snapshots.

Revision ID: 20260611_0020
Revises: 20260602_0019
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260611_0020"
down_revision: str | None = "20260602_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # drift_runs
    # ------------------------------------------------------------------
    op.create_table(
        "drift_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column(
            "detector_names",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_findings", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_drift_runs"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_drift_runs_workspace_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed','cancelled')",
            name="ck_drift_runs_status",
        ),
    )
    op.create_index("ix_drift_runs_workspace_id", "drift_runs", ["workspace_id"])
    op.create_index("ix_drift_runs_status", "drift_runs", ["status"])
    op.create_index("ix_drift_runs_created_at", "drift_runs", ["created_at"])

    # ------------------------------------------------------------------
    # drift_findings
    # ------------------------------------------------------------------
    op.create_table(
        "drift_findings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("finding_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column(
            "detail",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_drift_findings"),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["drift_runs.id"],
            name="fk_drift_findings_run_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_drift_findings_workspace_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "finding_type IN ("
            "'DOCUMENT_DRIFT','METADATA_DRIFT','LIFECYCLE_DRIFT',"
            "'SOURCE_STATUS_DRIFT','RETRIEVAL_DRIFT'"
            ")",
            name="ck_drift_findings_finding_type",
        ),
        sa.CheckConstraint(
            "severity IN ('info','warning','error','critical')",
            name="ck_drift_findings_severity",
        ),
    )
    op.create_index("ix_drift_findings_run_id", "drift_findings", ["run_id"])
    op.create_index("ix_drift_findings_workspace_id", "drift_findings", ["workspace_id"])
    op.create_index("ix_drift_findings_finding_type", "drift_findings", ["finding_type"])
    op.create_index("ix_drift_findings_severity", "drift_findings", ["severity"])
    op.create_index("ix_drift_findings_entity_id", "drift_findings", ["entity_id"])

    # ------------------------------------------------------------------
    # drift_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "drift_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("snapshot_type", sa.String(16), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_drift_snapshots"),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["drift_runs.id"],
            name="fk_drift_snapshots_run_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_drift_snapshots_workspace_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "snapshot_type IN ('pre_run','post_run','baseline','delta')",
            name="ck_drift_snapshots_snapshot_type",
        ),
    )
    op.create_index("ix_drift_snapshots_run_id", "drift_snapshots", ["run_id"])
    op.create_index("ix_drift_snapshots_workspace_id", "drift_snapshots", ["workspace_id"])
    op.create_index("ix_drift_snapshots_snapshot_type", "drift_snapshots", ["snapshot_type"])


def downgrade() -> None:
    op.drop_table("drift_snapshots")
    op.drop_table("drift_findings")
    op.drop_table("drift_runs")
