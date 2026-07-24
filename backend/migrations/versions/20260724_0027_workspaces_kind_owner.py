"""Workspace kind (private/shared) and owner linkage for multi-user V1 (Story 1).

Adds the schema foundation for the multi-user Definition of Done:
- every user gets a private workspace, and there is exactly one shared workspace.

Columns:
- workspaces.kind           String(16) NOT NULL default 'private',
                            CHECK kind in ('private','shared')
- workspaces.owner_user_id  String NULL, FK users.id ON DELETE CASCADE
                            (set for private workspaces, NULL for the shared one)

Invariants (enforced on PostgreSQL):
- Exactly one shared workspace: tied to the EXISTING partial unique index
  ux_workspaces_single_default via the consistency check
  (kind='shared') <=> (is_default = true). No second singleton mechanism.
- At most one private workspace per user: partial unique index on owner_user_id
  WHERE owner_user_id IS NOT NULL.

Data backfill (PO decision 2026-07-24: today's default workspace becomes the
shared/common area, keeping its existing documents visible to all users):
- workspaces with is_default = true  -> kind='shared'
- all other existing workspaces      -> kind='private' (owner_user_id stays NULL
  for legacy rows; new private workspaces receive their owner via
  ProvisioningService in a later story).

Revision ID: 20260724_0027
Revises: 20260618_0026
Create Date: 2026-07-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_0027"
down_revision: str | None = "20260618_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # 1. Add columns (kind nullable first so we can backfill deterministically).
    op.add_column("workspaces", sa.Column("kind", sa.String(16), nullable=True))
    op.add_column("workspaces", sa.Column("owner_user_id", sa.String(), nullable=True))

    # 2. Owner FK -> users (cascade delete removes the private workspace with its user).
    op.create_foreign_key(
        "fk_workspaces_owner_user_id_users",
        "workspaces",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Backfill: today's default workspace becomes the shared area.
    op.execute("UPDATE workspaces SET kind = 'shared' WHERE is_default = true")
    op.execute("UPDATE workspaces SET kind = 'private' WHERE kind IS NULL")

    # 4. Enforce NOT NULL + server default for future inserts.
    op.alter_column(
        "workspaces",
        "kind",
        existing_type=sa.String(16),
        nullable=False,
        server_default="private",
    )

    # 5. Value + consistency checks.
    op.create_check_constraint(
        "ck_workspaces_kind_allowed",
        "workspaces",
        "kind in ('private','shared')",
    )
    # Tie shared<->default and private<->non-default. This reuses the existing
    # partial unique index ux_workspaces_single_default to guarantee exactly one
    # shared workspace, without introducing a second singleton mechanism.
    op.create_check_constraint(
        "ck_workspaces_kind_default_consistency",
        "workspaces",
        "(kind = 'shared' AND is_default) OR (kind = 'private' AND NOT is_default)",
    )

    # 6. At most one private workspace per user (NULL owners are skipped).
    if is_pg:
        op.create_index(
            "uq_workspaces_owner_private",
            "workspaces",
            ["owner_user_id"],
            unique=True,
            postgresql_where=sa.text("owner_user_id IS NOT NULL"),
        )
    else:
        op.create_index(
            "uq_workspaces_owner_private",
            "workspaces",
            ["owner_user_id"],
            unique=True,
            sqlite_where=sa.text("owner_user_id IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("uq_workspaces_owner_private", table_name="workspaces")
    op.drop_constraint("ck_workspaces_kind_default_consistency", "workspaces", type_="check")
    op.drop_constraint("ck_workspaces_kind_allowed", "workspaces", type_="check")
    op.drop_constraint("fk_workspaces_owner_user_id_users", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "owner_user_id")
    op.drop_column("workspaces", "kind")
