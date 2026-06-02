"""M5a Orphan Object Finding Types.

Adds finding types needed by the Orphan Object Detector.

Revision ID: 20260602_0019
Revises: 20260601_0018
Create Date: 2026-06-02
"""
from __future__ import annotations

from alembic import op

revision: str = "20260602_0019"
down_revision: str | None = "20260601_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE dq_finding_type ADD VALUE IF NOT EXISTS 'ORPHAN_CITATION'")
    op.execute("ALTER TYPE dq_finding_type ADD VALUE IF NOT EXISTS 'ORPHAN_FINDING'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without recreating the type.
    pass
