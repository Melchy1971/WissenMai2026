"""Allow status 'cancelled' on background_jobs.

Defektbefund 2026-07-26: Die Anwendung kennt den Status `cancelled` durchgaengig
(`app/schemas/jobs.py::JobStatus`, ORM-Check in `app/models/documents.py`), die
DB nicht. Der Check aus Migration 20260505_0015 erlaubt nur
('pending','running','completed','retryable','failed','dead_letter').

Folge vor diesem Fix: Ein abgebrochener Job liess sich auf PostgreSQL nicht
persistieren (CheckViolation), waehrend die SQLite-Unit-Suite ihn akzeptierte —
der Fehler war ausschliesslich auf der echten DB sichtbar.

Revision ID: 20260726_0029
Revises: 20260726_0028
Create Date: 2026-07-26
"""
from __future__ import annotations

from alembic import op

revision: str = "20260726_0029"
down_revision: str | None = "20260726_0028"
branch_labels = None
depends_on = None

CONSTRAINT = "ck_background_jobs_status_allowed"
OLD_STATUSES = "'pending', 'running', 'completed', 'retryable', 'failed', 'dead_letter'"
NEW_STATUSES = OLD_STATUSES + ", 'cancelled'"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, "background_jobs", type_="check")
    op.create_check_constraint(CONSTRAINT, "background_jobs", f"status in ({NEW_STATUSES})")


def downgrade() -> None:
    # Zeilen im neuen Status wuerden den alten Check verletzen; sie werden auf
    # 'failed' zurueckgesetzt, damit der Downgrade deterministisch durchlaeuft.
    op.execute("UPDATE background_jobs SET status = 'failed' WHERE status = 'cancelled'")
    op.drop_constraint(CONSTRAINT, "background_jobs", type_="check")
    op.create_check_constraint(CONSTRAINT, "background_jobs", f"status in ({OLD_STATUSES})")
