"""Create analytics_snapshots and analytics_metrics tables (PRI-4 Dashboard Drift Analytics).

These tables are separate from the M5b drift detection layer (drift_runs,
drift_findings, drift_snapshots). They store immutable product quality snapshots
for Dashboard Drift Analytics widgets: ProductMaturity, GoldPath, ReleaseGate,
TestCoverage, IdLeakAudit, SecurityAudit.

Key constraints:
- analytics_snapshots.status: PASS|WARNING|FAIL|BLOCKED
- analytics_snapshots.snapshot_type: PRODUCT_MATURITY|GOLD_PATH|RELEASE_GATE|
                                     TEST_COVERAGE|ID_LEAK_AUDIT|SECURITY_AUDIT
- analytics_metrics.status: same 4 values
- All rows are INSERT-only (no UPDATE by application code)
- workspace_id is nullable FK (NULL = global snapshot)

Indexes:
- ix_analytics_snapshots_type           (snapshot_type)
- ix_analytics_snapshots_status         (status)
- ix_analytics_snapshots_created_at     (created_at)
- ix_analytics_snapshots_type_created   (snapshot_type, created_at) composite
- ix_analytics_snapshots_workspace_id   (workspace_id)
- ix_analytics_metrics_snapshot_id      (snapshot_id)
- ix_analytics_metrics_status           (status)

Revision ID: 20260617_0025
Revises: 20260616_0024
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260617_0025"
down_revision: str | None = "20260616_0024"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # --- analytics_snapshots ---
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_snapshots"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_analytics_snapshots_workspace",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "snapshot_type IN ("
            "'PRODUCT_MATURITY','GOLD_PATH','RELEASE_GATE',"
            "'TEST_COVERAGE','ID_LEAK_AUDIT','SECURITY_AUDIT'"
            ")",
            name="ck_analytics_snapshots_snapshot_type",
        ),
        sa.CheckConstraint(
            "status IN ('PASS','WARNING','FAIL','BLOCKED')",
            name="ck_analytics_snapshots_status",
        ),
    )

    op.create_index("ix_analytics_snapshots_type", "analytics_snapshots", ["snapshot_type"])
    op.create_index("ix_analytics_snapshots_status", "analytics_snapshots", ["status"])
    op.create_index("ix_analytics_snapshots_created_at", "analytics_snapshots", ["created_at"])
    op.create_index(
        "ix_analytics_snapshots_type_created",
        "analytics_snapshots",
        ["snapshot_type", "created_at"],
    )
    op.create_index(
        "ix_analytics_snapshots_workspace_id", "analytics_snapshots", ["workspace_id"]
    )

    # --- analytics_metrics ---
    op.create_table(
        "analytics_metrics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=False),
        sa.Column("metric_label", sa.String(length=255), nullable=False),
        sa.Column("metric_value", sa.Text(), nullable=False),
        sa.Column("metric_unit", sa.String(length=32), nullable=True),
        sa.Column("threshold_warning", sa.Float(), nullable=True),
        sa.Column("threshold_fail", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_metrics"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["analytics_snapshots.id"],
            name="fk_analytics_metrics_snapshot",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('PASS','WARNING','FAIL','BLOCKED')",
            name="ck_analytics_metrics_status",
        ),
    )

    op.create_index("ix_analytics_metrics_snapshot_id", "analytics_metrics", ["snapshot_id"])
    op.create_index("ix_analytics_metrics_status", "analytics_metrics", ["status"])


def downgrade() -> None:
    op.drop_index("ix_analytics_metrics_status", table_name="analytics_metrics")
    op.drop_index("ix_analytics_metrics_snapshot_id", table_name="analytics_metrics")
    op.drop_table("analytics_metrics")

    op.drop_index("ix_analytics_snapshots_workspace_id", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_type_created", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_created_at", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_status", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_type", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
