from datetime import UTC, datetime

import pytest

from app.repositories.documents import DocumentDetailRecord, DocumentListRecord
from app.services.documents.read_service import DocumentNotFoundError, DocumentReadService, DocumentStateConflictError


class FakeDocumentRepository:
    def __init__(
        self,
        detail: DocumentDetailRecord | None = None,
        documents: list[DocumentListRecord] | None = None,
    ) -> None:
        self.detail = detail
        self.documents = documents or []

    def get_documents(self, *, workspace_id: str, limit: int, offset: int, lifecycle_status=None, include_archived=False):
        return self.documents

    def get_document_detail(self, document_id: str) -> DocumentDetailRecord | None:
        return self.detail

    def get_versions(self, document_id: str):
        return []

    def get_latest_version_id(self, document_id: str) -> str | None:
        return None

    def get_chunks(self, *, document_id: str, version_id: str, limit: int | None = None):
        return []

    def document_exists(self, document_id: str) -> bool:
        return self.detail is not None


def test_get_document_detail_maps_repository_record_without_fastapi_or_database() -> None:
    created_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    service = DocumentReadService(
        FakeDocumentRepository(
            DocumentDetailRecord(
                id="document-1",
                workspace_id="workspace-1",
                owner_user_id="user-1",
                title="Title",
                source_type="upload",
                mime_type="text/plain",
                content_hash="content-hash",
                created_at=created_at,
                updated_at=created_at,
                latest_version_id="version-1",
                import_status="chunked",
                lifecycle_status="active",
                archived_at=None,
                deleted_at=None,
                version_id="version-1",
                version_number=1,
                version_created_at=created_at,
                version_content_hash="markdown-hash",
                parser_version="1.0",
                ocr_used=False,
                ki_provider=None,
                ki_model=None,
                version_metadata={"parser_name": "txt-parser"},
                chunk_count=1,
                total_chars=42,
                first_chunk_id="chunk-1",
                last_chunk_id="chunk-1",
            )
        )
    )

    detail = service.get_document_detail("document-1", workspace_id="workspace-1")

    assert detail.id == "document-1"
    assert detail.latest_version is not None
    assert detail.latest_version.id == "version-1"
    assert detail.latest_version.content_hash == "markdown-hash"
    assert detail.parser_metadata is not None
    assert detail.parser_metadata.metadata == {"parser_name": "txt-parser"}
    assert detail.import_status == "chunked"
    assert detail.chunk_summary.chunk_count == 1
    assert detail.chunk_summary.first_chunk_id == "chunk-1"


def test_get_document_detail_raises_conflict_for_document_without_version() -> None:
    created_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    service = DocumentReadService(
        FakeDocumentRepository(
            DocumentDetailRecord(
                id="document-1",
                workspace_id="workspace-1",
                owner_user_id="user-1",
                title="Title",
                source_type="upload",
                mime_type="text/plain",
                content_hash="content-hash",
                created_at=created_at,
                updated_at=created_at,
                latest_version_id=None,
                import_status="chunked",
                lifecycle_status="active",
                archived_at=None,
                deleted_at=None,
                version_id=None,
                version_number=None,
                version_created_at=None,
                version_content_hash=None,
                parser_version=None,
                ocr_used=None,
                ki_provider=None,
                ki_model=None,
                version_metadata=None,
                chunk_count=0,
                total_chars=0,
                first_chunk_id=None,
                last_chunk_id=None,
            )
        )
    )

    with pytest.raises(DocumentStateConflictError, match="without a latest version"):
        service.get_document_detail("document-1", workspace_id="workspace-1")


def test_get_document_detail_returns_pending_document_without_version() -> None:
    created_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    service = DocumentReadService(
        FakeDocumentRepository(
            DocumentDetailRecord(
                id="document-1",
                workspace_id="workspace-1",
                owner_user_id="user-1",
                title="Title",
                source_type="upload",
                mime_type="text/plain",
                content_hash="content-hash",
                created_at=created_at,
                updated_at=created_at,
                latest_version_id=None,
                import_status="pending",
                lifecycle_status="active",
                archived_at=None,
                deleted_at=None,
                version_id=None,
                version_number=None,
                version_created_at=None,
                version_content_hash=None,
                parser_version=None,
                ocr_used=None,
                ki_provider=None,
                ki_model=None,
                version_metadata=None,
                chunk_count=0,
                total_chars=0,
                first_chunk_id=None,
                last_chunk_id=None,
            )
        )
    )

    detail = service.get_document_detail("document-1", workspace_id="workspace-1")

    assert detail.import_status == "pending"
    assert detail.latest_version is None
    assert detail.parser_metadata is None
    assert detail.chunk_summary.chunk_count == 0


def test_get_document_detail_raises_conflict_for_completed_version_without_chunks() -> None:
    created_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    service = DocumentReadService(
        FakeDocumentRepository(
            DocumentDetailRecord(
                id="document-1",
                workspace_id="workspace-1",
                owner_user_id="user-1",
                title="Title",
                source_type="upload",
                mime_type="text/plain",
                content_hash="content-hash",
                created_at=created_at,
                updated_at=created_at,
                latest_version_id="version-1",
                import_status="chunked",
                lifecycle_status="active",
                archived_at=None,
                deleted_at=None,
                version_id="version-1",
                version_number=1,
                version_created_at=created_at,
                version_content_hash="markdown-hash",
                parser_version="1.0",
                ocr_used=False,
                ki_provider=None,
                ki_model=None,
                version_metadata={},
                chunk_count=0,
                total_chars=0,
                first_chunk_id=None,
                last_chunk_id=None,
            )
        )
    )

    with pytest.raises(DocumentStateConflictError, match="no chunks"):
        service.get_document_detail("document-1", workspace_id="workspace-1")


def test_get_documents_maps_stable_list_fields_without_fastapi_or_database() -> None:
    created_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    service = DocumentReadService(
        FakeDocumentRepository(
            documents=[
                DocumentListRecord(
                    id="document-1",
                    title="Title",
                    mime_type="text/plain",
                    created_at=created_at,
                    updated_at=created_at,
                    latest_version_id="version-1",
                    import_status="chunked",
                    lifecycle_status="active",
                    archived_at=None,
                    deleted_at=None,
                    version_count=2,
                    chunk_count=7,
                )
            ]
        )
    )

    documents = service.get_documents(workspace_id="workspace-1", limit=20, offset=0)

    assert len(documents) == 1
    assert documents[0].id == "document-1"
    assert documents[0].mime_type == "text/plain"
    assert documents[0].latest_version_id == "version-1"
    assert documents[0].lifecycle_status == "active"
    assert documents[0].version_count == 2
    assert documents[0].chunk_count == 7


def test_get_document_detail_raises_not_found_without_fastapi() -> None:
    service = DocumentReadService(FakeDocumentRepository())

    with pytest.raises(DocumentNotFoundError):
        service.get_document_detail("missing", workspace_id="workspace-1")
