import pytest

pytestmark = pytest.mark.unit_fast


def test_member_cannot_toggle_privacy_mode(member_client):
    response = member_client.patch("/api/v1/governance/privacy-mode", json={"enabled": True})
    assert response.status_code == 403


def test_member_cannot_approve(member_client):
    response = member_client.post("/api/v1/approvals/missing/approve", json={"comment": ""})
    assert response.status_code == 403

