from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthLoginRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=500)


class AuthMembershipResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str
    role: str


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    login: str
    display_name: str


class AuthLoginResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    token: str
    expires_at: datetime
    user: AuthUserResponse
    memberships: list[AuthMembershipResponse]
    active_workspace_id: str | None


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    user: AuthUserResponse
    memberships: list[AuthMembershipResponse]
    active_workspace_id: str | None