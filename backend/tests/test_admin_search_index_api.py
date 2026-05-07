from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.api.v1.admin import get_background_job_service, get_search_index_service
from app.core.config import settings
from app.main import app
from app.models.documents import WorkspaceMembership


class FakeBackgroundJobService:
    def __init__(self) -> None:
        self.calls: list[str | None] = []
        self.created_at = datetime(2026, 5, 5, 0, 0, tzinfo=UTC)

    def enqueue_search_index_rebuild_job(self, *, workspace_id: str, requested_by_user_id: str | None, target_workspace_id: str | None):
        from types import SimpleNamespace

        self.calls.append(target_workspace_id)
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
            progress_message="Rebuild ist in Warteschlange",
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
            "progress_message": "Rebuild ist in Warteschlange",
            "error_code": None,
            "error_message": None,
            "result": None,
        }


class FakeSearchIndexService:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def inspect_inconsistencies(self, *, workspace_id: str | None = None):
        self.calls.append(workspace_id)
        return {
            "workspace_id": workspace_id,
            "checked_at": datetime(2026, 5, 6, 10, 0, tzinfo=UTC),
            "index_name": "ix_document_chunks_search_vector",
            "status": "inconsistent",
            "searchable_chunk_count": 12,
            "missing_index_entries": {
                "count": 1,
                "status": "inconsistent",
                "sample_chunk_ids": ["chunk-missing-1"],
                "sample_document_ids": ["doc-active-1"],
                "note": None,
            },
            "orphan_index_entries": {
                "count": 0,
                "status": "not_applicable",
                "sample_chunk_ids": [],
                "sample_document_ids": [],
                "note": "GIN index entries are derived from document_chunks.search_vector and cannot be enumerated as standalone rows.",
            },
            "deleted_documents_in_index": {
                "count": 2,
                "status": "inconsistent",
                "sample_chunk_ids": ["chunk-deleted-1"],
                "sample_document_ids": ["doc-deleted-1"],
                "note": None,
            },
            "archived_documents_in_active_index": {
                "count": 1,
                "status": "inconsistent",
                "sample_chunk_ids": ["chunk-archived-1"],
                "sample_document_ids": ["doc-archived-1"],
                "note": None,
            },
        }


def test_admin_search_index_rebuild_requires_authentication() -> None:
    response = TestClient(app).post("/api/v1/admin/search-index/rebuild")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_search_index_rebuild_requires_authentication_even_with_legacy_admin_token_header() -> None:
    response = TestClient(app).post(
        "/api/v1/admin/search-index/rebuild",
        headers={"x-admin-token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_search_index_rebuild_requires_admin_role(client: TestClient, db_session) -> None:
    db_session.execute(update(WorkspaceMembership).values(role="member"))
    db_session.commit()

    response = client.post("/api/v1/admin/search-index/rebuild")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_REQUIRED"


def test_admin_search_index_rebuild_returns_stable_shape(client: TestClient) -> None:
    response = client.post("/api/v1/admin/search-index/rebuild")

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "code": "ADMIN_ACTION_NOT_IMPLEMENTED",
            "message": "Search index rebuild is disabled until M4a, M4b and M4c gates are complete",
            "details": {
                "action": "search_index_rebuild",
                "scope": "M4d read-only diagnostics",
                "required_gates": ["M4a", "M4b", "M4c"],
            },
        }
    }


def test_admin_search_index_inconsistencies_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/admin/search-index/inconsistencies")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_search_index_inconsistencies_returns_stable_shape(client: TestClient) -> None:
    service = FakeSearchIndexService()
    app.dependency_overrides[get_search_index_service] = lambda: service
    try:
        response = client.get("/api/v1/admin/search-index/inconsistencies")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.calls == ["00000000-0000-0000-0000-000000000001"]
    assert response.json() == {
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "checked_at": "2026-05-06T10:00:00Z",
        "index_name": "ix_document_chunks_search_vector",
        "status": "inconsistent",
        "searchable_chunk_count": 12,
        "missing_index_entries": {
            "count": 1,
            "status": "inconsistent",
            "sample_chunk_ids": ["chunk-missing-1"],
            "sample_document_ids": ["doc-active-1"],
            "note": None,
        },
        "orphan_index_entries": {
            "count": 0,
            "status": "not_applicable",
            "sample_chunk_ids": [],
            "sample_document_ids": [],
            "note": "GIN index entries are derived from document_chunks.search_vector and cannot be enumerated as standalone rows.",
        },
        "deleted_documents_in_index": {
            "count": 2,
            "status": "inconsistent",
            "sample_chunk_ids": ["chunk-deleted-1"],
            "sample_document_ids": ["doc-deleted-1"],
            "note": None,
        },
        "archived_documents_in_active_index": {
            "count": 1,
            "status": "inconsistent",
            "sample_chunk_ids": ["chunk-archived-1"],
            "sample_document_ids": ["doc-archived-1"],
            "note": None,
        },
    }
