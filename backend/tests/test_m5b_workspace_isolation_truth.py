"""M5b Workspace Isolation Truth Tests.

Verifies that drift detection is strictly workspace-scoped:
- Workspace A findings contain only WS-A entities
- Workspace B findings contain only WS-B entities
- No cross-workspace leakage in findings or snapshots

Runs against in-memory SQLite -- no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

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
WS_A = "ws-isolation-a"
WS_B = "ws-isolation-b"
OWNER = "user-iso-001"


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
        s.add(Workspace(id=WS_A, name="WS-A", is_default=True, created_at=datetime.now(UTC)))
        s.add(Workspace(id=WS_B, name="WS-B", is_default=False, created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _make_doc(session, workspace_id, lifecycle_status="active",
              import_status="chunked", is_searchable=True, meta=None):
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        owner_user_id=OWNER,
        current_version_id=None,
        title=f"Doc-{workspace_id[:6]}",
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
        normalized_markdown="# Content",
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


def _run(session, workspace_id):
    eng = DriftRunEngine(session, workspace_id)
    eng.register(DocumentDriftDetector())
    eng.register(MetadataDriftDetector())
    eng.register(LifecycleDriftDetector())
    return eng.run()


def _findings_for_run(session, run_id):
    return session.execute(
        select(DriftFinding).where(DriftFinding.run_id == run_id)
    ).scalars().all()


def _run_record(session, run_id):
    return session.get(DriftRun, run_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWorkspaceASeesOnlyA:
    def test_findings_workspace_id_all_a(self, session):
        # WS-A: active doc with lifecycle drift (no searchable chunk)
        doc_a, ver_a, chunk_a = _make_doc(session, WS_A, is_searchable=False)
        # WS-B: clean doc (should produce no findings from WS-A run)
        _make_doc(session, WS_B)
        session.commit()

        result = _run(session, WS_A)
        session.commit()

        findings = _findings_for_run(session, result.run_id)
        assert len(findings) > 0, "Expected findings for WS-A"
        for f in findings:
            assert f.workspace_id == WS_A, (
                f"Finding workspace_id={f.workspace_id!r} must be {WS_A!r}"
            )

    def test_a_run_does_not_include_b_entities(self, session):
        _make_doc(session, WS_A)
        doc_b, _, _ = _make_doc(session, WS_B, is_searchable=False)
        session.commit()

        result = _run(session, WS_A)
        session.commit()

        findings = _findings_for_run(session, result.run_id)
        b_entity_ids = {f.entity_id for f in findings if f.entity_id == doc_b.id}
        assert len(b_entity_ids) == 0, "WS-A run must not reference WS-B document ids"


class TestWorkspaceBSeesOnlyB:
    def test_findings_workspace_id_all_b(self, session):
        _make_doc(session, WS_A)
        # WS-B: archived doc with searchable chunk → lifecycle drift
        doc_b, ver_b, chunk_b = _make_doc(session, WS_B, lifecycle_status="archived",
                                           is_searchable=True)
        session.commit()

        result = _run(session, WS_B)
        session.commit()

        findings = _findings_for_run(session, result.run_id)
        assert len(findings) > 0, "Expected findings for WS-B"
        for f in findings:
            assert f.workspace_id == WS_B

    def test_b_run_does_not_include_a_entities(self, session):
        doc_a, _, chunk_a = _make_doc(session, WS_A, is_searchable=False)
        _make_doc(session, WS_B)
        session.commit()

        result = _run(session, WS_B)
        session.commit()

        findings = _findings_for_run(session, result.run_id)
        a_entity_ids = {f.entity_id for f in findings if f.entity_id == doc_a.id}
        assert len(a_entity_ids) == 0


class TestFindingsHaveCorrectWorkspaceId:
    def test_run_record_workspace_id_matches(self, session):
        _make_doc(session, WS_A)
        session.commit()
        result = _run(session, WS_A)
        session.commit()
        run = _run_record(session, result.run_id)
        assert run.workspace_id == WS_A

    def test_findings_workspace_id_matches_run_workspace(self, session):
        _make_doc(session, WS_B, is_searchable=False)
        session.commit()
        result = _run(session, WS_B)
        session.commit()
        findings = _findings_for_run(session, result.run_id)
        run = _run_record(session, result.run_id)
        for f in findings:
            assert f.workspace_id == run.workspace_id

    def test_snapshot_workspace_id_matches_run(self, session):
        _make_doc(session, WS_A)
        session.commit()
        result = _run(session, WS_A)
        session.commit()
        snaps = session.execute(
            select(DriftSnapshot).where(DriftSnapshot.run_id == result.run_id)
        ).scalars().all()
        assert len(snaps) >= 1
        for snap in snaps:
            assert snap.workspace_id == WS_A


class TestCrossWorkspaceNoLeakage:
    def test_parallel_runs_no_cross_contamination(self, session):
        """Both workspaces run independently; findings do not overlap."""
        _make_doc(session, WS_A, is_searchable=False)
        _make_doc(session, WS_B, lifecycle_status="archived", is_searchable=True)
        session.commit()

        result_a = _run(session, WS_A)
        session.commit()
        result_b = _run(session, WS_B)
        session.commit()

        findings_a = _findings_for_run(session, result_a.run_id)
        findings_b = _findings_for_run(session, result_b.run_id)

        ids_a = {f.workspace_id for f in findings_a}
        ids_b = {f.workspace_id for f in findings_b}

        assert ids_a == {WS_A}, f"WS-A findings contain: {ids_a}"
        assert ids_b == {WS_B}, f"WS-B findings contain: {ids_b}"

    def test_empty_workspace_produces_no_findings(self, session):
        # WS_A has docs, WS_B is empty
        _make_doc(session, WS_A, is_searchable=False)
        session.commit()

        result_b = _run(session, WS_B)
        session.commit()

        findings = _findings_for_run(session, result_b.run_id)
        assert findings == [], "Empty workspace must produce zero findings"
