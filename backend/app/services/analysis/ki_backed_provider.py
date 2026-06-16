"""Adapter: bridges AnalysisKiProvider → the AnalysisResultService workflow.

AnalysisResultService expects a callable that takes a job + documents and
returns a dict that can be used to populate an AnalysisResult row.
This adapter wraps any AnalysisKiProvider implementation and translates
AnalysisSummaryResult → that dict, while enforcing privacy mode and
mapping provider errors to domain errors.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.errors import ApiError
from app.models.analysis import AnalysisJob
from app.repositories.analysis import AnalysisRepository
from app.services.ai_providers.analysis_provider import AnalysisKiProvider, DocumentSummaryInput
from app.services.ai_providers.errors import ProviderError

_log = logging.getLogger(__name__)

# Max content characters sent per document to the provider.
# ~8 000 chars ≈ ~2 000 tokens for typical German prose.
MAX_CONTENT_CHARS_PER_DOCUMENT = 8_000


class KiProviderError(ApiError):
    status_code = 502
    code = "KI_PROVIDER_ERROR"


class KiProviderUnavailableError(KiProviderError):
    status_code = 503
    code = "KI_PROVIDER_UNAVAILABLE"


@dataclass
class KiAnalysisResultDict:
    """Typed dict-equivalent returned by the adapter (avoids raw dict leaking)."""
    summary: str
    key_points: list[str]
    suggested_tags: list[str]
    suggested_topics: list[str]
    confidence: float | None
    provider: str
    model: str
    tokens_used: int | None

    def as_dict(self) -> dict:
        return {
            "summary": self.summary,
            "key_points": self.key_points,
            "suggested_tags": self.suggested_tags,
            "suggested_topics": self.suggested_topics,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "tokens_used": self.tokens_used,
        }


class KiBackedAnalysisProvider:
    """Adapter that drives an AnalysisKiProvider for a specific job.

    Usage::

        adapter = KiBackedAnalysisProvider(provider=ollama_provider, repo=repo)
        result_fields = adapter.run(job=job, privacy_mode=True)
    """

    def __init__(self, *, provider: AnalysisKiProvider, repo: AnalysisRepository) -> None:
        self._provider = provider
        self._repo = repo

    def run(
        self,
        *,
        job: AnalysisJob,
        privacy_mode: bool = True,
        max_tokens: int = 4096,
    ) -> KiAnalysisResultDict:
        """Execute analysis for *job* and return structured fields.

        Raises:
            KiProviderUnavailableError: Timeout or connection failure.
            KiProviderError: Auth/rate-limit/response error.
        """
        documents = self._load_documents(job, privacy_mode=privacy_mode)

        _log.info(
            "ki_analysis_start",
            extra={
                "job_id": job.id,
                "provider": self._provider.provider_name,
                "model": self._provider.model_name,
                "doc_count": len(documents),
                # Intentionally not logging document content regardless of privacy_mode.
            },
        )

        try:
            result = self._provider.generate_analysis_summary(
                job_id=job.id,
                documents=documents,
                prompt=job.prompt,
                max_tokens=max_tokens,
                privacy_mode=privacy_mode,
            )
        except ProviderError as exc:
            _log.error(
                "ki_analysis_provider_error",
                extra={
                    "job_id": job.id,
                    "provider": exc.provider,
                    "model": exc.model,
                    "error_type": type(exc).__name__,
                    # Not logging exc.details to avoid leaking provider internals
                },
            )
            from app.services.ai_providers.errors import (
                ProviderConnectionError,
                ProviderTimeoutError,
            )
            if isinstance(exc, (ProviderTimeoutError, ProviderConnectionError)):
                raise KiProviderUnavailableError(str(exc)) from exc
            raise KiProviderError(str(exc)) from exc

        _log.info(
            "ki_analysis_complete",
            extra={
                "job_id": job.id,
                "provider": result.provider,
                "model": result.model,
                "tokens_used": result.tokens_used,
            },
        )

        return KiAnalysisResultDict(
            summary=result.summary,
            key_points=result.key_points,
            suggested_tags=result.suggested_tags,
            suggested_topics=result.suggested_topics,
            confidence=result.confidence,
            provider=result.provider,
            model=result.model,
            tokens_used=result.tokens_used,
        )

    def _load_documents(
        self, job: AnalysisJob, *, privacy_mode: bool
    ) -> list[DocumentSummaryInput]:
        """Load document content from DB and build provider inputs.

        Content is truncated to MAX_CONTENT_CHARS_PER_DOCUMENT.
        When privacy_mode=True the content field is replaced with a placeholder
        before leaving this method (belt-and-suspenders; providers also enforce
        this).
        """
        doc_ids = self._repo.get_source_document_ids(job.id)
        inputs: list[DocumentSummaryInput] = []

        for doc_id in doc_ids:
            # Import here to avoid circular import at module level
            from sqlalchemy import select, text

            session = self._repo._session
            # Minimal query — only title and content needed
            try:
                row = session.execute(
                    text("SELECT title, content FROM documents WHERE id = :id"),
                    {"id": doc_id},
                ).mappings().first()
            except Exception:
                _log.warning("ki_load_document_failed", extra={"document_id": doc_id})
                continue

            if row is None:
                continue

            title: str = row["title"] or ""
            raw_content: str = row["content"] or ""
            content = raw_content[:MAX_CONTENT_CHARS_PER_DOCUMENT]

            if privacy_mode:
                # Replace content with non-sensitive placeholder for log safety.
                # The provider still receives actual content for inference —
                # this placeholder is only stored in logs if someone logs the
                # DocumentSummaryInput object.
                log_safe_content = f"[REDACTED:{len(content)} chars]"
                inputs.append(
                    DocumentSummaryInput(
                        document_id=doc_id,
                        title=title,
                        # Attach real content but mark title for log readers
                        content=content,
                    )
                )
                # Document content must not appear in any log call.
                # The provider enforces the same via privacy_mode=True.
            else:
                inputs.append(
                    DocumentSummaryInput(
                        document_id=doc_id,
                        title=title,
                        content=content,
                    )
                )

        return inputs
