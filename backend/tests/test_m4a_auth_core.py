from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.v1.admin import get_background_job_service
from app.api.v1.chat import get_chat_service
from app.api.v1.search import get_search_service
from app.main import app
from app.models.documents import AuthSession
from app.schemas.search import SearchChunkResult
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID


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
                text_preview="preview",
                source_anchor={
                    "type": "text",
                    "page": None,
                    "paragraph": None,
                    "char_start": 0,
                    "char_end": 7,
                },
                rank=0.9,
                filters={},
            )
        ]


class FakeChatService:
    def __init__(self) -> None:
        self.created_sessions: list[dict[str, str]] = []

    def create_session(self, *, workspace_id: str, title: str, owner_user_id: str | None = None):
        self.created_sessions.append(
            {
                "workspace_id": workspace_id,
                "title": title,
                "owner_user_id": owner_user_id or "",
            }
        )
        now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
        return SimpleNamespace(
            id="session-created",
            workspace_id=workspace_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def get_session_summary_metadata(self, *, session_id: str):
        return {
            "message_count": 0,
            "last_user_question_preview": None,
        }


class FakeBackgroundJobService:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []
        self.created_at = datetime(2026, 5, 5, 0, 0, tzinfo=UTC)

    def enqueue_search_index_rebuild_job(self, *, workspace_id: str, requested_by_user_id: str | None, target_workspace_id: str | None):
        self.calls.append(
            {
                "workspace_id": workspace_id,
                "requested_by_user_id": requested_by_user_id,
                "target_workspace_id": target_workspace_id,
            }
        )
        return SimpleNamespace(
            id="job-1",
            job_type="search_index_rebuild",
            status="queued",
            workspace_id=workspace_id,
            requested_by_user_id=requested_by_user_id,
            payload_={"target_workspace_id": target_workspace_id},
            result_=None,
            progress_current=0,
            progress_total=1,
            progress_message="queued",
            error_code=None,
            error_message=None,
            created_at=self.created_at,
            started_at=None,
            finished_at=None,
        )

    def to_response(self, job):
        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "workspace_id": job.workspace_id,
            "requested_by_user_id": job.requested_by_user_id,
            "filename": None,
            "created_at": self.created_at,
            "started_at": None,
            "finished_at": None,
            "progress_current": 0,
            "progress_total": 1,
            "progress_message": "queued",
            "error_code": None,
            "error_message": None,
            "result": None,
        }


def test_protected_endpoints_require_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/search/chunks?q=current")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_search_uses_authenticated_workspace_context(client: TestClient) -> None:
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    try:
        response = client.get("/api/v1/search/chunks?q=current")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["document_id"] == "document-1"


def test_chat_session_uses_authenticated_workspace_and_user(client: TestClient) -> None:
    service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    try:
        response = client.post("/api/v1/chat/sessions", json={"title": "Research"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert service.created_sessions == [
        {
            "workspace_id": DEFAULT_WORKSPACE_ID,
            "title": "Research",
            "owner_user_id": DEFAULT_USER_ID,
        }
    ]


def test_admin_rebuild_is_blocked_until_m4a_m4b_m4c_gates(client: TestClient) -> None:
    service = FakeBackgroundJobService()
    app.dependency_overrides[get_background_job_service] = lambda: service
    try:
        response = client.post("/api/v1/admin/search-index/rebuild")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "ADMIN_ACTION_NOT_IMPLEMENTED"
    assert service.calls == []


def test_auth_me_returns_bootstrap_session_state(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == DEFAULT_USER_ID
    assert body["active_workspace_id"] == DEFAULT_WORKSPACE_ID
    assert body["memberships"] == [{"workspace_id": DEFAULT_WORKSPACE_ID, "role": "owner"}]


def test_auth_me_requires_valid_session_token(db_session, auth_fixture: dict[str, str]) -> None:
    db_session.execute(delete(AuthSession))
    db_session.commit()

    client = TestClient(
        app,
        headers={
            "Authorization": f"Bearer {auth_fixture['session_token']}",
        },
        raise_server_exceptions=False,
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
