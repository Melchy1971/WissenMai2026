"""Tests for Drift Persistence Layer (drift_runs, drift_findings, drift_snapshots).

Runs against in-memory SQLite — no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from app.models.documents import Base, Workspace  # noqa: F401 — registers Base
from app.models.drift import (  # noqa: F401 — registers Drift tables with Base
    DRIFT_FINDING_TYPES,
    DRIFT_RUN_STATUS_VALUES,
    DRIFT_SEVERITY_VALUES,
    DRIFT_SNAPSHOT_TYPES,
    DriftFinding,
    DriftRun,
    DriftSnapshot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WS_ID = "ws-test-001"


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _fk_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        # seed workspace so FKs resolve
        s.add(
            Workspace(
                id=WS_ID,
                name="Test Workspace",
                is_default=True,
                created_at=datetime.now(UTC),
            )
        )
        s.commit()
        yield s


def _run(workspace_id: str = WS_ID, status: str = "pending") -> DriftRun:
    now = datetime.now(UTC)
    return DriftRun(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        status=status,
        triggered_by="system",
        detector_names=["DocumentDriftDetector", "MetadataDriftDetector"],
        started_at=now,
        created_at=now,
        updated_at=now,
    )


def _finding(run: DriftRun, finding_type: str = "DOCUMENT_DRIFT", severity: str = "warning") -> DriftFinding:
    return DriftFinding(
        id=str(uuid.uuid4()),
        run_id=run.id,
        workspace_id=run.workspace_id,
        finding_type=finding_type,
        severity=severity,
        entity_type="document",
        entity_id=str(uuid.uuid4()),
        detail={"reason": "test finding"},
        created_at=datetime.now(UTC),
    )


def _snapshot(run: DriftRun, snapshot_type: str = "pre_run") -> DriftSnapshot:
    return DriftSnapshot(
        id=str(uuid.uuid4()),
        run_id=run.id,
        workspace_id=run.workspace_id,
        snapshot_type=snapshot_type,
        entity_count=42,
        data={"document_count": 42, "version_count": 10},
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# drift_runs
# ---------------------------------------------------------------------------

class TestDriftRun:
    def test_create_and_retrieve(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.commit()

        loaded = session.get(DriftRun, run.id)
        assert loaded is not None
        assert loaded.workspace_id == WS_ID
        assert loaded.status == "pending"
        assert loaded.detector_names == ["DocumentDriftDetector", "MetadataDriftDetector"]

    def test_workspace_scoped(self, session: Session) -> None:
        """workspace_id must be present on every run."""
        run = _run()
        session.add(run)
        session.commit()
        loaded = session.get(DriftRun, run.id)
        assert loaded.workspace_id == WS_ID

    def test_audit_fields_present(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.commit()
        loaded = session.get(DriftRun, run.id)
        assert loaded.created_at is not None
        assert loaded.updated_at is not None

    def test_status_transitions(self, session: Session) -> None:
        run = _run(status="pending")
        session.add(run)
        session.commit()

        run.status = "running"
        run.updated_at = datetime.now(UTC)
        session.commit()

        loaded = session.get(DriftRun, run.id)
        assert loaded.status == "running"

    def test_all_valid_statuses(self, session: Session) -> None:
        for status in DRIFT_RUN_STATUS_VALUES:
            run = _run(status=status)
            session.add(run)
        session.commit()

    def test_cascade_delete_removes_findings_and_snapshots(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        finding = _finding(run)
        snap = _snapshot(run)
        session.add_all([finding, snap])
        session.commit()

        finding_id = finding.id
        snap_id = snap.id

        session.delete(run)
        session.commit()

        assert session.get(DriftFinding, finding_id) is None
        assert session.get(DriftSnapshot, snap_id) is None

    def test_workspace_fk_enforced(self, session: Session) -> None:
        """FK violation: workspace does not exist."""
        run = _run(workspace_id="nonexistent-ws")
        session.add(run)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()


# ---------------------------------------------------------------------------
# drift_findings
# ---------------------------------------------------------------------------

class TestDriftFinding:
    def test_create_and_retrieve(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        finding = _finding(run)
        session.add(finding)
        session.commit()

        loaded = session.get(DriftFinding, finding.id)
        assert loaded is not None
        assert loaded.finding_type == "DOCUMENT_DRIFT"
        assert loaded.severity == "warning"
        assert loaded.detail == {"reason": "test finding"}

    def test_all_finding_types_accepted(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        for ft in DRIFT_FINDING_TYPES:
            session.add(_finding(run, finding_type=ft))
        session.commit()

    def test_all_severity_levels_accepted(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        for sev in DRIFT_SEVERITY_VALUES:
            session.add(_finding(run, severity=sev))
        session.commit()

    def test_no_mutation_of_non_drift_tables(self, session: Session) -> None:
        """Findings reference entity_id as a plain String — no writes to other tables."""
        run = _run()
        session.add(run)
        session.flush()

        finding = DriftFinding(
            id=str(uuid.uuid4()),
            run_id=run.id,
            workspace_id=run.workspace_id,
            finding_type="LIFECYCLE_DRIFT",
            severity="error",
            entity_type="document",
            entity_id="doc-that-may-not-exist",
            created_at=datetime.now(UTC),
        )
        session.add(finding)
        session.commit()  # must not raise: entity_id has no FK

        loaded = session.get(DriftFinding, finding.id)
        assert loaded.entity_id == "doc-that-may-not-exist"

    def test_workspace_scoped(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()
        finding = _finding(run)
        session.add(finding)
        session.commit()
        loaded = session.get(DriftFinding, finding.id)
        assert loaded.workspace_id == WS_ID

    def test_run_fk_enforced(self, session: Session) -> None:
        """FK violation: run does not exist."""
        orphan = DriftFinding(
            id=str(uuid.uuid4()),
            run_id="nonexistent-run",
            workspace_id=WS_ID,
            finding_type="DOCUMENT_DRIFT",
            severity="info",
            created_at=datetime.now(UTC),
        )
        session.add(orphan)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()


# ---------------------------------------------------------------------------
# drift_snapshots
# ---------------------------------------------------------------------------

class TestDriftSnapshot:
    def test_create_and_retrieve(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        snap = _snapshot(run, "pre_run")
        session.add(snap)
        session.commit()

        loaded = session.get(DriftSnapshot, snap.id)
        assert loaded is not None
        assert loaded.snapshot_type == "pre_run"
        assert loaded.entity_count == 42
        assert loaded.data["document_count"] == 42

    def test_all_snapshot_types_accepted(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        for st in DRIFT_SNAPSHOT_TYPES:
            session.add(_snapshot(run, snapshot_type=st))
        session.commit()

    def test_pre_run_and_post_run_per_run(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()

        pre = _snapshot(run, "pre_run")
        post = _snapshot(run, "post_run")
        session.add_all([pre, post])
        session.commit()

        snaps = session.query(DriftSnapshot).filter_by(run_id=run.id).all()
        types = {s.snapshot_type for s in snaps}
        assert types == {"pre_run", "post_run"}

    def test_workspace_scoped(self, session: Session) -> None:
        run = _run()
        session.add(run)
        session.flush()
        snap = _snapshot(run)
        session.add(snap)
        session.commit()
        loaded = session.get(DriftSnapshot, snap.id)
        assert loaded.workspace_id == WS_ID

    def test_run_fk_enforced(self, session: Session) -> None:
        orphan = DriftSnapshot(
            id=str(uuid.uuid4()),
            run_id="nonexistent-run",
            workspace_id=WS_ID,
            snapshot_type="pre_run",
            created_at=datetime.now(UTC),
        )
        session.add(orphan)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()


# ---------------------------------------------------------------------------
# Cross-table invariants
# ---------------------------------------------------------------------------

class TestCrossTableInvariants:
    def test_full_run_lifecycle(self, session: Session) -> None:
        """Run -> pre_run snapshot -> findings -> post_run snapshot."""
        now = datetime.now(UTC)
        run = _run(status="pending")
        session.add(run)
        session.flush()

        pre = _snapshot(run, "pre_run")
        session.add(pre)
        session.flush()

        run.status = "running"
        run.updated_at = now

        findings = [_finding(run, ft) for ft in DRIFT_FINDING_TYPES]
        session.add_all(findings)
        session.flush()

        post = _snapshot(run, "post_run")
        post.entity_count = 42
        session.add(post)

        run.status = "completed"
        run.completed_at = now
        run.total_findings = len(DRIFT_FINDING_TYPES)
        run.updated_at = now
        session.commit()

        loaded = session.get(DriftRun, run.id)
        assert loaded.status == "completed"
        assert loaded.total_findings == len(DRIFT_FINDING_TYPES)
        assert len(loaded.findings) == len(DRIFT_FINDING_TYPES)
        assert len(loaded.snapshots) == 2

    def test_findings_isolated_to_workspace(self, session: Session) -> None:
        """Findings from one run must not bleed into query for another workspace."""
        # WS_ID run
        run_a = _run(workspace_id=WS_ID)
        session.add(run_a)

        # second workspace
        session.add(
            Workspace(id="ws-other", name="Other", is_default=False, created_at=datetime.now(UTC))
        )
        run_b = _run(workspace_id="ws-other")
        session.add(run_b)
        session.flush()

        session.add(_finding(run_a))
        session.add(_finding(run_b))
        session.commit()

        ws_a_findings = (
            session.query(DriftFinding).filter_by(workspace_id=WS_ID).all()
        )
        ws_b_findings = (
            session.query(DriftFinding).filter_by(workspace_id="ws-other").all()
        )
        assert len(ws_a_findings) == 1
        assert len(ws_b_findings) == 1
