from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import get_session
from app.models.documents import User, Workspace, WorkspaceMembership
from app.services.auth import AuthService, hash_password

# Canonical env vars: SEED_ADMIN_* (primary) › WISSEN_DEV_* (legacy fallback) › built-in default.
# Built-in defaults are last-resort only — set SEED_ADMIN_LOGIN in .env for real deployments.
_FALLBACK_LOGIN = "admin@localhost"
_FALLBACK_PASSWORD = "change-me"
USER_LOGIN: str = (
    os.environ.get("SEED_ADMIN_LOGIN")
    or os.environ.get("WISSEN_DEV_LOGIN")
    or _FALLBACK_LOGIN
)
USER_PASSWORD: str = (
    os.environ.get("SEED_ADMIN_PASSWORD")
    or os.environ.get("WISSEN_DEV_PASSWORD")
    or _FALLBACK_PASSWORD
)
USER_DISPLAY_NAME = USER_LOGIN
# Logins that were used in the past and must be migrated/cleared.
LEGACY_LOGINS = ("default-user", "mdickscheit@googlemail.com", "mdickscheit@gmail.com")
DEFAULT_USER_ID = os.environ.get("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001")
DEFAULT_WORKSPACE_ID = os.environ.get("DEFAULT_WORKSPACE_ID", "00000000-0000-0000-0000-000000000001")
WORKSPACE_NAME: str = os.environ.get("SEED_WORKSPACE_NAME", "Default Workspace")
ROLE = "admin"
REPORT_PATH = Path(__file__).resolve().parents[2] / "reports" / "seed_report.json"


def _now() -> datetime:
    return datetime.now(UTC)


def _database_url_for_report() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    if "@" not in database_url:
        return database_url
    credentials, host = database_url.rsplit("@", 1)
    scheme, _, userinfo = credentials.partition("://")
    user, _, _password = userinfo.partition(":")
    return f"{scheme}://{user}:***@{host}"


def _find_user(session) -> User | None:
    user = session.scalar(select(User).where(User.id == DEFAULT_USER_ID))
    if user is not None:
        return user

    user = session.scalar(select(User).where(User.login == USER_LOGIN))
    if user is not None:
        return user

    for legacy_login in LEGACY_LOGINS:
        user = session.scalar(select(User).where(User.login == legacy_login))
        if user is not None:
            return user

    return None


def _clear_conflicting_login(session, *, login: str, keep_user_id: str, repaired: list[str]) -> None:
    conflicting_user = session.scalar(select(User).where(User.login == login, User.id != keep_user_id))
    if conflicting_user is None:
        return
    conflicting_user.login = None
    conflicting_user.is_active = False
    repaired.append(f"cleared conflicting login {login} on user {conflicting_user.id}")


def _assert_bootstrap_invariant(
    session,
    *,
    workspace: Workspace,
) -> dict[str, object]:
    token, auth_session, login_user, memberships = AuthService(session).login(
        login=USER_LOGIN,
        password=USER_PASSWORD,
    )
    matching_membership = next(
        (
            item
            for item in memberships
            if str(item.workspace_id) == str(workspace.id) and item.role == ROLE
        ),
        None,
    )
    if matching_membership is None:
        raise RuntimeError(
            "Auth seed invariant failed: seeded admin login has no admin membership "
            f"for workspace {workspace.id}"
        )
    session.delete(auth_session)
    session.commit()

    return {
        "id": "auth_seed_bootstrap_admin_login",
        "status": "PASS",
        "login": login_user.login,
        "user_id": str(login_user.id),
        "workspace_id": str(matching_membership.workspace_id),
        "role": matching_membership.role,
        "token_issued": bool(token),
        "legacy_logins": list(LEGACY_LOGINS),
    }


def _write_report(
    *,
    workspace: Workspace,
    user: User,
    membership: WorkspaceMembership,
    repaired: list[str],
    invariant: dict[str, object],
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now().isoformat().replace("+00:00", "Z"),
        "database_url": _database_url_for_report(),
        "status": "success",
        "seeded": {
            "workspace": {
                "id": workspace.id,
                "name": workspace.name,
                "is_default": workspace.is_default,
            },
            "user": {
                "id": user.id,
                "login": user.login,
                "role": membership.role,
            },
            "membership": {
                "workspace_id": membership.workspace_id,
                "user_id": membership.user_id,
                "role": membership.role,
            },
        },
        "credentials": {
            "login": USER_LOGIN,
        },
        "bootstrap_invariant": invariant,
        "legacy_repairs": repaired,
    }
    REPORT_PATH.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def main():
    for session in get_session():
        repaired: list[str] = []
        now = _now()

        workspace = session.scalar(select(Workspace).where(Workspace.id == DEFAULT_WORKSPACE_ID))
        if workspace is None:
            workspace = Workspace(
                id=DEFAULT_WORKSPACE_ID,
                name=WORKSPACE_NAME,
                is_default=True,
                created_at=now,
            )
            session.add(workspace)
            print(f"Workspace created: {workspace.id}")
        else:
            workspace.name = WORKSPACE_NAME
            workspace.is_default = True

        user = _find_user(session)
        if user is None:
            user = User(
                id=DEFAULT_USER_ID,
                display_name=USER_DISPLAY_NAME,
                login=USER_LOGIN,
                password_hash=hash_password(USER_PASSWORD, salt=USER_LOGIN),
                is_active=True,
                is_default=True,
                created_at=now,
            )
            session.add(user)
            session.commit()
            print(f"User created: {user.id}")
        else:
            if user.login in LEGACY_LOGINS:
                repaired.append(f"updated legacy login {user.login} on user {user.id}")
            _clear_conflicting_login(session, login=USER_LOGIN, keep_user_id=str(user.id), repaired=repaired)
            for legacy_login in LEGACY_LOGINS:
                _clear_conflicting_login(session, login=legacy_login, keep_user_id=str(user.id), repaired=repaired)

            updated = bool(repaired)
            if user.display_name != USER_DISPLAY_NAME:
                user.display_name = USER_DISPLAY_NAME
                updated = True
            if user.login != USER_LOGIN:
                user.login = USER_LOGIN
                updated = True
            if not user.is_active:
                user.is_active = True
                updated = True
            if not user.is_default:
                user.is_default = True
                updated = True
            new_hash = hash_password(USER_PASSWORD, salt=USER_LOGIN)
            if user.password_hash != new_hash:
                user.password_hash = new_hash
                updated = True
            if updated:
                session.commit()
                print(f"User updated: {user.id}")

        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.workspace_id == workspace.id,
            )
        )
        if not membership:
            membership = WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=workspace.id,
                user_id=user.id,
                role=ROLE,
                created_at=now,
                updated_at=now,
            )
            session.add(membership)
            session.commit()
            print(f"Membership created: {membership.id}")
        else:
            if membership.role != ROLE:
                membership.role = ROLE
                membership.updated_at = now
                session.commit()
                print(f"Membership role updated: {membership.id}")

        session.commit()
        invariant = _assert_bootstrap_invariant(session, workspace=workspace)
        _write_report(
            workspace=workspace,
            user=user,
            membership=membership,
            repaired=repaired,
            invariant=invariant,
        )

        print("\nValidation:")
        print(f"user_id: {user.id}")
        print(f"workspace_id: {workspace.id}")
        print(f"role: {membership.role}")
        print(f"is_active: {user.is_active}")
        print(f"login: {user.login}")
        print("bootstrap_invariant: PASS")
        print(f"report: {REPORT_PATH}")

if __name__ == "__main__":
    main()
            repaired=repaired,
            invariant=invariant,
        )

        print("\nValidation:")
        print(f"user_id: {user.id}")
        print(f"workspace_id: {workspace.id}")
        print(f"role: {membership.role}")
        print(f"is_active: {user.is_active}")
        print(f"login: {user.login}")
        print("bootstrap_invariant: PASS")
        print(f"report: {REPORT_PATH}")

if __name__ == "__main__":
    main()
