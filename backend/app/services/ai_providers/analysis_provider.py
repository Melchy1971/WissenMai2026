"""Protocol and data types for KI-backed analysis summary generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class DocumentSummaryInput:
    """Truncated document representation passed to the provider.

    content is already capped to max_tokens_per_document characters.
    Never logged when privacy_mode is enabled.
    """
    document_id: str
    title: str
    content: str


@dataclass(frozen=True)
class AnalysisSummaryResult:
    """Normalized response from any KI provider."""
    summary: str
    key_points: list[str]
    suggested_tags: list[str]
    suggested_topics: list[str]
    confidence: float | None
    provider: str
    model: str
    tokens_used: int | None


class AnalysisKiProvider(Protocol):
    """Interface that every KI provider backend must satisfy."""

    provider_name: str
    model_name: str
    timeout_seconds: float

    def generate_analysis_summary(
        self,
        *,
        job_id: str,
        documents: list[DocumentSummaryInput],
        prompt: str,
        max_tokens: int = 4096,
        privacy_mode: bool = True,
    ) -> AnalysisSummaryResult:
        """Generate a structured analysis summary.

        Raises:
            ProviderTimeoutError: Request exceeded timeout_seconds.
            ProviderConnectionError: Network error reaching the endpoint.
            ProviderAuthError: Credentials rejected (401/403).
            ProviderRateLimitError: Rate limit hit (429).
            ProviderResponseError: Unparseable response.
        """
        ...
