from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.api.v1.chat import get_rag_chat_service
from app.api.v1.search import get_search_service
from app.main import app
from app.models.documents import BackgroundJob, ChatMessage, ChatSession
from app.schemas.chat import ChatMessageResponse
from app.schemas.jobs import ImportJobResult, SearchIndexRebuildJobResult
from app.schemas.search import SearchChunkResult
from tests.conftest import DEFAULT_WORKSPACE_ID


IMPORT_STATUSES = {"pending", "parsing", "parsed", "chunked", "failed", "duplicate"}
LIFECYCLE_STATUSES = {"active", "archived", "deleted"}
JOB_TYPES = {"document_import", "search_index_rebuild"}
JOB_STATUSES = {"pending", "running", "completed", "failed", "retryable", "dead_letter", "cancelled"}
SOURCE_ANCHOR_TYPES = {"text", "pdf_page", "docx_paragraph", "legacy_unknown"}
CHAT_ROLES = {"system", "user", "assistant"}
CHAT_BASIS_TYPES = {"knowledge_base", "general", "mixed", "unknown"}
SOURCE_STATUSES = {"active", "archived", "deleted", "missing"}


def assert_exact_keys(payload: dict[str, Any], expected: set[str]) -> None:
    assert set(payload) == expected


def assert_nullable_string(value: Any) -> None:
    assert value is None or isinstance(value, str)


def assert_source_anchor_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"type", "page", "paragraph", "char_start", "char_end"})
    assert payload["type"] in SOURCE_ANCHOR_TYPES
    for key in ("page", "paragraph", "char_start", "char_end"):
        assert payload[key] is None or isinstance(payload[key], int)


def assert_error_response_contract(payload: dict[str, Any], *, expected_code: str | None = None) -> None:
    assert_exact_keys(payload, {"error"})
    assert_exact_keys(payload["error"], {"code", "message", "details"})
    assert isinstance(payload["error"]["code"], str)
    assert isinstance(payload["error"]["message"], str)
    assert isinstance(payload["error"]["details"], dict)
    if expected_code is not None:
        assert payload["error"]["code"] == expected_code


def assert_workspace_membership_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"workspace_id", "role"})
    assert isinstance(payload["workspace_id"], str)
    assert payload["role"] in {"owner", "admin", "member"}


def assert_document_list_item_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(
        payload,
        {
            "id",
            "title",
            "mime_type",
            "created_at",
            "updated_at",
            "latest_version_id",
            "import_status",
            "lifecycle_status",
            "archived_at",
            "deleted_at",
            "version_count",
            "chunk_count",
        },
    )
    assert isinstance(payload["id"], str)
    assert isinstance(payload["title"], str)
    assert_nullable_string(payload["mime_type"])
    assert isinstance(payload["created_at"], str)
    assert isinstance(payload["updated_at"], str)
    assert_nullable_string(payload["latest_version_id"])
    assert payload["import_status"] in IMPORT_STATUSES
    assert payload["lifecycle_status"] in LIFECYCLE_STATUSES
    assert_nullable_string(payload["archived_at"])
    assert_nullable_string(payload["deleted_at"])
    assert isinstance(payload["version_count"], int)
    assert isinstance(payload["chunk_count"], int)


def assert_document_detail_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(
        payload,
        {
            "id",
            "workspace_id",
            "owner_user_id",
            "title",
            "source_type",
            "mime_type",
            "content_hash",
            "created_at",
            "updated_at",
            "latest_version_id",
            "latest_version",
            "parser_metadata",
            "import_status",
            "lifecycle_status",
            "archived_at",
            "deleted_at",
            "chunk_summary",
        },
    )
    for key in ("id", "workspace_id", "owner_user_id", "title", "source_type", "content_hash", "created_at", "updated_at"):
        assert isinstance(payload[key], str)
    assert_nullable_string(payload["mime_type"])
    assert_nullable_string(payload["latest_version_id"])
    assert payload["import_status"] in IMPORT_STATUSES
    assert payload["lifecycle_status"] in LIFECYCLE_STATUSES
    assert_nullable_string(payload["archived_at"])
    assert_nullable_string(payload["deleted_at"])

    if payload["latest_version"] is not None:
        assert_exact_keys(payload["latest_version"], {"id", "version_number", "created_at", "content_hash"})
    if payload["parser_metadata"] is not None:
        assert_exact_keys(payload["parser_metadata"], {"parser_version", "ocr_used", "ki_provider", "ki_model", "metadata"})
    assert_exact_keys(payload["chunk_summary"], {"chunk_count", "total_chars", "first_chunk_id", "last_chunk_id"})


def assert_job_replay_entry_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"previous_error_code", "previous_error_message", "replayed_at", "replayed_by_user_id"})
    assert_nullable_string(payload["previous_error_code"])
    assert_nullable_string(payload["previous_error_message"])
    assert isinstance(payload["replayed_at"], str)
    assert_nullable_string(payload["replayed_by_user_id"])


def assert_import_job_result_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"document_id", "version_id", "import_status", "duplicate_of_document_id", "chunk_count", "parser_type", "warnings"})
    assert isinstance(payload["document_id"], str)
    assert_nullable_string(payload["version_id"])
    assert payload["import_status"] in IMPORT_STATUSES
    assert_nullable_string(payload["duplicate_of_document_id"])
    assert isinstance(payload["chunk_count"], int)
    assert isinstance(payload["parser_type"], str)
    assert isinstance(payload["warnings"], list)


def assert_search_index_rebuild_result_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"workspace_id", "reindexed_chunk_count", "reindexed_document_count", "index_name", "index_action", "status"})
    assert_nullable_string(payload["workspace_id"])
    assert isinstance(payload["reindexed_chunk_count"], int)
    assert isinstance(payload["reindexed_document_count"], int)
    assert isinstance(payload["index_name"], str)
    assert isinstance(payload["index_action"], str)
    assert isinstance(payload["status"], str)


def assert_job_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(
        payload,
        {
            "id",
            "job_type",
            "status",
            "workspace_id",
            "requested_by_user_id",
            "filename",
            "created_at",
            "started_at",
            "finished_at",
            "progress_current",
            "progress_total",
            "progress_message",
            "error_code",
            "error_message",
            "previous_error",
            "replay_history",
            "result",
        },
    )
    assert isinstance(payload["id"], str)
    assert payload["job_type"] in JOB_TYPES
    assert payload["status"] in JOB_STATUSES
    assert isinstance(payload["workspace_id"], str)
    assert_nullable_string(payload["requested_by_user_id"])
    assert_nullable_string(payload["filename"])
    assert isinstance(payload["created_at"], str)
    assert_nullable_string(payload["started_at"])
    assert_nullable_string(payload["finished_at"])
    assert isinstance(payload["progress_current"], int)
    assert isinstance(payload["progress_total"], int)
    assert_nullable_string(payload["progress_message"])
    assert_nullable_string(payload["error_code"])
    assert_nullable_string(payload["error_message"])
    if payload["previous_error"] is not None:
        assert_job_replay_entry_contract(payload["previous_error"])
    assert isinstance(payload["replay_history"], list)
    for entry in payload["replay_history"]:
        assert_job_replay_entry_contract(entry)
    if payload["result"] is not None:
        if payload["job_type"] == "document_import":
            assert_import_job_result_contract(payload["result"])
        elif payload["job_type"] == "search_index_rebuild":
            assert_search_index_rebuild_result_contract(payload["result"])


def assert_search_result_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(
        payload,
        {
            "document_id",
            "document_title",
            "document_created_at",
            "document_version_id",
            "version_number",
            "chunk_id",
            "position",
            "text_preview",
            "source_anchor",
            "rank",
            "filters",
        },
    )
    for key in ("document_id", "document_title", "document_created_at", "document_version_id", "chunk_id", "text_preview"):
        assert isinstance(payload[key], str)
    assert isinstance(payload["version_number"], int)
    assert isinstance(payload["position"], int)
    assert isinstance(payload["rank"], float)
    assert isinstance(payload["filters"], dict)
    assert_source_anchor_contract(payload["source_anchor"])


def assert_chat_session_contract(payload: dict[str, Any], *, detail: bool = False) -> None:
    expected = {"id", "workspace_id", "title", "created_at", "updated_at", "message_count", "last_user_question_preview"}
    if detail:
        expected.add("messages")
    assert_exact_keys(payload, expected)
    for key in ("id", "workspace_id", "title", "created_at", "updated_at"):
        assert isinstance(payload[key], str)
    assert isinstance(payload["message_count"], int)
    assert_nullable_string(payload["last_user_question_preview"])
    if detail:
        assert isinstance(payload["messages"], list)


def assert_chat_message_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"id", "session_id", "role", "content", "basis_type", "created_at", "citations", "confidence"})
    for key in ("id", "session_id", "content", "created_at"):
        assert isinstance(payload[key], str)
    assert payload["role"] in CHAT_ROLES
    assert payload["basis_type"] in CHAT_BASIS_TYPES
    assert isinstance(payload["citations"], list)
    for citation in payload["citations"]:
        assert_exact_keys(citation, {"chunk_id", "document_id", "document_title", "source_anchor", "quote_preview", "source_status"})
        assert_nullable_string(citation["chunk_id"])
        assert isinstance(citation["document_id"], str)
        assert isinstance(citation["document_title"], str)
        assert_source_anchor_contract(citation["source_anchor"])
        assert isinstance(citation["quote_preview"], str)
        assert citation["source_status"] in SOURCE_STATUSES
    if payload["confidence"] is not None:
        assert_exact_keys(payload["confidence"], {"sufficient_context", "retrieval_score_max", "retrieval_score_avg"})
        assert isinstance(payload["confidence"]["sufficient_context"], bool)


def assert_diagnostics_contract(payload: dict[str, Any]) -> None:
    assert_exact_keys(payload, {"system", "database", "counts", "imports", "search", "auth"})
    assert_exact_keys(payload["system"], {"status", "version", "environment"})
    assert payload["system"]["status"] in {"ok", "degraded", "error"}
    assert payload["system"]["environment"] in {"local", "test", "production"}
    assert_exact_keys(payload["database"], {"reachable", "migration_head", "current_revision", "is_current"})
    assert_exact_keys(payload["counts"], {"documents", "versions", "chunks", "chat_sessions", "chat_messages"})
    assert_exact_keys(payload["imports"], {"running_jobs", "failed_jobs_last_24h", "last_error_code"})
    assert_exact_keys(payload["search"], {"index_available", "indexed_chunks", "stale_index_entries"})
    assert_exact_keys(payload["auth"], {"auth_enabled", "workspace_isolation_enabled"})


class FakeSearchService:
    def search_chunks(self, workspace_id: str, query: str, limit: int, offset: int, filters=None):
        return [
            SearchChunkResult(
                document_id="document-1",
                document_title="Current Document",
                document_created_at=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
                document_version_id="version-1",
                version_number=1,
                chunk_id="chunk-1",
                position=0,
                text_preview="First chunk preview",
                source_anchor={
                    "type": "text",
                    "page": None,
                    "paragraph": 1,
                    "char_start": 0,
                    "char_end": 42,
                },
                rank=0.91,
                filters={},
            )
        ]


class FakeRagChatService:
    def answer_question(self, *, session_id: str, workspace_id: str, question: str, retrieval_limit: int | None = None):
        return ChatMessageResponse(
            id="assistant-message-1",
            session_id=session_id,
            role="assistant",
            content="Antwort mit Quelle.",
            basis_type="knowledge_base",
            created_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            citations=[
                {
                    "chunk_id": "chunk-1",
                    "document_id": "document-1",
                    "document_title": "Document Title",
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": 1,
                        "char_start": 0,
                        "char_end": 42,
                    },
                    "quote_preview": "Quelle",
                    "source_status": "active",
                }
            ],
            confidence={
                "sufficient_context": True,
                "retrieval_score_max": 0.91,
                "retrieval_score_avg": 0.81,
            },
        )


def test_auth_me_and_workspace_membership_contract(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert_exact_keys(body, {"user", "memberships", "active_workspace_id"})
    assert_exact_keys(body["user"], {"id", "login", "display_name"})
    assert isinstance(body["memberships"], list)
    assert body["memberships"]
    assert_workspace_membership_contract(body["memberships"][0])
    assert_nullable_string(body["active_workspace_id"])


def test_document_list_and_detail_contract(client: TestClient, document_fixture: dict[str, str]) -> None:
    list_response = client.get("/documents")
    detail_response = client.get(f"/documents/{document_fixture['document_id']}")

    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)
    assert_document_list_item_contract(list_response.json()[0])

    assert detail_response.status_code == 200
    assert_document_detail_contract(detail_response.json())


def test_upload_job_contract(client: TestClient) -> None:
    response = client.post(
        "/documents/import",
        files={"file": ("contract.txt", b"# Contract\n\nPayload\n", "text/plain")},
    )

    assert response.status_code == 202
    assert_job_contract(response.json())

    job_response = client.get(f"/api/v1/jobs/{response.json()['id']}")
    assert job_response.status_code == 200
    assert_job_contract(job_response.json())


def test_search_response_contract(client: TestClient) -> None:
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    try:
        response = client.get("/api/v1/search/chunks?q=contract")
    finally:
        app.dependency_overrides.pop(get_search_service, None)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert_search_result_contract(body[0])


def test_chat_session_and_message_contract(client: TestClient, db_session) -> None:
    created = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    db_session.add(
        ChatSession(
            id="contract-session-1",
            workspace_id=DEFAULT_WORKSPACE_ID,
            owner_user_id="00000000-0000-0000-0000-000000000001",
            title="Contract Chat",
            created_at=created,
            updated_at=created,
        )
    )
    db_session.add(
        ChatMessage(
            id="contract-message-1",
            session_id="contract-session-1",
            message_index=0,
            role="user",
            content="Question",
            basis_type="unknown",
            metadata_={},
            created_at=created,
        )
    )
    db_session.commit()

    list_response = client.get("/api/v1/chat/sessions")
    detail_response = client.get("/api/v1/chat/sessions/contract-session-1")

    assert list_response.status_code == 200
    assert_chat_session_contract(list_response.json()[0])

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert_chat_session_contract(detail, detail=True)
    assert_chat_message_contract(detail["messages"][0])

    app.dependency_overrides[get_rag_chat_service] = lambda: FakeRagChatService()
    try:
        message_response = client.post(
            "/api/v1/chat/sessions/contract-session-1/messages",
            json={"question": "Bitte antworten.", "retrieval_limit": 3},
        )
    finally:
        app.dependency_overrides.pop(get_rag_chat_service, None)

    assert message_response.status_code == 201
    assert_chat_message_contract(message_response.json())


def test_diagnostics_response_contract(client: TestClient, document_fixture: dict[str, str], db_session) -> None:
    db_session.add(
        BackgroundJob(
            id="contract-job-running",
            job_type="document_import",
            status="running",
            workspace_id=document_fixture["workspace_id"],
            requested_by_user_id=None,
            payload_={},
            result_=None,
            progress_current=0,
            progress_total=1,
            progress_message=None,
            error_code=None,
            error_message=None,
            attempt_count=0,
            locked_at=None,
            locked_by=None,
            created_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            finished_at=None,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/admin/diagnostics")

    assert response.status_code == 200
    assert_diagnostics_contract(response.json())


def test_error_response_contract() -> None:
    response = TestClient(app, raise_server_exceptions=False).get("/api/v1/search/chunks?q=contract")

    assert response.status_code == 401
    assert_error_response_contract(response.json(), expected_code="AUTH_REQUIRED")


def test_job_result_schemas() -> None:
    import_result = ImportJobResult(
        document_id="doc-1",
        version_id="ver-1",
        import_status="chunked",
        duplicate_of_document_id=None,
        chunk_count=5,
        parser_type="txt",
        warnings=[],
    )
    assert_import_job_result_contract(import_result.model_dump())

    rebuild_result = SearchIndexRebuildJobResult(
        workspace_id=None,
        reindexed_chunk_count=42,
        reindexed_document_count=3,
        index_name="wissen_chunks",
        index_action="full_rebuild",
        status="completed",
    )
    assert_search_index_rebuild_result_contract(rebuild_result.model_dump())
