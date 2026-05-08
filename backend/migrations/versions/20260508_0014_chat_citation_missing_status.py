"""align chat citation source_status with missing live lookup

Revision ID: 20260508_0014
Revises: 20260506_0013
Create Date: 2026-05-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260508_0014"
down_revision: str | None = "20260506_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("update chat_citations set source_status = 'missing' where source_status = 'unknown'")
    with op.batch_alter_table("chat_citations") as batch_op:
        batch_op.drop_constraint("ck_chat_citations_source_status_allowed", type_="check")
        batch_op.create_check_constraint(
            "ck_chat_citations_source_status_allowed",
            "source_status in ('active', 'archived', 'deleted', 'missing')",
        )


def downgrade() -> None:
    op.execute("update chat_citations set source_status = 'unknown' where source_status = 'missing'")
    with op.batch_alter_table("chat_citations") as batch_op:
        batch_op.drop_constraint("ck_chat_citations_source_status_allowed", type_="check")
        batch_op.create_check_constraint(
            "ck_chat_citations_source_status_allowed",
            "source_status in ('active', 'archived', 'deleted', 'unknown')",
        )