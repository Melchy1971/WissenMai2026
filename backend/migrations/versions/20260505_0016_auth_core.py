"""add auth core tables and user credentials

Revision ID: 20260505_0016
Revises: 20260505_0015
Create Date: 2026-05-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260505_0016"
down_revision: str | None = "20260505_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("login", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_unique_constraint("uq_users_login", "users", ["login"])

    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role in ('owner', 'admin', 'member')", name="ck_workspace_memberships_role_allowed"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade() -> None:
    op.drop_table("auth_sessions")
    op.drop_table("workspace_memberships")
    op.drop_constraint("uq_users_login", "users", type_="unique")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "login")