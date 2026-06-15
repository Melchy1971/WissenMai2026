import pytest

pytestmark = pytest.mark.unit_fast


def test_high_governance_action_creates_approval(api_client):
    response = api_client.patch("/api/v1/governance/privacy-mode", json={"enabled": True, "reason": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["approval_required"] is True
    assert data["risk"] == "HIGH"
    assert data["approval_id"]

