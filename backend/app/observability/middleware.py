from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.logging import reset_observability_context, set_observability_context
from app.observability.prometheus_metrics import (
    HTTP_ERROR_COUNT,
    HTTP_REQUEST_COUNT,
    HTTP_REQUEST_DURATION,
)


_UNMATCHED_ROUTE = "unmatched"


def _route_template(request: Request) -> str:
    """Return a bounded route label without IDs or query parameters."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path.startswith("/") else _UNMATCHED_ROUTE


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            labels = {
                "method": request.method,
                "path": _route_template(request),
            }
            HTTP_REQUEST_COUNT.labels(**labels, status=str(status_code)).inc()
            HTTP_REQUEST_DURATION.labels(**labels).observe(perf_counter() - started_at)
            if status_code >= 400:
                HTTP_ERROR_COUNT.labels(**labels, status=str(status_code)).inc()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
        request.state.correlation_id = correlation_id
        request.state.request_started_at = perf_counter()
        token = set_observability_context(correlation_id=correlation_id)
        try:
            response = await call_next(request)
        finally:
            reset_observability_context(token)

        response.headers["x-correlation-id"] = correlation_id
        return response
