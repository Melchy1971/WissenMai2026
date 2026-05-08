from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import cast, desc, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.core.errors import ServiceUnavailableApiError
from app.models.documents import Chunk, Document, DocumentVersion


READABLE_IMPORT_STATUSES = ("parsed", "chunked")


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


class SearchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

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
            raise ServiceUnavailableApiError(message="Chunk search requires PostgreSQL full text search")

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