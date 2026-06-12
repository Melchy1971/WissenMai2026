"""M5b Drift Runner Idempotency Tests.

Verifies that two drift runs on the same workspace with unchanged data
produce logically equivalent findings, no duplicate active findings
within a run, and reproducible snapshots.

Runs against in-memory SQLite -- no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from collections import Counter

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.models.documents import (
    Base,
    Chunk,
    Document,
    DocumentVersion,
    Workspace,
)
from app.models.drift import DriftFinding, DriftRun, DriftSnapshot
from app.services.drift.document_drift_detector import DocumentDriftDetector
from app.services.drift.lifecycle_drift_detector import LifecycleDriftDetector
from app.services.drift.metadata_drift_detector import MetadataDriftDetector
from app.services.drift_run_engine import DriftRunEngine

UTC = timezone.utc
WS_ID = "ws-idempotency"
OWNER = "user-idem-001"


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
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_ID, name="Idempotency WS", is_default=True,
                        created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _make_doc(session, lifecycle_status="active", import_status="chunked",
              is_searchable=True, meta=None):
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=WS_ID,
        owner_user_id=OWNER,
        current_version_id=None,
        title="Doc",
        source_type="upload",
        content_hash=str(uuid.uuid4()),
        import_status=import_status,
        lifecycle_status=lifecycle_status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()
    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        normalized_markdown="# Title",
        markdown_hash=str(uuid.uuid4()),
        parser_version="1.0",
        ocr_used=False,
        metadata_=meta or {"category": "tech", "summary": "ok", "title": "Doc"},
        created_at=datetime.now(UTC),
    )
    session.add(ver)
    session.flush()
    doc.current_version_id = ver.id
    chunk = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        document_version_id=ver.id,
        chunk_index=0,
        heading_path=[],
        anchor="c0",
        content="content",
        content_hash=str(uuid.uuid4()),
        is_searchable=is_searchable,
        metadata_={},
        created_at=datetime.now(UTC),
    )
    session.add(chunk)
    session.flush()
    return doc, ver, chunk


def _run(session):
    eng = DriftRunEngine(session, WS_ID)
    eng.register(DocumentDriftDetector())
    eng.register(MetadataDriftDetector())
    eng.register(LifecycleDriftDetector())
    return eng.run()


def _findings_for_run(session, run_id):
    return session.execute(
        select(DriftFinding).where(DriftFinding.run_id == run_id)
    ).scalars().all()


def _finding_signature(f):
    """Logical key for a finding: type + severity + entity_id (ignoring UUID/timestamp)."""
    return (f.finding_type, f.severity, f.entity_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTwoRunsSameDataLogicallyIdentical:
    def test_finding_types_match_across_runs(self, session):
        _make_doc(session, is_searchable=False)  # → LIFECYCLE_DRIFT
        session.commit()

        r1 = _run(session)
        session.commit()
        r2 = _run(session)
        session.commit()

        f1 = Counter(f.finding_type for f in _findings_for_run(session, r1.run_id))
        f2 = Counter(f.finding_type for f in _findings_for_run(session, r2.run_id))
        assert f1 == f2, f"Run 1 types: {f1} vs Run 2 types: {f2}"

    def test_finding_count_matches_across_runs(self, session):
        _make_doc(session, is_searchable=False)
        _make_doc(session, lifecycle_status="archived", is_searchable=True)
        session.commit()

        r1 = _run(session)
        session.commit()
        r2 = _run(session)
        session.commit()

        assert r1.total_findings == r2.total_findings, (
            f"Run 1 findings={r1.total_findings}, Run 2 findings={r2.total_findings}"
        )

    def test_finding_severity_distribution_matches(self, session):
        _make_doc(session, lifecycle_status="deleted", is_searchable=True)  # critical
        _make_doc(session, is_searchable=False)  # error
        session.commit()

        r1 = _run(session)
        session.commit()
        r2 = _run(session)
        session.commit()

        sev1 = Counter(f.severity for f in _findings_for_run(session, r1.run_id))
        sev2 = Counter(f.severity for f in _findings_for_run(session, r2.run_id))
        assert sev1 == sev2, f"Severity distribution changed: {sev1} vs {sev2}"

    def test_entity_ids_match_across_runs(self, session):
        doc, _, _ = _make_doc(session, is_searchable=False)
        session.commit()

        r1 = _run(session)
        session.commit()
        r2 = _run(session)
        session.commit()

        entities1 = {f.entity_id for f in _findings_for_run(session, r1.run_id)}
        entities2 = {f.entity_id for f in _findings_for_run(session, r2.run_id)}
        assert entities1 == entities2


class TestNoDuplicateActiveFindings:
    def test_no_duplicate_type_entity_within_run(self, session):
        _make_doc(session, is_searchable=False)
        session.commit()

        result = _run(session)
        session.commit()

        findings = _findings_for_run(session, result.run_id)
        signatures = [_finding_signature(f) for f in findings]
        counter = Counter(signatures)
        duplicates = {sig: cnt for sig, cnt in counter.items() if cnt > 1}
        assert not duplicates, f"Duplicate findings within run: {duplicates}"

    def test_multiple_drift_types_no_cross_duplicates(self, session):
        _make_doc(session, lifecycle_status="archived", is_searchable=True)
        _make_doc(session, is_searchable=False)
        session.commit()

        result = _run(session)
        session.commit()

        findings = _findings_for_run(session, result.run_id)
        signatures = [_finding_signature(f) for f in findings]
        counter = Counter(signatures)
        duplicates = {sig: cnt for sig, cnt in counter.items() if cnt > 1}
        assert not duplicates, f"Duplicate findings: {duplicates}"


class TestSnapshotsReproducible:
    def test_snapshot_entity_count_stable(self, session):
        _make_doc(session, is_searchable=False)
        session.commit()

        r1 = _run(session)
        session.commit()
        r2 = _run(session)
        session.commit()

        snap1 = session.execute(
            select(DriftSnapshot).where(DriftSnapshot.run_id == r1.run_id)
        ).scalars().first()
        snap2 = session.execute(
            select(DriftSnapshot).where(DriftSnapshot.run_id == r2.run_id)
        ).scalars().first()

        assert snap1 is not None
        assert snap2 is not None
        assert snap1.entity_count == snap2.entity_count, (
            f"Snapshot entity_count changed: {snap1.entity_count} vs {snap2.entity_count}"
        )

    def test_snapshot_type_is_post_run(self, session):
        _make_doc(session)
        session.commit()

        result = _run(session)
        session.commit()

        snaps = session.execute(
            select(DriftSnapshot).where(DriftSnapshot.run_id == result.run_id)
        ).scalars().all()
        assert len(snaps) >= 1
        for snap in snaps:
            assert snap.snapshot_type == "post_run"


class TestRunIdIdempotency:
    def test_same_run_id_raises_runtime_error(self, session):
        _make_doc(session)
        session.commit()

        fixed_run_id = str(uuid.uuid4())
        eng1 = DriftRunEngine(session, WS_ID)
        eng1.register(DocumentDriftDetector())
        eng1.run(run_id=fixed_run_id)
        session.commit()

        eng2 = DriftRunEngine(session, WS_ID)
        eng2.register(DocumentDriftDetector())
        with pytest.raises(RuntimeError, match=fixed_run_id):
            eng2.run(run_id=fixed_run_id)
