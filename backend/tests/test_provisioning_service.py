"""Multi-user provisioning service tests (Story 3/4).

Runs on the SQLite unit path (conftest ``db_session``). DB-level invariants
(single shared workspace, one private workspace per user) are covered separately
by the PostgreSQL migration test for revision 20260724_0027.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core import errors as E
from app.models.documents import AuthSession, Workspace, WorkspaceMembership
from app.services.auth import AuthenticationError, AuthService
from app.services.provisioning import ProvisioningService

pytestmark = [pytest.mark.m4a_auth_truth]

_PW = "secret12"


def _svc(db_session):
    return ProvisioningService(db_session)


def test_create_user_requires_shared_workspace(db_session):
    with pytest.raises(E.SharedWorkspaceMissingApiError):
        _svc(db_session).create_user(display_name="A", login="a@x.de", initial_password=_PW)


def test_ensure_shared_workspace_is_idempotent(db_session):
    svc = _svc(db_session)
    first = svc.ensure_shared_workspace()
    second = svc.ensure_shared_workspace()
    assert first.id == second.id
    assert first.kind == "shared" and first.is_default is True


def test_initialize_shared_workspace_twice_fails(db_session):
    svc = _svc(db_session)
    svc.initialize_shared_workspace()
    with pytest.raises(E.SharedWorkspaceExistsApiError):
        svc.initialize_shared_workspace()


def test_create_user_provisions_private_and_shared(db_session):
    svc = _svc(db_session)
    shared = svc.ensure_shared_workspace()
    result = svc.create_user(display_name="Alice", login="alice@x.de", initial_password=_PW)

    private = db_session.get(Workspace, result["private_workspace_id"])
    assert private.kind == "private"
    assert private.owner_user_id == result["user_id"]
    assert result["shared_workspace_id"] == shared.id

    roles = {
        ("shared" if m.workspace_id == shared.id else "private"): m.role
        for m in db_session.scalars(
            select(WorkspaceMembership).where(WorkspaceMembership.user_id == result["user_id"])
        )
    }
    assert roles == {"private": "owner", "shared": "member"}


def test_duplicate_login_rejected(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    svc.create_user(display_name="Alice", login="alice@x.de", initial_password=_PW)
    with pytest.raises(E.UserAlreadyExistsApiError):
        svc.create_user(display_name="Alice2", login="alice@x.de", initial_password=_PW)


def test_weak_password_rejected(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    with pytest.raises(E.PasswordPolicyViolatedApiError):
        svc.create_user(display_name="Bob", login="bob@x.de", initial_password="short")


def test_provisioned_user_can_authenticate(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    svc.create_user(display_name="Alice", login="alice@x.de", initial_password=_PW)
    token, _session, user, memberships = AuthService(db_session).login(login="alice@x.de", password=_PW)
    assert token
    assert user.login == "alice@x.de"
    assert len(memberships) == 2


def test_last_admin_cannot_be_demoted(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    a = svc.create_user(display_name="Alice", login="alice@x.de", initial_password=_PW)
    svc.set_shared_role(user_id=a["user_id"], role="admin")
    with pytest.raises(E.LastAdminProtectedApiError):
        svc.set_shared_role(user_id=a["user_id"], role="member")


def test_demote_allowed_when_second_admin_exists(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    a = svc.create_user(display_name="Alice", login="alice@x.de", initial_password=_PW)
    b = svc.create_user(display_name="Bob", login="bob@x.de", initial_password=_PW)
    svc.set_shared_role(user_id=a["user_id"], role="admin")
    svc.set_shared_role(user_id=b["user_id"], role="admin")
    svc.set_shared_role(user_id=a["user_id"], role="member")  # must not raise
    shared = svc.ensure_shared_workspace()
    membership = db_session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == shared.id,
            WorkspaceMembership.user_id == a["user_id"],
        )
    )
    assert membership.role == "member"


def test_deactivate_user_revokes_sessions_and_blocks_login(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    a = svc.create_user(display_name="Alice", login="alice@x.de", initial_password=_PW)
    AuthService(db_session).login(login="alice@x.de", password=_PW)

    svc.deactivate_user(user_id=a["user_id"])

    open_sessions = list(
        db_session.scalars(
            select(AuthSession).where(
                AuthSession.user_id == a["user_id"], AuthSession.revoked_at.is_(None)
            )
        )
    )
    assert open_sessions == []
    with pytest.raises(AuthenticationError):
        AuthService(db_session).login(login="alice@x.de", password=_PW)


def test_unknown_user_deactivate_and_role(db_session):
    svc = _svc(db_session)
    svc.ensure_shared_workspace()
    with pytest.raises(E.UserNotFoundApiError):
        svc.deactivate_user(user_id="does-not-exist")
    with pytest.raises(E.UserNotFoundApiError):
        svc.set_shared_role(user_id="does-not-exist", role="admin")
