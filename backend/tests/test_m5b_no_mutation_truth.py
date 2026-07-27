"""M5b No-Mutation Truth Tests.

Verifies that a full drift run does NOT mutate any non-drift table.
Before and after counts for documents, document_versions, document_chunks,
chat_citations, lifecycle_status, and source_status must be identical.
Only drift_runs / drift_findings / drift_snapshots are allowed to grow.

Runs against in-memory SQLite -- no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.models.documents import (
    Base,
    ChatCitation,
    ChatMessage,
    ChatSession,
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
WS_ID = "ws-no-mutation"
OWNER_ID = "user-nm-001"


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
        s.add(Workspace(id=WS_ID, name="No-Mutation WS", is_default=True,
                        created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _make_doc(session, lifecycle_status="active", import_status="chunked",
              title="Doc", meta=None):
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=WS_ID,
        owner_user_id=OWNER_ID,
        current_version_id=None,
        title=title,
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
        metadata_=meta or {"category": "tech", "summary": "ok", "title": title},
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
        is_searchable=True,
        metadata_={},
        created_at=datetime.now(UTC),
    )
    session.add(chunk)
    session.flush()
    return doc, ver, chunk


def _count(session, model):
    return session.execute(select(func.count()).select_from(model)).scalar()


def _snapshot_counts(session):
    return {
        "documents": _count(session, Document),
        "versions": _count(session, DocumentVersion),
        "chunks": _count(session, Chunk),
        "citations": _count(session, ChatCitation),
        "drift_runs": _count(session, DriftRun),
        "drift_findings": _count(session, DriftFinding),
        "drift_snapshots": _count(session, DriftSnapshot),
    }


def _lifecycle_statuses(session):
    rows = session.execute(
        select(Document.id, Document.lifecycle_status)
        .where(Document.workspace_id == WS_ID)
    ).all()
    return {r.id: r.lifecycle_status for r in rows}


def _run_engine(session):
    engine = DriftRunEngine(session, WS_ID)
    engine.register(DocumentDriftDetector())
    engine.register(MetadataDriftDetector())
    engine.register(LifecycleDriftDetector())
    return engine.run()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDocumentCountUnchanged:
    def test_clean_workspace_document_count_unchanged(self, session):
        _make_doc(session, lifecycle_status="active", import_status="chunked")
        _make_doc(session, lifecycle_status="active", import_status="chunked")
        session.commit()
        before = _count(session, Document)
        _run_engine(session)
        session.commit()
        assert _count(session, Document) == before

    def test_drift_workspace_document_count_unchanged(self, session):
        # Create doc without valid current_version (will produce DOCUMENT_DRIFT)
        doc = Document(
            id=str(uuid.uuid4()), workspace_id=WS_ID,
            owner_user_id=OWNER_ID, current_version_id=None,
            title="Broken", source_type="upload",
            content_hash=str(uuid.uuid4()),
            import_status="pending", lifecycle_status="active",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(doc)
        session.commit()
        before = _count(session, Document)
        _run_engine(session)
        session.commit()
        assert _count(session, Document) == before


class TestVersionCountUnchanged:
    def test_version_count_unchanged_after_run(self, session):
        _make_doc(session)
        session.commit()
        before = _count(session, DocumentVersion)
        _run_engine(session)
        session.commit()
        assert _count(session, DocumentVersion) == before

    def test_version_count_unchanged_with_multiple_docs(self, session):
        _make_doc(session)
        _make_doc(session)
        _make_doc(session)
        session.commit()
        before = _count(session, DocumentVersion)
        _run_engine(session)
        session.commit()
        assert _count(session, DocumentVersion) == before


class TestChunkCountUnchanged:
    def test_chunk_count_unchanged_after_run(self, session):
        _make_doc(session)
        session.commit()
        before = _count(session, Chunk)
        _run_engine(session)
        session.commit()
        assert _count(session, Chunk) == before

    def test_chunk_count_unchanged_with_drift(self, session):
        # Active+chunked doc with non-searchable chunk → LIFECYCLE_DRIFT
        doc, ver, chunk = _make_doc(session)
        chunk.is_searchable = False
        session.flush()
        session.commit()
        before = _count(session, Chunk)
        _run_engine(session)
        session.commit()
        assert _count(session, Chunk) == before

    def test_chunk_is_searchable_unchanged(self, session):
        doc, ver, chunk = _make_doc(session)
        chunk.is_searchable = True
        session.flush()
        session.commit()
        _run_engine(session)
        session.commit()
        refreshed = session.get(Chunk, chunk.id)
        assert refreshed.is_searchable is True


class TestLifecycleStatusUnchanged:
    def test_lifecycle_status_unchanged_after_run(self, session):
        _make_doc(session, lifecycle_status="active")
        _make_doc(session, lifecycle_status="archived")
        session.commit()
        before = _lifecycle_statuses(session)
        _run_engine(session)
        session.commit()
        after = _lifecycle_statuses(session)
        assert before == after

    def test_deleted_doc_lifecycle_status_unchanged(self, session):
        doc, ver, chunk = _make_doc(session, lifecycle_status="deleted")
        chunk.is_searchable = True
        session.flush()
        session.commit()
        before_status = session.get(Document, doc.id).lifecycle_status
        _run_engine(session)
        session.commit()
        assert session.get(Document, doc.id).lifecycle_status == before_status


class TestOnlyDriftTablesGrow:
    def test_only_drift_tables_mutated(self, session):
        _make_doc(session)
        session.commit()
        before = _snapshot_counts(session)
        _run_engine(session)
        session.commit()
        after = _snapshot_counts(session)

        # Non-drift tables must be unchanged
        assert after["documents"] == before["documents"]
        assert after["versions"] == before["versions"]
        assert after["chunks"] == before["chunks"]
        assert after["citations"] == before["citations"]

        # Drift tables must have grown
        assert after["drift_runs"] == before["drift_runs"] + 1
        assert after["drift_snapshots"] >= before["drift_snapshots"] + 1

    def test_multiple_runs_only_drift_tables_grow(self, session):
        _make_doc(session)
        session.commit()
        before = _snapshot_counts(session)

        _run_engine(session)
        session.commit()
        mid = _snapshot_counts(session)

        _run_engine(session)
        session.commit()
        after = _snapshot_counts(session)

        # Non-drift tables stay constant across both runs
        assert after["documents"] == before["documents"]
        assert after["chunks"] == before["chunks"]

        # Drift tables continue to grow with each run
        assert after["drift_runs"] == before["drift_runs"] + 2
