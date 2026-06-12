"""Tests for DocumentDriftDetector.

Runs against in-memory SQLite -- no TEST_DATABASE_URL required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.documents import Base, Chunk, Document, DocumentVersion, Workspace  # noqa: F401
from app.models.drift import DriftFinding, DriftRun, DriftSnapshot  # noqa: F401
from app.services.drift.document_drift_detector import DocumentDriftDetector

UTC = timezone.utc
WS_ID = "ws-doc-drift"
OWNER_ID = "user-001"


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
def engine_no_fk():
    """Engine without FK enforcement -- for tests that deliberately create dangling refs."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_ID, name="Doc Drift Test WS", is_default=True, created_at=datetime.now(UTC)))
        s.commit()
        yield s


@pytest.fixture()
def session_no_fk(engine_no_fk):
    with Session(engine_no_fk) as s:
        s.add(Workspace(id=WS_ID, name="Doc Drift Test WS NFK", is_default=True, created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _doc(version_id=None, lifecycle_status="active", import_status="chunked",
         archived_at=None, deleted_at=None):
    now = datetime.now(UTC)
    return Document(
        id=str(uuid.uuid4()),
        workspace_id=WS_ID,
        owner_user_id=OWNER_ID,
        current_version_id=version_id,
        title="Test Doc",
        source_type="upload",
        content_hash=str(uuid.uuid4()),
        import_status=import_status,
        lifecycle_status=lifecycle_status,
        archived_at=archived_at,
        deleted_at=deleted_at,
        created_at=now,
        updated_at=now,
    )


def _version(doc_id):
    return DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        version_number=1,
        normalized_markdown="# Title\n\nContent",
        markdown_hash=str(uuid.uuid4()),
        parser_version="1.0",
        ocr_used=False,
        metadata_={},
        created_at=datetime.now(UTC),
    )


def _chunk(doc_id, version_id, chunk_index):
    return Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        document_version_id=version_id,
        chunk_index=chunk_index,
        heading_path=[],
        anchor=f"chunk-{chunk_index}",
        content=f"chunk content {chunk_index}",
        content_hash=str(uuid.uuid4()),
        metadata_={},
        created_at=datetime.now(UTC),
    )


def _detect(session):
    return DocumentDriftDetector().detect(session, WS_ID)


def _add_doc_with_version(session, **doc_kwargs):
    """Helper: insert doc -> version -> link (avoids circular FK issue in SQLite)."""
    doc = _doc(version_id=None, **doc_kwargs)
    session.add(doc)
    session.flush()
    ver = _version(doc.id)
    session.add(ver)
    session.flush()
    doc.current_version_id = ver.id
    return doc, ver


# ---------------------------------------------------------------------------
# Check 1: Dokument vorhanden
# ---------------------------------------------------------------------------

class TestDocumentPresent:
    def test_clean_document_no_finding(self, session):
        doc, ver = _add_doc_with_version(session)
        session.add(_chunk(doc.id, ver.id, 0))
        session.add(_chunk(doc.id, ver.id, 1))
        session.commit()

        findings = _detect(session)
        doc_present = [f for f in findings if f.detail and f.detail.get("check") == "document_present"]
        assert len(doc_present) == 0

    def test_active_chunked_no_version_id(self, session):
        doc = _doc(version_id=None, import_status="chunked")
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.finding_type == "DOCUMENT_DRIFT"
            and f.detail.get("check") == "document_present"
            and "no current_version_id" in f.detail.get("reason", "")
            for f in findings
        )

    def test_active_chunked_zero_chunks(self, session):
        doc, ver = _add_doc_with_version(session, import_status="chunked")
        session.commit()  # no chunks added

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "document_present"
            and "zero chunks" in f.detail.get("reason", "")
            for f in findings
        )

    def test_non_active_skipped(self, session):
        doc = _doc(version_id=None, lifecycle_status="archived", import_status="chunked",
                   archived_at=datetime.now(UTC))
        session.add(doc)
        session.commit()

        findings = _detect(session)
        doc_present = [f for f in findings if f.detail and f.detail.get("check") == "document_present"]
        assert len(doc_present) == 0


# ---------------------------------------------------------------------------
# Check 2: Version vorhanden
# ---------------------------------------------------------------------------

class TestVersionPresent:
    def test_missing_version_record(self, session_no_fk):
        """Dangling FK: version_id set but no matching DocumentVersion. Needs FK-off session."""
        doc = _doc(version_id="nonexistent-version-id")
        session_no_fk.add(doc)
        session_no_fk.commit()

        findings = DocumentDriftDetector().detect(session_no_fk, WS_ID)
        assert any(
            f.detail.get("check") == "version_present"
            and "non-existent DocumentVersion" in f.detail.get("reason", "")
            for f in findings
        )

    def test_version_owned_by_other_document(self, session):
        other_doc = _doc(version_id=None, import_status="parsed")
        session.add(other_doc)
        session.flush()
        ver = _version(other_doc.id)
        session.add(ver)
        session.flush()

        # doc points to a version that belongs to other_doc
        doc = _doc(version_id=None, import_status="parsed")
        session.add(doc)
        session.flush()
        doc.current_version_id = ver.id
        session.commit()

        findings = _detect(session)
        assert any(
            f.entity_id == doc.id
            and f.detail.get("check") == "version_present"
            and "different document" in f.detail.get("reason", "")
            for f in findings
        )

    def test_null_version_id_skipped(self, session):
        doc = _doc(version_id=None, import_status="pending")
        session.add(doc)
        session.commit()

        findings = _detect(session)
        version_findings = [f for f in findings if f.detail and f.detail.get("check") == "version_present"]
        assert len(version_findings) == 0


# ---------------------------------------------------------------------------
# Check 3: Chunkstruktur konsistent
# ---------------------------------------------------------------------------

class TestChunkStructure:
    def test_sequential_chunks_no_finding(self, session):
        doc, ver = _add_doc_with_version(session, import_status="chunked")
        for i in range(4):
            session.add(_chunk(doc.id, ver.id, i))
        session.commit()

        findings = _detect(session)
        chunk_findings = [f for f in findings if f.detail and f.detail.get("check") == "chunk_structure"]
        assert len(chunk_findings) == 0

    def test_gap_in_chunk_indices(self, session):
        doc, ver = _add_doc_with_version(session, import_status="chunked")
        for i in [0, 1, 3]:  # gap at 2
            session.add(_chunk(doc.id, ver.id, i))
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "chunk_structure"
            and "non-sequential" in f.detail.get("reason", "")
            for f in findings
        )

    def test_non_chunked_status_skipped(self, session):
        doc, ver = _add_doc_with_version(session, import_status="parsed")
        session.commit()

        findings = _detect(session)
        chunk_findings = [f for f in findings if f.detail and f.detail.get("check") == "chunk_structure"]
        assert len(chunk_findings) == 0

    def test_empty_chunks_no_structure_finding(self, session):
        """Archived doc with no chunks: no chunk_structure finding (nothing to compare)."""
        doc, ver = _add_doc_with_version(session, lifecycle_status="archived",
                                         import_status="chunked", archived_at=datetime.now(UTC))
        session.commit()

        findings = _detect(session)
        chunk_findings = [f for f in findings if f.detail and f.detail.get("check") == "chunk_structure"]
        assert len(chunk_findings) == 0


# ---------------------------------------------------------------------------
# Check 4: Dokumentstatus konsistent
# ---------------------------------------------------------------------------

class TestStatusConsistent:
    def test_archived_without_archived_at(self, session):
        doc = _doc(lifecycle_status="archived", archived_at=None)
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "status_consistent"
            and "archived_at is NULL" in f.detail.get("reason", "")
            for f in findings
        )

    def test_deleted_without_deleted_at(self, session):
        doc = _doc(lifecycle_status="deleted", deleted_at=None)
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "status_consistent"
            and "deleted_at is NULL" in f.detail.get("reason", "")
            for f in findings
        )

    def test_active_with_deleted_at_set(self, session):
        doc = _doc(lifecycle_status="active", deleted_at=datetime.now(UTC))
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "status_consistent"
            and "active but deleted_at is set" in f.detail.get("reason", "")
            and f.severity == "error"
            for f in findings
        )

    def test_active_with_archived_at_set(self, session):
        doc = _doc(lifecycle_status="active", archived_at=datetime.now(UTC))
        session.add(doc)
        session.commit()

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "status_consistent"
            and "active but archived_at is set" in f.detail.get("reason", "")
            for f in findings
        )

    def test_clean_archived_document_no_status_finding(self, session):
        doc = _doc(lifecycle_status="archived", import_status="chunked",
                   archived_at=datetime.now(UTC))
        session.add(doc)
        session.commit()

        findings = _detect(session)
        status_findings = [f for f in findings if f.detail and f.detail.get("check") == "status_consistent"]
        assert len(status_findings) == 0

    def test_clean_deleted_document_no_status_finding(self, session):
        doc = _doc(lifecycle_status="deleted", import_status="chunked",
                   deleted_at=datetime.now(UTC))
        session.add(doc)
        session.commit()

        findings = _detect(session)
        status_findings = [f for f in findings if f.detail and f.detail.get("check") == "status_consistent"]
        assert len(status_findings) == 0

    def test_active_clean_no_finding(self, session):
        doc, ver = _add_doc_with_version(session, lifecycle_status="active",
                                         import_status="chunked",
                                         archived_at=None, deleted_at=None)
        session.add(_chunk(doc.id, ver.id, 0))
        session.commit()

        findings = _detect(session)
        status_findings = [f for f in findings if f.detail and f.detail.get("check") == "status_consistent"]
        assert len(status_findings) == 0


# ---------------------------------------------------------------------------
# All findings are DOCUMENT_DRIFT
# ---------------------------------------------------------------------------

class TestFindingType:
    def test_all_findings_are_document_drift(self, session):
        doc_no_version = _doc(version_id=None, import_status="chunked")
        doc_bad_status = _doc(lifecycle_status="archived", archived_at=None)
        session.add_all([doc_no_version, doc_bad_status])
        session.commit()

        findings = _detect(session)
        assert len(findings) > 0
        assert all(f.finding_type == "DOCUMENT_DRIFT" for f in findings)

    def test_empty_workspace_no_findings(self, session):
        findings = _detect(session)
        assert findings == []
