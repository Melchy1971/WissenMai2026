from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.models.documents import ChatCitation, Chunk, Document
from app.services.orphan_detector import OrphanObjectDetector


pytestmark = [pytest.mark.postgres_truth, pytest.mark.m5_truth]


def _now() -> datetime:
    return datetime(2026, 6, 5, 9, 30, tzinfo=UTC)


def _execute_with_disabled_triggers(session, table_name: str, statement, params: dict) -> None:
    session.execute(text(f"alter table {table_name} disable trigger all"))
    try:
        session.execute(statement, params)
    finally:
        session.execute(text(f"alter table {table_name} enable trigger all"))


def _seed_document_source(session, truth_seed: dict[str, str], truth_ids, *, label: str) -> tuple[str, str, str]:
    document_id = truth_ids.document_id(label)
    version_id = truth_ids.version_id(label)
    chunk_id = truth_ids.chunk_id(label)
    timestamp = _now()
    session.execute(
        text(
            """
            insert into documents (
                id, workspace_id, owner_user_id, current_version_id, title,
                source_type, mime_type, content_hash, import_status,
                lifecycle_status, created_at, updated_at
            )
            values (
                :document_id, :workspace_id, :user_id, null, :title,
                'upload', 'text/plain', :content_hash, 'pending',
                'active', :created_at, :updated_at
            )
            """
        ),
        {
            "document_id": document_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "title": f"Orphan Truth {label}",
            "content_hash": truth_ids.content_hash(label),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    session.execute(
        text(
            """
            insert into document_versions (
                id, document_id, version_number, normalized_markdown,
                markdown_hash, parser_version, ocr_used, metadata, created_at
            )
            values (
                :version_id, :document_id, 1, :markdown,
                :markdown_hash, 'truth-1', false, cast(:metadata as jsonb), :created_at
            )
            """
        ),
        {
            "version_id": version_id,
            "document_id": document_id,
            "markdown": f"# Orphan Truth {label}\n",
            "markdown_hash": truth_ids.content_hash(f"markdown-{label}"),
            "metadata": json.dumps({}),
            "created_at": timestamp,
        },
    )
    _insert_chunk(
        session,
        chunk_id=chunk_id,
        document_id=document_id,
        version_id=version_id,
        truth_ids=truth_ids,
        label=label,
    )
    session.execute(
        text("update documents set current_version_id=:version_id, import_status='chunked' where id=:document_id"),
        {"version_id": version_id, "document_id": document_id},
    )
    return document_id, version_id, chunk_id


def _insert_chunk(session, *, chunk_id: str, document_id: str, version_id: str, truth_ids, label: str) -> None:
    session.execute(
        text(
            """
            insert into document_chunks (
                id, document_id, document_version_id, chunk_index, heading_path,
                anchor, content, is_searchable, content_hash, token_estimate,
                metadata, created_at
            )
            values (
                :chunk_id, :document_id, :version_id, 0, cast(:heading_path as jsonb),
                :anchor, :content, true, :content_hash, 6,
                cast(:metadata as jsonb), :created_at
            )
            """
        ),
        {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "version_id": version_id,
            "heading_path": json.dumps(["truth"]),
            "anchor": f"truth-{label}",
            "content": f"orphan truth content {label}",
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
            "created_at": _now(),
        },
    )


def _seed_chat_message(session, truth_seed: dict[str, str], truth_ids, *, label: str) -> str:
    chat_session_id = truth_ids.chat_session_id(label)
    message_id = truth_ids.chat_message_id(label)
    timestamp = _now()
    session.execute(
        text(
            """
            insert into chat_sessions (id, workspace_id, owner_user_id, title, created_at, updated_at)
            values (:id, :workspace_id, :user_id, :title, :created_at, :updated_at)
            """
        ),
        {
            "id": chat_session_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "title": f"Orphan Truth {label}",
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    session.execute(
        text(
            """
            insert into chat_messages (id, session_id, message_index, role, content, basis_type, metadata, created_at)
            values (:id, :session_id, 0, 'assistant', 'truth answer', 'knowledge_base', cast(:metadata as jsonb), :created_at)
            """
        ),
        {
            "id": message_id,
            "session_id": chat_session_id,
            "metadata": json.dumps({}),
            "created_at": timestamp,
        },
    )
    return message_id


def _detect(session, truth_seed: dict[str, str]) -> list[dict]:
    return OrphanObjectDetector(session, truth_seed["workspace_id"]).detect()


def test_m5a_orphan_detector_detects_chunk_without_document_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    chunk_id = truth_ids.chunk_id("orphan-chunk")
    missing_document_id = truth_ids.document_id("missing-for-chunk")
    missing_version_id = truth_ids.version_id("missing-for-chunk")
    _execute_with_disabled_triggers(
        truth_session,
        "document_chunks",
        text(
            """
            insert into document_chunks (
                id, document_id, document_version_id, chunk_index, heading_path,
                anchor, content, is_searchable, content_hash, token_estimate,
                metadata, created_at
            )
            values (
                :chunk_id, :document_id, :version_id, 0, cast(:heading_path as jsonb),
                'truth-orphan-chunk', 'orphan chunk', true, :content_hash, 3,
                cast(:metadata as jsonb), :created_at
            )
            """
        ),
        {
            "chunk_id": chunk_id,
            "document_id": missing_document_id,
            "version_id": missing_version_id,
            "heading_path": json.dumps(["truth"]),
            "content_hash": truth_ids.content_hash("orphan-chunk"),
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
            "created_at": _now(),
        },
    )

    findings = _detect(truth_session, truth_seed)

    assert any(f["chunk_id"] == chunk_id and f["finding_type"] == "ORPHAN_CHUNK" for f in findings)


def test_m5a_orphan_detector_detects_version_without_document_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    version_id = truth_ids.version_id("orphan-version")
    missing_document_id = truth_ids.document_id("missing-for-version")
    _execute_with_disabled_triggers(
        truth_session,
        "document_versions",
        text(
            """
            insert into document_versions (
                id, document_id, version_number, normalized_markdown,
                markdown_hash, parser_version, ocr_used, metadata, created_at
            )
            values (
                :version_id, :document_id, 1, 'orphan version',
                :markdown_hash, 'truth-1', false, cast(:metadata as jsonb), :created_at
            )
            """
        ),
        {
            "version_id": version_id,
            "document_id": missing_document_id,
            "markdown_hash": truth_ids.content_hash("orphan-version"),
            "metadata": json.dumps({}),
            "created_at": _now(),
        },
    )

    findings = _detect(truth_session, truth_seed)

    assert any(f["version_id"] == version_id and f["finding_type"] == "ORPHAN_VERSION" for f in findings)


def test_m5a_orphan_detector_detects_citation_without_source_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    message_id = _seed_chat_message(truth_session, truth_seed, truth_ids, label="orphan-citation")
    citation_id = truth_ids.citation_id("orphan-citation")
    missing_document_id = truth_ids.document_id("missing-for-citation")
    missing_chunk_id = truth_ids.chunk_id("missing-for-citation")
    _execute_with_disabled_triggers(
        truth_session,
        "chat_citations",
        text(
            """
            insert into chat_citations (
                id, message_id, chunk_id, document_id, document_title,
                quote_preview, source_anchor, source_status
            )
            values (
                :citation_id, :message_id, :chunk_id, :document_id, 'Missing Source',
                'truth', cast(:source_anchor as jsonb), 'active'
            )
            """
        ),
        {
            "citation_id": citation_id,
            "message_id": message_id,
            "chunk_id": missing_chunk_id,
            "document_id": missing_document_id,
            "source_anchor": json.dumps({"type": "text"}),
        },
    )

    findings = _detect(truth_session, truth_seed)

    assert any(
        citation_id in f["description"] and f["finding_type"] == "ORPHAN_CITATION"
        for f in findings
    )


def test_m5a_orphan_detector_clean_state_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    document_id, _version_id, chunk_id = _seed_document_source(
        truth_session, truth_seed, truth_ids, label="clean"
    )
    message_id = _seed_chat_message(truth_session, truth_seed, truth_ids, label="clean")
    truth_session.execute(
        text(
            """
            insert into chat_citations (
                id, message_id, chunk_id, document_id, document_title,
                quote_preview, source_anchor, source_status
            )
            values (
                :citation_id, :message_id, :chunk_id, :document_id, 'Clean Source',
                'truth', cast(:source_anchor as jsonb), 'active'
            )
            """
        ),
        {
            "citation_id": truth_ids.citation_id("clean"),
            "message_id": message_id,
            "chunk_id": chunk_id,
            "document_id": document_id,
            "source_anchor": json.dumps({"type": "text"}),
        },
    )

    assert _detect(truth_session, truth_seed) == []


def test_m5a_orphan_detector_is_read_only_postgres(
    truth_session,
    truth_seed: dict[str, str],
    truth_ids,
) -> None:
    document_id, _version_id, chunk_id = _seed_document_source(
        truth_session, truth_seed, truth_ids, label="read-only"
    )
    run_id = f"truth-{truth_ids.slug}-dq-run"
    finding_id = f"truth-{truth_ids.slug}-dq-finding"
    timestamp = _now()
    truth_session.add(
        DataQualityRun(
            id=run_id,
            workspace_id=truth_seed["workspace_id"],
            status="completed",
            started_at=timestamp,
            finished_at=timestamp,
        )
    )
    truth_session.flush()
    truth_session.add(
        DataQualityFinding(
            id=finding_id,
            run_id=run_id,
            workspace_id=truth_seed["workspace_id"],
            finding_type="ORPHAN_CHUNK",
            severity="warning",
            document_id=document_id,
            chunk_id=chunk_id,
            title="existing finding",
            description="existing finding",
            remediation="review",
            created_at=timestamp,
        )
    )
    truth_session.flush()
    before = {
        "document": truth_session.get(Document, document_id).updated_at,
        "chunk": truth_session.get(Chunk, chunk_id).is_searchable,
        "finding": truth_session.get(DataQualityFinding, finding_id).run_id,
    }
    _detect(truth_session, truth_seed)
    truth_session.flush()
    after = {
        "document": truth_session.get(Document, document_id).updated_at,
        "chunk": truth_session.get(Chunk, chunk_id).is_searchable,
        "finding": truth_session.get(DataQualityFinding, finding_id).run_id,
    }

    assert after == before
