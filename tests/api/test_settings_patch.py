"""Settings PATCH – Validierung und Persistenz."""
import pytest

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

BASE = "http://localhost:8000/api/v1"
HEADERS = {
    "Authorization": "Bearer test-token",
    "X-Workspace-Id": "ws-test",
    "Content-Type": "application/json",
}

pytestmark = pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")


def test_get_settings_returns_all_sections():
    r = httpx.get(f"{BASE}/settings", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    for section in ("provider", "rag", "agents", "governance", "security"):
        assert section in data, f"Missing section: {section}"


def test_patch_provider_valid():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"provider": {"timeout_seconds": 60, "max_retries": 2}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["provider"]["timeout_seconds"] == 60


def test_patch_provider_timeout_too_high():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"provider": {"timeout_seconds": 9999}},
    )
    assert r.status_code == 422


def test_patch_provider_retries_negative():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"provider": {"max_retries": -1}},
    )
    assert r.status_code == 422


def test_patch_rag_valid():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"rag": {"chunk_size": 800, "chunk_overlap": 100, "min_score": 0.6, "max_chunks": 8}},
    )
    assert r.status_code == 200


def test_patch_rag_overlap_too_large():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"rag": {"chunk_size": 300, "chunk_overlap": 400}},
    )
    assert r.status_code == 422


def test_patch_rag_min_score_out_of_range():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"rag": {"min_score": 1.5}},
    )
    assert r.status_code == 422


def test_patch_agents_valid():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"agents": {"max_steps": 30, "max_tool_calls": 10, "max_runtime_seconds": 300}},
    )
    assert r.status_code == 200


def test_patch_agents_steps_too_high():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"agents": {"max_steps": 999}},
    )
    assert r.status_code == 422


def test_patch_governance_expiry_valid():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"governance": {"approval_expiry_minutes": 120}},
    )
    assert r.status_code == 200


def test_patch_governance_expiry_too_high():
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"governance": {"approval_expiry_minutes": 9999}},
    )
    assert r.status_code == 422


def test_patch_ignores_secret_fields():
    """api_key in PATCH-Body darf nicht in Response auftauchen."""
    r = httpx.patch(
        f"{BASE}/settings",
        headers=HEADERS,
        json={"provider": {"api_key": "sk-should-not-appear", "timeout_seconds": 30}},
    )
    assert r.status_code == 200
    assert "sk-should-not-appear" not in r.text
    assert "api_key" not in r.text
