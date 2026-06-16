"""Google Gemini provider for analysis summary generation."""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

from app.services.ai_providers.analysis_provider import AnalysisSummaryResult, DocumentSummaryInput
from app.services.ai_providers.errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.services.ai_providers.ollama import format_documents, parse_json_response

_log = logging.getLogger(__name__)

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_SYSTEM_INSTRUCTION = (
    "Du bist ein Analyse-Assistent. Antworte ausschließlich mit einem JSON-Objekt mit den Feldern: "
    "summary, key_points (Liste), suggested_tags (Liste), suggested_topics (Liste), confidence (0..1)."
)


class GeminiAnalysisProvider:
    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-1.5-flash",
        timeout_seconds: float = 60.0,
        max_retries: int = 1,
    ) -> None:
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self._api_key = api_key  # never logged
        self._max_retries = max_retries

    def generate_analysis_summary(
        self,
        *,
        job_id: str,
        documents: list[DocumentSummaryInput],
        prompt: str,
        max_tokens: int = 4096,
        privacy_mode: bool = True,
    ) -> AnalysisSummaryResult:
        doc_block = format_documents(documents, privacy_mode=privacy_mode)
        user_text = f"{prompt}\n\nDokumente:\n{doc_block}"

        payload = json.dumps({
            "system_instruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": max_tokens,
            },
        }).encode()

        url = f"{_GEMINI_API_BASE}/{self.model_name}:generateContent?key={self._api_key}"
        # NOTE: api_key in URL — do not log the url string anywhere

        _log.info(
            "gemini_analysis_request",
            extra={"job_id": job_id, "model": self.model_name, "doc_count": len(documents)},
        )

        raw = self._post_with_retry(url, payload)
        return _parse_gemini_response(raw, provider=self.provider_name, model=self.model_name)

    def _post_with_retry(self, url: str, payload: bytes) -> dict:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(2 ** attempt)
            try:
                req = urllib.request.Request(
                    url, data=payload, method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    return json.loads(resp.read())
            except TimeoutError as exc:
                last_exc = exc
                _log.warning("gemini_timeout", extra={"attempt": attempt})
            except urllib.error.HTTPError as exc:
                _handle_http_error(exc, provider=self.provider_name, model=self.model_name)
            except urllib.error.URLError as exc:
                last_exc = exc
                _log.warning("gemini_connection_error", extra={"attempt": attempt})

        if isinstance(last_exc, TimeoutError):
            raise ProviderTimeoutError(
                f"Gemini timed out after {self.timeout_seconds}s",
                provider=self.provider_name, model=self.model_name,
            )
        raise ProviderConnectionError(
            "Cannot reach Gemini API",
            provider=self.provider_name, model=self.model_name,
            details={"error": str(last_exc)},
        )


def _handle_http_error(exc: urllib.error.HTTPError, *, provider: str, model: str) -> None:
    if exc.code in (400, 401, 403):
        raise ProviderAuthError(
            f"Gemini rejected credentials or request (HTTP {exc.code})",
            provider=provider, model=model,
        ) from exc
    if exc.code == 429:
        raise ProviderRateLimitError(
            "Gemini rate limit exceeded (HTTP 429)",
            provider=provider, model=model,
        ) from exc
    raise ProviderResponseError(
        f"Gemini returned HTTP {exc.code}",
        provider=provider, model=model,
        details={"http_status": exc.code},
    ) from exc


def _parse_gemini_response(raw: dict, *, provider: str, model: str) -> AnalysisSummaryResult:
    try:
        candidate = raw["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
        # Gemini doesn't return aggregate token counts in the same place —
        # usageMetadata.totalTokenCount is available in some response versions
        meta = raw.get("usageMetadata", {})
        tokens_used: int | None = meta.get("totalTokenCount")
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderResponseError(
            "Unexpected Gemini response structure",
            provider=provider, model=model,
        ) from exc
    return parse_json_response(text, provider=provider, model=model, tokens_used=tokens_used)
