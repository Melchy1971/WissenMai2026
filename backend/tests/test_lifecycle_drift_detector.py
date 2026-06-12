"""Tests for LifecycleDriftDetector.

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
from app.services.drift.lifecycle_drift_detector import LifecycleDriftDetector

UTC = timezone.utc
WS_ID = "ws-lifecycle-drift"
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
def session(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_ID, name="Lifecycle Drift WS", is_default=True, created_at=datetime.now(UTC)))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _doc(lifecycle_status="active", import_status="chunked",
         archived_at=None, deleted_at=None):
    now = datetime.now(UTC)
    return Document(
        id=str(uuid.uuid4()),
        workspace_id=WS_ID,
        owner_user_id=OWNER_ID,
        current_version_id=None,
        title="Test Doc",
        source_type="upload",
        content_hash=str(uuid.uuid4()),
        import_status=import_status,
        lifecycle_status=lifecycle_status,
        archived_at=archived_at,
        deleted_at=deleted_at,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _version(doc_id):
    return DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        version_number=1,
        normalized_markdown="# Title",
        markdown_hash=str(uuid.uuid4()),
        parser_version="1.0",
        ocr_used=False,
        metadata_={"category": "tech", "summary": "ok"},
        created_at=datetime.now(UTC),
    )


def _chunk(doc_id, version_id, chunk_index=0, is_searchable=True):
    return Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        document_version_id=version_id,
        chunk_index=chunk_index,
        heading_path=[],
        anchor=f"chunk-{chunk_index}",
        content=f"chunk content {chunk_index}",
        content_hash=str(uuid.uuid4()),
        is_searchable=is_searchable,
        metadata_={},
        created_at=datetime.now(UTC),
    )


def _setup_doc(session, lifecycle_status="active", import_status="chunked",
               archived_at=None, deleted_at=None):
    """Insert doc and version in the correct order (circular FK workaround)."""
    doc = _doc(lifecycle_status=lifecycle_status, import_status=import_status,
               archived_at=archived_at, deleted_at=deleted_at)
    session.add(doc)
    session.flush()
    ver = _version(doc.id)
    session.add(ver)
    session.flush()
    doc.current_version_id = ver.id
    return doc, ver


def _detect(session):
    return LifecycleDriftDetector().detect(session, WS_ID)


# ---------------------------------------------------------------------------
# Check 1: active auffindbar
# ---------------------------------------------------------------------------

class TestActiveFindable:
    def test_active_with_searchable_chunk_no_finding(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="active", import_status="chunked")
        session.add(_chunk(doc.id, ver.id, is_searchable=True))
        session.commit()

        findings = _detect(session)
        active_findings = [f for f in findings if f.detail and f.detail.get("check") == "active_findable"]
        assert len(active_findings) == 0

    def test_active_chunked_no_searchable_chunk(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="active", import_status="chunked")
        session.add(_chunk(doc.id, ver.id, is_searchable=False))
        session.commit()

        findings = _detect(session)
        assert any(
            f.finding_type == "LIFECYCLE_DRIFT"
            and f.detail.get("check") == "active_findable"
            and f.severity == "error"
            and f.entity_id == doc.id
            for f in findings
        )

    def test_active_chunked_no_chunks_at_all(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="active", import_status="chunked")
        session.commit()  # no chunks

        findings = _detect(session)
        assert any(
            f.detail.get("check") == "active_findable"
            and f.detail.get("searchable_chunk_count") == 0
            for f in findings
        )

    def test_active_not_chunked_skipped(self, session):
        """active document with import_status != chunked should not be checked."""
        doc, ver = _setup_doc(session, lifecycle_status="active", import_status="parsed")
        session.commit()

        findings = _detect(session)
        active_findings = [f for f in findings if f.detail and f.detail.get("check") == "active_findable"]
        assert len(active_findings) == 0

    def test_active_mixed_chunks_has_at_least_one_searchable(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="active", import_status="chunked")
        session.add(_chunk(doc.id, ver.id, chunk_index=0, is_searchable=False))
        session.add(_chunk(doc.id, ver.id, chunk_index=1, is_searchable=True))
        session.commit()

        findings = _detect(session)
        active_findings = [f for f in findings if f.detail and f.detail.get("check") == "active_findable"]
        assert len(active_findings) == 0


# ---------------------------------------------------------------------------
# Check 2: archived nicht auffindbar
# ---------------------------------------------------------------------------

class TestArchivedNotFindable:
    def test_archived_no_searchable_chunks_no_finding(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="archived",
                              archived_at=datetime.now(UTC))
        session.commit()

        findings = _detect(session)
        arch_findings = [f for f in findings if f.detail and f.detail.get("check") == "archived_not_findable"]
        assert len(arch_findings) == 0

    def test_archived_non_searchable_chunk_no_finding(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="archived",
                              archived_at=datetime.now(UTC))
        session.add(_chunk(doc.id, ver.id, is_searchable=False))
        session.commit()

        findings = _detect(session)
        arch_findings = [f for f in findings if f.detail and f.detail.get("check") == "archived_not_findable"]
        assert len(arch_findings) == 0

    def test_archived_with_searchable_chunk(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="archived",
                              archived_at=datetime.now(UTC))
        session.add(_chunk(doc.id, ver.id, is_searchable=True))
        session.commit()

        findings = _detect(session)
        assert any(
            f.finding_type == "LIFECYCLE_DRIFT"
            and f.detail.get("check") == "archived_not_findable"
            and f.severity == "error"
            and f.entity_id == doc.id
            for f in findings
        )

    def test_archived_finding_reports_count(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="archived",
                              archived_at=datetime.now(UTC))
        for i in range(3):
            session.add(_chunk(doc.id, ver.id, chunk_index=i, is_searchable=True))
        session.commit()

        findings = _detect(session)
        arch = [f for f in findings if f.detail and f.detail.get("check") == "archived_not_findable"]
        assert len(arch) == 1
        assert arch[0].detail["searchable_chunk_count"] == 3


# ---------------------------------------------------------------------------
# Check 3: deleted nicht auffindbar
# ---------------------------------------------------------------------------

class TestDeletedNotFindable:
    def test_deleted_no_searchable_chunks_no_finding(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="deleted",
                              deleted_at=datetime.now(UTC))
        session.commit()

        findings = _detect(session)
        del_findings = [f for f in findings if f.detail and f.detail.get("check") == "deleted_not_findable"]
        assert len(del_findings) == 0

    def test_deleted_non_searchable_chunk_no_finding(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="deleted",
                              deleted_at=datetime.now(UTC))
        session.add(_chunk(doc.id, ver.id, is_searchable=False))
        session.commit()

        findings = _detect(session)
        del_findings = [f for f in findings if f.detail and f.detail.get("check") == "deleted_not_findable"]
        assert len(del_findings) == 0

    def test_deleted_with_searchable_chunk(self, session):
        doc, ver = _setup_doc(session, lifecycle_status="deleted",
                              deleted_at=datetime.now(UTC))
        session.add(_chunk(doc.id, ver.id, is_searchable=True))
        session.commit()

        findings = _detect(session)
        assert any(
            f.finding_type == "LIFECYCLE_DRIFT"
            and f.detail.get("check") == "deleted_not_findable"
            and f.severity == "critical"
            and f.entity_id == doc.id
            for f in findings
        )

    def test_deleted_severity_is_critical(self, session):
        """deleted > archived in severity: data must not be exposed after deletion."""
        doc, ver = _setup_doc(session, lifecycle_status="deleted",
                              deleted_at=datetime.now(UTC))
        session.add(_chunk(doc.id, ver.id, is_searchable=True))
        session.commit()

        findings = _detect(session)
        del_f = [f for f in findings if f.detail and f.detail.get("check") == "deleted_not_findable"]
        assert all(f.severity == "critical" for f in del_f)


# ---------------------------------------------------------------------------
# All findings are LIFECYCLE_DRIFT
# ---------------------------------------------------------------------------

class TestFindingType:
    def test_all_findings_are_lifecycle_drift(self, session):
        # archived doc with searchable chunk + active doc with no searchable chunk
        doc_arch, ver_arch = _setup_doc(session, lifecycle_status="archived",
                                        archived_at=datetime.now(UTC))
        session.add(_chunk(doc_arch.id, ver_arch.id, is_searchable=True))

        doc_active, ver_active = _setup_doc(session, lifecycle_status="active",
                                            import_status="chunked")
        # no chunks for active doc
        session.commit()

        findings = _detect(session)
        assert len(findings) >= 2
        assert all(f.finding_type == "LIFECYCLE_DRIFT" for f in findings)

    def test_empty_workspace_no_findings(self, session):
        findings = _detect(session)
        assert findings == []

    def test_clean_workspace_no_findings(self, session):
        # active+chunked with searchable chunk
        doc, ver = _setup_doc(session, lifecycle_status="active", import_status="chunked")
        session.add(_chunk(doc.id, ver.id, is_searchable=True))

        # archived with no searchable chunks
        doc2, ver2 = _setup_doc(session, lifecycle_status="archived",
                                archived_at=datetime.now(UTC))
        session.add(_chunk(doc2.id, ver2.id, is_searchable=False))

        # deleted with no chunks
        doc3, ver3 = _setup_doc(session, lifecycle_status="deleted",
                                deleted_at=datetime.now(UTC))
        session.commit()

        findings = _detect(session)
        assert findings == []
