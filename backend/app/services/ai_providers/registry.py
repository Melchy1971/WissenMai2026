"""Provider registry — factory for AnalysisKiProvider implementations.

Usage::

    from app.services.ai_providers.registry import build_provider, list_provider_names

    provider = build_provider("ollama", model="llama3")
    provider = build_provider("openai", model="gpt-4o", api_key="sk-...")
    provider = build_provider("gemini", model="gemini-1.5-flash", api_key="AIza...")
"""
from __future__ import annotations

import os
from typing import Any

from app.services.ai_providers.analysis_provider import AnalysisKiProvider
from app.services.ai_providers.gemini import GeminiAnalysisProvider
from app.services.ai_providers.ollama import OllamaAnalysisProvider
from app.services.ai_providers.openai_provider import OpenAiAnalysisProvider

# Registry: provider_name → (class, required_kwargs)
_REGISTRY: dict[str, type] = {
    "ollama": OllamaAnalysisProvider,
    "openai": OpenAiAnalysisProvider,
    "gemini": GeminiAnalysisProvider,
}

# Environment variable names for API keys, keyed by provider name.
# The registry reads these when the caller does not supply api_key explicitly.
_ENV_KEY_NAMES: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def list_provider_names() -> list[str]:
    """Return the names of all registered providers."""
    return list(_REGISTRY.keys())


def build_provider(
    provider_name: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 60.0,
    max_retries: int = 1,
    **kwargs: Any,
) -> AnalysisKiProvider:
    """Instantiate a named provider.

    For providers that require an API key, supply it via *api_key* or set the
    corresponding environment variable (see ``_ENV_KEY_NAMES``).  The key is
    never logged.

    Raises:
        ValueError: unknown provider name or missing required credential.
    """
    if provider_name not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown provider {provider_name!r}. Known providers: {known}")

    cls = _REGISTRY[provider_name]
    init_kwargs: dict[str, Any] = {
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        **kwargs,
    }

    if model is not None:
        init_kwargs["model"] = model

    if provider_name == "ollama":
        if base_url is not None:
            init_kwargs["base_url"] = base_url
    else:
        # API-key–based providers
        key = api_key or os.environ.get(_ENV_KEY_NAMES.get(provider_name, ""), "")
        if not key:
            env_var = _ENV_KEY_NAMES.get(provider_name, "<unknown env var>")
            raise ValueError(
                f"Provider {provider_name!r} requires an API key. "
                f"Pass api_key= or set the {env_var} environment variable."
            )
        init_kwargs["api_key"] = key  # passed to constructor, never logged here

    return cls(**init_kwargs)  # type: ignore[return-value]
