import pytest

pytestmark = pytest.mark.unit_fast


def test_overlap_must_be_smaller_than_chunk_size(api_client):
    response = api_client.patch("/api/v1/settings", json={"rag": {"chunk_size": 200, "chunk_overlap": 200}})
    assert response.status_code == 422


def test_dependent_rules_block_invalid_settings(api_client):
    response = api_client.patch(
        "/api/v1/settings",
        json={"agents": {"agents_enabled": True}, "security": {"validation_pipeline_enabled": False}},
    )
    assert response.status_code == 422


def test_member_cannot_disable_source_required(member_client):
    response = member_client.patch("/api/v1/settings", json={"security": {"source_required": False}})
    assert response.status_code == 422

