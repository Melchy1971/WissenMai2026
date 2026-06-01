"""Unit tests for DataQualityRunner — no database required.

Tests run against in-memory SQLite via the standard test fixtures.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.models.documents import Base
from app.services.data_quality_runner import (
    DataQualityRunner,
    EmptyChunkDetector,
    InvalidLifecycleDetector,
    MissingMetadataDetector,
    OrphanChunkDetector,
    RunResult,
    _calculate_score,
)


# ---------------------------------------------------------------------------
# In-memory SQLite fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    from app.models.data_quality import DataQualityFinding, DataQualityRun  # noqa: F401
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Enable FK enforcement on SQLite
    @event.listens_for(eng, "connect")
    def _fk_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


def _workspace_id() -> str:
    return str(uuid.uuid4())


def _seed_workspace(session: Session, workspace_id: str) -> None:
    from app.models.documents import Workspace
    session.add(Workspace(
        id=workspace_id,
        name="test-ws",
        is_default=False,
        created_at=datetime.now(UTC),
    ))
    session.flush()


# ---------------------------------------------------------------------------
# _calculate_score
# ---------------------------------------------------------------------------

class TestCalculateScore:
    def test_no_findings_returns_100(self):
        assert _calculate_score([]) == 100.0

    def test_error_findings_reduce_score(self):
        findings = [
            {"finding_type": "INVALID_LIFECYCLE", "severity": "error"},
            {"finding_type": "ORPHAN_CHUNK", "severity": "error"},
        ]
        score = _calculate_score(findings)
        assert 0.0 <= score < 100.0

    def test_warning_penalises_less_than_error(self):
        error_score = _calculate_score([{"finding_type": "INVALID_LIFECYCLE", "severity": "error"}])
        warn_score = _calculate_score([{"finding_type": "INVALID_LIFECYCLE", "severity": "warning"}])
        assert warn_score > error_score

    def test_score_never_below_zero(self):
        findings = [{"finding_type": "INVALID_LIFECYCLE", "severity": "error"}] * 100
        assert _calculate_score(findings) >= 0.0

    def test_score_never_above_100(self):
        assert _calculate_score([]) <= 100.0


# ---------------------------------------------------------------------------
# Skeleton detectors — return empty (no DB data)
# ---------------------------------------------------------------------------

class TestSkeletonDetectors:
    def test_orphan_chunk_detector_returns_list(self, session, engine):
        wid = _workspace_id()
        _seed_workspace(session, wid)
        d = OrphanChunkDetector(session, wid)
        result = d.detect()
        assert isinstance(result, list)

    def test_empty_chunk_detector_returns_list(self, session):
        d = EmptyChunkDetector(session, _workspace_id())
        assert isinstance(d.detect(), list)

    def test_invalid_lifecycle_detector_empty_db(self, session, engine):
        wid = _workspace_id()
        _seed_workspace(session, wid)
        d = InvalidLifecycleDetector(session, wid)
        assert d.detect() == []

    def test_missing_metadata_detector_empty_db(self, session, engine):
        wid = _workspace_id()
        _seed_workspace(session, wid)
        d = MissingMetadataDetector(session, wid)
        assert d.detect() == []

    def test_invalid_lifecycle_finding_shape(self, session, engine):
        """Detector returns correctly shaped dicts when violations exist."""
        from app.models.documents import Document
        wid = _workspace_id()
        _seed_workspace(session, wid)
        session.add(Document(
            id=str(uuid.uuid4()),
            workspace_id=wid,
            owner_user_id="u1",
            title="doc",
            source_type="upload",
            content_hash="abc",
            import_status="parsed",
            lifecycle_status="INVALID",  # violates constraint in Postgres; SQLite ignores CHECK
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        session.flush()
        d = InvalidLifecycleDetector(session, wid)
        findings = d.detect()
        for f in findings:
            assert "finding_type" in f
            assert "severity" in f
            assert "title" in f
            assert "description" in f
            assert "remediation" in f
            # No automated repair field
            assert "remediation_applied" not in f


# ---------------------------------------------------------------------------
# DataQualityRunner — run lifecycle
# ---------------------------------------------------------------------------

class TestDataQualityRunnerLifecycle:
    def test_run_creates_completed_run(self, session, engine):
        wid = _workspace_id()
        _seed_workspace(session, wid)
        runner = DataQualityRunner.from_session(session, wid)
        result = runner.run()
        assert isinstance(result, RunResult)
        assert result.status == "completed"
        assert result.workspace_id == wid
        assert result.total_findings >= 0
        assert 0.0 <= result.quality_score <= 100.0
        assert result.finished_at > result.started_at

    def test_run_persists_to_db(self, session, engine):
        wid = _workspace_id()
        _seed_workspace(session, wid)
        runner = DataQualityRunner.from_session(session, wid)
        result = runner.run()
        session.commit()
        stored = session.get(DataQualityRun, result.run_id)
        assert stored is not None
        assert stored.status == "completed"
        assert stored.workspace_id == wid

    def test_run_idempotent_completed(self, session, engine):
        """Re-running with same run_id returns stored result, does not re-execute."""
        wid = _workspace_id()
        _seed_workspace(session, wid)
        run_id = str(uuid.uuid4())
        runner = DataQualityRunner.from_session(session, wid)
        r1 = runner.run(run_id=run_id)
        session.commit()
        r2 = runner.run(run_id=run_id)
        assert r2.run_id == r1.run_id
        assert r2.status == r1.status

    def test_run_idempotent_failed(self, session, engine):
        """Re-running with run_id of a failed run returns stored result."""
        wid = _workspace_id()
        _seed_workspace(session, wid)
        run_id = str(uuid.uuid4())
        # Manually insert a failed run
        run = DataQualityRun(
            id=run_id,
            workspace_id=wid,
            status="failed",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            total_findings=0,
            quality_score=0.0,
        )
        session.add(run)
        session.commit()
        runner = DataQualityRunner.from_session(session, wid)
        result = runner.run(run_id=run_id)
        assert result.status == "failed"

    def test_run_raises_if_already_running(self, session, engine):
        """run_id already in 'running' state → ValueError."""
        wid = _workspace_id()
        _seed_workspace(session, wid)
        run_id = str(uuid.uuid4())
        run = DataQualityRun(
            id=run_id,
            workspace_id=wid,
            status="running",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        session.commit()
        runner = DataQualityRunner.from_session(session, wid)
        with pytest.raises(ValueError, match="running"):
            runner.run(run_id=run_id)

    def test_run_sets_failed_on_detector_error(self, session, engine):
        """If any detector raises, the run is marked failed."""
        wid = _workspace_id()
        _seed_workspace(session, wid)
        runner = DataQualityRunner.from_session(session, wid)
        run_id = str(uuid.uuid4())
        with patch.object(
            InvalidLifecycleDetector, "detect", side_effect=RuntimeError("db error")
        ):
            with pytest.raises(RuntimeError):
                runner.run(run_id=run_id)
        session.commit()
        stored = session.get(DataQualityRun, run_id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.finished_at is not None

    def test_run_does_not_mutate_documents(self, session, engine):
        """Running the runner must not modify any row in the documents table."""
        from app.models.documents import Document
        wid = _workspace_id()
        _seed_workspace(session, wid)
        doc_id = str(uuid.uuid4())
        session.add(Document(
            id=doc_id,
            workspace_id=wid,
            owner_user_id="u1",
            title="untouched",
            source_type="upload",
            content_hash="xyz",
            import_status="parsed",
            lifecycle_status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ))
        session.commit()
        before = session.get(Document, doc_id)
        before_updated = before.updated_at

        runner = DataQualityRunner.from_session(session, wid)
        runner.run()
        session.commit()

        after = session.get(Document, doc_id)
        assert after.updated_at == before_updated
        assert after.title == "untouched"
        assert after.lifecycle_status == "active"

    def test_run_workspace_scoped(self, session, engine):
        """Runs and findings for workspace A must not appear under workspace B."""
        wid_a = _workspace_id()
        wid_b = _workspace_id()
        _seed_workspace(session, wid_a)
        _seed_workspace(session, wid_b)
        runner_a = DataQualityRunner.from_session(session, wid_a)
        result_a = runner_a.run()
        session.commit()

        # wid_b should have no runs
        from sqlalchemy import select as sa_select
        count = session.scalar(
            sa_select(DataQualityRun)
            .where(DataQualityRun.workspace_id == wid_b)
        )
        assert count is None

    def test_run_result_has_required_fields(self, session, engine):
        wid = _workspace_id()
        _seed_workspace(session, wid)
        result = DataQualityRunner.from_session(session, wid).run()
        assert result.run_id
        assert result.workspace_id == wid
        assert result.status in ("completed", "failed")
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.finished_at, datetime)
        assert isinstance(result.total_findings, int)
        assert isinstance(result.quality_score, float)
        assert isinstance(result.findings, list)
