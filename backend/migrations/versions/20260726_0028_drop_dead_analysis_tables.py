"""Drop dead analysis tables left over from the pre-0021 analysis model.

Vier Tabellen sind in `app/` nirgends referenziert (Stand 2026-07-26, verifiziert
per Volltextsuche ueber `backend/app`):

- `analysis_groups` / `analysis_group_documents`
  Aus Migration 20260430_0004. Das Gruppen-Modell wurde nie implementiert; das
  aktive Modell ist `analysis_jobs` + `analysis_job_source_documents`
  (Migration 20260612_0021).
- `analysis_results_legacy` / `analysis_result_sources_legacy`
  Entstehen in 20260612_0021 durch `rename_table`, damit die neuen Tabellen
  `analysis_results` / `analysis_result_sources` die Namen belegen koennen. Die
  umbenannten Altbestaende wurden nie aufgeraeumt.

Bewusst NICHT gedroppt: `migration_document_repairs`. Das ist das Audit-Log der
Datenreparatur aus 20260504_0010 und damit Nachweis, nicht Feature-Rest. Ein
Drop waere ein Dokumentationsverlust und braucht eine eigene PO-Entscheidung.

Datenschutz gegen stillen Verlust:
Der Upgrade bricht ab, wenn eine der Tabellen noch Zeilen enthaelt. Der Abbruch
nennt Tabelle und Zeilenzahl. Wer bewusst mit Daten droppen will, setzt
`ALLOW_DROP_NONEMPTY_LEGACY=1`.

Downgrade stellt die Tabellenstruktur wieder her, NICHT die Daten. Das ist
explizit dokumentiert und war die Voraussetzung fuer den Drop.

Revision ID: 20260726_0028
Revises: 20260724_0027
Create Date: 2026-07-26
"""
from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260726_0028"
down_revision: str | None = "20260724_0027"
branch_labels = None
depends_on = None

# Drop-Reihenfolge: Kinder vor Eltern. Die FK-Kanten zwischen den vier Tabellen
# (aus Migration 20260430_0004, Tabellennamen nach dem rename in 0021):
#
#   analysis_group_documents      --fk_ag_docs_group_id-->        analysis_groups
#   analysis_results_legacy       --fk_analysis_results_group_id--> analysis_groups
#   analysis_result_sources_legacy--fk_analysis_sources_result_id-> analysis_results_legacy
#
# analysis_groups muss deshalb ZULETZT fallen, nicht als zweites.
DEAD_TABLES = (
    "analysis_group_documents",
    "analysis_result_sources_legacy",
    "analysis_results_legacy",
    "analysis_groups",
)

ANALYSIS_STATUSES = "'draft', 'review', 'approved', 'archived'"
ANALYSIS_RESULT_TYPES = "'summary', 'comparison', 'extraction', 'custom'"


def _jsonb():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _guard_not_empty(bind) -> None:
    if os.environ.get("ALLOW_DROP_NONEMPTY_LEGACY") == "1":
        return
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    populated: list[str] = []
    for table in DEAD_TABLES:
        if table not in existing:
            continue
        count = bind.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one()
        if count:
            populated.append(f"{table}={count}")
    if populated:
        raise RuntimeError(
            "Migration 20260726_0028 abgebrochen: als tot eingestufte Tabellen enthalten "
            f"Daten ({', '.join(populated)}). Inhalt pruefen und sichern. Bewusster Drop: "
            "ALLOW_DROP_NONEMPTY_LEGACY=1 setzen."
        )


def upgrade() -> None:
    bind = op.get_bind()
    _guard_not_empty(bind)
    existing = set(sa.inspect(bind).get_table_names())
    for table in DEAD_TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    """Stellt die Struktur wieder her. Daten sind nicht wiederherstellbar.

    Anlagereihenfolge ist die Umkehrung des Drops: Eltern vor Kindern.
    """
    op.create_table(
        "analysis_groups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_analysis_groups_title_not_blank"),
        sa.CheckConstraint(
            f"status in ({ANALYSIS_STATUSES})", name="ck_analysis_groups_status_allowed"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_analysis_groups_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_analysis_groups_owner_user_id_users",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_analysis_groups_workspace_id", "analysis_groups", ["workspace_id"])
    op.create_index("ix_analysis_groups_owner_user_id", "analysis_groups", ["owner_user_id"])
    op.create_index("ix_analysis_groups_status", "analysis_groups", ["status"])
    op.create_index("ix_analysis_groups_updated_at", "analysis_groups", ["updated_at"])

    op.create_table(
        "analysis_group_documents",
        sa.Column("analysis_group_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("document_version_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_group_id"], ["analysis_groups.id"], name="fk_ag_docs_group_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="fk_ag_docs_document_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_ag_docs_document_version_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("analysis_group_id", "document_id", name="pk_analysis_group_documents"),
    )
    op.create_index(
        "ix_analysis_group_documents_document_id", "analysis_group_documents", ["document_id"]
    )
    op.create_index(
        "ix_analysis_group_documents_document_version_id",
        "analysis_group_documents",
        ["document_version_id"],
    )

    op.create_table(
        "analysis_results_legacy",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_group_id", sa.String(), nullable=False),
        sa.Column("result_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("result_markdown", sa.Text(), nullable=True),
        sa.Column("commit_ref", sa.String(length=255), nullable=True),
        sa.Column("metadata", _jsonb(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"result_type in ({ANALYSIS_RESULT_TYPES})", name="ck_analysis_results_type_allowed"
        ),
        sa.CheckConstraint(
            f"status in ({ANALYSIS_STATUSES})", name="ck_analysis_results_status_allowed"
        ),
        sa.CheckConstraint(
            "result_markdown IS NULL OR length(trim(result_markdown)) > 0",
            name="ck_analysis_results_markdown_not_blank",
        ),
        # Genau die FK-Kante, die den Drop-Fehler ausgeloest hat.
        sa.ForeignKeyConstraint(
            ["analysis_group_id"],
            ["analysis_groups.id"],
            name="fk_analysis_results_group_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_analysis_results_analysis_group_id", "analysis_results_legacy", ["analysis_group_id"]
    )

    op.create_table(
        "analysis_result_sources_legacy",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_result_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("document_version_id", sa.String(), nullable=True),
        sa.Column("document_chunk_id", sa.String(), nullable=True),
        sa.Column("anchor", sa.String(length=255), nullable=True),
        sa.Column("metadata", _jsonb(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_result_id"],
            ["analysis_results_legacy.id"],
            name="fk_analysis_sources_result_id",
            ondelete="CASCADE",
        ),
    )
