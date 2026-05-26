"""
Auth Bootstrap — Truth Tests.

Tests the /api/v1/auth/me bootstrap contract with a real PostgreSQL database
and the FastAPI test client (no mocks, no fakes).

Scenarios:
  1. Valid token  → full session (user, memberships, active_workspace_id)
  2. active_workspace_id equals first membership workspace
  3. Invalid token → 401 AUTH_REQUIRED
  4. No Authorization header → 401 AUTH_REQUIRED
  5. Non-bearer Authorization (Basic ...) → 401 AUTH_REQUIRED
  6. User with zero workspace memberships → 200, active_workspace_id = null
  7. Login flow → /auth/me → active_workspace_id matches login response
  8. Logout → same token → /auth/me → 401 (session revoked)
"""
from __future__ import annotations

from datetime import UTC, datetime
from tests.postgres_truth.support import _uuid_with_prefix
from typing import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection

from app.main import app
from app.services.auth import hash_password, hash_token


pytestmark = [pytest.mark.postgres_truth, pytest.mark.auth_bootstrap, pytest.mark.m4a_auth_truth]

_NO_MEMBERSHIP_USER_ID = _uuid_with_prefix("f2000000", "auth-bootstrap", "no-membership-user")
_NO_MEMBERSHIP_SESSION_ID = "truth-auth-bootstrap-no-membership-session"
_NO_MEMBERSHIP_TOKEN = "truth-auth-bootstrap-no-membership-token-fixed"


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture
def no_membership_token(postgres_truth_database_url: str) -> Iterator[str]:
    """Yields a valid session token for a user with zero workspace memberships."""
    created = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)
    expires = datetime(2036, 5, 13, 10, 0, tzinfo=UTC)

    with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, display_name, login, password_hash, is_active, is_default, created_at)
                VALUES (%s::uuid, 'Bootstrap No Membership', 'auth-bootstrap-no-membership', %s, true, false, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (_NO_MEMBERSHIP_USER_ID, hash_password("nm-pw", salt="nm-salt"), created),
            )
            cur.execute(
                """
                INSERT INTO auth_sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
                VALUES (%s, %s::uuid, %s, %s, %s, %s, null)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    _NO_MEMBERSHIP_SESSION_ID,
                    _NO_MEMBERSHIP_USER_ID,
                    hash_token(_NO_MEMBERSHIP_TOKEN),
                    expires,
                    created,
                    created,
                ),
            )
        conn.commit()

    try:
        yield _NO_MEMBERSHIP_TOKEN
    finally:
        with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM auth_sessions WHERE id = %s", (_NO_MEMBERSHIP_SESSION_ID,))
                cur.execute("DELETE FROM users WHERE id::text = %s", (_NO_MEMBERSHIP_USER_ID,))
            conn.commit()


class TestAuthMeContract:
    """Tests /api/v1/auth/me with real PostgreSQL."""

    def test_valid_token_returns_full_session(self, truth_client: TestClient, truth_seed: dict) -> None:
        resp = truth_client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == truth_seed["user_id"]
        assert data["user"]["login"] != ""
        assert data["user"]["display_name"] != ""
        assert isinstance(data["memberships"], list)
        assert len(data["memberships"]) >= 1
        assert data["active_workspace_id"] == truth_seed["workspace_id"]

    def test_active_workspace_id_matches_first_membership(self, truth_client: TestClient) -> None:
        resp = truth_client.get("/api/v1/auth/me")

        data = resp.json()
        assert data["active_workspace_id"] == data["memberships"][0]["workspace_id"]

    def test_invalid_token_returns_401(self, truth_connection: Connection) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this-token-does-not-exist-in-db"},
        )

        assert resp.status_code == 401
        error = resp.json()["error"]
        assert error["code"] == "AUTH_REQUIRED"

    def test_missing_authorization_header_returns_401(self, truth_connection: Connection) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/auth/me")

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_non_bearer_authorization_returns_401(self, truth_connection: Connection) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_user_without_membership_gets_null_workspace(
        self, no_membership_token: str, truth_connection: Connection
    ) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {no_membership_token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["memberships"] == []
        assert data["active_workspace_id"] is None


class TestAuthLoginLogoutContract:
    """Tests login → /auth/me → logout → /auth/me revocation chain."""

    def test_login_produces_workspace_matching_auth_me(
        self, truth_seed: dict, truth_connection: Connection
    ) -> None:
        truth_ids = truth_seed["ids"]
        client = TestClient(app, raise_server_exceptions=False)

        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "login": f"truth-user-{truth_ids.slug}",
                "password": "secret-password",
            },
        )
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        new_token = login_data["token"]

        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["active_workspace_id"] == login_data["active_workspace_id"]
        assert me_data["user"]["id"] == login_data["user"]["id"]

    def test_logout_revokes_session(
        self, truth_seed: dict, truth_connection: Connection
    ) -> None:
        token = truth_seed["token"]
        client = TestClient(app, raise_server_exceptions=False)

        logout_resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_resp.status_code == 204

        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 401
        assert me_resp.json()["error"]["code"] == "AUTH_REQUIRED"
