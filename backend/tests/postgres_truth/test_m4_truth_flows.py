from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.jobs.background_jobs import BackgroundJobService, process_import_job, process_search_index_rebuild_job
from app.services.chat.citation_mapper import CitationMapper
from app.services.chat.context_builder import ContextBuilder
from app.services.chat.fake_llm_provider import FakeLlmProvider
from app.services.chat.insufficient_context_policy import InsufficientContextPolicy
from app.services.chat.persistence_service import ChatPersistenceService
from app.services.chat.prompt_builder import PromptBuilder
from app.services.chat.rag_chat_service import RagChatService
from app.services.search_service import SearchService
from app.services.search_index_service import SearchIndexRebuildService
from app.main import app

from tests.postgres_truth.support import (
    TRUTH_OTHER_WORKSPACE_ID,
    TRUTH_USER_ID,
    TRUTH_WORKSPACE_ID,
    assert_no_truth_rows,
)


pytestmark = pytest.mark.postgres_truth

DOC_ACTIVE = "f3000000-0000-0000-0000-000000000001"
DOC_ARCHIVED = "f3000000-0000-0000-0000-000000000002"
DOC_OTHER_WS = "f3000000-0000-0000-0000-000000000003"
DOC_DELETED = "f3000000-0000-0000-0000-000000000004"
VER_ACTIVE = "f5000000-0000-0000-0000-000000000001"
VER_ARCHIVED = "f5000000-0000-0000-0000-000000000002"
VER_OTHER_WS = "f5000000-0000-0000-0000-000000000003"
VER_DELETED = "f5000000-0000-0000-0000-000000000004"
CHUNK_ACTIVE = "f4000000-0000-0000-0000-000000000001"
CHUNK_ARCHIVED = "f4000000-0000-0000-0000-000000000002"
CHUNK_OTHER_WS = "f4000000-0000-0000-0000-000000000003"
CHUNK_DELETED = "f4000000-0000-0000-0000-000000000004"
TRUTH_TERM = "truthretrievalterm"
TRUTH_IMPORT_JOB_ID = "truth-job-import-1"
TRUTH_REINDEX_JOB_ID = "truth-job-reindex-1"


def test_truth_cleanup_starts_without_stale_state(truth_session: Session) -> None:
    assert_no_truth_rows(truth_session)


@pytest.mark.m4b_gate
def test_upload_and_duplicate_handling_use_real_postgresql_transactions(truth_client: TestClient, truth_session: Session) -> None:
    first = truth_client.post(
        "/documents/import",
        files={"file": ("truth.txt", b"# Truth\n\nsame duplicate content\n", "text/plain")},
    )
    second = truth_client.post(
        "/documents/import",
        files={"file": ("truth.txt", b"# Truth\n\nsame duplicate content\n", "text/plain")},
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

    assert truth_session.execute(text("select count(*) from documents where workspace_id = :workspace_id"), {"workspace_id": TRUTH_WORKSPACE_ID}).scalar_one() == 1
    assert truth_session.execute(text("select count(*) from document_versions")).scalar_one() == 1
    assert truth_session.execute(text("select count(*) from document_chunks")).scalar_one() == 1


@pytest.mark.m4a_gate
@pytest.mark.m4c_gate
def test_lifecycle_and_workspace_isolation_are_truth_checked(truth_client: TestClient, truth_session: Session) -> None:
    _seed_search_documents(truth_session)

    archive = truth_client.patch(f"/documents/{DOC_ACTIVE}/archive")
    assert archive.status_code == 200
    assert archive.json()["lifecycle_status"] == "archived"
    assert truth_session.execute(text("select is_searchable from document_chunks where id = :id"), {"id": CHUNK_ACTIVE}).scalar_one() is False

    restore = truth_client.patch(f"/documents/{DOC_ACTIVE}/restore")
    assert restore.status_code == 200
    assert restore.json()["lifecycle_status"] == "active"
    assert truth_session.execute(text("select is_searchable from document_chunks where id = :id"), {"id": CHUNK_ACTIVE}).scalar_one() is True

    forbidden = truth_client.patch(f"/documents/{DOC_OTHER_WS}/archive")
    assert forbidden.status_code in {403, 404}
    assert truth_session.execute(text("select lifecycle_status from documents where id = :id"), {"id": DOC_OTHER_WS}).scalar_one() == "active"


@pytest.mark.m4c_gate
def test_search_chat_retrieval_and_reindex_use_real_postgresql_state(truth_client: TestClient, truth_session: Session) -> None:
    _seed_search_documents(truth_session)

    search = truth_client.get("/api/v1/search/chunks", params={"q": TRUTH_TERM})
    assert search.status_code == 200
    assert [item["document_id"] for item in search.json()] == [DOC_ACTIVE]

    rag_service = RagChatService(
        persistence=ChatPersistenceService(truth_session),
        retrieval=SearchService.from_session(truth_session),
        context_builder=ContextBuilder(max_context_chars=12000, max_context_tokens=2500, min_chunk_chars=40),
        prompt_builder=PromptBuilder(),
        insufficient_context_policy=InsufficientContextPolicy(),
        llm_provider=FakeLlmProvider(),
        citation_mapper=CitationMapper(),
        retrieval_limit=5,
    )
    chat_session = ChatPersistenceService(truth_session).create_session(
        workspace_id=TRUTH_WORKSPACE_ID,
        title="truth chat",
        owner_user_id=TRUTH_USER_ID,
    )
    answer = rag_service.answer_question(
        session_id=chat_session.id,
        workspace_id=TRUTH_WORKSPACE_ID,
        question=f"What mentions {TRUTH_TERM}?",
        retrieval_limit=5,
    )
    assert answer.citations
    assert {citation.document_id for citation in answer.citations} == {DOC_ACTIVE}

    truth_session.execute(text("update document_chunks set is_searchable = false where id = :id"), {"id": CHUNK_ACTIVE})
    truth_session.commit()
    report_before = SearchIndexRebuildService.from_session(truth_session).inspect_inconsistencies(workspace_id=TRUTH_WORKSPACE_ID)
    assert report_before["missing_index_entries"]["count"] == 1

    result = SearchIndexRebuildService.from_session(truth_session).rebuild_search_index(workspace_id=TRUTH_WORKSPACE_ID)
    assert result["status"] == "completed"
    assert truth_session.execute(text("select is_searchable from document_chunks where id = :id"), {"id": CHUNK_ACTIVE}).scalar_one() is True


@pytest.mark.m4c_gate
def test_search_index_drift_endpoint_reports_real_postgresql_drift(
    truth_client: TestClient,
    truth_session: Session,
) -> None:
    _seed_search_documents(truth_session)

    truth_session.execute(
        text(
            """
            update document_chunks
            set is_searchable = false
            where id = :chunk_id
            """
        ),
        {"chunk_id": CHUNK_ACTIVE},
    )
    truth_session.execute(
        text(
            """
            insert into documents
                (id, workspace_id, owner_user_id, current_version_id, title, source_type, mime_type,
                 content_hash, import_status, lifecycle_status, archived_at, deleted_at, created_at, updated_at)
            values
                (:document_id, :workspace_id, :owner_user_id, null, :title, 'upload', 'text/plain',
                 :content_hash, 'chunked', 'active', null, null, now(), now())
            """
        ),
        {
            "document_id": "f3000000-0000-0000-0000-000000000099",
            "workspace_id": TRUTH_WORKSPACE_ID,
            "owner_user_id": TRUTH_USER_ID,
            "title": "Truth Duplicate",
            "content_hash": "truth-duplicate-drift",
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
                 false, null, null, cast(:metadata as jsonb), now())
            """
        ),
        {
            "version_id": "f5000000-0000-0000-0000-000000000099",
            "document_id": "f3000000-0000-0000-0000-000000000099",
            "markdown": "# Duplicate\n\ntruth duplicate drift",
            "markdown_hash": "truth-duplicate-version-hash",
            "metadata": json.dumps({}),
        },
    )
    truth_session.execute(
        text(
            "update documents set current_version_id = :version_id where id = :document_id"
        ),
        {
            "version_id": "f5000000-0000-0000-0000-000000000099",
            "document_id": "f3000000-0000-0000-0000-000000000099",
        },
    )
    truth_session.execute(
        text(
            """
            insert into document_chunks
                (id, document_id, document_version_id, chunk_index, heading_path, anchor, content,
                 is_searchable, search_vector, content_hash, token_estimate, metadata, created_at)
            values
                (:chunk_a, :document_id, :version_id, 0, cast(:heading_path as jsonb), :anchor, :content_a,
                 true, to_tsvector('simple', :vector_text), :content_hash, 10, cast(:metadata as jsonb), now()),
                (:chunk_b, :document_id, :version_id, 1, cast(:heading_path as jsonb), :anchor, :content_b,
                 true, to_tsvector('simple', :vector_text), :content_hash, 10, cast(:metadata as jsonb), now())
            """
        ),
        {
            "chunk_a": "f4000000-0000-0000-0000-000000000099",
            "chunk_b": "f4000000-0000-0000-0000-000000000100",
            "document_id": "f3000000-0000-0000-0000-000000000099",
            "version_id": "f5000000-0000-0000-0000-000000000099",
            "heading_path": json.dumps([]),
            "anchor": "duplicate-anchor",
            "content_a": "truth duplicate drift A",
            "content_b": "truth duplicate drift B",
            "vector_text": "truth duplicate drift",
            "content_hash": "truth-duplicate-chunk-hash",
            "metadata": json.dumps({"source_anchor": {"type": "text", "page": None, "paragraph": 9, "char_start": 0, "char_end": 24}}),
        },
    )
    truth_session.commit()

    response = truth_client.get("/api/v1/admin/search-index/drift")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == TRUTH_WORKSPACE_ID
    assert payload["status"] == "drifted"
    assert payload["severity"] == "critical"
    assert payload["drift_score"] == 20
    assert payload["chunks_without_index"]["count"] >= 1
    assert payload["chunks_without_index"]["severity"] == "high"
    assert payload["deleted_documents_in_index"]["count"] == 1
    assert payload["deleted_documents_in_index"]["severity"] == "critical"
    assert payload["deleted_documents_in_index"]["sample_document_ids"] == [DOC_DELETED]
    assert payload["archived_documents_in_active_index"]["count"] == 1
    assert payload["archived_documents_in_active_index"]["sample_document_ids"] == [DOC_ARCHIVED]
    assert payload["duplicate_index_entries"]["count"] == 1
    assert payload["duplicate_index_entries"]["sample_document_ids"] == ["f3000000-0000-0000-0000-000000000099"]
    assert payload["invalid_lifecycle_status"]["count"] >= 3
    assert payload["index_without_chunk"]["status"] == "not_applicable"
    assert "reindexing the workspace" in payload["repair_recommendation"]


@pytest.mark.m4c_gate
def test_search_and_chat_retrieval_use_identical_active_chunks_and_source_anchors(
    truth_client: TestClient,
    truth_session: Session,
) -> None:
    _seed_search_documents(truth_session)

    search_service = SearchService.from_session(truth_session)
    search_response = truth_client.get("/api/v1/search/chunks", params={"q": TRUTH_TERM, "limit": 10})
    assert search_response.status_code == 200
    search_api_results = search_response.json()
    search_results = search_service.search_chunks(
        workspace_id=TRUTH_WORKSPACE_ID,
        query=TRUTH_TERM,
        limit=10,
        offset=0,
    )

    recording_retrieval = RecordingRetrieval(search_service)
    rag_service = RagChatService(
        persistence=ChatPersistenceService(truth_session),
        retrieval=recording_retrieval,
        context_builder=ContextBuilder(max_context_chars=12000, max_context_tokens=2500, min_chunk_chars=40),
        prompt_builder=PromptBuilder(),
        insufficient_context_policy=InsufficientContextPolicy(),
        llm_provider=FakeLlmProvider(),
        citation_mapper=CitationMapper(),
        retrieval_limit=10,
    )
    chat_session = ChatPersistenceService(truth_session).create_session(
        workspace_id=TRUTH_WORKSPACE_ID,
        title="truth consistency chat",
        owner_user_id=TRUTH_USER_ID,
    )

    answer = rag_service.answer_question(
        session_id=chat_session.id,
        workspace_id=TRUTH_WORKSPACE_ID,
        question=f"What mentions {TRUTH_TERM}?",
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
    assert citation_chunks == [CHUNK_ACTIVE]
    assert [item.chunk_id for item in search_results] == [CHUNK_ACTIVE]
    assert CHUNK_ARCHIVED not in [item.chunk_id for item in search_results]
    assert CHUNK_DELETED not in [item.chunk_id for item in search_results]
    assert all(item.source_anchor.model_dump() == chat_retrieval_results[index].source_anchor.model_dump() for index, item in enumerate(search_results))


@pytest.mark.m4a_gate
def test_auth_workspace_truth_blocks_foreign_workspace_and_non_admin_diagnostics(
    truth_seed: dict[str, str],
) -> None:
    foreign_workspace_client = TestClient(
        app,
        headers={
            "Authorization": f"Bearer {truth_seed['token']}",
            "X-Workspace-Id": TRUTH_OTHER_WORKSPACE_ID,
        },
    )
    response = foreign_workspace_client.get("/api/v1/admin/diagnostics")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.m4b_gate
def test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows(
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            "id": TRUTH_IMPORT_JOB_ID,
            "workspace_id": TRUTH_WORKSPACE_ID,
            "user_id": TRUTH_USER_ID,
            "payload": json.dumps(
                {
                    "filename": "truth-retry.txt",
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
                "document_id": DOC_ACTIVE,
                "version_id": VER_ACTIVE,
                "import_status": "duplicate",
                "duplicate_of_document_id": DOC_ACTIVE,
                "chunk_count": 1,
                "parser_type": "txt-parser",
                "warnings": [],
            }

    monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", SuccessfulImportExecutor)
    monkeypatch.setattr("app.services.jobs.background_jobs.Path.read_bytes", lambda _self: b"truth payload")

    process_import_job(TRUTH_IMPORT_JOB_ID, truth_session.connection())

    job_row = truth_session.execute(
        text("select status, attempt_count, error_code from background_jobs where id = :id"),
        {"id": TRUTH_IMPORT_JOB_ID},
    ).one()
    assert job_row.status == "completed"
    assert job_row.attempt_count == 2
    assert job_row.error_code is None


@pytest.mark.m4c_gate
def test_postgres_truth_search_rebuild_failure_keeps_lifecycle_state_and_stays_retryable(
    truth_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_search_documents(truth_session)
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
            "id": TRUTH_REINDEX_JOB_ID,
            "workspace_id": TRUTH_WORKSPACE_ID,
            "user_id": TRUTH_USER_ID,
            "payload": json.dumps({"target_workspace_id": TRUTH_WORKSPACE_ID}),
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

    process_search_index_rebuild_job(TRUTH_REINDEX_JOB_ID, truth_session.connection())

    job_row = truth_session.execute(
        text("select status, error_code from background_jobs where id = :id"),
        {"id": TRUTH_REINDEX_JOB_ID},
    ).one()
    assert job_row.status == "retryable"
    assert job_row.error_code == "SERVICE_UNAVAILABLE"
    assert truth_session.execute(text("select lifecycle_status from documents where id = :id"), {"id": DOC_ARCHIVED}).scalar_one() == "archived"


def _seed_search_documents(session: Session) -> None:
    created = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    rows = [
        (
            DOC_ACTIVE,
            TRUTH_WORKSPACE_ID,
            "Truth Active",
            "active",
            None,
            None,
            VER_ACTIVE,
            CHUNK_ACTIVE,
            f"{TRUTH_TERM} active source with enough supporting text for chat retrieval consistency.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 1, "char_start": 0, "char_end": 82}},
        ),
        (
            DOC_ARCHIVED,
            TRUTH_WORKSPACE_ID,
            "Truth Archived",
            "archived",
            created,
            None,
            VER_ARCHIVED,
            CHUNK_ARCHIVED,
            f"{TRUTH_TERM} archived source with enough supporting text that must not appear.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 2, "char_start": 0, "char_end": 72}},
        ),
        (
            DOC_OTHER_WS,
            TRUTH_OTHER_WORKSPACE_ID,
            "Truth Other",
            "active",
            None,
            None,
            VER_OTHER_WS,
            CHUNK_OTHER_WS,
            f"{TRUTH_TERM} other workspace source with enough supporting text that must not appear.",
            True,
            {"source_anchor": {"type": "text", "page": None, "paragraph": 3, "char_start": 0, "char_end": 81}},
        ),
        (
            DOC_DELETED,
            TRUTH_WORKSPACE_ID,
            "Truth Deleted",
            "deleted",
            None,
            created,
            VER_DELETED,
            CHUNK_DELETED,
            f"{TRUTH_TERM} deleted source with enough supporting text that must not appear.",
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
                "owner_user_id": TRUTH_USER_ID,
                "title": title,
                "content_hash": f"hash-{document_id}",
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
                "content_hash": f"chunk-{chunk_id}",
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
