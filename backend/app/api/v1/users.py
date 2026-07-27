"""Benutzerverwaltung fuer Multi-User V1 (Story 5).

Deckt den Onboarding-Pfad der V1-Definition-of-Done ab: neuen User anlegen ->
privater Workspace entsteht automatisch -> Mitgliedschaft im gemeinsamen
Workspace. Vorher entstanden User ausschliesslich ueber ``scripts/seed_auth.py``.

Rechte: alle Endpunkte verlangen die Rolle ``admin`` oder ``owner`` **im
gemeinsamen Workspace**, nicht im gerade aktiven. Das ist der Unterschied zu
``require_workspace_admin``: wer in seinem eigenen privaten Bereich ``owner``
ist, darf deshalb noch lange keine Benutzer anlegen.
"""
from __future__ import annotations

from typing import Annotated, Iterator

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.core.database import DatabaseConfigurationError
from app.core.errors import AdminRequiredApiError, ApiError, SharedWorkspaceMissingApiError
from app.db.session import get_session
from app.models.documents import User, Workspace, WorkspaceMembership
from app.repositories.provisioning import UserRepository, WorkspaceRepository
from app.schemas.users import (
    CreateUserRequest,
    CreateUserResponse,
    SetSharedRoleRequest,
    SharedWorkspaceResponse,
    UserResponse,
)
from app.services.provisioning import ProvisioningService

router = APIRouter(prefix="/users", tags=["users"])

_SHARED_ADMIN_ROLES = {"owner", "admin"}


def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def require_shared_admin(
    context: Annotated[AuthContext, Depends(get_current_auth_context)],
    session: Annotated[Session, Depends(get_db_session)],
) -> AuthContext:
    """Erlaubt nur Admins/Owner des gemeinsamen Workspace."""
    shared = WorkspaceRepository(session).get_shared()
    if shared is None:
        raise SharedWorkspaceMissingApiError()
    membership = session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == shared.id,
            WorkspaceMembership.user_id == str(context.user_id),
        )
    )
    if membership is None or membership.role not in _SHARED_ADMIN_ROLES:
        raise AdminRequiredApiError(details={"scope": "shared_workspace"})
    return context


SharedAdmin = Annotated[AuthContext, Depends(require_shared_admin)]
DbSession = Annotated[Session, Depends(get_db_session)]


def _to_response(
    user: User,
    *,
    shared_role: str | None,
    private_workspace_id: str | None,
) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        login=user.login,
        display_name=user.display_name,
        is_active=bool(user.is_active),
        created_at=user.created_at,
        shared_role=shared_role if shared_role in ("admin", "member") else None,
        private_workspace_id=private_workspace_id,
    )


@router.post("", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    _admin: SharedAdmin,
    session: DbSession,
) -> CreateUserResponse:
    result = ProvisioningService(session).create_user(
        display_name=payload.display_name,
        login=payload.login,
        initial_password=payload.initial_password,
    )
    return CreateUserResponse(**result)


@router.get("", response_model=list[UserResponse])
def list_users(
    _admin: SharedAdmin,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserResponse]:
    workspaces = WorkspaceRepository(session)
    shared = workspaces.get_shared()
    if shared is None:
        raise SharedWorkspaceMissingApiError()

    users = UserRepository(session).list(limit=limit, offset=offset)
    user_ids = [str(user.id) for user in users]

    roles = {
        row.user_id: row.role
        for row in session.execute(
            select(WorkspaceMembership.user_id, WorkspaceMembership.role).where(
                WorkspaceMembership.workspace_id == shared.id,
                WorkspaceMembership.user_id.in_(user_ids),
            )
        )
    }
    privates = {
        row.owner_user_id: row.id
        for row in session.execute(
            select(Workspace.owner_user_id, Workspace.id).where(
                Workspace.kind == "private", Workspace.owner_user_id.in_(user_ids)
            )
        )
    }
    return [
        _to_response(
            user,
            shared_role=roles.get(str(user.id)),
            private_workspace_id=privates.get(str(user.id)),
        )
        for user in users
    ]


@router.get("/shared-workspace", response_model=SharedWorkspaceResponse)
def get_shared_workspace(_admin: SharedAdmin, session: DbSession) -> SharedWorkspaceResponse:
    shared = WorkspaceRepository(session).get_shared()
    if shared is None:
        raise SharedWorkspaceMissingApiError()
    member_count = int(
        session.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(WorkspaceMembership.workspace_id == shared.id)
        )
        or 0
    )
    return SharedWorkspaceResponse(
        workspace_id=str(shared.id), name=shared.name, member_count=member_count
    )


@router.put("/{user_id}/shared-role", status_code=status.HTTP_204_NO_CONTENT)
def set_shared_role(
    user_id: str,
    payload: SetSharedRoleRequest,
    _admin: SharedAdmin,
    session: DbSession,
) -> None:
    ProvisioningService(session).set_shared_role(user_id=user_id, role=payload.role)


@router.post("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: str, _admin: SharedAdmin, session: DbSession) -> None:
    """Deaktiviert den User und widerruft alle offenen Sessions."""
    ProvisioningService(session).deactivate_user(user_id=user_id)
