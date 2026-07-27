"""Multi-user provisioning service (Story 4).

Creates users with an automatic private workspace and a membership in the single
shared workspace, and manages shared-workspace roles and user deactivation.

All write paths are transactional (one commit) and, on PostgreSQL, serialized per
login via a transaction-scoped advisory lock (``user_provisioning`` scope). On
non-PostgreSQL backends the advisory lock is a no-op (see AdvisoryLockService).
"""
from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    LastAdminProtectedApiError,
    PasswordPolicyViolatedApiError,
    RequestValidationApiError,
    SharedWorkspaceExistsApiError,
    SharedWorkspaceMissingApiError,
    UserAlreadyExistsApiError,
    UserNotFoundApiError,
)
from app.models.documents import AuthSession, User, Workspace, WorkspaceMembership
from app.repositories.provisioning import UserRepository, WorkspaceRepository
from app.services.advisory_lock import AdvisoryLockService
from app.services.auth import hash_password

# NOTE: concrete policy values are a pending PO decision (Fachkonzept §11.3).
# Minimum length is enforced as a safe default until that decision lands.
MIN_PASSWORD_LENGTH = 8

_SHARED_ROLES = ("admin", "member")


class ProvisioningService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._workspaces = WorkspaceRepository(session)

    # -- shared workspace ---------------------------------------------------

    def ensure_shared_workspace(self, *, name: str = "Gemeinsamer Bereich") -> Workspace:
        """Idempotent: return the shared workspace, creating it if absent."""
        existing = self._workspaces.get_shared()
        if existing is not None:
            return existing
        workspace = Workspace(
            id=str(uuid4()),
            name=name.strip() or "Gemeinsamer Bereich",
            is_default=True,  # ties into ux_workspaces_single_default (shared singleton)
            kind="shared",
            owner_user_id=None,
            created_at=datetime.now(UTC),
        )
        self._workspaces.add(workspace)
        self._session.commit()
        return workspace

    def initialize_shared_workspace(self, *, name: str = "Gemeinsamer Bereich") -> Workspace:
        """Explicit one-time init: fails if a shared workspace already exists."""
        if self._workspaces.get_shared() is not None:
            raise SharedWorkspaceExistsApiError()
        return self.ensure_shared_workspace(name=name)

    # -- user provisioning --------------------------------------------------

    def create_user(self, *, display_name: str, login: str, initial_password: str) -> dict[str, str]:
        normalized_login = (login or "").strip()
        normalized_name = (display_name or "").strip()
        if not normalized_login or not normalized_name:
            raise RequestValidationApiError(
                details={"fields": ["display_name", "login"], "reason": "must not be empty"}
            )
        self._validate_password(initial_password)

        # Serialize concurrent provisioning of the same login (PG only).
        AdvisoryLockService.from_session(self._session).acquire_user_provisioning_lock(login=normalized_login)

        shared = self._workspaces.get_shared()
        if shared is None:
            raise SharedWorkspaceMissingApiError()

        if self._users.get_by_login(normalized_login) is not None:
            raise UserAlreadyExistsApiError(details={"login": normalized_login})

        now = datetime.now(UTC)
        user = User(
            id=str(uuid4()),
            display_name=normalized_name,
            login=normalized_login,
            password_hash=hash_password(initial_password, salt=token_urlsafe(16)),
            is_active=True,
            is_default=False,
            created_at=now,
        )
        self._users.add(user)

        private = Workspace(
            id=str(uuid4()),
            name=normalized_name,
            is_default=False,
            kind="private",
            owner_user_id=user.id,
            created_at=now,
        )
        self._workspaces.add(private)

        self._workspaces.add_membership(
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=private.id,
                user_id=user.id,
                role="owner",
                created_at=now,
                updated_at=now,
            )
        )
        self._workspaces.add_membership(
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=shared.id,
                user_id=user.id,
                role="member",
                created_at=now,
                updated_at=now,
            )
        )

        self._session.commit()
        return {
            "user_id": user.id,
            "login": user.login,
            "private_workspace_id": private.id,
            "shared_workspace_id": shared.id,
        }

    def deactivate_user(self, *, user_id: str) -> None:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundApiError(details={"user_id": str(user_id)})
        now = datetime.now(UTC)
        user.is_active = False
        # Invalidate all active sessions of the user.
        sessions = self._session.scalars(
            select(AuthSession).where(AuthSession.user_id == str(user.id), AuthSession.revoked_at.is_(None))
        )
        for auth_session in sessions:
            auth_session.revoked_at = now
        self._session.commit()

    def set_shared_role(self, *, user_id: str, role: str) -> None:
        if role not in _SHARED_ROLES:
            raise RequestValidationApiError(details={"field": "role", "allowed": list(_SHARED_ROLES)})
        shared = self._workspaces.get_shared()
        if shared is None:
            raise SharedWorkspaceMissingApiError()
        membership = self._workspaces.get_membership(workspace_id=shared.id, user_id=user_id)
        if membership is None:
            raise UserNotFoundApiError(details={"user_id": str(user_id), "scope": "shared_membership"})

        # Protect the last active admin of the shared workspace.
        if membership.role == "admin" and role != "admin":
            if self._workspaces.count_active_admins(workspace_id=shared.id) <= 1:
                raise LastAdminProtectedApiError()

        membership.role = role
        membership.updated_at = datetime.now(UTC)
        self._session.commit()

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _validate_password(password: str | None) -> None:
        if not password or len(password.strip()) < MIN_PASSWORD_LENGTH:
            raise PasswordPolicyViolatedApiError(
                details={"min_length": MIN_PASSWORD_LENGTH}
            )
