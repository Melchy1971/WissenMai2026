"""Unit tests for OrphanObjectDetector - SQLite in-memory."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
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
from app.services.orphan_detector import OrphanObjectDetector


pytestmark = pytest.mark.m3a_truth


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


def _now():
    return datetime.now(UTC)


def _wid() -> str:
    return str(uuid.uuid4())


def _seed_workspace(session: Session, wid: str) -> None:
    session.add(Workspace(id=wid, name="ws", is_default=False, created_at=_now()))
    session.flush()


def _doc(session: Session, wid: str) -> str:
    did = str(uuid.uuid4())
    session.add(
        Document(
            id=did,
            workspace_id=wid,
            owner_user_id="u",
            title="doc",
            source_type="upload",
            content_hash=uuid.uuid4().hex,
            import_status="parsed",
            lifecycle_status="active",
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


def _chunk(session: Session, doc_id: str, version_id: str) -> str:
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
            is_searchable=True,
            search_vector=None,
            content_hash=uuid.uuid4().hex,
            token_estimate=1,
            metadata_={},
            created_at=_now(),
        )
    )
    session.flush()
    return cid


def _chat_message(session: Session, wid: str) -> str:
    sid = str(uuid.uuid4())
    mid = str(uuid.uuid4())
    session.add(ChatSession(id=sid, workspace_id=wid, owner_user_id="u", title="s", created_at=_now(), updated_at=_now()))
    session.flush()
    session.add(ChatMessage(id=mid, session_id=sid, message_index=0, role="assistant", content="c", basis_type="knowledge_base", metadata_={}, created_at=_now()))
    session.flush()
    return mid


def _citation(session: Session, wid: str, document_id: str, chunk_id: str | None) -> str:
    cid = str(uuid.uuid4())
    session.add(
        ChatCitation(
            id=cid,
            message_id=_chat_message(session, wid),
            chunk_id=chunk_id,
            document_id=document_id,
            document_title="d",
            quote_preview="q",
            source_anchor={"type": "text"},
            source_status="active",
        )
    )
    session.flush()
    return cid


def _run(session: Session, wid: str) -> str:
    rid = str(uuid.uuid4())
    session.add(DataQualityRun(id=rid, workspace_id=wid, status="completed", started_at=_now(), finished_at=_now()))
    session.flush()
    return rid


def _finding(session: Session, wid: str, run_id: str) -> str:
    fid = str(uuid.uuid4())
    session.add(
        DataQualityFinding(
            id=fid,
            run_id=run_id,
            workspace_id=wid,
            finding_type="ORPHAN_CHUNK",
            severity="warning",
            title="f",
            description="d",
            remediation="r",
            created_at=_now(),
        )
    )
    session.flush()
    return fid


def _detect(session: Session, wid: str):
    return OrphanObjectDetector(session, wid).detect()


def _assert_orphan(finding: dict, finding_type: str) -> None:
    assert finding["finding_type"] == finding_type
    assert finding["severity"] == "warning"
    assert finding["remediation"] == "Nur melden. Keine automatische Reparatur."


def test_chunk_without_document_detected(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    chunk_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    missing_doc_id = str(uuid.uuid4())
    session.execute(
        text(
            """
            INSERT INTO document_chunks (
                id, document_id, document_version_id, chunk_index, heading_path, anchor,
                content, is_searchable, search_vector, content_hash, token_estimate,
                metadata, created_at
            ) VALUES (
                :id, :document_id, :version_id, 0, '[]', :anchor,
                'text', 1, NULL, :content_hash, 1, '{}', :created_at
            )
            """
        ),
        {
            "id": chunk_id,
            "document_id": missing_doc_id,
            "version_id": version_id,
            "anchor": f"a-{chunk_id[:8]}",
            "content_hash": uuid.uuid4().hex,
            "created_at": _now(),
        },
    )
    session.commit()

    finding = next(f for f in _detect(session, wid) if f["chunk_id"] == chunk_id)
    _assert_orphan(finding, "ORPHAN_CHUNK")


def test_version_without_document_detected(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    version_id = str(uuid.uuid4())
    missing_doc_id = str(uuid.uuid4())
    session.execute(
        text(
            """
            INSERT INTO document_versions (
                id, document_id, version_number, normalized_markdown, markdown_hash,
                parser_version, ocr_used, metadata, created_at
            ) VALUES (
                :id, :document_id, 1, 'text', :markdown_hash,
                '1.0', 0, '{}', :created_at
            )
            """
        ),
        {
            "id": version_id,
            "document_id": missing_doc_id,
            "markdown_hash": uuid.uuid4().hex,
            "created_at": _now(),
        },
    )
    session.commit()

    finding = next(f for f in _detect(session, wid) if f["version_id"] == version_id)
    _assert_orphan(finding, "ORPHAN_VERSION")


def test_citation_without_source_detected(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    missing_doc_id = str(uuid.uuid4())
    missing_chunk_id = str(uuid.uuid4())
    citation_id = _citation(session, wid, missing_doc_id, missing_chunk_id)
    session.commit()

    finding = next(f for f in _detect(session, wid) if citation_id in f["description"])
    _assert_orphan(finding, "ORPHAN_CITATION")


def test_finding_without_run_detected(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    missing_run_id = str(uuid.uuid4())
    finding_id = _finding(session, wid, missing_run_id)
    session.commit()

    finding = next(f for f in _detect(session, wid) if finding_id in f["description"])
    _assert_orphan(finding, "ORPHAN_FINDING")


def test_metric_without_snapshot_detected_when_deferred_tables_exist(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    metric_id = str(uuid.uuid4())
    missing_snapshot_id = str(uuid.uuid4())
    session.execute(text("CREATE TABLE data_quality_snapshots (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL)"))
    session.execute(
        text(
            "CREATE TABLE data_quality_metrics ("
            "id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, snapshot_id TEXT NOT NULL)"
        )
    )
    session.execute(
        text(
            "INSERT INTO data_quality_metrics (id, workspace_id, snapshot_id) "
            "VALUES (:id, :workspace_id, :snapshot_id)"
        ),
        {"id": metric_id, "workspace_id": wid, "snapshot_id": missing_snapshot_id},
    )
    session.commit()

    finding = next(f for f in _detect(session, wid) if metric_id in f["description"])
    _assert_orphan(finding, "ORPHAN_FINDING")
    assert finding["title"] == "Metric without snapshot"


def test_absent_deferred_metric_tables_do_not_fail(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)

    assert _detect(session, wid) == []


def test_workspace_isolation_for_scoped_orphans(session, engine):
    wa = _wid()
    wb = _wid()
    _seed_workspace(session, wa)
    _seed_workspace(session, wb)
    _citation(session, wb, str(uuid.uuid4()), str(uuid.uuid4()))
    _finding(session, wb, str(uuid.uuid4()))
    session.commit()

    assert _detect(session, wa) == []


def test_no_document_chunk_citation_or_finding_mutation(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid)
    vid = _version(session, did)
    chunk_id = _chunk(session, did, vid)
    _citation(session, wid, did, chunk_id)
    run_id = _run(session, wid)
    _finding(session, wid, run_id)
    session.commit()

    before_docs = session.execute(text("SELECT id, updated_at FROM documents")).fetchall()
    before_chunks = session.execute(text("SELECT id, is_searchable FROM document_chunks")).fetchall()
    before_citations = session.execute(text("SELECT id, source_status FROM chat_citations")).fetchall()
    before_findings = session.execute(text("SELECT id, run_id FROM data_quality_findings")).fetchall()

    _detect(session, wid)
    session.commit()

    after_docs = session.execute(text("SELECT id, updated_at FROM documents")).fetchall()
    after_chunks = session.execute(text("SELECT id, is_searchable FROM document_chunks")).fetchall()
    after_citations = session.execute(text("SELECT id, source_status FROM chat_citations")).fetchall()
    after_findings = session.execute(text("SELECT id, run_id FROM data_quality_findings")).fetchall()

    assert set(before_docs) == set(after_docs)
    assert set(before_chunks) == set(after_chunks)
    assert set(before_citations) == set(after_citations)
    assert set(before_findings) == set(after_findings)


def test_finding_shape_and_clean_state(session, engine):
    wid = _wid()
    _seed_workspace(session, wid)
    did = _doc(session, wid)
    vid = _version(session, did)
    chunk_id = _chunk(session, did, vid)
    _citation(session, wid, did, chunk_id)
    run_id = _run(session, wid)
    _finding(session, wid, run_id)
    session.commit()

    assert _detect(session, wid) == []

    _citation(session, wid, str(uuid.uuid4()), str(uuid.uuid4()))
    session.commit()
    findings = _detect(session, wid)
    required = {"finding_type", "severity", "document_id", "version_id", "chunk_id", "title", "description", "remediation"}
    for finding in findings:
        assert required <= set(finding.keys())
        assert finding["severity"] == "warning"
        assert finding["remediation"] == "Nur melden. Keine automatische Reparatur."
        assert "run_id" not in finding
