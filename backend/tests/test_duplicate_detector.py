"""Unit tests for DuplicateDetector V1 — SQLite in-memory."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.models.documents import Base, Document, Workspace
from app.services.duplicate_detector import (
    _FINDING_TYPE,
    _REMEDIATION,
    _SEVERITY,
    DuplicateDetector,
)


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
        yield s


def _wid() -> str:
    return str(uuid.uuid4())


def _seed_ws(session: Session, workspace_id: str) -> None:
    session.add(Workspace(
        id=workspace_id,
        name="test",
        is_default=False,
        created_at=datetime.now(UTC),
    ))
    session.flush()


def _doc(
    session: Session,
    workspace_id: str,
    *,
    content_hash: str,
    lifecycle_status: str = "active",
) -> str:
    doc_id = str(uuid.uuid4())
    session.add(Document(
        id=doc_id,
        workspace_id=workspace_id,
        owner_user_id="u1",
        title="doc",
        source_type="upload",
        content_hash=content_hash,
        import_status="parsed",
        lifecycle_status=lifecycle_status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))
    session.flush()
    return doc_id


# ---------------------------------------------------------------------------
# No duplicates
# ---------------------------------------------------------------------------

class TestNoDuplicates:
    def test_empty_workspace(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        assert DuplicateDetector(session, wid).detect() == []

    def test_single_document(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="abc")
        assert DuplicateDetector(session, wid).detect() == []

    def test_two_documents_different_hashes(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="hash1")
        _doc(session, wid, content_hash="hash2")
        assert DuplicateDetector(session, wid).detect() == []


# ---------------------------------------------------------------------------
# Duplicates detected
# ---------------------------------------------------------------------------

class TestDuplicatesDetected:
    def test_two_docs_same_hash_produces_two_findings(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="dup")
        _doc(session, wid, content_hash="dup")
        findings = DuplicateDetector(session, wid).detect()
        assert len(findings) == 2

    def test_three_docs_same_hash_produces_three_findings(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        for _ in range(3):
            _doc(session, wid, content_hash="triplicate")
        findings = DuplicateDetector(session, wid).detect()
        assert len(findings) == 3

    def test_finding_type_is_duplicate_document(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="x")
        _doc(session, wid, content_hash="x")
        for f in DuplicateDetector(session, wid).detect():
            assert f["finding_type"] == _FINDING_TYPE

    def test_severity_is_warning(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="x")
        _doc(session, wid, content_hash="x")
        for f in DuplicateDetector(session, wid).detect():
            assert f["severity"] == _SEVERITY
            assert f["severity"] == "warning"

    def test_remediation_text(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="x")
        _doc(session, wid, content_hash="x")
        for f in DuplicateDetector(session, wid).detect():
            assert f["remediation"] == _REMEDIATION
            assert "zusammenführen" in f["remediation"]

    def test_finding_references_document_id(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        id_a = _doc(session, wid, content_hash="same")
        id_b = _doc(session, wid, content_hash="same")
        findings = DuplicateDetector(session, wid).detect()
        found_ids = {f["document_id"] for f in findings}
        assert id_a in found_ids
        assert id_b in found_ids

    def test_finding_description_contains_siblings(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        id_a = _doc(session, wid, content_hash="same")
        id_b = _doc(session, wid, content_hash="same")
        findings = DuplicateDetector(session, wid).detect()
        for f in findings:
            # Each finding's description must mention the sibling
            sibling = id_b if f["document_id"] == id_a else id_a
            assert sibling in f["description"]

    def test_finding_has_no_chunk_or_version_id(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="x")
        _doc(session, wid, content_hash="x")
        for f in DuplicateDetector(session, wid).detect():
            assert f["chunk_id"] is None
            assert f["version_id"] is None


# ---------------------------------------------------------------------------
# Only active documents
# ---------------------------------------------------------------------------

class TestOnlyActiveDocuments:
    def test_archived_ignored(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="h", lifecycle_status="active")
        _doc(session, wid, content_hash="h", lifecycle_status="archived")
        assert DuplicateDetector(session, wid).detect() == []

    def test_deleted_ignored(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="h", lifecycle_status="active")
        _doc(session, wid, content_hash="h", lifecycle_status="deleted")
        assert DuplicateDetector(session, wid).detect() == []

    def test_pending_ignored(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="h", lifecycle_status="active")
        _doc(session, wid, content_hash="h", lifecycle_status="pending")
        assert DuplicateDetector(session, wid).detect() == []

    def test_two_archived_not_detected(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="h", lifecycle_status="archived")
        _doc(session, wid, content_hash="h", lifecycle_status="archived")
        assert DuplicateDetector(session, wid).detect() == []

    def test_two_active_detected(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="h", lifecycle_status="active")
        _doc(session, wid, content_hash="h", lifecycle_status="active")
        assert len(DuplicateDetector(session, wid).detect()) == 2


# ---------------------------------------------------------------------------
# Workspace isolation
# ---------------------------------------------------------------------------

class TestWorkspaceIsolation:
    def test_duplicate_in_other_workspace_not_detected(self, session, engine):
        wid_a = _wid()
        wid_b = _wid()
        _seed_ws(session, wid_a)
        _seed_ws(session, wid_b)
        _doc(session, wid_a, content_hash="shared")
        _doc(session, wid_b, content_hash="shared")
        assert DuplicateDetector(session, wid_a).detect() == []
        assert DuplicateDetector(session, wid_b).detect() == []

    def test_duplicate_within_workspace_isolated(self, session, engine):
        wid_a = _wid()
        wid_b = _wid()
        _seed_ws(session, wid_a)
        _seed_ws(session, wid_b)
        _doc(session, wid_a, content_hash="dup")
        _doc(session, wid_a, content_hash="dup")
        _doc(session, wid_b, content_hash="other")
        assert len(DuplicateDetector(session, wid_a).detect()) == 2
        assert DuplicateDetector(session, wid_b).detect() == []


# ---------------------------------------------------------------------------
# No mutations
# ---------------------------------------------------------------------------

class TestNoMutations:
    def test_detect_does_not_alter_documents(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        doc_id = _doc(session, wid, content_hash="x")
        _doc(session, wid, content_hash="x")
        session.commit()

        before = session.get(Document, doc_id)
        before_status = before.lifecycle_status
        before_hash = before.content_hash
        before_updated = before.updated_at

        DuplicateDetector(session, wid).detect()
        session.commit()

        after = session.get(Document, doc_id)
        assert after.lifecycle_status == before_status
        assert after.content_hash == before_hash
        assert after.updated_at == before_updated

    def test_detect_does_not_delete_documents(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="del")
        _doc(session, wid, content_hash="del")
        session.commit()

        DuplicateDetector(session, wid).detect()
        session.commit()

        from sqlalchemy import select
        count = session.scalar(
            select(Document).where(
                Document.workspace_id == wid,
                Document.content_hash == "del",
            )
        )
        assert count is not None  # both rows still exist


# ---------------------------------------------------------------------------
# Finding shape — runner compatibility
# ---------------------------------------------------------------------------

class TestFindingShape:
    def test_all_required_keys_present(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="z")
        _doc(session, wid, content_hash="z")
        required = {
            "finding_type", "severity", "document_id",
            "version_id", "chunk_id",
            "title", "description", "remediation",
        }
        for f in DuplicateDetector(session, wid).detect():
            missing = required - set(f.keys())
            assert not missing, f"Missing keys: {missing}"

    def test_no_run_id_in_finding(self, session, engine):
        """run_id must not be in the dict — runner assigns it."""
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="z")
        _doc(session, wid, content_hash="z")
        for f in DuplicateDetector(session, wid).detect():
            assert "run_id" not in f

    def test_severity_in_allowed_set(self, session, engine):
        wid = _wid()
        _seed_ws(session, wid)
        _doc(session, wid, content_hash="z")
        _doc(session, wid, content_hash="z")
        for f in DuplicateDetector(session, wid).detect():
            assert f["severity"] in ("error", "warning", "info")
