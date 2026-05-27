"""
Workspace Bootstrap — Truth Tests.

Tests the workspace bootstrap contract with a real PostgreSQL database
and the FastAPI test client (no mocks, no fakes).

Rules under test:
  1. active_workspace_id comes only from membership (never fabricated)
  2. No default workspace: zero memberships → active_workspace_id = null
  3. X-Workspace-Id must match a workspace the user is a member of
  4. Multi-workspace user: active_workspace_id is the first membership workspace
  5. Workspace access is scoped: wrong X-Workspace-Id → WORKSPACE_ACCESS_FORBIDDEN
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection

from app.main import app
from app.services.auth import hash_password, hash_token
from tests.postgres_truth.support import TruthIds, _uuid_with_prefix

pytestmark = [pytest.mark.postgres_truth, pytest.mark.workspace_bootstrap, pytest.mark.m4a_auth_truth]

_NO_WS_USER_ID = _uuid_with_prefix("f2000000", "workspace-bootstrap", "no-workspace-user")
_NO_WS_SESSION_ID = "truth-workspace-bootstrap-no-ws-session"
_NO_WS_TOKEN = "truth-workspace-bootstrap-no-ws-token-fixed"


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _client(*, token: str, workspace_id: str | None = None) -> TestClient:
    headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    if workspace_id is not None:
        headers["X-Workspace-Id"] = workspace_id
    return TestClient(app, headers=headers, raise_server_exceptions=False)


@pytest.fixture
def no_workspace_token(postgres_truth_database_url: str) -> Iterator[str]:
    """Yields a valid session token for a user with zero workspace memberships."""
    created = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)
    expires = datetime(2036, 5, 13, 10, 0, tzinfo=UTC)

    with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, display_name, login, password_hash, is_active, is_default, created_at)
                VALUES (%s::uuid, 'WS Bootstrap No Membership', 'ws-bootstrap-no-ws', %s, true, false, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (_NO_WS_USER_ID, hash_password("wsboot-nm-pw", salt="wsboot-nm-salt"), created),
            )
            cur.execute(
                """
                INSERT INTO auth_sessions
                    (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
                VALUES (%s, %s::uuid, %s, %s, %s, %s, null)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    _NO_WS_SESSION_ID,
                    _NO_WS_USER_ID,
                    hash_token(_NO_WS_TOKEN),
                    expires,
                    created,
                    created,
                ),
            )
        conn.commit()

    try:
        yield _NO_WS_TOKEN
    finally:
        with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM auth_sessions WHERE id = %s", (_NO_WS_SESSION_ID,))
                cur.execute("DELETE FROM users WHERE id::text = %s", (_NO_WS_USER_ID,))
            conn.commit()


@pytest.fixture
def multi_workspace_seed(
    truth_seed: dict,
    truth_ids: TruthIds,
    postgres_truth_database_url: str,
) -> Iterator[dict]:
    """Adds a second membership to the main truth user (workspace_id + other_workspace_id)."""
    second_membership_id = f"truth-{truth_ids.slug}-multi-ws-membership"
    created = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)

    with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspace_memberships
                    (id, workspace_id, user_id, role, created_at, updated_at)
                VALUES (%s, %s::uuid, %s::uuid, 'member', %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    second_membership_id,
                    truth_ids.other_workspace_id,
                    truth_ids.user_id,
                    created,
                    created,
                ),
            )
        conn.commit()

    try:
        yield {
            **truth_seed,
            "second_membership_id": second_membership_id,
            "workspace_2_id": truth_ids.other_workspace_id,
        }
    finally:
        with psycopg.connect(_psycopg_url(postgres_truth_database_url)) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM workspace_memberships WHERE id = %s", (second_membership_id,)
                )
            conn.commit()


class TestWorkspaceBootstrapContract:
    """Tests the /auth/me workspace bootstrap contract with real PostgreSQL."""

    def test_single_workspace_user_gets_that_workspace_as_active(
        self,
        truth_client: TestClient,
        truth_seed: dict,
    ) -> None:
        resp = truth_client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["active_workspace_id"] == truth_seed["workspace_id"]
        assert any(
            m["workspace_id"] == truth_seed["workspace_id"]
            for m in data["memberships"]
        )

    def test_active_workspace_id_is_always_from_memberships(
        self,
        truth_client: TestClient,
        truth_seed: dict,
    ) -> None:
        resp = truth_client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        membership_workspace_ids = {m["workspace_id"] for m in data["memberships"]}
        assert data["active_workspace_id"] in membership_workspace_ids

    def test_no_membership_user_gets_null_active_workspace(
        self,
        no_workspace_token: str,
        truth_connection: Connection,
    ) -> None:
        client = _client(token=no_workspace_token)
        resp = client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["memberships"] == []
        assert data["active_workspace_id"] is None

    def test_multi_workspace_user_active_workspace_is_in_memberships(
        self,
        multi_workspace_seed: dict,
        truth_connection: Connection,
    ) -> None:
        client = _client(
            token=multi_workspace_seed["token"],
            workspace_id=multi_workspace_seed["workspace_id"],
        )
        resp = client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["memberships"]) == 2
        membership_workspace_ids = {m["workspace_id"] for m in data["memberships"]}
        assert data["active_workspace_id"] in membership_workspace_ids

    def test_multi_workspace_user_memberships_contains_both_workspaces(
        self,
        multi_workspace_seed: dict,
        truth_connection: Connection,
    ) -> None:
        client = _client(
            token=multi_workspace_seed["token"],
            workspace_id=multi_workspace_seed["workspace_id"],
        )
        resp = client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        membership_workspace_ids = {m["workspace_id"] for m in data["memberships"]}
        assert multi_workspace_seed["workspace_id"] in membership_workspace_ids
        assert multi_workspace_seed["workspace_2_id"] in membership_workspace_ids


class TestWorkspaceAccessEnforcement:
    """Tests that X-Workspace-Id is validated against membership on every request."""

    def test_valid_x_workspace_id_allows_document_list(
        self,
        truth_seed: dict,
        truth_connection: Connection,
    ) -> None:
        client = _client(
            token=truth_seed["token"],
            workspace_id=truth_seed["workspace_id"],
        )
        resp = client.get("/documents")

        assert resp.status_code == 200

    def test_x_workspace_id_for_non_member_workspace_is_forbidden(
        self,
        truth_seed: dict,
        truth_connection: Connection,
    ) -> None:
        # Main user is NOT a member of other_workspace_id (only other_user is)
        client = _client(
            token=truth_seed["token"],
            workspace_id=truth_seed["other_workspace_id"],
        )
        resp = client.get("/documents")

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"

    def test_x_workspace_id_for_non_member_workspace_blocks_search(
        self,
        truth_seed: dict,
        truth_connection: Connection,
    ) -> None:
        client = _client(
            token=truth_seed["token"],
            workspace_id=truth_seed["other_workspace_id"],
        )
        resp = client.get("/api/v1/search/chunks", params={"q": "test"})

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"

    def test_x_workspace_id_for_non_member_workspace_blocks_import(
        self,
        truth_seed: dict,
        truth_connection: Connection,
    ) -> None:
        client = _client(
            token=truth_seed["token"],
            workspace_id=truth_seed["other_workspace_id"],
        )
        resp = client.post(
            "/documents/import",
            files={"file": ("ws-bootstrap-forbidden.txt", b"# forbidden\n", "text/plain")},
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "WORKSPACE_ACCESS_FORBIDDEN"

    def test_missing_x_workspace_id_returns_auth_or_workspace_error(
        self,
        truth_seed: dict,
        truth_connection: Connection,
    ) -> None:
        client = _client(token=truth_seed["token"])
        resp = client.get("/documents")

        assert resp.status_code in {401, 403}
        assert resp.json()["error"]["code"] in {"AUTH_REQUIRED", "WORKSPACE_ACCESS_FORBIDDEN"}

    def test_multi_workspace_user_can_switch_to_second_workspace(
        self,
        multi_workspace_seed: dict,
        truth_connection: Connection,
    ) -> None:
        # After bootstrap, user can make requests against their second workspace
        client = _client(
            token=multi_workspace_seed["token"],
            workspace_id=multi_workspace_seed["workspace_2_id"],
        )
        resp = client.get("/documents")

        assert resp.status_code == 200
