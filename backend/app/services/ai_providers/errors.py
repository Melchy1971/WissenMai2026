"""Normalized error hierarchy for all KI provider backends."""
from __future__ import annotations


class ProviderError(Exception):
    """Base class for all provider errors."""

    def __init__(self, message: str, *, provider: str, model: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        # details must never contain secrets or raw document content
        self.details: dict = details or {}


class ProviderTimeoutError(ProviderError):
    """HTTP request to the provider timed out."""


class ProviderConnectionError(ProviderError):
    """Could not reach the provider endpoint."""


class ProviderAuthError(ProviderError):
    """Authentication rejected by the provider (HTTP 401/403)."""


class ProviderRateLimitError(ProviderError):
    """Provider rate limit exceeded (HTTP 429)."""


class ProviderTokenLimitError(ProviderError):
    """Input or output exceeds the provider's token limit."""


class ProviderResponseError(ProviderError):
    """Provider returned an unexpected or unparseable response."""
