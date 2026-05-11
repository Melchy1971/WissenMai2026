from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.error_handlers import error_content
from app.db.session import get_engine
from app.core.errors import AuthRequiredApiError, ForbiddenApiError, UnauthorizedApiError, WorkspaceAccessForbiddenApiError, WorkspaceRequiredApiError
from app.services.auth import AuthService, AuthenticationError, WorkspaceAccessError


EXEMPT_PATHS = {
    "/health",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/me",
    "/api/v1/auth/logout",
}

DIAGNOSTICS_PATHS = {
    "/api/v1/admin/diagnostics",
}


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        authorization = request.headers.get("authorization") or ""
        workspace_id = request.headers.get("x-workspace-id") or ""
        auth_required_error = UnauthorizedApiError() if request.url.path in DIAGNOSTICS_PATHS else AuthRequiredApiError()

        if not authorization.startswith("Bearer "):
            return self._error_response(auth_required_error)
        if not workspace_id.strip():
            return self._error_response(WorkspaceRequiredApiError(details={"header": "x-workspace-id"}))

        bearer_token = authorization.removeprefix("Bearer ").strip()
        if not bearer_token:
            return self._error_response(auth_required_error)

        with Session(get_engine()) as session:
            service = AuthService(session)
            try:
                request.state.auth_context = service.authenticate(
                    bearer_token=bearer_token,
                    workspace_id=workspace_id,
                )
            except AuthenticationError:
                return self._error_response(auth_required_error)
            except WorkspaceAccessError:
                if request.url.path in DIAGNOSTICS_PATHS:
                    return self._error_response(ForbiddenApiError())
                return self._error_response(WorkspaceAccessForbiddenApiError())

        return await call_next(request)

    def _error_response(self, error) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=error_content(error.code, error.message, error.details),
        )
