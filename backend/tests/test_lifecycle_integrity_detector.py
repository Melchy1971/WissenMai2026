"""Unit tests for LifecycleIntegrityDetector - SQLite in-memory."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, text
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
from app.services.lifecycle_integrity_detector import LifecycleIntegrityDetector


pytestmark = pytest.mark.m3a_truth


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


def _now():
    return datetime.now(timezone.utc)


def _wid() -> str:
    return str(uuid.uuid4())


def _seed_workspace(session: Session, wid: str) -> None:
    session.add(Workspace(id=wid, name="ws", is_default=False, created_at=_now()))
    session.flush()


def _doc(session: Session, wid: str, lifecycle_status: str = "active", title: str = "doc") -> str:
    did = str(uuid.uuid4())
    session.add(
        Document(
            id=did,
            workspace_id=wid,
            owner_user_id="u",
            title=title,
            source_type="upload",
            content_hash=uuid.uuid4().hex,
            import_status="parsed",
            lifecycle_status=lifecycle_status,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    session.flush()
    return did


def _version(session: Session, doc_id: str) -> str:
    vid = str(uuid.uuid4())
    session.add(
        DocumentVersion(
            id=vid,
            document_id=doc_id,
            version_number=1,
            normalized_markdown="text",
            markdown_hash=uuid.uuid4().hex,
            parser_version="1.0",
            ocr_used=False,
            metadata_={},
            created_at=_now(),
        )
    )
    session.flush()
    doc = session.get(Document, doc_id)
    doc.current_version_id = vid
    session.flush()
    return vid


def _chunk(session: Session, doc_id: str, version_id: str, *, searchable: bool) -> str:
    cid = str(uuid.uuid4())
    session.add(
        Chunk(
            id=cid,
            document_id=doc_id,
            document_version_id=version_id,
            chunk_index=0,
            heading_path=[],
            anchor=f"a-{cid[:8]}",
            content="sample content",
            is_searchable=searchable,
            search_vector=None,
            content_hash=uuid.uuid4().hex,
            token_estimate=1,
            metadata_={},
            created_at=_now(),
        )
    )
    session.flush()
    return cid


def _seed_citation(session: Session, wid: str, document_id: str, chunk_id: str | None, source_status: str) -> str:
    sid = str(uuid.uuid4())
    mid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    session.add(ChatSession(id=sid, workspace_id=wid, owner_user_id="u", title="s", created_at=_now(), updated_at=_now()))
    session.flush()
    session.add(ChatMessage(id=mid, session_id=sid, message_index=0, role="assistant", content="c", basis_type="knowledge_base", metadata_={}, created_at=_now()))
    session.flush()
    session.add(
        ChatCitation(
            id=cid,
            message_id=mid,
            chunk_id=chunk_id,
            document_id=document_id,
            document_title="d",
            quote_preview="q",
            source_anchor={"type": "text"},
            source_status=source_status,
        )
    )
    session.flush()
    return cid


def _detect(session: Session, wid: str):
    return LifecycleIntegrityDetector(session, wid).detect()


def test_archived_document_not_searchable_rule_detects_violation(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid, lifecycle_status="archived")
    vid = _version(session, did)
    _chunk(session, did, vid, searchable=True)
    session.commit()

    findings = _detect(session, wid)
    assert any(f["document_id"] == did and f["finding_type"] == "RETRIEVAL_RISK" for f in findings)


def test_deleted_document_not_searchable_rule_detects_violation(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid, lifecycle_status="deleted")
    vid = _version(session, did)
    _chunk(session, did, vid, searchable=True)
    session.commit()

    findings = _detect(session, wid)
    assert any(f["document_id"] == did and f["finding_type"] == "RETRIEVAL_RISK" for f in findings)


def test_active_document_not_retrievable_detected(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid, lifecycle_status="active")
    vid = _version(session, did)
    _chunk(session, did, vid, searchable=False)
    session.commit()

    findings = _detect(session, wid)
    assert any(f["document_id"] == did and f["title"] == "Active document not retrievable" for f in findings)


def test_source_status_drift_detected(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid, lifecycle_status="active")
    vid = _version(session, did)
    chunk_id = _chunk(session, did, vid, searchable=True)
    _seed_citation(session, wid, did, chunk_id, source_status="archived")
    session.commit()

    findings = _detect(session, wid)
    assert any(f["finding_type"] == "INVALID_SOURCE_STATUS" and f["document_id"] == did for f in findings)


def test_workspace_isolation(session, engine):
    wa = _wid()
    wb = _wid()
    _seed_workspace(session, wa)
    _seed_workspace(session, wb)

    did_b = _doc(session, wb, lifecycle_status="archived")
    vid_b = _version(session, did_b)
    _chunk(session, did_b, vid_b, searchable=True)
    session.commit()

    findings_a = _detect(session, wa)
    assert findings_a == []


def test_no_document_chunk_or_citation_mutation(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid, lifecycle_status="active")
    vid = _version(session, did)
    chunk_id = _chunk(session, did, vid, searchable=True)
    _seed_citation(session, wid, did, chunk_id, source_status="active")
    session.commit()

    before_doc = session.execute(
        text("SELECT id, lifecycle_status, archived_at, deleted_at FROM documents WHERE workspace_id=:w"),
        {"w": wid},
    ).fetchall()
    before_chunk = session.execute(
        text("SELECT id, is_searchable FROM document_chunks WHERE document_id=:d"),
        {"d": did},
    ).fetchall()
    before_citation = session.execute(
        text("SELECT id, source_status FROM chat_citations WHERE document_id=:d"),
        {"d": did},
    ).fetchall()

    _detect(session, wid)
    session.commit()

    after_doc = session.execute(
        text("SELECT id, lifecycle_status, archived_at, deleted_at FROM documents WHERE workspace_id=:w"),
        {"w": wid},
    ).fetchall()
    after_chunk = session.execute(
        text("SELECT id, is_searchable FROM document_chunks WHERE document_id=:d"),
        {"d": did},
    ).fetchall()
    after_citation = session.execute(
        text("SELECT id, source_status FROM chat_citations WHERE document_id=:d"),
        {"d": did},
    ).fetchall()

    assert set(before_doc) == set(after_doc)
    assert set(before_chunk) == set(after_chunk)
    assert set(before_citation) == set(after_citation)


def test_finding_shape_and_clean_state(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)

    # active searchable
    did_a = _doc(session, wid, lifecycle_status="active")
    vid_a = _version(session, did_a)
    chunk_id = _chunk(session, did_a, vid_a, searchable=True)
    _seed_citation(session, wid, did_a, chunk_id, source_status="active")

    # archived/deleted not searchable
    did_ar = _doc(session, wid, lifecycle_status="archived")
    vid_ar = _version(session, did_ar)
    _chunk(session, did_ar, vid_ar, searchable=False)

    did_del = _doc(session, wid, lifecycle_status="deleted")
    vid_del = _version(session, did_del)
    _chunk(session, did_del, vid_del, searchable=False)

    session.commit()

    findings = _detect(session, wid)
    assert findings == []

    # Create one violation and validate shape
    did_bad = _doc(session, wid, lifecycle_status="archived")
    vid_bad = _version(session, did_bad)
    _chunk(session, did_bad, vid_bad, searchable=True)
    session.commit()
    findings = _detect(session, wid)
    required = {"finding_type", "severity", "document_id", "version_id", "chunk_id", "title", "description", "remediation"}
    for finding in findings:
        assert required <= set(finding.keys())
        assert "run_id" not in finding
