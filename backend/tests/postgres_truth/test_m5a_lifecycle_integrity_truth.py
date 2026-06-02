"""M5a Lifecycle Integrity Detector - PostgreSQL Truth Tests.

Markers: postgres_truth, m5_truth
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.models.documents import ChatCitation, ChatMessage, ChatSession, Chunk, Document, DocumentVersion
from app.services.lifecycle_integrity_detector import LifecycleIntegrityDetector


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


def _now() -> datetime:
    return datetime.now(UTC)


def _doc(
    session: Session,
    workspace_id: str,
    *,
    owner_user_id: str,
    title: str = "doc",
    lifecycle_status: str = "active",
    archived_at=None,
    deleted_at=None,
) -> str:
    did = str(uuid.uuid4())
    session.add(
        Document(
            id=did,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            title=title,
            source_type="upload",
            content_hash=uuid.uuid4().hex,
            import_status="pending",
            lifecycle_status=lifecycle_status,
            archived_at=archived_at,
            deleted_at=deleted_at,
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


def _chunk(session: Session, doc_id: str, version_id: str, *, searchable: bool, content: str = "text") -> str:
    cid = str(uuid.uuid4())
    session.execute(
        text(
            """
            insert into document_chunks (
                id,
                document_id,
                document_version_id,
                chunk_index,
                heading_path,
                anchor,
                content,
                is_searchable,
                content_hash,
                token_estimate,
                metadata,
                created_at
            )
            values (
                :id,
                :document_id,
                :document_version_id,
                :chunk_index,
                cast(:heading_path as jsonb),
                :anchor,
                :content,
                :is_searchable,
                :content_hash,
                :token_estimate,
                cast(:metadata as jsonb),
                :created_at
            )
            """
        ),
        {
            "id": cid,
            "document_id": doc_id,
            "document_version_id": version_id,
            "chunk_index": 0,
            "heading_path": "[]",
            "anchor": f"a-{cid[:8]}",
            "content": content,
            "is_searchable": searchable,
            "content_hash": uuid.uuid4().hex,
            "token_estimate": 1,
            "metadata": '{"source_anchor": {"type": "text", "page": null, "paragraph": 1, "char_start": 0, "char_end": 4}}',
            "created_at": _now(),
        },
    )
    session.flush()
    return cid


def _citation(
    session: Session,
    workspace_id: str,
    owner_user_id: str,
    document_id: str,
    chunk_id: str | None,
    *,
    source_status: str,
) -> str:
    sid = str(uuid.uuid4())
    mid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    now = _now()
    session.add(
        ChatSession(
            id=sid,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            title="s",
            created_at=now,
            updated_at=now,
        )
    )
    session.flush()
    session.add(ChatMessage(id=mid, session_id=sid, message_index=0, role="assistant", content="c", basis_type="knowledge_base", metadata_={}, created_at=now))
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


def test_detector_returns_list_on_clean_workspace(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    result = LifecycleIntegrityDetector(truth_session, truth_seed["workspace_id"]).detect()
    assert isinstance(result, list)


def test_archived_document_not_in_search_detected(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    uid = truth_seed["user_id"]
    did = _doc(truth_session, wid, owner_user_id=uid, lifecycle_status="archived", archived_at=_now())
    vid = _version(truth_session, did)
    _chunk(truth_session, did, vid, searchable=True)
    truth_session.commit()

    findings = LifecycleIntegrityDetector(truth_session, wid).detect()
    assert any(
        f["document_id"] == did
        and f["finding_type"] == "INVALID_LIFECYCLE"
        and f["severity"] == "error"
        and f["remediation"] == "Lifecycle korrigieren"
        for f in findings
    )


def test_deleted_document_not_in_search_detected(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    uid = truth_seed["user_id"]
    did = _doc(truth_session, wid, owner_user_id=uid, lifecycle_status="deleted", deleted_at=_now())
    vid = _version(truth_session, did)
    _chunk(truth_session, did, vid, searchable=True)
    truth_session.commit()

    findings = LifecycleIntegrityDetector(truth_session, wid).detect()
    assert any(f["document_id"] == did and f["finding_type"] == "INVALID_LIFECYCLE" for f in findings)


def test_active_document_retrievable_rule_detects_gap(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    uid = truth_seed["user_id"]
    did = _doc(truth_session, wid, owner_user_id=uid, lifecycle_status="active")
    vid = _version(truth_session, did)
    _chunk(truth_session, did, vid, searchable=False)
    truth_session.commit()

    findings = LifecycleIntegrityDetector(truth_session, wid).detect()
    assert any(f["document_id"] == did and f["title"] == "Active document not findable" for f in findings)


def test_lifecycle_status_consistent_with_source_status_detects_drift(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    uid = truth_seed["user_id"]
    did = _doc(truth_session, wid, owner_user_id=uid, lifecycle_status="active")
    vid = _version(truth_session, did)
    chunk_id = _chunk(truth_session, did, vid, searchable=True)
    _citation(truth_session, wid, uid, did, chunk_id, source_status="archived")
    truth_session.commit()

    findings = LifecycleIntegrityDetector(truth_session, wid).detect()
    assert any(f["finding_type"] == "INVALID_LIFECYCLE" and f["document_id"] == did for f in findings)


def test_findings_pass_db_constraints(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    uid = truth_seed["user_id"]
    did = _doc(truth_session, wid, owner_user_id=uid, lifecycle_status="archived", archived_at=_now())
    vid = _version(truth_session, did)
    _chunk(truth_session, did, vid, searchable=True)
    truth_session.commit()

    run_id = str(uuid.uuid4())
    truth_session.add(DataQualityRun(id=run_id, workspace_id=wid, status="running", started_at=_now()))
    truth_session.flush()

    now = _now()
    for f in LifecycleIntegrityDetector(truth_session, wid).detect():
        truth_session.add(
            DataQualityFinding(
                id=str(uuid.uuid4()),
                run_id=run_id,
                workspace_id=wid,
                finding_type=f["finding_type"],
                severity=f["severity"],
                document_id=f.get("document_id"),
                version_id=f.get("version_id"),
                chunk_id=f.get("chunk_id"),
                title=f["title"],
                description=f["description"],
                remediation=f["remediation"],
                created_at=now,
            )
        )
    truth_session.commit()


def test_no_document_mutation(
    truth_session: Session, truth_seed: dict[str, str]
) -> None:
    wid = truth_seed["workspace_id"]
    uid = truth_seed["user_id"]
    did = _doc(truth_session, wid, owner_user_id=uid, lifecycle_status="active")
    vid = _version(truth_session, did)
    _chunk(truth_session, did, vid, searchable=True)
    truth_session.commit()

    before = truth_session.execute(
        text("SELECT id, lifecycle_status, archived_at, deleted_at FROM documents WHERE workspace_id=:w"),
        {"w": wid},
    ).fetchall()
    LifecycleIntegrityDetector(truth_session, wid).detect()
    truth_session.commit()
    after = truth_session.execute(
        text("SELECT id, lifecycle_status, archived_at, deleted_at FROM documents WHERE workspace_id=:w"),
        {"w": wid},
    ).fetchall()
    assert set(before) == set(after)
