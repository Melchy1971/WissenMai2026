from __future__ import annotations

from typing import Annotated, Iterator

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies.auth import RequestAuthContext, get_request_auth_context
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError, AuthInvalidCredentialsApiError, AuthRequiredApiError
from app.db.session import get_session
from app.schemas.auth import AuthLoginRequest, AuthLoginResponse, AuthMembershipResponse, AuthSessionResponse, AuthUserResponse
from app.services.auth import AuthService, AuthenticationError


router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> Iterator[AuthService]:
    try:
        for session in get_session():
            yield AuthService(session)
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


@router.post("/login", response_model=AuthLoginResponse, status_code=status.HTTP_200_OK)
def login(request: AuthLoginRequest, service: Annotated[AuthService, Depends(get_auth_service)]) -> AuthLoginResponse:
    try:
        token, auth_session, user, memberships = service.login(login=request.login, password=request.password)
    except AuthenticationError as exc:
        raise AuthInvalidCredentialsApiError(message=str(exc)) from exc

    return AuthLoginResponse(
        token=token,
        expires_at=auth_session.expires_at,
        user=AuthUserResponse(id=user.id, login=user.login or "", display_name=user.display_name),
        memberships=[AuthMembershipResponse(workspace_id=item.workspace_id, role=item.role) for item in memberships],
        active_workspace_id=memberships[0].workspace_id if memberships else None,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> None:
    bearer_value = (authorization or "").strip()
    if not bearer_value.startswith("Bearer "):
        raise AuthRequiredApiError()
    bearer_token = bearer_value.removeprefix("Bearer ").strip()
    if not bearer_token:
        raise AuthRequiredApiError()
    service.revoke_session(bearer_token=bearer_token)


@router.get("/me", response_model=AuthSessionResponse)
def me(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> AuthSessionResponse:
    bearer_value = (authorization or "").strip()
    if not bearer_value.startswith("Bearer "):
        raise AuthRequiredApiError()

    bearer_token = bearer_value.removeprefix("Bearer ").strip()
    if not bearer_token:
        raise AuthRequiredApiError()

    try:
        user, memberships = service.get_session_state(bearer_token=bearer_token)
    except AuthenticationError as exc:
        raise AuthRequiredApiError(message=str(exc)) from exc

    return AuthSessionResponse(
        user=AuthUserResponse(id=str(user.id), login=user.login or "", display_name=user.display_name),
        memberships=[AuthMembershipResponse(workspace_id=item.workspace_id, role=item.role) for item in memberships],
        active_workspace_id=memberships[0].workspace_id if memberships else None,
    )