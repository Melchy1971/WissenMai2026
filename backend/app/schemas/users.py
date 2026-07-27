"""Schemas fuer die Benutzerverwaltung (Multi-User V1, Story 5)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SharedRole = Literal["admin", "member"]


class CreateUserRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    login: str = Field(min_length=1, max_length=255)
    initial_password: str = Field(min_length=1, max_length=1024)


class CreateUserResponse(BaseModel):
    user_id: str
    login: str
    private_workspace_id: str
    shared_workspace_id: str


class UserResponse(BaseModel):
    id: str
    login: str | None
    display_name: str
    is_active: bool
    created_at: datetime
    shared_role: SharedRole | None
    private_workspace_id: str | None


class SetSharedRoleRequest(BaseModel):
    role: SharedRole


class SharedWorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    member_count: int
