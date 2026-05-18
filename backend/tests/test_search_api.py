from datetime import UTC, datetime
from fastapi.testclient import TestClient

from app.api.v1.search import get_search_service
from app.main import app
from app.schemas.search import SearchChunkResult
from app.services.search_service import SearchService


class FakeSearchService(SearchService):
    def __init__(self, results: list[SearchChunkResult]) -> None:
        self._results = results

    def search_chunks(self, workspace_id: str, query: str, limit: int, offset: int, filters=None):
        return self._results


def override_search_service(results: list[SearchChunkResult]) -> SearchService:
    return FakeSearchService(results)


def test_search_chunks_returns_results_with_stable_shape(client: TestClient) -> None:
    created_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    result = SearchChunkResult(
        document_id="document-1",
        document_title="Current Document",
        document_created_at=created_at,
        document_version_id="version-1",
        version_number=1,
        chunk_id="chunk-1",
        position=0,
        text_preview="First chunk preview",
        source_anchor={
            "type": "text",
            "page": None,
            "paragraph": None,
            "char_start": 0,
            "char_end": 42,
        },
        rank=0.91,
        filters={},
    )

    app.dependency_overrides[get_search_service] = lambda: override_search_service([result])
    try:
        response = client.get("/api/v1/search/chunks?q=current")
    finally:
        app.dependency_overrides.pop(get_search_service, None)

    assert response.status_code == 200
    assert response.json() == [
        {
            "document_id": "document-1",
            "document_title": "Current Document",
            "document_created_at": "2026-05-01T10:00:00Z",
            "document_version_id": "version-1",
            "version_number": 1,
            "chunk_id": "chunk-1",
            "position": 0,
            "text_preview": "First chunk preview",
            "source_anchor": {
                "type": "text",
                "page": None,
                "paragraph": None,
                "char_start": 0,
                "char_end": 42,
            },
            "rank": 0.91,
            "filters": {},
        }
    ]


def test_search_chunks_requires_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/search/chunks?q=current")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_search_chunks_requires_query(client: TestClient) -> None:
    app.dependency_overrides[get_search_service] = lambda: override_search_service([])
    try:
        response = client.get("/api/v1/search/chunks")
    finally:
        app.dependency_overrides.pop(get_search_service, None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUERY"


def test_search_chunks_rejects_invalid_pagination(client: TestClient) -> None:
    app.dependency_overrides[get_search_service] = lambda: override_search_service([])
    try:
        response = client.get("/api/v1/search/chunks?q=current&limit=101")
    finally:
        app.dependency_overrides.pop(get_search_service, None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PAGINATION"
