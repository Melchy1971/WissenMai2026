from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.documents import ChatCitation, Chunk, Document


class DocumentLifecycleNotFoundError(LookupError):
    pass


class DocumentLifecycleConflictError(RuntimeError):
    pass


class InvalidLifecycleTransitionError(DocumentLifecycleConflictError):
    pass


class DocumentAlreadyArchivedError(DocumentLifecycleConflictError):
    pass


class DocumentAlreadyDeletedError(DocumentLifecycleConflictError):
    pass


class DocumentLifecycleService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "DocumentLifecycleService":
        return cls(session)

    def archive(self, document_id: str, *, workspace_id: str):
        document = self._get_document(document_id, workspace_id=workspace_id)
        if document.lifecycle_status == "archived":
            raise DocumentAlreadyArchivedError("Document is already archived")
        if document.lifecycle_status == "deleted":
            raise DocumentAlreadyDeletedError("Document is already deleted")
        if document.lifecycle_status != "active":
            raise InvalidLifecycleTransitionError("Only active documents can be archived")

        now = datetime.now(UTC)
        document.lifecycle_status = "archived"
        document.archived_at = now
        document.deleted_at = None
        document.updated_at = now
        self._session.add(document)
        self._sync_chunk_searchability(document_id=document.id, is_searchable=False)
        self._sync_citation_source_status(document_id=document.id, source_status="archived")
        self._session.commit()
        self._session.refresh(document)
        return document

    def restore(self, document_id: str, *, workspace_id: str):
        document = self._get_document(document_id, workspace_id=workspace_id)
        if document.lifecycle_status == "deleted":
            raise DocumentAlreadyDeletedError("Deleted documents require an explicit admin restore")
        if document.lifecycle_status == "active":
            raise InvalidLifecycleTransitionError("Only archived documents can be restored")
        if document.lifecycle_status != "archived":
            raise InvalidLifecycleTransitionError("Only archived documents can be restored")

        now = datetime.now(UTC)
        document.lifecycle_status = "active"
        document.archived_at = None
        document.deleted_at = None
        document.updated_at = now
        self._session.add(document)
        self._sync_chunk_searchability(document_id=document.id, is_searchable=True)
        self._sync_citation_source_status(document_id=document.id, source_status="active")
        self._session.commit()
        self._session.refresh(document)
        return document

    def delete(self, document_id: str, *, workspace_id: str):
        document = self._get_document(document_id, workspace_id=workspace_id)
        if document.lifecycle_status == "deleted":
            raise DocumentAlreadyDeletedError("Document is already deleted")
        now = datetime.now(UTC)
        previous_status = document.lifecycle_status
        document.lifecycle_status = "deleted"
        if document.archived_at is None and previous_status == "archived":
            document.archived_at = now
        document.deleted_at = now
        document.updated_at = now
        self._session.add(document)
        self._sync_chunk_searchability(document_id=document.id, is_searchable=False)
        self._sync_citation_source_status(document_id=document.id, source_status="deleted")
        self._session.commit()
        self._session.refresh(document)
        return document

    def _sync_chunk_searchability(self, *, document_id: str, is_searchable: bool) -> None:
        self._session.execute(
            update(Chunk)
            .where(Chunk.document_id == document_id)
            .values(is_searchable=is_searchable)
        )

    def _sync_citation_source_status(self, *, document_id: str, source_status: str) -> None:
        self._session.execute(
            update(ChatCitation)
            .where(ChatCitation.document_id == document_id)
            .values(source_status=source_status)
        )

    def _get_document(self, document_id: str, *, workspace_id: str) -> Document:
        document = self._session.get(Document, document_id)
        if document is None:
            raise DocumentLifecycleNotFoundError(document_id)
        if document.workspace_id != workspace_id:
            raise DocumentLifecycleNotFoundError(document_id)
        return document