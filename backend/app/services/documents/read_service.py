from typing import Any, Protocol

from app.repositories.documents import (
    DocumentChunkRecord,
    DocumentDetailRecord,
    DocumentListRecord,
    DocumentRepository,
    DocumentVersionRecord,
)
from app.schemas.documents import (
    DocumentChunkPreview,
    DocumentChunkSummary,
    DocumentChunkSourceAnchor,
    DocumentDetail,
    DocumentListItem,
    DocumentParserMetadata,
    DocumentVersionSummary,
)


class DocumentNotFoundError(LookupError):
    pass


class DocumentStateConflictError(RuntimeError):
    pass


class DocumentReadRepository(Protocol):
    def get_documents(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        lifecycle_status: str | None = None,
        include_archived: bool = False,
    ) -> list[DocumentListRecord]: ...

    def get_document_detail(self, document_id: str, *, workspace_id: str) -> DocumentDetailRecord | None: ...

    def get_versions(self, document_id: str, *, workspace_id: str) -> list[DocumentVersionRecord]: ...

    def get_latest_version_id(self, document_id: str, *, workspace_id: str) -> str | None: ...

    def get_chunks(self, *, document_id: str, version_id: str, limit: int | None = None) -> list[DocumentChunkRecord]: ...

    def document_exists(self, document_id: str, *, workspace_id: str) -> bool: ...


class DocumentReadService:
    def __init__(self, repository: DocumentReadRepository) -> None:
        self._repository = repository

    @classmethod
    def from_session(cls, session) -> "DocumentReadService":
        return cls(DocumentRepository(session))

    def get_documents(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        lifecycle_status: str | None = None,
        include_archived: bool = False,
    ) -> list[DocumentListItem]:
        return [
            DocumentListItem(
                id=record.id,
                title=record.title,
                mime_type=record.mime_type,
                created_at=record.created_at,
                updated_at=record.updated_at,
                latest_version_id=record.latest_version_id,
                import_status=record.import_status,
                lifecycle_status=record.lifecycle_status,
                archived_at=record.archived_at,
                deleted_at=record.deleted_at,
                version_count=record.version_count,
                chunk_count=record.chunk_count,
            )
            for record in self._repository.get_documents(
                workspace_id=workspace_id,
                limit=limit,
                offset=offset,
                lifecycle_status=lifecycle_status,
                include_archived=include_archived,
            )
        ]

    def get_document_detail(self, document_id: str, *, workspace_id: str) -> DocumentDetail:
        record = self._repository.get_document_detail(document_id, workspace_id=workspace_id)
        if record is None:
            raise DocumentNotFoundError(document_id)
        # Frueher stand hier ein 409 fuer "parsed/chunked ohne Version". Der
        # Zustand ist seit Migration 20260504_0010 durch
        # ck_documents_readable_status_requires_current_version ausgeschlossen;
        # der Zweig war toter Code. Entfernt 2026-07-26.
        if record.version_id is None:
            return self._build_unversioned_detail(record)
        if record.import_status == "chunked" and record.chunk_count == 0:
            raise DocumentStateConflictError("Document import is chunked but latest version has no chunks")

        if (
            record.version_number is None
            or record.version_created_at is None
            or record.version_content_hash is None
            or record.parser_version is None
            or record.ocr_used is None
        ):
            raise DocumentStateConflictError("Document latest version metadata is incomplete")

        latest_version = DocumentVersionSummary(
            id=record.version_id,
            version_number=record.version_number,
            created_at=record.version_created_at,
            content_hash=record.version_content_hash,
        )

        return DocumentDetail(
            id=record.id,
            workspace_id=record.workspace_id,
            owner_user_id=record.owner_user_id,
            title=record.title,
            source_type=record.source_type,
            mime_type=record.mime_type,
            content_hash=record.content_hash,
            created_at=record.created_at,
            updated_at=record.updated_at,
            latest_version_id=record.latest_version_id,
            latest_version=latest_version,
            parser_metadata=DocumentParserMetadata(
                parser_version=record.parser_version,
                ocr_used=record.ocr_used,
                ki_provider=record.ki_provider,
                ki_model=record.ki_model,
                metadata=record.version_metadata or {},
            ),
            import_status=record.import_status,
            lifecycle_status=record.lifecycle_status,
            archived_at=record.archived_at,
            deleted_at=record.deleted_at,
            chunk_summary=DocumentChunkSummary(
                chunk_count=record.chunk_count,
                total_chars=record.total_chars,
                first_chunk_id=record.first_chunk_id,
                last_chunk_id=record.last_chunk_id,
            ),
        )

    def _build_unversioned_detail(self, record: DocumentDetailRecord) -> DocumentDetail:
        return DocumentDetail(
            id=record.id,
            workspace_id=record.workspace_id,
            owner_user_id=record.owner_user_id,
            title=record.title,
            source_type=record.source_type,
            mime_type=record.mime_type,
            content_hash=record.content_hash,
            created_at=record.created_at,
            updated_at=record.updated_at,
            latest_version_id=record.latest_version_id,
            latest_version=None,
            parser_metadata=None,
            import_status=record.import_status,
            lifecycle_status=record.lifecycle_status,
            archived_at=record.archived_at,
            deleted_at=record.deleted_at,
            chunk_summary=DocumentChunkSummary(
                chunk_count=0,
                total_chars=0,
                first_chunk_id=None,
                last_chunk_id=None,
            ),
        )

    def get_versions(self, document_id: str, *, workspace_id: str) -> list[DocumentVersionSummary]:
        records = self._repository.get_versions(document_id, workspace_id=workspace_id)
        if not records and not self._repository.document_exists(document_id, workspace_id=workspace_id):
            raise DocumentNotFoundError(document_id)

        return [
            DocumentVersionSummary(
                id=record.id,
                version_number=record.version_number,
                created_at=record.created_at,
                content_hash=record.content_hash,
            )
            for record in records
        ]

    def get_chunks(self, document_id: str, *, workspace_id: str, limit: int | None = None) -> list[DocumentChunkPreview]:
        latest_version_id = self._repository.get_latest_version_id(document_id, workspace_id=workspace_id)
        if latest_version_id is None:
            if not self._repository.document_exists(document_id, workspace_id=workspace_id):
                raise DocumentNotFoundError(document_id)
            return []

        return [
            DocumentChunkPreview(
                chunk_id=record.id,
                position=record.position,
                text_preview=record.text_preview,
                source_anchor=self._build_source_anchor(record.anchor, record.metadata),
            )
            for record in self._repository.get_chunks(
                document_id=document_id,
                version_id=latest_version_id,
                limit=limit,
            )
        ]

    def _build_source_anchor(self, anchor: str, metadata: dict[str, Any] | None) -> DocumentChunkSourceAnchor:
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
