from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.errors import AdminRequiredApiError, ApiError, AuthRequiredApiError, WorkspaceAccessForbiddenApiError
from app.services.auth import AuthenticatedContext


@dataclass(frozen=True)
class AuthContext:
    session_id: str
    user_id: str
    login: str
    display_name: str
    workspace_id: str
    role: str
    permissions: tuple[str, ...]


def _permissions_for_role(role: str) -> tuple[str, ...]:
    base_permissions = ("workspace:read", "document:import")
    if role in {"owner", "admin"}:
        return (
            *base_permissions,
            "workspace:admin",
            "settings:write",
            "governance:write",
            "approval:decide",
            "orchestrator:run",
            "collaboration:run",
            "tools:write",
            "plugins:write",
        )
    return base_permissions


def get_current_auth_context(request: Request) -> AuthContext:
    context = getattr(request.state, "auth_context", None)
    if context is None:
        raise AuthRequiredApiError()
    if not isinstance(context, AuthenticatedContext):
        raise ApiError(message="Invalid auth context")
    return AuthContext(
        session_id=context.session_id,
        user_id=context.user_id,
        login=context.login,
        display_name=context.display_name,
        workspace_id=context.workspace_id,
        role=context.role,
        permissions=_permissions_for_role(context.role),
    )


def get_request_auth_context(request: Request) -> AuthContext:
    return get_current_auth_context(request)


RequestAuthContext = AuthContext


def require_workspace_member(context: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
    if not context.workspace_id:
        raise WorkspaceAccessForbiddenApiError()
    return context


def require_workspace_admin(context: AuthContext = Depends(require_workspace_member)) -> AuthContext:
    if context.role not in {"owner", "admin"}:
        raise AdminRequiredApiError()
    return context


def has_permission(context: AuthContext, permission: str) -> bool:
    return context.role in {"owner", "admin"} or permission in context.permissions
