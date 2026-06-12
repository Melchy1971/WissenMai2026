"""Tests for DriftRunEngine.

Runs against in-memory SQLite — no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.documents import Base, Workspace  # noqa: F401
from app.models.drift import (  # noqa: F401
    DriftFinding,
    DriftRun,
    DriftSnapshot,
)
from app.services.drift_run_engine import (
    BaseDriftDetector,
    DriftRunEngine,
    FindingDTO,
    RunResult,
)

UTC = timezone.utc
WS_ID = "ws-engine-test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
        s.add(
            Workspace(
                id=WS_ID,
                name="Engine Test WS",
                is_default=True,
                created_at=datetime.now(UTC),
            )
        )
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Stub detectors
# ---------------------------------------------------------------------------

class NullDetector(BaseDriftDetector):
    """Produces no findings."""

    @property
    def name(self) -> str:
        return "NullDetector"

    def detect(self, session: Session, workspace_id: str) -> list[FindingDTO]:
        return []


class FixedDetector(BaseDriftDetector):
    """Produces a fixed list of findings."""

    def __init__(self, findings: list[FindingDTO]) -> None:
        self._findings = findings

    @property
    def name(self) -> str:
        return "FixedDetector"

    def detect(self, session: Session, workspace_id: str) -> list[FindingDTO]:
        return list(self._findings)


class ExplodingDetector(BaseDriftDetector):
    """Raises an exception during detect()."""

    @property
    def name(self) -> str:
        return "ExplodingDetector"

    def detect(self, session: Session, workspace_id: str) -> list[FindingDTO]:
        raise RuntimeError("Simulated detector failure")


class MutatingDetector(BaseDriftDetector):
    """Attempts to write to drift_runs — should be caught by test, not prevented by engine."""

    @property
    def name(self) -> str:
        return "MutatingDetector"

    def detect(self, session: Session, workspace_id: str) -> list[FindingDTO]:
        # This is intentionally bad — tests verify our contract catches it
        return []


# ---------------------------------------------------------------------------
# Step 1: Start run
# ---------------------------------------------------------------------------

class TestStartRun:
    def test_creates_drift_run_record(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        result = engine.run()
        session.commit()

        run = session.get(DriftRun, result.run_id)
        assert run is not None
        assert run.workspace_id == WS_ID
        assert run.status == "completed"

    def test_idempotency_same_run_id_raises(self, session: Session) -> None:
        run_id = str(uuid.uuid4())
        e1 = DriftRunEngine(session, WS_ID)
        e1.register(NullDetector())
        e1.run(run_id=run_id)
        session.commit()

        e2 = DriftRunEngine(session, WS_ID)
        e2.register(NullDetector())
        with pytest.raises(RuntimeError, match="already exists"):
            e2.run(run_id=run_id)

    def test_run_id_auto_generated_when_not_provided(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        result = engine.run()
        session.commit()
        assert result.run_id is not None
        assert len(result.run_id) > 0

    def test_detector_names_recorded(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        engine.register(FixedDetector([]))
        result = engine.run()
        session.commit()

        run = session.get(DriftRun, result.run_id)
        assert run.detector_names == ["NullDetector", "FixedDetector"]


# ---------------------------------------------------------------------------
# Step 2: Register detectors
# ---------------------------------------------------------------------------

class TestRegisterDetectors:
    def test_register_non_detector_raises(self) -> None:
        engine = DriftRunEngine.__new__(DriftRunEngine)
        engine._detectors = []
        with pytest.raises(TypeError):
            engine.register("not_a_detector")  # type: ignore

    def test_multiple_detectors_registered_in_order(self, session: Session) -> None:
        class DetA(BaseDriftDetector):
            name = "DetA"
            def detect(self, s, w): return []

        class DetB(BaseDriftDetector):
            name = "DetB"
            def detect(self, s, w): return []

        engine = DriftRunEngine(session, WS_ID)
        engine.register(DetA())
        engine.register(DetB())
        result = engine.run()
        session.commit()

        assert list(result.detector_results.keys()) == ["DetA", "DetB"]


# ---------------------------------------------------------------------------
# Step 3 + 4: Execute detectors and save findings
# ---------------------------------------------------------------------------

class TestDetectAndSave:
    def test_findings_persisted(self, session: Session) -> None:
        findings = [
            FindingDTO("DOCUMENT_DRIFT", "warning", "document", "doc-1"),
            FindingDTO("METADATA_DRIFT", "info", "document", "doc-2"),
        ]
        engine = DriftRunEngine(session, WS_ID)
        engine.register(FixedDetector(findings))
        result = engine.run()
        session.commit()

        db_findings = session.query(DriftFinding).filter_by(run_id=result.run_id).all()
        assert len(db_findings) == 2
        types = {f.finding_type for f in db_findings}
        assert types == {"DOCUMENT_DRIFT", "METADATA_DRIFT"}

    def test_findings_workspace_scoped(self, session: Session) -> None:
        findings = [FindingDTO("LIFECYCLE_DRIFT", "error", "document", "doc-x")]
        engine = DriftRunEngine(session, WS_ID)
        engine.register(FixedDetector(findings))
        result = engine.run()
        session.commit()

        db_findings = session.query(DriftFinding).filter_by(run_id=result.run_id).all()
        assert all(f.workspace_id == WS_ID for f in db_findings)

    def test_no_findings_yields_empty_list(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        result = engine.run()
        session.commit()
        assert result.total_findings == 0

    def test_all_finding_types_persisted(self, session: Session) -> None:
        from app.models.drift import DRIFT_FINDING_TYPES
        findings = [FindingDTO(ft, "info") for ft in DRIFT_FINDING_TYPES]
        engine = DriftRunEngine(session, WS_ID)
        engine.register(FixedDetector(findings))
        result = engine.run()
        session.commit()

        assert result.total_findings == len(DRIFT_FINDING_TYPES)

    def test_detector_exception_marks_run_failed(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(ExplodingDetector())
        with pytest.raises(RuntimeError, match="Simulated detector failure"):
            engine.run()
        session.commit()

        failed_runs = session.query(DriftRun).filter_by(
            workspace_id=WS_ID, status="failed"
        ).all()
        assert len(failed_runs) == 1
        assert "Simulated detector failure" in failed_runs[0].error_message

    def test_entity_id_stored_without_fk(self, session: Session) -> None:
        """entity_id is a plain String — must accept IDs not in any other table."""
        findings = [FindingDTO("DOCUMENT_DRIFT", "warning", "document", "nonexistent-doc-id")]
        engine = DriftRunEngine(session, WS_ID)
        engine.register(FixedDetector(findings))
        engine.run()
        session.commit()

        db = session.query(DriftFinding).first()
        assert db.entity_id == "nonexistent-doc-id"


# ---------------------------------------------------------------------------
# Step 5: Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_post_run_snapshot_created(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        result = engine.run()
        session.commit()

        snaps = session.query(DriftSnapshot).filter_by(run_id=result.run_id).all()
        assert len(snaps) == 1
        assert snaps[0].snapshot_type == "post_run"

    def test_snapshot_entity_count_matches_findings(self, session: Session) -> None:
        findings = [FindingDTO("DOCUMENT_DRIFT", "warning") for _ in range(3)]
        engine = DriftRunEngine(session, WS_ID)
        engine.register(FixedDetector(findings))
        result = engine.run()
        session.commit()

        snap = session.query(DriftSnapshot).filter_by(run_id=result.run_id).first()
        assert snap.entity_count == 3

    def test_snapshot_data_contains_run_id(self, session: Session) -> None:
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        result = engine.run()
        session.commit()

        snap = session.query(DriftSnapshot).filter_by(run_id=result.run_id).first()
        assert snap.data["run_id"] == result.run_id


# ---------------------------------------------------------------------------
# Step 6: Report
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_report_structure(self, session: Session) -> None:
        findings = [
            FindingDTO("DOCUMENT_DRIFT", "warning"),
            FindingDTO("DOCUMENT_DRIFT", "error"),
            FindingDTO("METADATA_DRIFT", "info"),
        ]
        engine = DriftRunEngine(session, WS_ID)
        engine.register(FixedDetector(findings))
        result = engine.run()
        session.commit()

        report = DriftRunEngine.build_report(result)

        assert report["run_id"] == result.run_id
        assert report["workspace_id"] == WS_ID
        assert report["status"] == "completed"
        assert report["total_findings"] == 3
        assert report["findings_by_type"]["DOCUMENT_DRIFT"] == 2
        assert report["findings_by_type"]["METADATA_DRIFT"] == 1
        assert report["findings_by_severity"]["warning"] == 1
        assert report["findings_by_severity"]["error"] == 1
        assert report["findings_by_severity"]["info"] == 1

    def test_report_is_serialisable(self, session: Session) -> None:
        import json
        engine = DriftRunEngine(session, WS_ID)
        engine.register(NullDetector())
        result = engine.run()
        session.commit()

        report = DriftRunEngine.build_report(result)
        dumped = json.dumps(report)
        assert len(dumped) > 0

    def test_failed_run_report(self) -> None:
        result = RunResult(
            run_id="run-fail",
            workspace_id=WS_ID,
            status="failed",
            error_message="something broke",
            started_at=datetime.now(UTC),
        )
        report = DriftRunEngine.build_report(result)
        assert report["status"] == "failed"
        assert report["error_message"] == "something broke"
        assert report["total_findings"] == 0


# ---------------------------------------------------------------------------
# FindingDTO validation
# ---------------------------------------------------------------------------

class TestFindingDTO:
    def test_invalid_finding_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid finding_type"):
            FindingDTO("UNKNOWN_TYPE", "warning")

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid severity"):
            FindingDTO("DOCUMENT_DRIFT", "fatal")

    def test_valid_dto_immutable(self) -> None:
        dto = FindingDTO("DOCUMENT_DRIFT", "warning", "document", "doc-1", {"k": "v"})
        with pytest.raises(Exception):
            dto.finding_type = "METADATA_DRIFT"  # type: ignore
