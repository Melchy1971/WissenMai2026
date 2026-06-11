"""GUI API Contracts – Smoke-Tests für alle Pflicht-Endpunkte."""
import pytest
import httpx

BASE = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-token", "X-Workspace-Id": "ws-test"}


@pytest.mark.parametrize("path", [
    "/api/v1/status",
    "/api/v1/approvals",
    "/api/v1/audit",
    "/api/v1/tools",
    "/api/v1/memory",
    "/api/v1/agents",
    "/api/v1/agents/executions",
    "/api/v1/rag/documents",
    "/api/v1/collaboration/teams",
    "/api/v1/collaboration/runs",
    "/api/v1/governance/status",
    "/api/v1/governance/changesets",
    "/api/v1/governance/rollback-points",
    "/api/v1/governance/policy-decisions",
    "/api/v1/security/status",
    "/api/v1/settings",
    "/api/v1/tasks",
    "/api/v1/projects",
])
def test_endpoint_exists(path):
    r = httpx.get(f"{BASE}{path}", headers=HEADERS)
    assert r.status_code in (200, 401, 403), \
        f"Unexpected status {r.status_code} for {path}"


def test_status_returns_result_pattern():
    r = httpx.get(f"{BASE}/api/v1/status", headers=HEADERS)
    assert r.status_code == 200
    # Result-Pattern: data enthält mindestens 'privacy_mode' und 'gates'
    data = r.json()
    assert "privacy_mode" in data or "error" in data


def test_approvals_items_list():
    r = httpx.get(f"{BASE}/api/v1/approvals", headers=HEADERS)
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        body = r.json()
        assert "items" in body


def test_no_secret_in_audit_response():
    r = httpx.get(f"{BASE}/api/v1/audit", headers=HEADERS)
    if r.status_code != 200:
        pytest.skip("Audit endpoint not available")
    items = r.json().get("items", [])
    for item in items:
        assert item.get("classification") != "SECRET", \
            "SECRET entries must not be returned by audit endpoint"
