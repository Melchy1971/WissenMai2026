import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.api.error_handlers import register_exception_handlers
from app.api.v1.router import api_router


pytestmark = pytest.mark.unit_fast

LEGACY_LIVE_HTTP_TESTS = {
    "test_gui_backend_endpoints.py",
    "test_gui_contracts.py",
    "test_gui_secret_masking.py",
    "test_secret_masking_api.py",
    "test_settings_endpoints.py",
    "test_settings_patch.py",
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.unit_fast)
        if item.path.name in LEGACY_LIVE_HTTP_TESTS:
            item.add_marker(pytest.mark.external_env_only)
            item.add_marker(pytest.mark.legacy_live_http)
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        "external_env_only legacy live-HTTP smoke test; "
                        "excluded from local final gate"
                    )
                )
            )
        else:
            item.add_marker(pytest.mark.local_gate)


def make_auth(role="admin"):
    return AuthContext(
        session_id="session-test",
        user_id="user-test",
        login=f"{role}-user",
        display_name="Test User",
        workspace_id="workspace-test",
        role=role,
        permissions=("workspace:read", "workspace:admin"),
    )


@pytest.fixture
def api_client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_current_auth_context] = lambda: make_auth("admin")
    return TestClient(app)


@pytest.fixture
def member_client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_current_auth_context] = lambda: make_auth("member")
    return TestClient(app)
