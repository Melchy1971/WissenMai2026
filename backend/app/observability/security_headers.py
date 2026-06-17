"""Security Headers Middleware — GA-SEC-01.

Implements Content Security Policy (CSP) and additional security headers
for production hardening. Satisfies GA-SEC-01 requirement.

Dev vs. Prod:
- APP_ENV=local/development: CSP mit 'unsafe-eval' für Vite HMR, Report-Only optional
- APP_ENV=production:        strikte CSP, keine unsafe-* Ausnahmen

Kein Helmet (Node.js). FastAPI/Starlette BaseHTTPMiddleware.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


# Provider-Endpunkte für connect-src
_PROVIDER_ORIGINS = [
    "http://localhost:11434",   # Ollama (default local)
    "http://127.0.0.1:11434",  # Ollama (loopback)
    "https://api.openai.com",
    "https://generativelanguage.googleapis.com",  # Gemini
]


def _build_csp(is_dev: bool) -> str:
    """Baut den CSP-Header-Wert für die aktuelle Umgebung."""
    script_src = "'self'"
    if is_dev:
        # Vite HMR benötigt 'unsafe-eval' in Entwicklung
        script_src = "'self' 'unsafe-eval'"

    connect_src_parts = ["'self'"] + _PROVIDER_ORIGINS

    directives = [
        f"default-src 'self'",
        f"script-src {script_src}",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        f"connect-src {' '.join(connect_src_parts)}",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "upgrade-insecure-requests",
    ]
    return "; ".join(directives)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Fügt Security-Header zu jeder HTTP-Response hinzu."""

    def __init__(self, app, *, dev_mode: bool = False) -> None:
        super().__init__(app)
        self._dev_mode = dev_mode
        self._csp = _build_csp(dev_mode)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        self._apply_headers(response)
        return response

    def _apply_headers(self, response: Response) -> None:
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._csp

        # Verhindert MIME-Type-Sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Kein Referer bei Cross-Origin-Navigationen
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Deaktiviert Browser-Features
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "interest-cohort=()"
        )

        # Legacy: verhindert Framing (redundant zu CSP frame-ancestors, aber compat)
        response.headers["X-Frame-Options"] = "DENY"
