from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.jobs.background_jobs import BackgroundJobService, process_import_job, process_search_index_rebuild_job
from app.services.chat.citation_mapper import CitationMapper
from app.services.chat.context_builder import ContextBuilder
from app.services.chat.fake_llm_provider import FakeLlmProvider
from app.services.chat.insufficient_context_policy import InsufficientContextPolicy, InsufficientContextThresholds
from app.services.chat.persistence_service import ChatPersistenceService
from app.services.chat.prompt_builder import PromptBuilder
from app.services.chat.rag_chat_service import RagChatService
from app.services.search_service import SearchService
from app.services.search_index_service import SearchIndexRebuildService
from app.main import app

from tests.postgres_truth.support import (
    TruthIds,
    assert_no_truth_rows,
)


pytestmark = pytest.mark.postgres_truth


@dataclass(frozen=True)
class SearchTruthIds:
    doc_active: str
    doc_archived: str
    doc_other_ws: str
    doc_deleted: str
    ver_active: str
    ver_archived: str
    ver_other_ws: str
    ver_deleted: str
    chunk_active: str
    chunk_archived: str
    chunk_other_ws: str
    chunk_deleted: str
    term: str


def _search_truth_ids(truth_ids: TruthIds) -> SearchTruthIds:
    return SearchTruthIds(
        doc_active=truth_ids.document_id("active"),
        doc_archived=truth_ids.document_id("archived"),
        doc_other_ws=truth_ids.document_id("other-workspace"),
        doc_deleted=truth_ids.document_id("deleted"),
        ver_active=truth_ids.version_id("active"),
        ver_archived=truth_ids.version_id("archived"),
        ver_other_ws=truth_ids.version_id("other-workspace"),
        ver_deleted=truth_ids.version_id("deleted"),
        chunk_active=truth_ids.chunk_id("active"),
        chunk_archived=truth_ids.chunk_id("archived"),
        chunk_other_ws=truth_ids.chunk_id("other-workspace"),
        chunk_deleted=truth_ids.chunk_id("deleted"),
        term=truth_ids.term("retrieval"),
    )


@pytest.mark.m4_truth
def test_truth_cleanup_starts_without_stale_state(truth_session: Session) -> None:
    assert_no_truth_rows(truth_session)


@pytest.mark.m4b_upload_queue_truth
def test_upload_and_duplicate_handling_use_real_postgresql_transactions(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    first = truth_client.post(
        "/documents/import",
        files={"file": (f"{truth_ids.slug}.txt", f"# Truth\n\nsame duplicate content {truth_ids.namespace}\n".encode(), "text/plain")},
    )
    second = truth_client.post(
        "/documents/import",
        files={"file": (f"{truth_ids.slug}.txt", f"# Truth\n\nsame duplicate content {truth_ids.namespace}\n".encode(), "text/plain")},
    )

    assert first.status_code == 202
    assert second.status_code == 202

    first_job = truth_client.get(f"/documents/import-jobs/{first.json()['id']}")
    second_job = truth_client.get(f"/documents/import-jobs/{second.json()['id']}")
    assert first_job.status_code == 200
    assert second_job.status_code == 200

    results = [first_job.json()["result"], second_job.json()["result"]]
    assert sorted(result["import_status"] for result in results) == ["chunked", "duplicate"]
    assert len({result["document_id"] for result in results}) == 1

    assert truth_session.execute(text("select count(*) from documents where workspace_id = :workspace_id"), {"workspace_id": truth_seed["workspace_id"]}).scalar_one() == 1
    assert truth_session.execute(
        text(
            """
            select count(*)
            from document_versions v
            join documents d on d.id = v.document_id
            where d.workspace_id = :workspace_id
            """
        ),
        {"workspace_id": truth_seed["workspace_id"]},
    ).scalar_one() == 1
    assert truth_session.execute(
        text(
            """
            select count(*)
            from document_chunks c
            join documents d on d.id = c.document_id
            where d.workspace_id = :workspace_id
            """
        ),
        {"workspace_id": truth_seed["workspace_id"]},
    ).scalar_one() == 1


@pytest.mark.m4_truth
def test_lifecycle_and_workspace_isolation_are_truth_checked(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    ids = _search_truth_ids(truth_ids)
    _seed_search_documents(truth_session, truth_ids=truth_ids, truth_seed=truth_seed, ids=ids)

    archive = truth_client.patch(f"/documents/{ids.doc_active}/archive")
    assert archive.status_code == 200
    assert archive.json()["lifecycle_status"] == "archived"
    assert truth_session.execute(text("select is_searchable from document_chunks where id = :id"), {"id": ids.chunk_active}).scalar_one() is False

    restore = truth_client.patch(f"/documents/{ids.doc_active}/restore")
    assert restore.status_code == 200
    assert restore.json()["lifecycle_status"] == "active"
    assert truth_session.execute(text("select is_searchable from document_chunks where id = :id"), {"id": ids.chunk_active}).scalar_one() is True

    forbidden = truth_client.patch(f"/documents/{ids.doc_other_ws}/archive")
    assert forbidden.status_code in {403, 404}
    assert truth_session.execute(text("select lifecycle_status from documents where id = :id"), {"id": ids.doc_other_ws}).scalar_one() == "active"


@pytest.mark.governance_truth
def test_search_chat_retrieval_and_reindex_use_real_postgresql_state(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    ids = _search_truth_ids(truth_ids)
    _seed_search_documents(truth_session, truth_ids=truth_ids, truth_seed=truth_seed, ids=ids)

    search = truth_client.get("/api/v1/search/chunks", params={"q": ids.term})
    assert search.status_code == 200
    assert [item["document_id"] for item in search.json()] == [ids.doc_active]

    rag_service = RagChatService(
        persistence=ChatPersistenceService(truth_session),
        retrieval=SearchService.from_session(truth_session),
        context_builder=ContextBuilder(max_context_chars=12000, max_context_tokens=2500, min_chunk_chars=40),
        prompt_builder=PromptBuilder(),
        insufficient_context_policy=InsufficientContextPolicy(InsufficientContextThresholds(min_retrieval_score=0.0)),
        llm_provider=FakeLlmProvider(),
        citation_mapper=CitationMapper(),
        retrieval_limit=5,
    )
    chat_session = ChatPersistenceService(truth_session).create_session(
        workspace_id=truth_seed["workspace_id"],
        title=f"truth chat {truth_ids.slug}",
        owner_user_id=truth_seed["user_id"],
    )
    answer = rag_service.answer_question(
        session_id=chat_session.id,
        workspace_id=truth_seed["workspace_id"],
        question=ids.term,
        retrieval_limit=5,
    )
    assert answer.citations
    assert {citation.document_id for citation in answer.citations} == {ids.doc_active}

    truth_session.execute(text("update document_chunks set is_searchable = false where id = :id"), {"id": ids.chunk_active})
    truth_session.commit()

    # After corruption: active chunk's search_vector is empty (GENERATED ALWAYS AS from is_searchable=False)
    # so FTS returns no results
    corrupted_search = truth_client.get("/api/v1/search/chunks", params={"q": ids.term})
    assert corrupted_search.status_code == 200
    assert corrupted_search.json() == []

    result = SearchIndexRebuildService.from_session(truth_session).rebuild_search_index(workspace_id=truth_seed["workspace_id"])
    assert result["status"] == "completed"
    assert truth_session.execute(text("select is_searchable from document_chunks where id = :id"), {"id": ids.chunk_active}).scalar_one() is True


@pytest.mark.governance_truth
def test_search_index_drift_endpoint_reports_real_postgresql_drift(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    ids = _search_truth_ids(truth_ids)
    duplicate_document_id = truth_ids.document_id("duplicate-drift")
    duplicate_version_id = truth_ids.version_id("duplicate-drift-current")
    duplicate_old_version_id = truth_ids.version_id("duplicate-drift-old")
    duplicate_chunk_id = truth_ids.chunk_id("duplicate-drift-current")
    duplicate_old_chunk_id = truth_ids.chunk_id("duplicate-drift-old")
    _seed_search_documents(truth_session, truth_ids=truth_ids, truth_seed=truth_seed, ids=ids)

    truth_session.execute(
        text(
            """
            update document_chunks
            set is_searchable = false
            where id = :chunk_id
            """
        ),
        {"chunk_id": ids.chunk_active},
    )
    truth_session.execute(
        text(
            """
            insert into documents
                (id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                 content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at)
            values
                (:document_id, :workspace_id, :owner_user_id, null, :title, 'upload', 'text/plain',
                 :content_hash, 'pending', 'active', null, null, now(), now())
            """
        ),
        {
            "document_id": duplicate_document_id,
            "workspace_id": truth_seed["workspace_id"],
            "owner_user_id": truth_seed["user_id"],
            "title": f"Truth Duplicate {truth_ids.slug}",
            "content_hash": truth_ids.content_hash("duplicate-drift"),
        },
    )
    truth_session.execute(
        text(
            """
            insert into document_versions
                (id, document_id, version_number, normalized_markdown, markdown_hash, parser_version,
                 ocr_used, ki_provider, ki_model, metadata, created_at)
            values
                (:version_id, :document_id, 1, :markdown, :markdown_hash, 'truth-parser',
                 false, null, null, cast(:metadata as jsonb), now()),
                (:old_version_id, :document_id, 2, :markdown, :old_markdown_hash, 'truth-parser',
                 false, null, null, cast(:metadata as jsonb), now() - interval '1 minute')
            """
        ),
        {
            "version_id": duplicate_version_id,
            "old_version_id": duplicate_old_version_id,
            "document_id": duplicate_document_id,
            "markdown": "# Duplicate\n\ntruth duplicate drift",
            "markdown_hash": truth_ids.content_hash("duplicate-drift-version"),
            "old_markdown_hash": truth_ids.content_hash("duplicate-drift-old-version"),
            "metadata": json.dumps({}),
        },
    )
    truth_session.execute(
        text(
            "update documents set current_version_id = :version_id, import_status = 'chunked' where id = :document_id"
        ),
        {
            "version_id": duplicate_version_id,
            "document_id": duplicate_document_id,
        },
    )
    truth_session.execute(
        text(
            """
            insert into document_chunks
                (id, document_id, document_version_id, chunk_index, heading_path, anchor, content,
                 is_searchable, content_hash, token_estimate, metadata, created_at)
            values
                (:chunk_a, :document_id, :version_id, 0, cast(:heading_path as jsonb), :anchor, :content_a,
                 true, :content_hash, 10, cast(:metadata as jsonb), now()),
                (:chunk_b, :document_id, :old_version_id, 0, cast(:heading_path as jsonb), :anchor, :content_b,
                 true, :content_hash, 10, cast(:metadata as jsonb), now())
            """
        ),
        {
            "chunk_a": duplicate_chunk_id,
            "chunk_b": duplicate_old_chunk_id,
            "document_id": duplicate_document_id,
            "version_id": duplicate_version_id,
            "old_version_id": duplicate_old_version_id,
            "heading_path": json.dumps([]),
            "anchor": "duplicate-anchor",
            "content_a": "truth duplicate drift A",
            "content_b": "truth duplicate drift B",
            "content_hash": truth_ids.content_hash("duplicate-drift-chunk"),
            "metadata": json.dumps({"source_anchor": {"type": "text", "page": None, "paragraph": 9, "char_start": 0, "char_end": 24}}),
        },
    )
    truth_session.commit()

    response = truth_client.get("/api/v1/admin/search-index/drift")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == truth_seed["workspace_id"]
    assert payload["status"] == "drifted"
    assert payload["severity"] == "critical"
    assert payload["drift_score"] == 20
    assert payload["deleted_documents_in_index"]["count"] == 1
    assert payload["deleted_documents_in_index"]["severity"] == "critical"
    assert payload["deleted_documents_in_index"]["sample_document_ids"] == [ids.doc_deleted]
    assert payload["archived_documents_in_active_index"]["count"] == 1
    assert payload["archived_documents_in_active_index"]["sample_document_ids"] == [ids.doc_archived]
    assert payload["duplicate_index_entries"]["count"] == 1
    assert payload["duplicate_index_entries"]["sample_document_ids"] == [duplicate_document_id]
    assert payload["invalid_lifecycle_status"]["count"] >= 3
    assert payload["index_without_chunk"]["status"] == "not_applicable"
    assert "reindexing the workspace" in payload["repair_recommendation"]


@pytest.mark.governance_truth
def test_search_and_chat_retrieval_use_identical_active_chunks_and_source_anchors(
    truth_client: TestClient,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    ids = _search_truth_ids(truth_ids)
    _seed_search_documents(truth_session, truth_ids=truth_ids, truth_seed=truth_seed, ids=ids)

    search_service = SearchService.from_session(truth_session)
    search_response = truth_client.get("/api/v1/search/chunks", params={"q": ids.term, "limit": 10})
    assert search_response.status_code == 200
    search_api_results = search_response.json()
    search_results = search_service.search_chunks(
        workspace_id=truth_seed["workspace_id"],
        query=ids.term,
        limit=10,
        offset=0,
    )

    recording_retrieval = RecordingRetrieval(search_service)
    rag_service = RagChatService(
        persistence=ChatPersistenceService(truth_session),
        retrieval=recording_retrieval,
        context_builder=ContextBuilder(max_context_chars=12000, max_context_tokens=2500, min_chunk_chars=40),
        prompt_builder=PromptBuilder(),
        insufficient_context_policy=InsufficientContextPolicy(InsufficientContextThresholds(min_retrieval_score=0.0)),
        llm_provider=FakeLlmProvider(),
        citation_mapper=CitationMapper(),
        retrieval_limit=10,
    )
    chat_session = ChatPersistenceService(truth_session).create_session(
        workspace_id=truth_seed["workspace_id"],
        title=f"truth consistency chat {truth_ids.slug}",
        owner_user_id=truth_seed["user_id"],
    )

    answer = rag_service.answer_question(
        session_id=chat_session.id,
        workspace_id=truth_seed["workspace_id"],
        question=ids.term,
        retrieval_limit=10,
    )

    chat_retrieval_results = recording_retrieval.last_results
    search_api_chunks = [_api_retrieval_signature(item) for item in search_api_results]
    search_chunks = [_retrieval_signature(item) for item in search_results]
    chat_chunks = [_retrieval_signature(item) for item in chat_retrieval_results]
    citation_chunks = [citation.chunk_id for citation in answer.citations]

    assert search_api_chunks == search_chunks, {
        "error": "SEARCH_API_SERVICE_MISMATCH",
        "search_api_chunks": search_api_chunks,
        "search_service_chunks": search_chunks,
    }
    assert search_chunks == chat_chunks, {
        "error": "SEARCH_CHAT_RETRIEVAL_MISMATCH",
        "search_chunks": search_chunks,
        "chat_chunks": chat_chunks,
    }
    assert citation_chunks == [ids.chunk_active]
    assert [item.chunk_id for item in search_results] == [ids.chunk_active]
    assert ids.chunk_archived not in [item.chunk_id for item in search_results]
    assert ids.chunk_deleted not in [item.chunk_id for item in search_results]
    assert all(item.source_anchor.model_dump() == chat_retrieval_results[index].source_anchor.model_dump() for index, item in enumerate(search_results))


@pytest.mark.m4a_auth_truth
def test_auth_workspace_truth_blocks_foreign_workspace_and_non_admin_diagnostics(
    truth_seed: dict[str, str],
) -> None:
    foreign_workspace_client = TestClient(
        app,
        headers={
            "Authorization": f"Bearer {truth_seed['token']}",
            "X-Workspace-Id": truth_seed["other_workspace_id"],
        },
    )
    response = foreign_workspace_client.get("/api/v1/admin/diagnostics")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.m4b_upload_queue_truth
def test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import_job_id = truth_ids.job_id("import-retry")
    doc_active = truth_ids.document_id("retry-active")
    ver_active = truth_ids.version_id("retry-active")
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', 'running', :workspace_id, :user_id, cast(:payload as jsonb), null,
                0, 1, 'running', null, null,
                1, now() - interval '10 minutes', 'stale-worker', now(), now(), null
            )
            """
        ),
        {
            "id": import_job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json.dumps(
                {
                    "filename": f"truth-retry-{truth_ids.slug}.txt",
                    "mime_type": "text/plain",
                    "temp_file_path": "unused-in-monkeypatch",
                }
            ),
        },
    )
    truth_session.commit()

    recovered = BackgroundJobService.from_session(truth_session).recover_stale_jobs(worker_id="truth-recovery")
    assert recovered == 1

    class SuccessfulImportExecutor:
        def execute(self, **_kwargs):
            return {
                "document_id": doc_active,
                "version_id": ver_active,
                "import_status": "duplicate",
                "duplicate_of_document_id": doc_active,
                "chunk_count": 1,
                "parser_type": "txt-parser",
                "warnings": [],
            }

    monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", SuccessfulImportExecutor)
    monkeypatch.setattr("app.services.jobs.background_jobs.Path.read_bytes", lambda _self: b"truth payload")

    process_import_job(import_job_id, truth_session.connection())

    job_row = truth_session.execute(
        text("select status, attempt_count, error_code from background_jobs where id = :id"),
        {"id": import_job_id},
    ).one()
    assert job_row.status == "completed"
    assert job_row.attempt_count == 2
    assert job_row.error_code is None


@pytest.mark.governance_truth
def test_postgres_truth_search_rebuild_failure_keeps_lifecycle_state_and_stays_retryable(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _search_truth_ids(truth_ids)
    reindex_job_id = truth_ids.job_id("reindex-failure")
    _seed_search_documents(truth_session, truth_ids=truth_ids, truth_seed=truth_seed, ids=ids)
    truth_session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'search_index_rebuild', 'pending', :workspace_id, :user_id, cast(:payload as jsonb), null,
                0, 1, 'pending', null, null,
                0, null, null, now(), null, null
            )
            """
        ),
        {
            "id": reindex_job_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "payload": json.dumps({"target_workspace_id": truth_seed["workspace_id"]}),
        },
    )
    truth_session.commit()

    class CrashingRebuildService:
        @classmethod
        def from_session(cls, _session):
            return cls()

        def rebuild_search_index(self, **_kwargs):
            raise RuntimeError("truth reindex crash")

    monkeypatch.setattr("app.services.jobs.background_jobs.SearchIndexRebuildService", CrashingRebuildService)

    process_search_index_rebuild_job(reindex_job_id, truth_session.connection())

    job_row = truth_session.execute(
        text("select status, error_code from background_jobs where id = :id"),
        {"id": reindex_job_id},
    ).one()
    assert job_row.status == "retryable"
    assert job_row.error_code == "SERVICE_UNAVAILABLE"
    assert truth_session.execute(text("select lifecycle_status from documents where id = :id"), {"id": ids.doc_archived}).scalar_one() == "archived"


@pytest.mark.governance_truth
def test_postgres_truth_chat_citations_use_missing_instead_of_unknown(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    document_id = truth_ids.document_id("chat-citation")
    session_id = truth_ids.chat_session_id("citation")
    message_id = truth_ids.chat_message_id("citation")
    citation_id = truth_ids.citation_id("missing")
    unknown_citation_id = truth_ids.citation_id("unknown")
    truth_session.execute(
        text(
            """
            insert into chat_sessions (id, workspace_id, owner_user_id, title, created_at, updated_at)
            values (:session_id, :workspace_id, :user_id, 'truth chat', now(), now())
            """
        ),
        {"session_id": session_id, "workspace_id": truth_seed["workspace_id"], "user_id": truth_seed["user_id"]},
    )
    truth_session.execute(
        text(
            """
            insert into chat_messages (id, session_id, message_index, role, content, basis_type, metadata, created_at)
            values (:message_id, :session_id, 0, 'assistant', 'historical answer', 'knowledge_base', cast(:metadata as jsonb), now())
            """
        ),
        {
            "message_id": message_id,
            "session_id": session_id,
            "metadata": json.dumps({}),
        },
    )
    truth_session.execute(
        text(
            """
            insert into documents (
                id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at
            ) values (
                :document_id, :workspace_id, :user_id, null, 'Truth citation document', 'upload', 'text/plain',
                :content_hash, 'pending', 'active', null, null, now(), now()
            )
            """
        ),
        {
            "document_id": document_id,
            "workspace_id": truth_seed["workspace_id"],
            "user_id": truth_seed["user_id"],
            "content_hash": truth_ids.content_hash("chat-citation"),
        },
    )
    truth_session.execute(
        text(
            """
            insert into chat_citations (id, message_id, chunk_id, document_id, document_title, quote_preview, source_anchor, source_status)
            values (:citation_id, :message_id, null, :document_id, 'Missing document', 'historical quote', cast(:source_anchor as jsonb), 'missing')
            """
        ),
        {
            "citation_id": citation_id,
            "message_id": message_id,
            "document_id": document_id,
            "source_anchor": json.dumps({"type": "text", "page": None, "paragraph": 1, "char_start": 0, "char_end": 16}),
        },
    )
    truth_session.commit()

    persisted = truth_session.execute(
        text("select source_status from chat_citations where id = :id"),
        {"id": citation_id},
    ).scalar_one()
    assert persisted == "missing"

    with pytest.raises(IntegrityError):
        truth_session.execute(
            text(
                """
                insert into chat_citations (id, message_id, chunk_id, document_id, document_title, quote_preview, source_anchor, source_status)
                values (:citation_id, :message_id, null, :document_id, 'Unknown document', 'historical quote', cast(:source_anchor as jsonb), 'unknown')
                """
            ),
            {
                "citation_id": unknown_citation_id,
                "message_id": message_id,
                "document_id": document_id,
                "source_anchor": json.dumps({"type": "text", "page": None, "paragraph": 1, "char_start": 0, "char_end": 16}),
            },
        )
        truth_session.commit()
    truth_session.rollback()


@pytest.mark.m4b_upload_queue_truth
def test_postgres_truth_parallel_replay_only_one_request_succeeds(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    postgres_truth_database_url: str,
) -> None:
    replay_job_id = truth_ids.job_id("parallel-replay")
    engine = create_engine(postgres_truth_database_url.replace("postgresql://", "postgresql+psycopg://", 1), pool_pre_ping=True)
    try:
        with Session(engine) as seed_session:
            seed_session.execute(
                text(
                    """
                    insert into background_jobs (
                        id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                        progress_current, progress_total, progress_message, error_code, error_message,
                        attempt_count, locked_at, locked_by, created_at, started_at, finished_at
                    ) values (
                        :id, 'document_import', 'dead_letter', :workspace_id, :user_id, cast(:payload as jsonb), null,
                        1, 1, 'Job in Dead Letter verschoben', 'IMPORT_FAILED', 'parallel replay failure',
                        3, null, null, now(), now(), now()
                    )
                    """
                ),
                {
                    "id": replay_job_id,
                    "workspace_id": truth_seed["workspace_id"],
                    "user_id": truth_seed["user_id"],
                    "payload": json.dumps({"filename": f"broken-{truth_ids.slug}.txt", "mime_type": "text/plain", "temp_file_path": "unused"}),
                },
            )
            seed_session.commit()

        barrier = threading.Barrier(2)
        results: list[str] = []
        errors: list[str] = []

        def replay(label: str) -> None:
            with Session(engine) as session:
                service = BackgroundJobService.from_session(session)
                try:
                    barrier.wait(timeout=5)
                    service.replay_job(job_id=replay_job_id, replayed_by_user_id=label)
                    results.append(label)
                except Exception as exc:
                    errors.append(type(exc).__name__)

        t1 = threading.Thread(target=replay, args=("admin-a",))
        t2 = threading.Thread(target=replay, args=("admin-b",))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert len(results) == 1, {"results": results, "errors": errors}
        assert len(errors) == 1, {"results": results, "errors": errors}

        with Session(engine) as verify_session:
            job = BackgroundJobService.from_session(verify_session).get_job(replay_job_id)
            response = BackgroundJobService.from_session(verify_session).to_response(job)
            assert job.status == "pending"
            assert response.previous_error is not None
            assert response.previous_error.previous_error_code == "IMPORT_FAILED"
            assert len(response.replay_history) == 1
    finally:
        engine.dispose()


def _seed_search_documents(
    session: Session,
    *,
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    ids: SearchTruthIds,
) -> None:
    created = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    rows = [
        (
            ids.doc_active,
            truth_seed["workspace_id"],
            f"Truth Active {truth_ids.slug}",
            "active",
            None,
            None,
            ids.ver_active,
            ids.chunk_active,
            f"{ids.term} active source with enough supporting text for chat retrieval consistency.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 1, "char_start": 0, "char_end": 82}},
        ),
        (
            ids.doc_archived,
            truth_seed["workspace_id"],
            f"Truth Archived {truth_ids.slug}",
            "archived",
            created,
            None,
            ids.ver_archived,
            ids.chunk_archived,
            f"{ids.term} archived source with enough supporting text that must not appear.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 2, "char_start": 0, "char_end": 72}},
        ),
        (
            ids.doc_other_ws,
            truth_seed["other_workspace_id"],
            f"Truth Other {truth_ids.slug}",
            "active",
            None,
            None,
            ids.ver_other_ws,
            ids.chunk_other_ws,
            f"{ids.term} other workspace source with enough supporting text that must not appear.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 3, "char_start": 0, "char_end": 81}},
        ),
        (
            ids.doc_deleted,
            truth_seed["workspace_id"],
            f"Truth Deleted {truth_ids.slug}",
            "deleted",
            None,
            created,
            ids.ver_deleted,
            ids.chunk_deleted,
            f"{ids.term} deleted source with enough supporting text that must not appear.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 4, "char_start": 0, "char_end": 72}},
        ),
    ]
    for (
        document_id,
        workspace_id,
        title,
        lifecycle_status,
        archived_at,
        deleted_at,
        version_id,
        chunk_id,
        content,
        is_searchable,
        metadata,
    ) in rows:
        session.execute(
            text(
                """
                insert into documents
                    (id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                     content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at)
                values
                    (:document_id, :workspace_id, :owner_user_id, null, :title, 'upload', 'text/plain',
                     :content_hash, 'pending', :lifecycle_status, :archived_at, :deleted_at, :created_at, :created_at)
                """
            ),
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "owner_user_id": truth_seed["user_id"],
                "title": title,
                "content_hash": truth_ids.content_hash(f"search-doc-{document_id}"),
                "lifecycle_status": lifecycle_status,
                "archived_at": archived_at,
                "deleted_at": deleted_at,
                "created_at": created,
            },
        )
        session.execute(
            text(
                """
                insert into document_versions
                    (id, document_id, version_number, normalized_markdown, markdown_hash, parser_version,
                     ocr_used, ki_provider, ki_model, metadata, created_at)
                values
                    (:version_id, :document_id, 1, :content, :markdown_hash, 'truth-parser',
                     false, null, null, '{}'::jsonb, :created_at)
                """
            ),
            {
                "version_id": version_id,
                "document_id": document_id,
                "content": content,
                "markdown_hash": f"md-{version_id}",
                "created_at": created,
            },
        )
        session.execute(
            text(
                """
                insert into document_chunks
                    (id, document_id, document_version_id, chunk_index, heading_path, anchor, content,
                     is_searchable, content_hash, token_estimate, metadata, created_at)
                values
                    (:chunk_id, :document_id, :version_id, 0, '[]'::jsonb, :anchor, :content,
                     :is_searchable, :content_hash, 20, cast(:metadata as jsonb), :created_at)
                """
            ),
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "version_id": version_id,
                "anchor": f"truth-{chunk_id}",
                "content": content,
                "is_searchable": is_searchable,
                "content_hash": truth_ids.content_hash(f"search-chunk-{chunk_id}"),
                "metadata": json.dumps(metadata),
                "created_at": created,
            },
        )
        session.execute(
            text("update documents set current_version_id = :version_id, import_status = 'chunked' where id = :document_id"),
            {"version_id": version_id, "document_id": document_id},
        )
    session.commit()


class RecordingRetrieval:
    def __init__(self, search_service: SearchService) -> None:
        self._search_service = search_service
        self.last_results = []

    def search_chunks(self, *, workspace_id: str, query: str, limit: int, offset: int, filters=None):
        self.last_results = self._search_service.search_chunks(
            workspace_id=workspace_id,
            query=query,
            limit=limit,
            offset=offset,
            filters=filters,
        )
        return self.last_results


def _retrieval_signature(result) -> dict:
    return {
        "document_id": result.document_id,
        "chunk_id": result.chunk_id,
        "position": result.position,
        "source_anchor": result.source_anchor.model_dump(),
    }


def _api_retrieval_signature(result: dict) -> dict:
    return {
        "document_id": result["document_id"],
        "chunk_id": result["chunk_id"],
        "position": result["position"],
        "source_anchor": result["source_anchor"],
    }
