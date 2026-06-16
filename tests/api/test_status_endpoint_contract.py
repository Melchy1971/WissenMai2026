from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.api.error_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.api.v1.approvals import get_approval_store, get_audit_log

pytestmark = pytest.mark.unit_fast


REQUIRED_FIELDS = {
    "release_status",
    "system_health",
    "provider_status",
    "workspace_status",
    "privacy_mode",
    "autonomy_level",
    "governance_gate",
    "security_gate",
    "gui_gate",
    "rag_status",
    "agent_status",
    "collaboration_status",
    "open_approvals_count",
    "critical_audit_events_count",
    "open_blockers",
}


@pytest.fixture(autouse=True)
def clear_status_stores():
    get_approval_store().clear()
    get_audit_log().clear()
    yield
    get_approval_store().clear()
    get_audit_log().clear()


def _app_with_auth(context):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_current_auth_context] = lambda: context
    return TestClient(app)


def test_status_contract_contains_required_fields(api_client):
    response = api_client.get("/api/v1/status")

    assert response.status_code == 200
    body = response.json()
    assert REQUIRED_FIELDS <= set(body)
    assert isinstance(body["open_blockers"], list)


def test_status_uses_unknown_instead_of_fake_pass_for_missing_sources(api_client):
    response = api_client.get("/api/v1/status")

    assert response.status_code == 200
    body = response.json()
    for field in (
        "release_status",
        "system_health",
        "provider_status",
        "autonomy_level",
        "governance_gate",
        "security_gate",
        "gui_gate",
        "rag_status",
        "agent_status",
        "collaboration_status",
    ):
        assert body[field] != "PASS"
    assert body["gui_gate"] == "UNKNOWN"
    assert all(gate["status"] != "PASS" for gate in body["gates"])


def test_status_surfaces_critical_blockers_and_counts(api_client):
    get_approval_store().append(
        {
            "id": "approval-critical",
            "status": "pending",
            "risk": "CRITICAL",
            "action": "ROLLBACK",
        }
    )
    get_audit_log().append(
        {
            "id": "audit-critical",
            "classification": "INTERNAL",
            "action": "ROLLBACK_BLOCKED",
            "details": {"risk": "CRITICAL"},
        }
    )

    response = api_client.get("/api/v1/status")

    assert response.status_code == 200
    body = response.json()
    assert body["open_approvals_count"] == 1
    assert body["critical_audit_events_count"] == 1
    assert body["system_health"] == "CRITICAL"
    assert {blocker["source"] for blocker in body["open_blockers"]} >= {"approvals", "audit"}


def test_status_requires_authentication():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    response = TestClient(app).get("/api/v1/status")

    assert response.status_code in {401, 403}


def test_status_requires_workspace():
    client = _app_with_auth(
        AuthContext(
            session_id="session-test",
            user_id="user-test",
            login="user",
            display_name="User",
            workspace_id="",
            role="member",
            permissions=("workspace:read",),
        )
    )

    response = client.get("/api/v1/status")

    assert response.status_code == 403
