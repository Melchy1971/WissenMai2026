"""TopicMergeService — AI-gestützte Themenzusammenführung.

Provider-Hierarchie:
  1. Ollama  (primär, lokal)
  2. OpenAI  (stub — nicht implementiert in 1.0)
  3. Gemini  (stub — nicht implementiert in 1.0)

Sicherheitsregeln:
  - Keine Dokumentinhalte werden geloggt (PROHIBIT: keine Dokumentinhalte loggen)
  - Keine Credentials/Tokens werden geloggt
  - Audit-Logging: nur topic_id, document_ids, provider, Ergebnis-Metadaten
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import TopicMergeProviderError
from app.models.documents import Chunk, Document
from app.schemas.topics import TopicMergeRequest, TopicMergeResponse


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

_OLLAMA_BASE_URL = "http://localhost:11434"
_OLLAMA_MODEL = "mistral"
_OLLAMA_TIMEOUT_SECONDS = 60
_OLLAMA_MAX_RETRIES = 3
_OLLAMA_RETRY_DELAY_SECONDS = 2

_MAX_CHARS_PER_DOCUMENT = 4000  # approx. token limit guard
_MAX_TOTAL_CHARS = 12000


# ---------------------------------------------------------------------------
# Progress callback type
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[str, int, int], None]
"""Called as callback(step_name, current, total)."""


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MergeResult:
    title: str
    summary: str
    sources: list[str]


class TopicMergeProvider(Protocol):
    def generate_topic_summary(
        self,
        *,
        document_excerpts: list[tuple[str, str]],  # (document_id, text_excerpt)
        progress: ProgressCallback | None = None,
    ) -> MergeResult: ...


# ---------------------------------------------------------------------------
# Ollama provider (primary)
# ---------------------------------------------------------------------------

class OllamaTopicProvider:
    """Calls local Ollama instance to generate a merged topic title + summary."""

    def __init__(
        self,
        base_url: str = _OLLAMA_BASE_URL,
        model: str = _OLLAMA_MODEL,
        timeout: float = _OLLAMA_TIMEOUT_SECONDS,
        max_retries: int = _OLLAMA_MAX_RETRIES,
        retry_delay: float = _OLLAMA_RETRY_DELAY_SECONDS,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def _build_prompt(self, document_excerpts: list[tuple[str, str]]) -> str:
        doc_blocks = "\n\n".join(
            f"[Dokument {i + 1}]\n{excerpt}"
            for i, (_, excerpt) in enumerate(document_excerpts)
        )
        return (
            "Du bist ein Assistent zur Wissensorganisation. "
            "Analysiere die folgenden Dokumentauszüge und erstelle:\n"
            "1. Einen kurzen, präzisen Titel (max. 100 Zeichen)\n"
            "2. Eine sachliche Zusammenfassung (3–5 Sätze)\n\n"
            "Format:\nTITEL: <titel>\nZUSAMMENFASSUNG: <zusammenfassung>\n\n"
            f"Dokumente:\n{doc_blocks}"
        )

    def _parse_response(self, response_text: str, sources: list[str]) -> MergeResult:
        lines = response_text.strip().splitlines()
        title = ""
        summary_lines: list[str] = []
        in_summary = False
        for line in lines:
            if line.startswith("TITEL:"):
                title = line[len("TITEL:"):].strip()
            elif line.startswith("ZUSAMMENFASSUNG:"):
                summary_lines.append(line[len("ZUSAMMENFASSUNG:"):].strip())
                in_summary = True
            elif in_summary and line.strip():
                summary_lines.append(line.strip())

        if not title:
            title = "Zusammengeführtes Thema"
        if not summary_lines:
            summary_lines = ["Keine Zusammenfassung verfügbar."]

        return MergeResult(
            title=title,
            summary=" ".join(summary_lines),
            sources=sources,
        )

    def generate_topic_summary(
        self,
        *,
        document_excerpts: list[tuple[str, str]],
        progress: ProgressCallback | None = None,
    ) -> MergeResult:
        if progress:
            progress("building_prompt", 1, 4)

        prompt = self._build_prompt(document_excerpts)
        sources = [doc_id for doc_id, _ in document_excerpts]

        if progress:
            progress("calling_provider", 2, 4)

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        f"{self._base_url}/api/generate",
                        json={"model": self._model, "prompt": prompt, "stream": False},
                    )
                response.raise_for_status()
                data = response.json()
                raw_text: str = data.get("response", "")

                if progress:
                    progress("parsing_response", 3, 4)

                result = self._parse_response(raw_text, sources)

                if progress:
                    progress("done", 4, 4)

                return result

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "OllamaTopicProvider: timeout on attempt %d/%d",
                    attempt, self._max_retries,
                )
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.warning(
                    "OllamaTopicProvider: HTTP %d on attempt %d/%d",
                    exc.response.status_code, attempt, self._max_retries,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "OllamaTopicProvider: unexpected error on attempt %d/%d: %s",
                    attempt, self._max_retries, type(exc).__name__,
                )

            if attempt < self._max_retries:
                time.sleep(self._retry_delay)

        raise TopicMergeProviderError(
            message=f"Ollama provider failed after {self._max_retries} attempts",
            details={"provider": "ollama", "error": str(last_exc)},
        )


# ---------------------------------------------------------------------------
# Stub providers (not implemented in 1.0)
# ---------------------------------------------------------------------------

class OpenAITopicProvider:
    """Stub — OpenAI integration not implemented in 1.0 (scope: KL-DEF-002)."""

    def generate_topic_summary(
        self,
        *,
        document_excerpts: list[tuple[str, str]],
        progress: ProgressCallback | None = None,
    ) -> MergeResult:
        raise TopicMergeProviderError(
            message="OpenAI provider is not implemented in this version",
            details={"provider": "openai", "scope": "KL-DEF-002"},
        )


class GeminiTopicProvider:
    """Stub — Gemini integration not implemented in 1.0 (scope: KL-DEF-002)."""

    def generate_topic_summary(
        self,
        *,
        document_excerpts: list[tuple[str, str]],
        progress: ProgressCallback | None = None,
    ) -> MergeResult:
        raise TopicMergeProviderError(
            message="Gemini provider is not implemented in this version",
            details={"provider": "gemini", "scope": "KL-DEF-002"},
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TopicMergeService:
    """Orchestrates AI-based topic summary generation from multiple documents."""

    def __init__(
        self,
        session: Session,
        *,
        ollama_provider: OllamaTopicProvider | None = None,
        openai_provider: OpenAITopicProvider | None = None,
        gemini_provider: GeminiTopicProvider | None = None,
    ) -> None:
        self._session = session
        self._providers: dict[str, TopicMergeProvider] = {
            "ollama": ollama_provider or OllamaTopicProvider(),
            "openai": openai_provider or OpenAITopicProvider(),
            "gemini": gemini_provider or GeminiTopicProvider(),
        }

    def _fetch_document_excerpts(
        self,
        document_ids: list[str],
        workspace_id: str,
    ) -> list[tuple[str, str]]:
        """Load chunk text from DB, truncate to token limit guard.

        SECURITY: text content is not logged anywhere in this method.
        """
        excerpts: list[tuple[str, str]] = []
        remaining_chars = _MAX_TOTAL_CHARS

        for doc_id in document_ids:
            # Verify document belongs to workspace
            doc = self._session.execute(
                select(Document.id, Document.current_version_id).where(
                    Document.id == doc_id,
                    Document.workspace_id == workspace_id,
                    Document.lifecycle_status != "deleted",
                )
            ).one_or_none()

            if doc is None:
                logger.warning(
                    "TopicMergeService: document %s not found in workspace — skipped",
                    doc_id,
                )
                continue

            if doc.current_version_id is None:
                logger.warning(
                    "TopicMergeService: document %s has no version — skipped",
                    doc_id,
                )
                continue

            rows = self._session.execute(
                select(Chunk.content)
                .where(
                    Chunk.document_id == doc_id,
                    Chunk.document_version_id == doc.current_version_id,
                )
                .order_by(Chunk.chunk_index.asc())
                .limit(20)
            ).scalars().all()

            doc_text = " ".join(rows)
            # Truncate per document
            if len(doc_text) > _MAX_CHARS_PER_DOCUMENT:
                doc_text = doc_text[:_MAX_CHARS_PER_DOCUMENT]
            # Truncate total
            if len(doc_text) > remaining_chars:
                doc_text = doc_text[:remaining_chars]
            if not doc_text.strip():
                continue

            excerpts.append((doc_id, doc_text))
            remaining_chars -= len(doc_text)
            if remaining_chars <= 0:
                break

        return excerpts

    def merge(
        self,
        *,
        workspace_id: str,
        request: TopicMergeRequest,
        progress: ProgressCallback | None = None,
    ) -> TopicMergeResponse:
        provider_key = request.provider
        provider = self._providers.get(provider_key)
        if provider is None:
            raise TopicMergeProviderError(
                message=f"Unknown provider: {provider_key}",
                details={"provider": provider_key},
            )

        # Audit log — no document content, no tokens
        logger.info(
            "TopicMergeService.merge: provider=%s document_count=%d",
            provider_key,
            len(request.document_ids),
        )

        if progress:
            progress("fetching_documents", 0, 4)

        excerpts = self._fetch_document_excerpts(request.document_ids, workspace_id)

        if not excerpts:
            raise TopicMergeProviderError(
                message="No processable document content found",
                details={"document_ids": request.document_ids},
            )

        result = provider.generate_topic_summary(
            document_excerpts=excerpts,
            progress=progress,
        )

        # Audit log — result metadata only, not full text
        logger.info(
            "TopicMergeService.merge: completed provider=%s sources=%d title_length=%d",
            provider_key,
            len(result.sources),
            len(result.title),
        )

        return TopicMergeResponse(
            title=result.title,
            summary=result.summary,
            sources=result.sources,
        )
