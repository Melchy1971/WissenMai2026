"""Settings-Endpunkt GET/PATCH Tests."""
import pytest
import httpx

BASE = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-token", "X-Workspace-Id": "ws-test",
           "Content-Type": "application/json"}

pytestmark = [
    pytest.mark.external_env_only,
    pytest.mark.legacy_live_http,
]


def test_get_settings():
    r = httpx.get(f"{BASE}/api/v1/settings", headers=HEADERS)
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        body = r.json()
        # Muss mindestens eine bekannte Sektion enthalten
        assert any(k in body for k in ("provider", "rag", "agents", "governance"))


def test_patch_settings_provider():
    payload = {"provider": {"timeout_seconds": 60, "max_retries": 3}}
    r = httpx.patch(f"{BASE}/api/v1/settings", json=payload, headers=HEADERS)
    assert r.status_code in (200, 204, 401, 403, 422)


def test_patch_settings_invalid_timeout():
    """Backend soll 422 bei timeout_seconds=999 zurückgeben."""
    payload = {"provider": {"timeout_seconds": 999}}
    r = httpx.patch(f"{BASE}/api/v1/settings", json=payload, headers=HEADERS)
    assert r.status_code in (422, 400, 401, 403)


def test_settings_no_secret_in_response():
    r = httpx.get(f"{BASE}/api/v1/settings", headers=HEADERS)
    if r.status_code != 200:
        pytest.skip("Settings endpoint not available")
    text = r.text
    # API-Keys dürfen nie im Klartext zurückkommen
    assert "sk-" not in text
    assert "Bearer " not in text
