import pytest

pytestmark = pytest.mark.unit_fast


def test_rag_response_blocks_when_sources_empty(api_client):
    response = api_client.post("/api/v1/rag/retrieve", json={"query": "anything"})
    assert response.status_code == 200
    data = response.json()
    assert data["used_rag_context"] is True
    assert data["status"] == "blocked"
    assert data["sources"] == []
    assert "blocked_source_count" in data

