"""GUI Backend Endpoints – Smoke-Tests.
Voraussetzung: Backend läuft auf http://localhost:8000 mit gültigem Test-Token.
"""
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
}

pytestmark = pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")


@pytest.mark.parametrize("path,methods", [
    ("/status",                         ["GET"]),
    ("/settings",                       ["GET"]),
    ("/security/status",                ["GET"]),
    ("/approvals",                      ["GET"]),
    ("/audit",                          ["GET"]),
    ("/governance/status",              ["GET"]),
    ("/governance/changesets",          ["GET"]),
    ("/governance/rollback-points",     ["GET"]),
    ("/governance/policy-decisions",    ["GET"]),
    ("/agents",                         ["GET"]),
    ("/agents/executions",              ["GET"]),
    ("/collaboration/teams",            ["GET"]),
    ("/collaboration/runs",             ["GET"]),
    ("/collaboration/conflicts",        ["GET"]),
    ("/rag/documents",                  ["GET"]),
])
def test_endpoint_reachable(path, methods):
    """Endpunkt antwortet – kein 500, keine Fehler bei leeren Daten."""
    client = httpx.Client(base_url=BASE, headers=HEADERS, timeout=5.0)
    for method in methods:
        r = getattr(client, method.lower())(path)
        assert r.status_code not in (500, 502, 503), (
            f"{method} {path} returned {r.status_code}: {r.text[:200]}"
        )


def test_status_fields():
    r = httpx.get(f"{BASE}/status", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "privacy_mode" in data
    assert "gates" in data
    assert isinstance(data["gates"], list)


def test_settings_no_secret_fields():
    r = httpx.get(f"{BASE}/settings", headers=HEADERS)
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        text = r.text
        assert "api_key" not in text
        assert "password" not in text
        assert "private_key" not in text


def test_approvals_returns_items():
    r = httpx.get(f"{BASE}/approvals", headers=HEADERS)
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        assert "items" in r.json()


def test_audit_no_secret_classification():
    r = httpx.get(f"{BASE}/audit", headers=HEADERS)
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        items = r.json().get("items", [])
        for item in items:
            assert item.get("classification") != "SECRET"


def test_rag_documents_no_content():
    r = httpx.get(f"{BASE}/rag/documents", headers=HEADERS)
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        for doc in r.json().get("items", []):
            assert "content" not in doc
            assert "chunks" not in doc


def test_empty_states_return_empty_lists():
    """Empty States müssen sauber sein (kein 500, leeres items-Array)."""
    for path in ("/collaboration/runs", "/governance/changesets", "/approvals"):
        r = httpx.get(f"{BASE}{path}", headers=HEADERS)
        assert r.status_code not in (500,), f"{path} returned 500"
        if r.status_code == 200:
            body = r.json()
            assert "items" in body
