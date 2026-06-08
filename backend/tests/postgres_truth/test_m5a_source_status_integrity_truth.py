from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.models.documents import ChatCitation, ChatMessage, ChatSession, Chunk, Document, DocumentVersion
from app.services.source_status_integrity_detector import SourceStatusIntegrityDetector


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


def _now() -> datetime:
    return datetime(2026, 6, 5, 9, 0, tzinfo=UTC)


def _seed_document_source(
    session,
    truth_seed: dict[str, str],
    truth_ids,
    *,
    label: str,
    lifecycle_status: str = "active",
    import_status: str = "parsed",
    is_searchable: bool = True,
) -> tuple[str, str]:
    document_id = truth_ids.document_id(label)
    version_id = truth_ids.version_id(label)
    chunk_id = truth_ids.chunk_id(label)
    timestamp = _now()

    session.add(
        Document(
            id=document_id,
            workspace_id=truth_seed["workspace_id"],
            owner_user_id=truth_seed["user_id"],
            current_version_id=None,
            title=f"Source Status Truth {label}",
            source_type="upload",
            mime_type="text/plain",
            content_hash=truth_ids.content_hash(label),
            import_status="pending",
            lifecycle_status=lifecycle_status,
            archived_at=timestamp if lifecycle_status == "archived" else None,
            deleted_at=timestamp if lifecycle_status == "deleted" else None,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    session.flush()
    session.add(
        DocumentVersion(
            id=version_id,
            document_id=document_id,
            version_number=1,
            normalized_markdown=f"# Source Status Truth {label}\n",
            markdown_hash=truth_ids.content_hash(f"markdown-{label}"),
            parser_version="truth-1",
            ocr_used=False,
            metadata_={},
            created_at=timestamp,
        )
    )
    session.flush()
    document = session.get(Document, document_id)
    document.current_version_id = version_id
    document.import_status = import_status
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
                0,
                cast(:heading_path as jsonb),
                :anchor,
                :content,
                :is_searchable,
                :content_hash,
                6,
                cast(:metadata as jsonb),
                :created_at
            )
            """
        ),
        {
            "id": chunk_id,
            "document_id": document_id,
            "document_version_id": version_id,
            "heading_path": json.dumps(["truth"]),
            "anchor": f"truth-{label}",
            "content": f"source status truth content {label}",
            "is_searchable": is_searchable,
            "content_hash": truth_ids.content_hash(f"chunk-{label}"),
            "metadata": json.dumps(
                {
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": None,
                        "char_start": 0,
                        "char_end": 12,
                    }
                }
            ),
            "created_at": timestamp,
        },
    )
    session.flush()
    return document_id, chunk_id


def _seed_citation(
    session,
    truth_seed: dict[str, str],
    truth_ids,
    *,
    label: str,
    document_id: str,
    chunk_id: str | None,
    source_status: str,
) -> str:
    timestamp = _now()
    chat_session_id = truth_ids.chat_session_id(label)
    message_id = truth_ids.chat_message_id(label)
    citation_id = truth_ids.citation_id(label)
    session.add(
        ChatSession(
            id=chat_session_id,
            workspace_id=truth_seed["workspace_id"],
            owner_user_id=truth_seed["user_id"],
            title=f"Source Status Truth {label}",
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    session.flush()
    session.add(
        ChatMessage(
            id=message_id,
            session_id=chat_session_id,
            message_index=0,
            role="assistant",
            content="truth answer",
            basis_type="knowledge_base",
            metadata_={},
            created_at=timestamp,
        )
    )
    session.flush()
    session.add(
        ChatCitation(
            id=citation_id,
            message_id=message_id,
            chunk_id=chunk_id,
            document_id=document_id,
            document_title="Source Status Truth",
            quote_preview="truth",
            source_anchor={"type": "text"},
            source_status=source_status,
        )
    )
    session.flush()
    return citation_id


def _detect(session, truth_seed: dict[str, str]) -> list[dict]:
    return SourceStatusIntegrityDetector(session, truth_seed["workspace_id"]).detect()


def test_m5a_source_status_integrity_detects_active_status_mismatch_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    document_id, chunk_id = _seed_document_source(truth_session, truth_seed, truth_ids, label="active-mismatch")
    _seed_citation(
        truth_session,
        truth_seed,
        truth_ids,
        label="active-mismatch",
        document_id=document_id,
        chunk_id=chunk_id,
        source_status="archived",
    )
    truth_session.flush()

    findings = _detect(truth_session, truth_seed)

    assert any(
        finding["document_id"] == document_id
        and finding["finding_type"] == "INVALID_SOURCE_STATUS"
        and finding["title"] == "Active source status mismatch"
        for finding in findings
    )


def test_m5a_source_status_integrity_clean_state_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    document_id, chunk_id = _seed_document_source(truth_session, truth_seed, truth_ids, label="clean")
    _seed_citation(
        truth_session,
        truth_seed,
        truth_ids,
        label="clean",
        document_id=document_id,
        chunk_id=chunk_id,
        source_status="active",
    )
    truth_session.flush()

    assert _detect(truth_session, truth_seed) == []


def test_m5a_source_status_integrity_is_read_only_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    document_id, chunk_id = _seed_document_source(truth_session, truth_seed, truth_ids, label="read-only")
    citation_id = _seed_citation(
        truth_session,
        truth_seed,
        truth_ids,
        label="read-only",
        document_id=document_id,
        chunk_id=chunk_id,
        source_status="active",
    )
    truth_session.flush()

    before = {
        "document": truth_session.get(Document, document_id).lifecycle_status,
        "chunk": truth_session.get(Chunk, chunk_id).is_searchable,
        "citation": truth_session.get(ChatCitation, citation_id).source_status,
    }
    _detect(truth_session, truth_seed)
    truth_session.flush()
    after = {
        "document": truth_session.get(Document, document_id).lifecycle_status,
        "chunk": truth_session.get(Chunk, chunk_id).is_searchable,
        "citation": truth_session.get(ChatCitation, citation_id).source_status,
    }

    assert after == before
