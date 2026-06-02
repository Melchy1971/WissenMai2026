from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import (
    ApiError,
    ChatMessageInvalidApiError,
    InvalidPaginationApiError,
    InvalidQueryApiError,
    RequestValidationApiError,
    WorkspaceRequiredApiError,
)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_content(exc.code, exc.message, exc.details))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content("HTTP_ERROR", str(exc.detail), {}),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    mapped = map_validation_error(exc)
    return JSONResponse(status_code=mapped.status_code, content=error_content(mapped.code, mapped.message, mapped.details))


def map_validation_error(exc: RequestValidationError) -> ApiError:
    errors = exc.errors()
    for error in errors:
        location = tuple(error.get("loc", ()))
        if location in {("query", "workspace_id"), ("body", "workspace_id"), ("header", "x-workspace-id")}:
            return WorkspaceRequiredApiError(details={"errors": errors})
        if location in {
            ("body", "content"),
            ("body", "question"),
            ("body", "role"),
            ("body", "basis_type"),
            ("body", "retrieval_limit"),
        }:
            return ChatMessageInvalidApiError(details={"errors": errors})
        if location == ("query", "q"):
            return InvalidQueryApiError(details={"errors": errors})
    for error in errors:
        location = tuple(error.get("loc", ()))
        if location in {("query", "limit"), ("query", "offset")}:
            return InvalidPaginationApiError(details={"errors": errors})
    return RequestValidationApiError(details={"errors": errors})


def error_content(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}
