from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.repositories.search import SearchChunkRecord, SearchRepository, UnifiedSearchRecord
from app.schemas.documents import DocumentChunkSourceAnchor
from app.schemas.search import (
    SearchChunkResult,
    UnifiedSearchFilters,
    UnifiedSearchHit,
    UnifiedSearchResponse,
    _VALID_SORTS,
    decode_cursor,
    encode_cursor,
)


class InvalidSearchQueryError(ValueError):
    pass


class SearchRepositoryProtocol(Protocol):
    def search_chunks(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchChunkRecord]: ...

    def search_unified(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
        sort: str,
        kind_filter: list[str] | None,
        status_filter: list[str] | None,
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> tuple[list[UnifiedSearchRecord], int]: ...


class SearchService:
    def __init__(self, repository: SearchRepositoryProtocol) -> None:
        self._repository = repository

    @classmethod
    def from_session(cls, session) -> "SearchService":
        return cls(SearchRepository(session))

    # -- Legacy chunk search ---------------------------------------------------

    def search_chunks(
        self,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchChunkResult]:
        normalized_workspace_id = workspace_id.strip()
        if not normalized_workspace_id:
            raise InvalidSearchQueryError("workspace_id is required")
        normalized_query = query.strip()
        if not normalized_query:
            raise InvalidSearchQueryError("query must not be blank")
        if limit < 1 or limit > 100:
            raise InvalidSearchQueryError("limit must be between 1 and 100")
        if offset < 0:
            raise InvalidSearchQueryError("offset must be non-negative")

        return [
            SearchChunkResult(
                document_id=record.document_id,
                document_title=record.document_title,
                document_created_at=record.document_created_at,
                document_version_id=record.document_version_id,
                version_number=record.version_number,
                chunk_id=record.chunk_id,
                position=record.position,
                text_preview=record.text_preview,
                source_anchor=self._build_source_anchor(record.anchor, record.metadata),
                rank=record.rank,
                filters=filters or {},
            )
            for record in self._repository.search_chunks(
                workspace_id=normalized_workspace_id,
                query=normalized_query,
                limit=limit,
                offset=offset,
                filters=filters,
            )
        ]

    # -- Unified search --------------------------------------------------------

    def search_unified(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int = 20,
        cursor: str | None = None,
        sort: str = "score_desc",
        filters: UnifiedSearchFilters | None = None,
    ) -> UnifiedSearchResponse:
        ws = workspace_id.strip()
        if not ws:
            raise InvalidSearchQueryError("workspace_id is required")
        q = query.strip()
        if not q:
            raise InvalidSearchQueryError("query must not be blank")
        if limit < 1 or limit > 100:
            raise InvalidSearchQueryError("limit must be between 1 and 100")
        if sort not in _VALID_SORTS:
            raise InvalidSearchQueryError(
                f"sort must be one of: {', '.join(sorted(_VALID_SORTS))}"
            )

        offset = decode_cursor(cursor) if cursor else 0
        if offset < 0:
            offset = 0

        f = filters or UnifiedSearchFilters()

        records, total = self._repository.search_unified(
            workspace_id=ws,
            query=q,
            limit=limit,
            offset=offset,
            sort=sort,
            kind_filter=f.kind,
            status_filter=f.status,
            created_after=f.created_after,
            created_before=f.created_before,
        )

        next_offset = offset + limit
        has_more = next_offset < total
        next_cursor = encode_cursor(next_offset) if has_more else None

        hits = [
            UnifiedSearchHit(
                kind=r.kind,  # type: ignore[arg-type]
                id=r.id,
                title=r.title,
                highlight=r.highlight,
                score=r.score,
                status=r.status,
                created_at=r.created_at,
                meta=r.meta,
            )
            for r in records
        ]

        filters_applied: dict[str, Any] = {}
        if f.kind:
            filters_applied["kind"] = f.kind
        if f.status:
            filters_applied["status"] = f.status
        if f.created_after:
            filters_applied["created_after"] = f.created_after.isoformat()
        if f.created_before:
            filters_applied["created_before"] = f.created_before.isoformat()

        return UnifiedSearchResponse(
            hits=hits,
            total=total,
            next_cursor=next_cursor,
            has_more=has_more,
            query=q,
            sort=sort,  # type: ignore[arg-type]
            filters_applied=filters_applied,
        )

    # -- Internal helpers ------------------------------------------------------

    def _build_source_anchor(
        self, anchor: str, metadata: dict[str, Any] | None
    ) -> DocumentChunkSourceAnchor:
        source_metadata = metadata or {}
        nested_anchor = source_metadata.get("source_anchor")
        if isinstance(nested_anchor, dict):
            source_metadata = {**source_metadata, **nested_anchor}
        return DocumentChunkSourceAnchor(
            type=self._source_anchor_type(source_metadata.get("type")),
            page=self._optional_int(source_metadata.get("page")),
            paragraph=self._optional_int(source_metadata.get("paragraph")),
            char_start=self._optional_int(source_metadata.get("char_start")),
            char_end=self._optional_int(source_metadata.get("char_end")),
        )

    def _source_anchor_type(self, value: Any) -> str:
        if value in {"text", "pdf_page", "docx_paragraph", "legacy_unknown"}:
            return str(value)
        return "legacy_unknown"

    def _optional_int(self, value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
        return None
