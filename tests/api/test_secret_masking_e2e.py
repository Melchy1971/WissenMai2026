import pytest

pytestmark = pytest.mark.unit_fast


def test_secret_never_returns_cleartext(api_client):
    secret = "sk-testsecret1234567890"
    response = api_client.patch("/api/v1/settings/secrets", json={"key": "provider.api_key", "value": secret})
    assert response.status_code == 200

    for path in ("/api/v1/settings", "/api/v1/audit", "/api/v1/status", "/api/v1/memory", "/api/v1/rag/documents"):
        body = api_client.get(path).text
        assert secret not in body
        assert "sk-testsecret" not in body

