"""Repositories for multi-user provisioning (Story 3).

Pure data access for users, workspaces and memberships. No business rules here;
those live in ``app.services.provisioning.ProvisioningService``.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.documents import User, Workspace, WorkspaceMembership


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: str) -> User | None:
        return self._session.scalar(select(User).where(User.id == str(user_id)))

    def get_by_login(self, login: str) -> User | None:
        return self._session.scalar(select(User).where(User.login == login))

    def add(self, user: User) -> None:
        self._session.add(user)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        return list(
            self._session.scalars(
                select(User).order_by(User.created_at.asc(), User.id.asc()).limit(limit).offset(offset)
            )
        )


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- workspaces ---------------------------------------------------------

    def get_shared(self) -> Workspace | None:
        return self._session.scalar(select(Workspace).where(Workspace.kind == "shared"))

    def get_private_for_user(self, user_id: str) -> Workspace | None:
        return self._session.scalar(
            select(Workspace).where(Workspace.kind == "private", Workspace.owner_user_id == str(user_id))
        )

    def add(self, workspace: Workspace) -> None:
        self._session.add(workspace)

    # -- memberships --------------------------------------------------------

    def get_membership(self, *, workspace_id: str, user_id: str) -> WorkspaceMembership | None:
        return self._session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == str(workspace_id),
                WorkspaceMembership.user_id == str(user_id),
            )
        )

    def add_membership(self, membership: WorkspaceMembership) -> None:
        self._session.add(membership)

    def count_active_admins(self, *, workspace_id: str) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(WorkspaceMembership)
                .join(User, User.id == WorkspaceMembership.user_id)
                .where(
                    WorkspaceMembership.workspace_id == str(workspace_id),
                    WorkspaceMembership.role == "admin",
                    User.is_active.is_(True),
                )
            )
            or 0
        )
