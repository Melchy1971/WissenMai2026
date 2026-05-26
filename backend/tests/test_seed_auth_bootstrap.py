from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import AuthSession, User, Workspace, WorkspaceMembership
from app.services.auth import AuthService, hash_password
from scripts import seed_auth


pytestmark = pytest.mark.m4a_auth_truth


def _seed_report_path(tmp_path, monkeypatch):
    report_path = tmp_path / "seed_report.json"
    monkeypatch.setattr(seed_auth, "REPORT_PATH", report_path)
    return report_path


def test_seed_auth_creates_idempotent_bootstrap_admin_login(
    db_session: Session,
    tmp_path,
    monkeypatch,
) -> None:
    report_path = _seed_report_path(tmp_path, monkeypatch)

    seed_auth.main()
    seed_auth.main()

    user = db_session.scalar(select(User).where(User.login == seed_auth.USER_LOGIN))
    workspace = db_session.scalar(select(Workspace).where(Workspace.id == seed_auth.DEFAULT_WORKSPACE_ID))
    memberships = list(db_session.scalars(select(WorkspaceMembership)))
    auth_sessions_before_login = list(db_session.scalars(select(AuthSession)))
    token, _auth_session, login_user, login_memberships = AuthService(db_session).login(
        login=seed_auth.USER_LOGIN,
        password=seed_auth.USER_PASSWORD,
    )

    assert user is not None
    assert user.id == seed_auth.DEFAULT_USER_ID
    assert user.is_active is True
    assert workspace is not None
    assert workspace.is_default is True
    assert auth_sessions_before_login == []
    assert memberships == [
        next(
            item
            for item in memberships
            if item.user_id == seed_auth.DEFAULT_USER_ID
            and item.workspace_id == seed_auth.DEFAULT_WORKSPACE_ID
        )
    ]
    assert memberships[0].role == seed_auth.ROLE
    assert token
    assert login_user.id == seed_auth.DEFAULT_USER_ID
    assert any(
        item.workspace_id == seed_auth.DEFAULT_WORKSPACE_ID and item.role == seed_auth.ROLE
        for item in login_memberships
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["bootstrap_invariant"]["status"] == "PASS"
    assert report["bootstrap_invariant"]["id"] == "auth_seed_bootstrap_admin_login"
    assert "password" not in report["credentials"]


def test_seed_auth_migrates_legacy_login_to_canonical_admin(
    db_session: Session,
    tmp_path,
    monkeypatch,
) -> None:
    _seed_report_path(tmp_path, monkeypatch)
    created = datetime(2026, 5, 26, 8, 0, tzinfo=UTC)
    db_session.add(
        Workspace(
            id=seed_auth.DEFAULT_WORKSPACE_ID,
            name="Old Default",
            is_default=False,
            created_at=created,
        )
    )
    db_session.add(
        User(
            id=seed_auth.DEFAULT_USER_ID,
            display_name="Legacy User",
            login=seed_auth.LEGACY_LOGINS[0],
            password_hash=hash_password("old-password", salt=seed_auth.LEGACY_LOGINS[0]),
            is_active=False,
            is_default=False,
            created_at=created,
        )
    )
    db_session.add(
        WorkspaceMembership(
            id="legacy-membership",
            workspace_id=seed_auth.DEFAULT_WORKSPACE_ID,
            user_id=seed_auth.DEFAULT_USER_ID,
            role="member",
            created_at=created,
            updated_at=created,
        )
    )
    db_session.commit()

    seed_auth.main()

    user = db_session.scalar(select(User).where(User.id == seed_auth.DEFAULT_USER_ID))
    legacy_users = list(db_session.scalars(select(User).where(User.login.in_(seed_auth.LEGACY_LOGINS))))
    membership = db_session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == seed_auth.DEFAULT_USER_ID,
            WorkspaceMembership.workspace_id == seed_auth.DEFAULT_WORKSPACE_ID,
        )
    )
    token, _auth_session, login_user, login_memberships = AuthService(db_session).login(
        login=seed_auth.USER_LOGIN,
        password=seed_auth.USER_PASSWORD,
    )

    assert user is not None
    assert user.login == seed_auth.USER_LOGIN
    assert user.is_active is True
    assert user.is_default is True
    assert legacy_users == []
    assert membership is not None
    assert membership.role == seed_auth.ROLE
    assert token
    assert login_user.id == seed_auth.DEFAULT_USER_ID
    assert any(item.role == seed_auth.ROLE for item in login_memberships)
