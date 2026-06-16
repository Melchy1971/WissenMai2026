from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import cast, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ServiceUnavailableApiError
from app.models.documents import Chunk, Document, DocumentVersion
from app.models.topics import Topic, TopicTag


READABLE_IMPORT_STATUSES = ("parsed", "chunked")

_HIGHLIGHT_MAX_LEN = 240
_EXCERPT_CONTEXT = 80


# ── Legacy record ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SearchChunkRecord:
    document_id: str
    document_title: str
    document_created_at: datetime
    document_version_id: str
    version_number: int
    chunk_id: str
    position: int
    text_preview: str
    anchor: str
    metadata: dict[str, Any] | None
    rank: float


# ── Unified record ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UnifiedSearchRecord:
    kind: str          # "chunk" | "topic" | "document"
    id: str
    title: str
    highlight: str
    score: float
    status: str | None
    created_at: datetime
    meta: dict[str, Any]


# ── Highlighting helpers ──────────────────────────────────────────────────────

def _highlight_ilike(text: str, query_words: list[str], max_len: int = _HIGHLIGHT_MAX_LEN) -> str:
    """Return a short excerpt with matched words wrapped in <mark>...</mark>."""
    if not text:
        return ""

    text_lower = text.lower()
    first_pos = len(text)
    for word in query_words:
        pos = text_lower.find(word.lower())
        if pos != -1:
            first_pos = min(first_pos, pos)

    if first_pos == len(text):
        excerpt_raw = text[:max_len]
        prefix = ""
        suffix = "..." if len(text) > max_len else ""
    else:
        start = max(0, first_pos - _EXCERPT_CONTEXT)
        excerpt_raw = text[start : start + max_len]
        prefix = "..." if start > 0 else ""
        suffix = "..." if start + max_len < len(text) else ""

    result = excerpt_raw
    for word in query_words:
        escaped = re.escape(word)
        result = re.sub(f"({escaped})", r"<mark>\1</mark>", result, flags=re.IGNORECASE)

    return prefix + result + suffix


def _score_ilike(text: str, query_words: list[str], base: float) -> float:
    """Compute a simple relevance score in [0, 1] for ILIKE matches."""
    if not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for w in query_words if w.lower() in text_lower)
    if hits == 0:
        return 0.0
    coverage = hits / max(len(query_words), 1)
    return round(base * (0.5 + 0.5 * coverage), 4)


class SearchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Legacy chunk search ───────────────────────────────────────────────────

    def _uuid_param(self, value: str) -> str:
        return str(value)

    def search_chunks(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchChunkRecord]:
        bind = self._session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            raise ServiceUnavailableApiError(
                message="Chunk search requires PostgreSQL full text search"
            )

        from sqlalchemy.dialects import postgresql

        ts_query = func.plainto_tsquery("simple", query)
        rank_expr = func.ts_rank(Chunk.search_vector, ts_query)

        query_stmt = (
            select(
                Document.id.label("document_id"),
                Document.title.label("document_title"),
                Document.created_at.label("document_created_at"),
                DocumentVersion.id.label("document_version_id"),
                DocumentVersion.version_number,
                Chunk.id.label("chunk_id"),
                Chunk.chunk_index.label("position"),
                func.substr(Chunk.content, 1, 200).label("text_preview"),
                Chunk.anchor,
                Chunk.metadata_,
                cast(rank_expr, postgresql.DOUBLE_PRECISION).label("rank"),
            )
            .join(Document, Document.id == Chunk.document_id)
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
            .where(
                Document.workspace_id == self._uuid_param(workspace_id),
                Document.current_version_id == DocumentVersion.id,
                Document.import_status.in_(READABLE_IMPORT_STATUSES),
                Document.lifecycle_status == "active",
                Chunk.search_vector.op("@@")(ts_query),
            )
            .order_by(
                desc(rank_expr),
                desc(Document.created_at),
                Chunk.chunk_index.asc(),
                Chunk.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        rows = self._session.execute(query_stmt).all()
        return [
            SearchChunkRecord(
                document_id=str(row.document_id),
                document_title=row.document_title,
                document_created_at=row.document_created_at,
                document_version_id=str(row.document_version_id),
                version_number=row.version_number,
                chunk_id=str(row.chunk_id),
                position=row.position,
                text_preview=row.text_preview,
                anchor=row.anchor,
                metadata=row.metadata_,
                rank=float(row.rank),
            )
            for row in rows
        ]

    # ── Unified search ────────────────────────────────────────────────────────

    def search_unified(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
        sort: str = "score_desc",
        kind_filter: list[str] | None = None,
        status_filter: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> tuple[list[UnifiedSearchRecord], int]:
        """Search across topics, documents, chunks. Returns (page, total).

        Topics and documents use ILIKE (cross-DB). Chunks use ts_rank on
        PostgreSQL, ILIKE on SQLite. Sorting and pagination happen in Python
        after merging all three sub-result sets.
        """
        query_words = [w.strip() for w in query.split() if w.strip()]
        include_topics = kind_filter is None or "topic" in kind_filter
        include_docs = kind_filter is None or "document" in kind_filter
        include_chunks = kind_filter is None or "chunk" in kind_filter

        records: list[UnifiedSearchRecord] = []

        if include_topics:
            records.extend(
                self._search_topics(
                    workspace_id=workspace_id,
                    query_words=query_words,
                    status_filter=status_filter,
                    created_after=created_after,
                    created_before=created_before,
                )
            )

        if include_docs:
            records.extend(
                self._search_documents(
                    workspace_id=workspace_id,
                    query_words=query_words,
                    created_after=created_after,
                    created_before=created_before,
                )
            )

        if include_chunks:
            records.extend(
                self._search_chunks_unified(
                    workspace_id=workspace_id,
                    query=query,
                    query_words=query_words,
                    created_after=created_after,
                    created_before=created_before,
                )
            )

        records = _sort_records(records, sort)
        total = len(records)
        page = records[offset : offset + limit]
        return page, total

    # ── Topic sub-search ──────────────────────────────────────────────────────

    def _search_topics(
        self,
        *,
        workspace_id: str,
        query_words: list[str],
        status_filter: list[str] | None,
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> list[UnifiedSearchRecord]:
        if not query_words:
            return []

        like_conditions = []
        for word in query_words:
            pattern = f"%{word}%"
            like_conditions.append(Topic.title.ilike(pattern))
            like_conditions.append(Topic.summary.ilike(pattern))

        stmt = select(Topic).where(
            Topic.workspace_id == workspace_id,
            Topic.deleted_at.is_(None),
            or_(*like_conditions),
        )
        if status_filter:
            stmt = stmt.where(Topic.status.in_(status_filter))
        if created_after:
            stmt = stmt.where(Topic.created_at >= created_after)
        if created_before:
            stmt = stmt.where(Topic.created_at <= created_before)

        topics = self._session.scalars(stmt).all()

        results: list[UnifiedSearchRecord] = []
        for t in topics:
            title_score = _score_ilike(t.title or "", query_words, base=0.90)
            summary_score = _score_ilike(t.summary or "", query_words, base=0.65)
            score = max(title_score, summary_score)

            if title_score >= summary_score:
                highlight = _highlight_ilike(t.title or "", query_words)
            else:
                highlight = _highlight_ilike(t.summary or "", query_words)

            tag_rows = (
                self._session.execute(
                    select(TopicTag.tag_id).where(TopicTag.topic_id == t.id)
                )
                .scalars()
                .all()
            )

            results.append(
                UnifiedSearchRecord(
                    kind="topic",
                    id=t.id,
                    title=t.title,
                    highlight=highlight,
                    score=score,
                    status=t.status,
                    created_at=t.created_at,
                    meta={"slug": t.slug, "tag_ids": list(tag_rows)},
                )
            )
        return results

    # ── Document sub-search ───────────────────────────────────────────────────

    def _search_documents(
        self,
        *,
        workspace_id: str,
        query_words: list[str],
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> list[UnifiedSearchRecord]:
        if not query_words:
            return []

        like_conditions = [Document.title.ilike(f"%{w}%") for w in query_words]

        stmt = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.lifecycle_status == "active",
            or_(*like_conditions),
        )
        if created_after:
            stmt = stmt.where(Document.created_at >= created_after)
        if created_before:
            stmt = stmt.where(Document.created_at <= created_before)

        docs = self._session.scalars(stmt).all()

        results: list[UnifiedSearchRecord] = []
        for d in docs:
            score = _score_ilike(d.title or "", query_words, base=0.85)
            highlight = _highlight_ilike(d.title or "", query_words)
            results.append(
                UnifiedSearchRecord(
                    kind="document",
                    id=d.id,
                    title=d.title,
                    highlight=highlight,
                    score=score,
                    status=d.lifecycle_status,
                    created_at=d.created_at,
                    meta={
                        "mime_type": d.mime_type,
                        "import_status": d.import_status,
                    },
                )
            )
        return results

    # ── Chunk sub-search ──────────────────────────────────────────────────────

    def _search_chunks_unified(
        self,
        *,
        workspace_id: str,
        query: str,
        query_words: list[str],
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> list[UnifiedSearchRecord]:
        bind = self._session.get_bind()
        is_pg = bind is not None and bind.dialect.name == "postgresql"

        if is_pg:
            return self._search_chunks_pg(
                workspace_id=workspace_id,
                query=query,
                query_words=query_words,
                created_after=created_after,
                created_before=created_before,
            )
        return self._search_chunks_sqlite(
            workspace_id=workspace_id,
            query_words=query_words,
            created_after=created_after,
            created_before=created_before,
        )

    def _search_chunks_pg(
        self,
        *,
        workspace_id: str,
        query: str,
        query_words: list[str],
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> list[UnifiedSearchRecord]:
        from sqlalchemy.dialects import postgresql

        ts_query = func.plainto_tsquery("simple", query)
        rank_expr = func.ts_rank(Chunk.search_vector, ts_query)
        headline_expr = func.ts_headline(
            "simple",
            Chunk.content,
            ts_query,
            "MaxWords=35,MinWords=15,StartSel=<mark>,StopSel=</mark>,MaxFragments=1",
        )

        stmt = (
            select(
                Document.id.label("doc_id"),
                Document.title.label("doc_title"),
                Document.created_at.label("doc_created_at"),
                Document.lifecycle_status.label("lifecycle_status"),
                Document.mime_type.label("mime_type"),
                Chunk.id.label("chunk_id"),
                cast(rank_expr, postgresql.DOUBLE_PRECISION).label("rank"),
                headline_expr.label("headline"),
            )
            .join(Document, Document.id == Chunk.document_id)
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
            .where(
                Document.workspace_id == workspace_id,
                Document.current_version_id == DocumentVersion.id,
                Document.import_status.in_(READABLE_IMPORT_STATUSES),
                Document.lifecycle_status == "active",
                Chunk.search_vector.op("@@")(ts_query),
            )
            .order_by(desc(rank_expr))
            .limit(200)
        )
        if created_after:
            stmt = stmt.where(Document.created_at >= created_after)
        if created_before:
            stmt = stmt.where(Document.created_at <= created_before)

        rows = self._session.execute(stmt).all()
        return [
            UnifiedSearchRecord(
                kind="chunk",
                id=str(row.chunk_id),
                title=row.doc_title,
                highlight=row.headline or "",
                score=min(float(row.rank), 1.0),
                status=row.lifecycle_status,
                created_at=row.doc_created_at,
                meta={
                    "document_id": str(row.doc_id),
                    "mime_type": row.mime_type,
                },
            )
            for row in rows
        ]

    def _search_chunks_sqlite(
        self,
        *,
        workspace_id: str,
        query_words: list[str],
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> list[UnifiedSearchRecord]:
        if not query_words:
            return []
        like_conditions = [Chunk.content.ilike(f"%{w}%") for w in query_words]
        stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
            .where(
                Document.workspace_id == workspace_id,
                Document.lifecycle_status == "active",
                Document.import_status.in_(READABLE_IMPORT_STATUSES),
                Document.current_version_id == DocumentVersion.id,
                or_(*like_conditions),
            )
            .limit(100)
        )
        if created_after:
            stmt = stmt.where(Document.created_at >= created_after)
        if created_before:
            stmt = stmt.where(Document.created_at <= created_before)

        rows = self._session.execute(stmt).all()
        results: list[UnifiedSearchRecord] = []
        for chunk, doc in rows:
            score = _score_ilike(chunk.content or "", query_words, base=0.70)
            highlight = _highlight_ilike(chunk.content or "", query_words)
            results.append(
                UnifiedSearchRecord(
                    kind="chunk",
                    id=str(chunk.id),
                    title=doc.title,
                    highlight=highlight,
                    score=score,
                    status=doc.lifecycle_status,
                    created_at=doc.created_at,
                    meta={"document_id": str(doc.id), "mime_type": doc.mime_type},
                )
            )
        return results


# ── Sort ─────────────────────────────────────────────────────────────────────

def _sort_records(records: list[UnifiedSearchRecord], sort: str) -> list[UnifiedSearchRecord]:
    if sort == "score_desc":
        return sorted(records, key=lambda r: (-r.score, r.created_at.isoformat(), r.id))
    if sort == "created_at_desc":
        return sorted(records, key=lambda r: (r.created_at.isoformat(), r.id), reverse=True)
    if sort == "created_at_asc":
        return sorted(records, key=lambda r: (r.created_at.isoformat(), r.id))
    if sort == "title_asc":
        return sorted(records, key=lambda r: (r.title.lower(), r.id))
    # fallback
    return sorted(records, key=lambda r: (-r.score, r.created_at.isoformat(), r.id))
