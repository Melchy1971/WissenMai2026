from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.documents import Chunk, Document, DocumentVersion


VISIBLE_DOCUMENT_STATUSES = ("active", "archived")


@dataclass(frozen=True)
class DocumentListRecord:
    id: str
    title: str
    mime_type: str | None
    created_at: datetime
    updated_at: datetime
    latest_version_id: str | None
    import_status: str
    lifecycle_status: str
    archived_at: datetime | None
    deleted_at: datetime | None
    version_count: int
    chunk_count: int


@dataclass(frozen=True)
class DocumentDetailRecord:
    id: str
    workspace_id: str
    owner_user_id: str
    title: str
    source_type: str
    mime_type: str | None
    content_hash: str
    created_at: datetime
    updated_at: datetime
    latest_version_id: str | None
    import_status: str
    lifecycle_status: str
    archived_at: datetime | None
    deleted_at: datetime | None
    version_id: str | None
    version_number: int | None
    version_created_at: datetime | None
    version_content_hash: str | None
    parser_version: str | None
    ocr_used: bool | None
    ki_provider: str | None
    ki_model: str | None
    version_metadata: dict[str, Any] | None
    chunk_count: int
    total_chars: int
    first_chunk_id: str | None
    last_chunk_id: str | None


@dataclass(frozen=True)
class DocumentVersionRecord:
    id: str
    version_number: int
    created_at: datetime
    content_hash: str


@dataclass(frozen=True)
class DocumentChunkRecord:
    id: str
    position: int
    text_preview: str
    anchor: str
    metadata: dict[str, Any] | None


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _uuid_param(self, value: str) -> str:
        return str(value)

    def get_documents(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        lifecycle_status: str | None = None,
        include_archived: bool = False,
    ) -> list[DocumentListRecord]:
        # Correlated scalar subqueries run only for the LIMIT-d rows, not the entire table.
        # With indexes on document_versions(document_id) and
        # document_chunks(document_id, document_version_id, chunk_index), each subquery
        # becomes an index lookup instead of a full-table aggregation.
        version_count_sq = (
            select(func.count(DocumentVersion.id))
            .where(DocumentVersion.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )
        chunk_count_sq = (
            select(func.count(Chunk.id))
            .where(
                Chunk.document_id == Document.id,
                Chunk.document_version_id == Document.current_version_id,
            )
            .correlate(Document)
            .scalar_subquery()
        )

        conditions = [
            Document.workspace_id == self._uuid_param(workspace_id),
            Document.lifecycle_status != "deleted",
        ]
        if lifecycle_status is not None:
            conditions.append(Document.lifecycle_status == lifecycle_status)
        elif not include_archived:
            conditions.append(Document.lifecycle_status == "active")

        rows = self._session.execute(
            select(
                Document.id,
                Document.title,
                Document.mime_type,
                Document.created_at,
                Document.updated_at,
                Document.current_version_id.label("latest_version_id"),
                Document.import_status,
                Document.lifecycle_status,
                Document.archived_at,
                Document.deleted_at,
                func.coalesce(version_count_sq, 0).label("version_count"),
                func.coalesce(chunk_count_sq, 0).label("chunk_count"),
            )
            .where(*conditions)
            .order_by(desc(Document.created_at))
            .limit(limit)
            .offset(offset)
        ).all()

        return [
            DocumentListRecord(
                id=row.id,
                title=row.title,
                mime_type=row.mime_type,
                created_at=row.created_at,
                updated_at=row.updated_at,
                latest_version_id=row.latest_version_id,
                import_status=row.import_status,
                lifecycle_status=row.lifecycle_status,
                archived_at=row.archived_at,
                deleted_at=row.deleted_at,
                version_count=row.version_count,
                chunk_count=row.chunk_count,
            )
            for row in rows
        ]

    def get_document_detail(self, document_id: str, *, workspace_id: str) -> DocumentDetailRecord | None:
        chunk_count = (
            select(func.count(Chunk.id))
            .where(Chunk.document_id == Document.id, Chunk.document_version_id == Document.current_version_id)
            .scalar_subquery()
        )
        total_chars = (
            select(func.coalesce(func.sum(func.length(Chunk.content)), 0))
            .where(Chunk.document_id == Document.id, Chunk.document_version_id == Document.current_version_id)
            .scalar_subquery()
        )
        first_chunk_id = (
            select(Chunk.id)
            .where(Chunk.document_id == Document.id, Chunk.document_version_id == Document.current_version_id)
            .order_by(Chunk.chunk_index.asc())
            .limit(1)
            .scalar_subquery()
        )
        last_chunk_id = (
            select(Chunk.id)
            .where(Chunk.document_id == Document.id, Chunk.document_version_id == Document.current_version_id)
            .order_by(Chunk.chunk_index.desc())
            .limit(1)
            .scalar_subquery()
        )

        row = self._session.execute(
            select(
                Document.id,
                Document.workspace_id,
                Document.owner_user_id,
                Document.title,
                Document.source_type,
                Document.mime_type,
                Document.content_hash,
                Document.created_at,
                Document.updated_at,
                Document.current_version_id.label("latest_version_id"),
                Document.import_status,
                Document.lifecycle_status,
                Document.archived_at,
                Document.deleted_at,
                DocumentVersion.id.label("version_id"),
                DocumentVersion.version_number,
                DocumentVersion.created_at.label("version_created_at"),
                DocumentVersion.markdown_hash.label("version_content_hash"),
                DocumentVersion.parser_version,
                DocumentVersion.ocr_used,
                DocumentVersion.ki_provider,
                DocumentVersion.ki_model,
                DocumentVersion.metadata_,
                chunk_count.label("chunk_count"),
                total_chars.label("total_chars"),
                first_chunk_id.label("first_chunk_id"),
                last_chunk_id.label("last_chunk_id"),
            )
            .outerjoin(DocumentVersion, Document.current_version_id == DocumentVersion.id)
            .where(
                Document.id == self._uuid_param(document_id),
                Document.workspace_id == self._uuid_param(workspace_id),
                Document.lifecycle_status != "deleted",
            )
        ).one_or_none()

        if row is None:
            return None

        return DocumentDetailRecord(
            id=row.id,
            workspace_id=row.workspace_id,
            owner_user_id=row.owner_user_id,
            title=row.title,
            source_type=row.source_type,
            mime_type=row.mime_type,
            content_hash=row.content_hash,
            created_at=row.created_at,
            updated_at=row.updated_at,
            latest_version_id=row.latest_version_id,
            import_status=row.import_status,
            lifecycle_status=row.lifecycle_status,
            archived_at=row.archived_at,
            deleted_at=row.deleted_at,
            version_id=row.version_id,
            version_number=row.version_number,
            version_created_at=row.version_created_at,
            version_content_hash=row.version_content_hash,
            parser_version=row.parser_version,
            ocr_used=row.ocr_used,
            ki_provider=row.ki_provider,
            ki_model=row.ki_model,
            version_metadata=row.metadata_,
            chunk_count=row.chunk_count,
            total_chars=row.total_chars,
            first_chunk_id=row.first_chunk_id,
            last_chunk_id=row.last_chunk_id,
        )

    def get_versions(self, document_id: str, *, workspace_id: str) -> list[DocumentVersionRecord]:
        rows = self._session.execute(
            select(
                DocumentVersion.id,
                DocumentVersion.version_number,
                DocumentVersion.created_at,
                DocumentVersion.markdown_hash.label("content_hash"),
            )
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(DocumentVersion.document_id == self._uuid_param(document_id))
            .where(Document.workspace_id == self._uuid_param(workspace_id))
            .where(Document.lifecycle_status != "deleted")
            .order_by(desc(DocumentVersion.created_at), desc(DocumentVersion.version_number))
        ).all()

        return [
            DocumentVersionRecord(
                id=row.id,
                version_number=row.version_number,
                created_at=row.created_at,
                content_hash=row.content_hash,
            )
            for row in rows
        ]

    def get_latest_version_id(self, document_id: str, *, workspace_id: str) -> str | None:
        return self._session.execute(
            select(Document.current_version_id).where(
                Document.id == self._uuid_param(document_id),
                Document.workspace_id == self._uuid_param(workspace_id),
                Document.lifecycle_status != "deleted",
            )
        ).scalar_one_or_none()

    def get_chunks(self, *, document_id: str, version_id: str, limit: int | None = None) -> list[DocumentChunkRecord]:
        query = (
            select(
                Chunk.id,
                Chunk.chunk_index,
                func.substr(Chunk.content, 1, 200).label("text_preview"),
                Chunk.anchor,
                Chunk.metadata_,
            )
            .where(
                Chunk.document_id == self._uuid_param(document_id),
                Chunk.document_version_id == self._uuid_param(version_id),
            )
            .order_by(Chunk.chunk_index.asc())
        )
        if limit is not None:
            query = query.limit(limit)

        rows = self._session.execute(query).all()

        return [
            DocumentChunkRecord(
                id=row.id,
                position=row.chunk_index,
                text_preview=row.text_preview,
                anchor=row.anchor,
                metadata=row.metadata_,
            )
            for row in rows
        ]

    def document_exists(self, document_id: str, *, workspace_id: str) -> bool:
        return (
            self._session.execute(
                select(Document.id).where(
                    Document.id == self._uuid_param(document_id),
                    Document.workspace_id == self._uuid_param(workspace_id),
                    Document.lifecycle_status != "deleted",
                )
            ).scalar_one_or_none()
            is not None
        )

    def get_document_lifecycle(self, document_id: str) -> Document | None:
        return self._session.execute(
            select(Document).where(Document.id == self._uuid_param(document_id), Document.lifecycle_status != "deleted")
        ).scalar_one_or_none()

