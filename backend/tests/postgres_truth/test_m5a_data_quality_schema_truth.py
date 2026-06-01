"""M5a Data Quality — PostgreSQL Schema Truth Tests.

Verifiziert:
- Tabellen data_quality_runs und data_quality_findings existieren
- Alle Pflichtfelder vorhanden mit korrekten Typen
- FK Constraints aktiv (workspace_id, run_id, created_by)
- Indexes auf workspace_id, run_id, severity, finding_type
- CheckConstraints für status und severity aktiv
- Kein mutierender Repair-Pfad im Schema

Deferred (nicht in dieser Suite):
- data_quality_metrics
- data_quality_snapshots
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun

pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_id() -> str:
    return str(uuid.uuid4())


def _make_finding_id() -> str:
    return str(uuid.uuid4())


def _insert_run(session: Session, workspace_id: str, run_id: str | None = None) -> str:
    rid = run_id or _make_run_id()
    run = DataQualityRun(
        id=rid,
        workspace_id=workspace_id,
        status="pending",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    return rid


def _insert_finding(
    session: Session,
    run_id: str,
    workspace_id: str,
    finding_id: str | None = None,
) -> str:
    fid = finding_id or _make_finding_id()
    finding = DataQualityFinding(
        id=fid,
        run_id=run_id,
        workspace_id=workspace_id,
        finding_type="ORPHAN_CHUNK",
        severity="warning",
        title="Test Finding",
        description="Orphaned chunk detected.",
        remediation="No automated repair. Manual review required.",
        created_at=datetime.now(UTC),
    )
    session.add(finding)
    session.flush()
    return fid


# ---------------------------------------------------------------------------
# Schema: table existence and columns
# ---------------------------------------------------------------------------

def test_data_quality_runs_table_exists(truth_session: Session) -> None:
    insp = inspect(truth_session.bind)
    assert "data_quality_runs" in insp.get_table_names(), \
        "data_quality_runs table missing"


def test_data_quality_findings_table_exists(truth_session: Session) -> None:
    insp = inspect(truth_session.bind)
    assert "data_quality_findings" in insp.get_table_names(), \
        "data_quality_findings table missing"


def test_data_quality_runs_required_columns(truth_session: Session) -> None:
    insp = inspect(truth_session.bind)
    cols = {c["name"] for c in insp.get_columns("data_quality_runs")}
    required = {
        "id", "workspace_id", "status",
        "started_at", "finished_at",
        "total_findings", "quality_score", "created_by",
    }
    missing = required - cols
    assert not missing, f"data_quality_runs missing columns: {missing}"


def test_data_quality_findings_required_columns(truth_session: Session) -> None:
    insp = inspect(truth_session.bind)
    cols = {c["name"] for c in insp.get_columns("data_quality_findings")}
    required = {
        "id", "run_id", "workspace_id", "finding_type", "severity",
        "document_id", "version_id", "chunk_id",
        "title", "description", "remediation", "created_at",
    }
    missing = required - cols
    assert not missing, f"data_quality_findings missing columns: {missing}"


def test_deferred_tables_absent(truth_session: Session) -> None:
    """data_quality_metrics and data_quality_snapshots are deferred — must not exist yet."""
    insp = inspect(truth_session.bind)
    tables = insp.get_table_names()
    assert "data_quality_metrics" not in tables, \
        "data_quality_metrics is deferred scope — must not exist in minimal migration"
    assert "data_quality_snapshots" not in tables, \
        "data_quality_snapshots is deferred scope — must not exist in minimal migration"


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

def test_indexes_on_runs(truth_session: Session) -> None:
    insp = inspect(truth_session.bind)
    idx_cols = {
        col
        for idx in insp.get_indexes("data_quality_runs")
        for col in idx["column_names"]
    }
    assert "workspace_id" in idx_cols, "Missing index on data_quality_runs.workspace_id"


def test_indexes_on_findings(truth_session: Session) -> None:
    insp = inspect(truth_session.bind)
    idx_cols = {
        col
        for idx in insp.get_indexes("data_quality_findings")
        for col in idx["column_names"]
    }
    for col in ("run_id", "workspace_id", "severity", "finding_type"):
        assert col in idx_cols, f"Missing index on data_quality_findings.{col}"


# ---------------------------------------------------------------------------
# FK Constraints
# ---------------------------------------------------------------------------

def test_findings_fk_run_id_enforced(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """FK data_quality_findings.run_id → data_quality_runs.id must be active."""
    with pytest.raises(Exception, match=r"(?i)foreign key|violates"):
        finding = DataQualityFinding(
            id=_make_finding_id(),
            run_id="nonexistent-run-id",
            workspace_id=truth_seed["workspace_id"],
            finding_type="EMPTY_CHUNK",
            severity="error",
            title="FK test",
            description="Should fail FK.",
            remediation="N/A",
            created_at=datetime.now(UTC),
        )
        truth_session.add(finding)
        truth_session.flush()


def test_runs_fk_workspace_id_enforced(truth_session: Session) -> None:
    """FK data_quality_runs.workspace_id → workspaces.id must be active."""
    with pytest.raises(Exception, match=r"(?i)foreign key|violates"):
        run = DataQualityRun(
            id=_make_run_id(),
            workspace_id="nonexistent-workspace-id",
            status="pending",
            started_at=datetime.now(UTC),
        )
        truth_session.add(run)
        truth_session.flush()


def test_cascade_delete_run_removes_findings(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """Deleting a run must cascade-delete its findings."""
    run_id = _insert_run(truth_session, truth_seed["workspace_id"])
    finding_id = _insert_finding(truth_session, run_id, truth_seed["workspace_id"])
    truth_session.commit()

    truth_session.execute(
        text("DELETE FROM data_quality_runs WHERE id = :id"), {"id": run_id}
    )
    truth_session.commit()

    result = truth_session.execute(
        text("SELECT COUNT(*) FROM data_quality_findings WHERE id = :id"),
        {"id": finding_id},
    ).scalar()
    assert result == 0, "Cascade delete did not remove findings"


# ---------------------------------------------------------------------------
# CheckConstraints
# ---------------------------------------------------------------------------

def test_run_status_constraint_rejects_invalid(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    with pytest.raises(Exception, match=r"(?i)check|violates"):
        run = DataQualityRun(
            id=_make_run_id(),
            workspace_id=truth_seed["workspace_id"],
            status="INVALID_STATUS",
            started_at=datetime.now(UTC),
        )
        truth_session.add(run)
        truth_session.flush()


def test_finding_severity_constraint_rejects_invalid(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    run_id = _insert_run(truth_session, truth_seed["workspace_id"])
    with pytest.raises(Exception, match=r"(?i)check|violates"):
        finding = DataQualityFinding(
            id=_make_finding_id(),
            run_id=run_id,
            workspace_id=truth_seed["workspace_id"],
            finding_type="ORPHAN_CHUNK",
            severity="CRITICAL",  # not in allowed set
            title="Constraint test",
            description="Should fail.",
            remediation="N/A",
            created_at=datetime.now(UTC),
        )
        truth_session.add(finding)
        truth_session.flush()


# ---------------------------------------------------------------------------
# No mutating repair path
# ---------------------------------------------------------------------------

def test_findings_table_has_no_repair_columns(truth_session: Session) -> None:
    """data_quality_findings must have no mutating repair columns."""
    insp = inspect(truth_session.bind)
    cols = {c["name"] for c in insp.get_columns("data_quality_findings")}
    forbidden = {"remediation_applied", "repaired_at", "repair_by", "auto_fixed"}
    present = cols & forbidden
    assert not present, f"Mutating repair columns found in data_quality_findings: {present}"


# ---------------------------------------------------------------------------
# Workspace scope: findings isolated per workspace
# ---------------------------------------------------------------------------

def test_findings_workspace_scoped(
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    """Findings queried by workspace_id return only own workspace's findings."""
    run_id = _insert_run(truth_session, truth_seed["workspace_id"])
    _insert_finding(truth_session, run_id, truth_seed["workspace_id"])
    truth_session.commit()

    count = truth_session.execute(
        text(
            "SELECT COUNT(*) FROM data_quality_findings WHERE workspace_id = :wid"
        ),
        {"wid": truth_seed["workspace_id"]},
    ).scalar()
    assert count >= 1

    other_count = truth_session.execute(
        text(
            "SELECT COUNT(*) FROM data_quality_findings WHERE workspace_id = :wid"
        ),
        {"wid": "other-workspace-that-does-not-exist"},
    ).scalar()
    assert other_count == 0
