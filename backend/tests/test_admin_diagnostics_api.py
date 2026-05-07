from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.main import app
from app.models.documents import BackgroundJob, ChatMessage, ChatSession, WorkspaceMembership
from app.services.diagnostics import DiagnosticsService


def test_admin_diagnostics_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/admin/diagnostics")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_diagnostics_requires_admin_role(client: TestClient, db_session) -> None:
    db_session.execute(update(WorkspaceMembership).values(role="member"))
    db_session.commit()

    response = client.get("/api/v1/admin/diagnostics")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_diagnostics_rejects_foreign_workspace(client: TestClient) -> None:
    response = client.get("/api/v1/admin/diagnostics", headers={"X-Workspace-Id": "workspace-foreign"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_diagnostics_returns_read_only_summary(client: TestClient, db_session, document_fixture) -> None:
    created = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    db_session.add(
        ChatSession(
            id="chat-session-1",
            workspace_id=document_fixture["workspace_id"],
            owner_user_id="00000000-0000-0000-0000-000000000001",
            title="Diagnostics test session",
            created_at=created,
            updated_at=created,
        )
    )
    db_session.add(
        ChatMessage(
            id="chat-message-1",
            session_id="chat-session-1",
            message_index=0,
            role="user",
            content="This content must not appear in diagnostics",
            basis_type="knowledge_base",
            metadata_={},
            created_at=created,
        )
    )
    db_session.add(
        BackgroundJob(
            id="job-running-1",
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
            created_at=created,
            started_at=created,
            finished_at=None,
        )
    )
    db_session.add(
        BackgroundJob(
            id="job-failed-1",
            job_type="document_import",
            status="failed",
            workspace_id=document_fixture["workspace_id"],
            requested_by_user_id=None,
            payload_={},
            result_=None,
            progress_current=1,
            progress_total=1,
            progress_message=None,
            error_code="PARSER_FAILED",
            error_message="Filename must not appear",
            attempt_count=1,
            locked_at=None,
            locked_by=None,
            created_at=created,
            started_at=created,
            finished_at=created,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/admin/diagnostics")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"system", "database", "counts", "imports", "search", "auth"}
    assert body["system"]["status"] in {"ok", "degraded", "error"}
    assert body["database"]["reachable"] is True
    assert body["counts"]["documents"] == 2
    assert body["counts"]["versions"] == 2
    assert body["counts"]["chunks"] == 2
    assert body["counts"]["chat_sessions"] == 1
    assert body["counts"]["chat_messages"] == 1
    assert body["imports"]["running_jobs"] == 1
    assert body["imports"]["failed_jobs_last_24h"] == 1
    assert body["imports"]["last_error_code"] == "PARSER_FAILED"
    assert body["search"]["index_available"] is True
    assert body["search"]["indexed_chunks"] == 2
    assert body["auth"] == {"auth_enabled": True, "workspace_isolation_enabled": True}
    assert "Current Document" not in response.text
    assert "Older Document" not in response.text
    assert "This content must not appear" not in response.text
    assert "Filename must not appear" not in response.text


def test_admin_diagnostics_maps_database_failure_to_diagnostics_failed(client: TestClient, monkeypatch) -> None:
    def raise_database_error(self):
        raise RuntimeError("secret database failure")

    monkeypatch.setattr(DiagnosticsService, "_database_status", raise_database_error)

    response = client.get("/api/v1/admin/diagnostics")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "DIAGNOSTICS_FAILED",
            "message": "Diagnostics failed",
            "details": {"failed_check": "diagnostics"},
        }
    }
    assert "secret database failure" not in response.text
    assert "RuntimeError" not in response.text
