from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisJob
from app.models.documents import Chunk, Document, DocumentVersion


class AnalysisProvider(Protocol):
    def build_result(
        self,
        *,
        job: AnalysisJob,
        documents: list[Document],
        comparison: dict | None,
        prompt: str,
        max_suggestions: int,
        created_at: datetime,
    ) -> dict:
        ...


class AnalysisComparisonProvider(Protocol):
    def compare(
        self,
        *,
        job: AnalysisJob,
        compared_document_ids: list[str],
        created_at: datetime,
        max_differences: int,
    ) -> dict:
        ...


@dataclass(frozen=True)
class AnalysisDocumentInput:
    document_id: str
    title: str
    source_type: str
    import_status: str
    chunk_count: int
    first_chunk_id: str | None
    first_heading: str
    first_text: str | None
    content: str

    @property
    def documented_input(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source_type": self.source_type,
            "import_status": self.import_status,
            "chunk_count": self.chunk_count,
            "first_chunk_id": self.first_chunk_id,
        }


class DeterministicAnalysisStubEngine:
    """Deterministic local engine used until a real provider is configured."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def compare(
        self,
        *,
        job: AnalysisJob,
        compared_document_ids: list[str],
        created_at: datetime,
        max_differences: int,
    ) -> dict:
        base = self._document_input(job.source_document_ids[0])
        compared_inputs = [self._document_input(document_id) for document_id in compared_document_ids]
        comparison_text = "\n".join(item.content for item in compared_inputs)
        similarity = _jaccard_similarity(base.content, comparison_text)
        differences: list[dict] = []
        overlaps: list[dict] = []

        for compared in compared_inputs:
            overlap_terms = sorted(_token_set(base.content) & _token_set(compared.content))
            overlaps.append(
                {
                    "document_id": compared.document_id,
                    "document_title": compared.title,
                    "terms": overlap_terms[:20],
                    "term_count": len(overlap_terms),
                }
            )

            if base.content != compared.content and len(differences) < max_differences:
                differences.append(
                    {
                        "document_id": compared.document_id,
                        "document_title": compared.title,
                        "section": base.first_heading or compared.first_heading or "Document",
                        "base_text": _preview(base.first_text or base.content),
                        "compared_text": _preview(compared.first_text or compared.content),
                        "significance": "high" if similarity < 0.5 else "medium",
                        "chunk_id": base.first_chunk_id,
                    }
                )

        return {
            "job_id": job.id,
            "compared_document_ids": compared_document_ids,
            "overlaps": overlaps,
            "differences": differences,
            "suggested_merge": {
                "strategy": "manual_review",
                "reason": "Deterministic stub output requires explicit approval before changes are applied.",
            },
            "input_documents": [base.documented_input, *[item.documented_input for item in compared_inputs]],
            "created_at": created_at,
        }

    def build_result(
        self,
        *,
        job: AnalysisJob,
        documents: list[Document],
        comparison: dict | None,
        prompt: str,
        max_suggestions: int,
        created_at: datetime,
    ) -> dict:
        inputs = [self._document_input(document.id, fallback=document) for document in documents]
        key_points = [
            f"Input documents processed: {len(inputs)}.",
            "Engine: deterministic local stub; no external API calls.",
            "No suggestion is applied without explicit approval.",
        ]
        key_points.extend(
            f"Input document {item.document_id}: {item.title} ({item.chunk_count} chunks)."
            for item in inputs
        )
        if prompt:
            key_points.append(f"Prompt recorded: {_preview(prompt, 160)}")

        suggestions = self._suggestions(job=job, comparison=comparison, max_suggestions=max_suggestions)
        suggested_topics = _stable_unique([job.analysis_type, *[_slug(item.title) for item in inputs]])
        return {
            "job_id": job.id,
            "summary": (
                f"Deterministic analysis stub processed {len(inputs)} provided document(s) "
                f"for analysis type '{job.analysis_type}'."
            ),
            "key_points": key_points,
            "suggested_tags": _stable_unique(["analysis", job.analysis_type, *(item.source_type for item in inputs)]),
            "suggested_topics": suggested_topics,
            "confidence": 0.8 if comparison else 0.7,
            "suggestions": suggestions,
            "input_documents": [item.documented_input for item in inputs],
            "created_at": created_at,
        }

    def _suggestions(self, *, job: AnalysisJob, comparison: dict | None, max_suggestions: int) -> list[dict]:
        differences = (comparison or {}).get("differences") or []
        if not differences:
            return [
                {
                    "job_id": job.id,
                    "suggestion_type": "review",
                    "payload": {
                        "title": "Review deterministic analysis result",
                        "rationale": "No deterministic document difference was detected.",
                        "priority": "low",
                    },
                }
            ][:max_suggestions]

        return [
            {
                "job_id": job.id,
                "suggestion_type": "merge_review",
                "payload": {
                    "title": f"Review {diff.get('section', 'document section')}",
                    "rationale": "A deterministic document difference was detected in the provided input.",
                    "priority": diff.get("significance", "medium"),
                    "base_text": diff.get("base_text"),
                    "proposed_text": diff.get("compared_text"),
                    "source_document_id": diff.get("document_id"),
                },
            }
            for diff in differences[:max_suggestions]
        ]

    def _document_input(self, document_id: str, *, fallback: Document | None = None) -> AnalysisDocumentInput:
        document = fallback
        if document is None and self._session is not None:
            document = self._session.get(Document, document_id)
        if document is None:
            return AnalysisDocumentInput(document_id, "", "", "", 0, None, "Document", None, "")

        version = None
        if self._session is not None and document.current_version_id:
            version = self._session.get(DocumentVersion, document.current_version_id)

        chunks: list[Chunk] = []
        if self._session is not None:
            chunks = self._session.scalars(
                select(Chunk)
                .where(Chunk.document_id == document.id, Chunk.is_searchable.is_(True))
                .order_by(Chunk.chunk_index.asc())
            ).all()
        if chunks:
            first_chunk = chunks[0]
            return AnalysisDocumentInput(
                document_id=document.id,
                title=document.title,
                source_type=document.source_type,
                import_status=document.import_status,
                chunk_count=len(chunks),
                first_chunk_id=first_chunk.id,
                first_heading=" > ".join(first_chunk.heading_path or []) or document.title,
                first_text=first_chunk.content,
                content="\n".join(chunk.content for chunk in chunks),
            )

        content = version.normalized_markdown if version is not None else ""
        return AnalysisDocumentInput(
            document_id=document.id,
            title=document.title,
            source_type=document.source_type,
            import_status=document.import_status,
            chunk_count=1 if content else 0,
            first_chunk_id=None,
            first_heading=document.title,
            first_text=content,
            content=content,
        )


def _token_set(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _jaccard_similarity(left: str, right: str) -> float:
    left_words = _token_set(left)
    right_words = _token_set(right)
    if not left_words and not right_words:
        return 1.0
    if not left_words or not right_words:
        return 0.0
    return round(len(left_words & right_words) / len(left_words | right_words), 4)


def _preview(value: str | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())[:limit]


def _slug(value: str) -> str:
    normalized = "-".join(re.findall(r"[a-z0-9]+", value.lower()))
    return normalized[:64] or "document"


def _stable_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
