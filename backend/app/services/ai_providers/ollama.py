"""Ollama local LLM provider for analysis summary generation."""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.services.ai_providers.analysis_provider import AnalysisSummaryResult, DocumentSummaryInput
from app.services.ai_providers.errors import (
    ProviderConnectionError,
    ProviderResponseError,
    ProviderTimeoutError,
)

_log = logging.getLogger(__name__)

_ANALYSIS_PROMPT_TEMPLATE = """\
Du bist ein Analyse-Assistent. Analysiere die folgenden Dokumente und beantworte: {prompt}

Dokumente:
{documents}

Antworte ausschließlich mit einem JSON-Objekt in folgendem Format:
{{
  "summary": "<Zusammenfassung, max. 3 Absätze>",
  "key_points": ["<Punkt 1>", "<Punkt 2>"],
  "suggested_tags": ["<tag1>", "<tag2>"],
  "suggested_topics": ["<thema1>"],
  "confidence": 0.85
}}
"""


class OllamaAnalysisProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout_seconds: float = 60.0,
        max_retries: int = 1,
    ) -> None:
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self._base_url = base_url.rstrip("/")
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
        doc_block = _format_documents(documents, privacy_mode=privacy_mode)
        full_prompt = _ANALYSIS_PROMPT_TEMPLATE.format(prompt=prompt, documents=doc_block)

        payload = json.dumps({
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }).encode()

        _log.info(
            "ollama_analysis_request",
            extra={"job_id": job_id, "model": self.model_name, "doc_count": len(documents)},
        )

        raw = self._post_with_retry(f"{self._base_url}/api/generate", payload)
        return _parse_ollama_response(raw, provider=self.provider_name, model=self.model_name)

    def _post_with_retry(self, url: str, payload: bytes) -> dict:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s
            try:
                req = urllib.request.Request(
                    url, data=payload, method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    return json.loads(resp.read())
            except TimeoutError as exc:
                last_exc = exc
                _log.warning("ollama_timeout", extra={"attempt": attempt, "url": url})
            except urllib.error.URLError as exc:
                last_exc = exc
                _log.warning("ollama_connection_error", extra={"attempt": attempt})
        if isinstance(last_exc, TimeoutError):
            raise ProviderTimeoutError(
                f"Ollama timed out after {self.timeout_seconds}s",
                provider=self.provider_name, model=self.model_name,
            )
        raise ProviderConnectionError(
            f"Cannot reach Ollama at {self._base_url}",
            provider=self.provider_name, model=self.model_name,
            details={"error": str(last_exc)},
        )


def _format_documents(docs: list[DocumentSummaryInput], *, privacy_mode: bool) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        if privacy_mode:
            parts.append(f"[Dokument {i}] {doc.title} (ID: {doc.document_id})\n{doc.content}")
        else:
            _log.debug("doc_content_included", extra={"document_id": doc.document_id})
            parts.append(f"[Dokument {i}] {doc.title}\n{doc.content}")
    return "\n\n".join(parts)


def _parse_ollama_response(raw: dict, *, provider: str, model: str) -> AnalysisSummaryResult:
    text = raw.get("response", "")
    tokens_used = raw.get("eval_count")
    return _parse_json_response(text, provider=provider, model=model, tokens_used=tokens_used)


def _parse_json_response(text: str, *, provider: str, model: str, tokens_used: int | None) -> AnalysisSummaryResult:
    # Extract JSON block (LLMs sometimes wrap in markdown code fences).
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ProviderResponseError(
            "No JSON object found in provider response",
            provider=provider, model=model,
        )
    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError as exc:
        raise ProviderResponseError(
            "Provider response is not valid JSON",
            provider=provider, model=model,
            details={"json_error": str(exc)},
        ) from exc

    summary = str(data.get("summary") or "")
    if not summary.strip():
        raise ProviderResponseError("Provider returned empty summary", provider=provider, model=model)

    return AnalysisSummaryResult(
        summary=summary,
        key_points=list(data.get("key_points") or []),
        suggested_tags=list(data.get("suggested_tags") or []),
        suggested_topics=list(data.get("suggested_topics") or []),
        confidence=_to_float(data.get("confidence")),
        provider=provider,
        model=model,
        tokens_used=tokens_used,
    )


def _to_float(value: object) -> float | None:
    try:
        v = float(value)  # type: ignore[arg-type]
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return None


# Export helpers for reuse by other providers.
parse_json_response = _parse_json_response
format_documents = _format_documents
