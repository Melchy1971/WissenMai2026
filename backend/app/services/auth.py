from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac, sha256
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import AuthSession, User, WorkspaceMembership

logger = logging.getLogger("app.services.auth")


PBKDF2_ITERATIONS = 600_000


def hash_password(password: str, *, salt: str) -> str:
    derived = pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${derived.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations, salt, digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
    return candidate == digest


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthenticatedContext:
    session_id: str
    user_id: str
    login: str
    display_name: str
    workspace_id: str
    role: str


class AuthenticationError(ValueError):
    pass


class WorkspaceAccessError(ValueError):
    pass


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def login(self, *, login: str, password: str) -> tuple[str, AuthSession, User, list[WorkspaceMembership]]:
        normalized_login = login.strip()
        if not normalized_login or not password.strip():
            logger.warning(
                "auth.login_failed",
                extra={"event": "auth.login_failed", "reason": "empty_credentials"},
            )
            raise AuthenticationError("Invalid credentials")

        user: User | None = None
        try:
            user = self._session.scalar(select(User).where(User.login == normalized_login))
        except Exception:
            logger.exception(
                "auth.login_failed",
                extra={"event": "auth.login_failed", "reason": "db_error"},
            )
            raise AuthenticationError("Invalid credentials")

        if user is None:
            logger.warning(
                "auth.login_failed",
                extra={"event": "auth.login_failed", "reason": "login_not_found"},
            )
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            logger.warning(
                "auth.login_failed",
                extra={
                    "event": "auth.login_failed",
                    "reason": "user_inactive",
                    "user_id": str(user.id),
                },
            )
            raise AuthenticationError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            logger.warning(
                "auth.login_failed",
                extra={
                    "event": "auth.login_failed",
                    "reason": "password_mismatch",
                    "user_id": str(user.id),
                },
            )
            raise AuthenticationError("Invalid credentials")

        memberships = list(
            self._session.scalars(
                select(WorkspaceMembership)
                .where(WorkspaceMembership.user_id == str(user.id))
                .order_by(WorkspaceMembership.workspace_id.asc())
            )
        )

        now = datetime.now(UTC)
        token = token_urlsafe(32)
        auth_session = AuthSession(
            id=str(uuid4()),
            user_id=str(user.id),
            token_hash=hash_token(token),
            expires_at=now + timedelta(hours=12),
            created_at=now,
            last_seen_at=now,
            revoked_at=None,
        )
        self._session.add(auth_session)
        self._session.commit()
        self._session.refresh(auth_session)
        return token, auth_session, user, memberships

    def authenticate(self, *, bearer_token: str, workspace_id: str) -> AuthenticatedContext:
        normalized_workspace_id = workspace_id.strip()
        if not normalized_workspace_id:
            raise WorkspaceAccessError("workspace header is required")

        session_token_hash = hash_token(bearer_token)
        auth_session = self._session.scalar(select(AuthSession).where(AuthSession.token_hash == session_token_hash))
        now = datetime.now(UTC)
        expires_at = self._normalize_datetime(auth_session.expires_at) if auth_session is not None else None
        if auth_session is None or auth_session.revoked_at is not None or expires_at is None or expires_at <= now:
            raise AuthenticationError("Authentication required")

        user = self._session.scalar(
            select(User).where(User.id == str(auth_session.user_id))
        )
        if user is None or not user.is_active or not user.login:
            raise AuthenticationError("Authentication required")

        membership = self._session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == str(user.id),
                WorkspaceMembership.workspace_id == normalized_workspace_id,
            )
        )
        if membership is None:
            raise WorkspaceAccessError("Workspace access forbidden")

        session_id = str(auth_session.id)
        user_id = str(user.id)
        user_login = user.login
        user_display_name = user.display_name
        workspace_id = str(membership.workspace_id)
        role = membership.role

        auth_session.last_seen_at = now
        self._session.add(auth_session)
        self._session.commit()

        return AuthenticatedContext(
            session_id=session_id,
            user_id=user_id,
            login=user_login,
            display_name=user_display_name,
            workspace_id=workspace_id,
            role=role,
        )

    def revoke_session(self, *, bearer_token: str) -> None:
        session_token_hash = hash_token(bearer_token)
        auth_session = self._session.scalar(select(AuthSession).where(AuthSession.token_hash == session_token_hash))
        if auth_session is None or auth_session.revoked_at is not None:
            return
        auth_session.revoked_at = datetime.now(UTC)
        self._session.add(auth_session)
        self._session.commit()

    def get_session_state(self, *, bearer_token: str) -> tuple[User, list[WorkspaceMembership]]:
        session_token_hash = hash_token(bearer_token)
        auth_session = self._session.scalar(select(AuthSession).where(AuthSession.token_hash == session_token_hash))
        now = datetime.now(UTC)
        expires_at = self._normalize_datetime(auth_session.expires_at) if auth_session is not None else None
        if auth_session is None or auth_session.revoked_at is not None or expires_at is None or expires_at <= now:
            raise AuthenticationError("Authentication required")

        user = self._session.scalar(select(User).where(User.id == str(auth_session.user_id)))
        if user is None or not user.is_active or not user.login:
            raise AuthenticationError("Authentication required")

        memberships = list(
            self._session.scalars(
                select(WorkspaceMembership)
                .where(WorkspaceMembership.user_id == str(user.id))
                .order_by(WorkspaceMembership.workspace_id.asc())
            )
        )

        auth_session.last_seen_at = now
        self._session.add(auth_session)
        self._session.commit()

        return user, memberships

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)        session_token_hash = hash_token(bearer_token)
        auth_session = self._session.scalar(
            select(AuthSession).where(AuthSession.token_hash == session_token_hash)
        )
        now = datetime.now(UTC)
        expires_at = self._normalize_datetime(auth_session.expires_at) if auth_session is not None else None
        if auth_session is None or auth_session.revoked_at is not None or expires_at is None or expires_at <= now:
            raise AuthenticationError("Authentication required")

        user = self._session.scalar(select(User).where(User.id == str(auth_session.user_id)))
        if user is None or not user.is_active:
            raise AuthenticationError("Authentication required")

        memberships = list(
            self._session.scalars(
                select(WorkspaceMembership)
                .where(WorkspaceMembership.user_id == str(user.id))
                .order_by(WorkspaceMembership.workspace_id.asc())
            )
        )

        auth_session.last_seen_at = now
        self._session.add(auth_session)
        self._session.commit()

        return user, memberships

    @staticmethod
    def _normalize_datetime(dt: datetime | None) -> datetime | None:
        """Ensure datetime is timezone-aware (UTC) for consistent comparison."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt
