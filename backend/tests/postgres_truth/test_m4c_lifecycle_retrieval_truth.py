from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.documents.lifecycle_service import DocumentLifecycleService
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m4c_gate]


def test_m4c_archive_excludes_document_from_search_restore_reactivates(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    """
    M4c Areas 2, 3, 4:
    - active document appears in search
    - archived document does NOT appear in search
    - restored document appears in search again
    """
    term = truth_ids.term("m4c-archive-search")
    doc_id = truth_ids.document_id("m4c-archive-search")
    version_id = truth_ids.version_id("m4c-archive-search")
    chunk_id = truth_ids.chunk_id("m4c-archive-search")
    workspace_id = truth_seed["workspace_id"]

    _seed_active_searchable_document(
        truth_session,
        truth_ids=truth_ids,
        document_id=doc_id,
        version_id=version_id,
        chunk_id=chunk_id,
        workspace_id=workspace_id,
        user_id=truth_seed["user_id"],
        title=f"M4c Archive Test {truth_ids.slug}",
        content=f"{term} lifecycle retrieval test",
    )

    # Active: document must appear in search
    resp = truth_client.get("/api/v1/search/chunks", params={"q": term})
    assert resp.status_code == 200, f"search failed: {resp.text}"
    assert any(r["document_id"] == doc_id for r in resp.json()), "active document must appear in search"

    # Archive → must be excluded from search
    svc = DocumentLifecycleService.from_session(truth_session)
    svc.archive(document_id=doc_id, workspace_id=workspace_id)
    truth_session.expire_all()

    resp_archived = truth_client.get("/api/v1/search/chunks", params={"q": term})
    assert resp_archived.status_code == 200
    assert not any(r["document_id"] == doc_id for r in resp_archived.json()), \
        "archived document must NOT appear in search"

    # Restore → must reappear in search
    svc.restore(document_id=doc_id, workspace_id=workspace_id)
    truth_session.expire_all()

    resp_restored = truth_client.get("/api/v1/search/chunks", params={"q": term})
    assert resp_restored.status_code == 200
    assert any(r["document_id"] == doc_id for r in resp_restored.json()), \
        "restored document must reappear in search"


def test_m4c_historical_citations_reflect_live_source_status(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    """
    M4c Areas 6, 7, 8:
    - citation source_status reflects live lifecycle state via API (live override)
    - message content remains readable after archive and delete (chat replay stable)
    """
    doc_id = truth_ids.document_id("m4c-citation-lifecycle")
    version_id = truth_ids.version_id("m4c-citation-lifecycle")
    chunk_id = truth_ids.chunk_id("m4c-citation-lifecycle")
    session_id = truth_ids.chat_session_id("m4c-citation-lifecycle")
    message_id = truth_ids.chat_message_id("m4c-citation-lifecycle")
    citation_id = truth_ids.citation_id("m4c-citation-lifecycle")
    workspace_id = truth_seed["workspace_id"]
    term = truth_ids.term("m4c-citation-lifecycle")

    _seed_active_searchable_document(
        truth_session,
        truth_ids=truth_ids,
        document_id=doc_id,
        version_id=version_id,
        chunk_id=chunk_id,
        workspace_id=workspace_id,
        user_id=truth_seed["user_id"],
        title=f"M4c Citation Lifecycle {truth_ids.slug}",
        content=f"{term} citation source status test",
    )

    # Seed chat session with assistant message + citation
    truth_session.execute(
        text(
            """
            insert into chat_sessions (id, workspace_id, owner_user_id, title, created_at, updated_at)
            values (:id, :workspace_id, :user_id, 'M4c Citation Test', now(), now())
            """
        ),
        {"id": session_id, "workspace_id": workspace_id, "user_id": truth_seed["user_id"]},
    )
    truth_session.execute(
        text(
            """
            insert into chat_messages
                (id, session_id, message_index, role, content, basis_type, metadata, created_at)
            values
                (:id, :session_id, 0, 'assistant', :content, 'knowledge_base',
                 cast(:metadata as jsonb), now())
            """
        ),
        {
            "id": message_id,
            "session_id": session_id,
            "content": f"Found relevant content about {term}.",
            "metadata": json.dumps({}),
        },
    )
    truth_session.execute(
        text(
            """
            insert into chat_citations
                (id, message_id, chunk_id, document_id, document_title,
                 quote_preview, source_anchor, source_status)
            values
                (:id, :message_id, :chunk_id, :document_id, :document_title,
                 :quote_preview, cast(:source_anchor as jsonb), 'active')
            """
        ),
        {
            "id": citation_id,
            "message_id": message_id,
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "document_title": f"M4c Citation Lifecycle {truth_ids.slug}",
            "quote_preview": f"{term} citation source status test",
            "source_anchor": json.dumps(
                {"type": "text", "page": None, "paragraph": 1, "char_start": 0, "char_end": 30}
            ),
        },
    )
    truth_session.commit()

    def _fetch_citation() -> dict:
        r = truth_client.get(f"/api/v1/chat/sessions/{session_id}")
        assert r.status_code == 200, f"session fetch failed: {r.text}"
        msgs = r.json()["messages"]
        assert len(msgs) == 1
        assert len(msgs[0]["citations"]) == 1
        return msgs[0]["citations"][0], msgs[0]["content"]

    # Active document → source_status must be "active", message content readable
    citation, content = _fetch_citation()
    assert citation["source_status"] == "active", f"expected active, got {citation['source_status']}"
    assert citation["document_id"] == doc_id
    assert len(content) > 0, "message content must be readable"

    # Archive → source_status must reflect "archived"
    svc = DocumentLifecycleService.from_session(truth_session)
    svc.archive(document_id=doc_id, workspace_id=workspace_id)
    truth_session.expire_all()

    citation_after_archive, content_after_archive = _fetch_citation()
    assert citation_after_archive["source_status"] == "archived", \
        f"expected archived, got {citation_after_archive['source_status']}"
    assert len(content_after_archive) > 0, "message content must remain readable after archive"

    # Delete → source_status must reflect "deleted"
    svc.delete(document_id=doc_id, workspace_id=workspace_id)
    truth_session.expire_all()

    citation_after_delete, content_after_delete = _fetch_citation()
    assert citation_after_delete["source_status"] == "deleted", \
        f"expected deleted, got {citation_after_delete['source_status']}"
    assert len(content_after_delete) > 0, "message content must remain readable after delete (chat replay stable)"


def _seed_active_searchable_document(
    session: Session,
    *,
    truth_ids: TruthIds,
    document_id: str,
    version_id: str,
    chunk_id: str,
    workspace_id: str,
    user_id: str,
    title: str,
    content: str,
) -> None:
    created = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)
    session.execute(
        text(
            """
            insert into documents
                (id, workspace_id, owner_user_id, current_version_id, title, source_type,
                 mime_type, content_hash, import_status, lifecycle_status,
                 archived_at, deleted_at, created_at, updated_at)
            values
                (:id, :workspace_id, :user_id, null, :title, 'upload', 'text/plain',
                 :content_hash, 'pending', 'active', null, null, :created_at, :created_at)
            """
        ),
        {
            "id": document_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "title": title,
            "content_hash": truth_ids.content_hash(f"m4c-doc-{document_id}"),
            "created_at": created,
        },
    )
    session.execute(
        text(
            """
            insert into document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash,
                 parser_version, ocr_used, ki_provider, ki_model, metadata, created_at)
            values
                (:version_id, :document_id, 1, :content, :markdown_hash, 'truth-parser',
                 false, null, null, cast(:metadata as jsonb), :created_at)
            """
        ),
        {
            "version_id": version_id,
            "document_id": document_id,
            "content": content,
            "markdown_hash": truth_ids.content_hash(f"m4c-md-{version_id}"),
            "metadata": json.dumps({}),
            "created_at": created,
        },
    )
    session.execute(
        text(
            """
            insert into document_chunks
                (id, document_id, document_version_id, chunk_index, heading_path, anchor,
                 content, is_searchable, content_hash, token_estimate, metadata, created_at)
            values
                (:chunk_id, :document_id, :version_id, 0, cast(:heading_path as jsonb),
                 :anchor, :content, true, :content_hash, 20,
                 cast(:metadata as jsonb), :created_at)
            """
        ),
        {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "version_id": version_id,
            "heading_path": json.dumps([]),
            "anchor": f"truth-m4c-{chunk_id[-12:]}",
            "content": content,
            "content_hash": truth_ids.content_hash(f"m4c-chunk-{chunk_id}"),
            "metadata": json.dumps(
                {
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": 1,
                        "char_start": 0,
                        "char_end": len(content),
                    }
                }
            ),
            "created_at": created,
        },
    )
    session.execute(
        text(
            "update documents set current_version_id = :version_id, import_status = 'chunked' "
            "where id = :document_id"
        ),
        {"version_id": version_id, "document_id": document_id},
    )
    session.commit()
