"""M5a Lifecycle Integrity Detector.

Detects lifecycle/search/retrieval inconsistencies for one workspace.

Contract:
- read-only: no document, chunk, version, or citation mutation
- workspace-scoped
- finding_type: INVALID_LIFECYCLE
- severity: error
- remediation: Lifecycle korrigieren
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.documents import ChatCitation, ChatMessage, ChatSession, Chunk, Document, DocumentVersion


_FINDING_TYPE = "INVALID_LIFECYCLE"
_SEVERITY = "error"
_REMEDIATION = "Lifecycle korrigieren"
_ACTIVE = "active"
_ARCHIVED = "archived"
_DELETED = "deleted"
_PENDING = "pending"
_ALLOWED_LIFECYCLE_STATUSES = frozenset({_ACTIVE, _ARCHIVED, _DELETED, _PENDING})


@dataclass(frozen=True)
class LifecycleIntegrityConfig:
    max_rows_per_rule: int = 500


class LifecycleIntegrityDetector:
    def __init__(
        self,
        session: Session,
        workspace_id: str,
        config: LifecycleIntegrityConfig | None = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._config = config or LifecycleIntegrityConfig()

    def detect(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        findings.extend(self._detect_active_documents_not_findable())
        findings.extend(self._detect_archived_documents_in_search())
        findings.extend(self._detect_archived_documents_in_retrieval())
        findings.extend(self._detect_deleted_documents_in_search())
        findings.extend(self._detect_deleted_documents_in_retrieval())
        findings.extend(self._detect_inconsistent_lifecycle_status())
        findings.extend(self._detect_version_lifecycle_violations())
        return findings

    def _detect_active_documents_not_findable(self) -> list[dict[str, Any]]:
        searchable_chunks = func.sum(self._searchable_case())
        rows = self._session.execute(
            select(
                Document.id.label("document_id"),
                Document.current_version_id.label("version_id"),
                func.count(Chunk.id).label("chunk_count"),
                searchable_chunks.label("searchable_count"),
            )
            .outerjoin(Chunk, Chunk.document_id == Document.id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == _ACTIVE,
                Document.import_status.in_(("parsed", "chunked")),
            )
            .group_by(Document.id, Document.current_version_id)
            .having(searchable_chunks == 0)
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id="LI-1",
                title="Active document not findable",
                description=(
                    f"Active document {row.document_id} has {int(row.chunk_count)} chunks "
                    "but no searchable chunk."
                ),
                document_id=row.document_id,
                version_id=row.version_id,
            )
            for row in rows
        ]

    def _detect_archived_documents_in_search(self) -> list[dict[str, Any]]:
        return self._detect_non_active_documents_in_search(
            lifecycle_status=_ARCHIVED,
            rule_id="LI-2",
            title="Archived document appears in search",
        )

    def _detect_archived_documents_in_retrieval(self) -> list[dict[str, Any]]:
        return self._detect_non_active_documents_in_retrieval(
            lifecycle_status=_ARCHIVED,
            expected_source_status=_ARCHIVED,
            rule_id="LI-3",
            title="Archived document appears in retrieval",
        )

    def _detect_deleted_documents_in_search(self) -> list[dict[str, Any]]:
        return self._detect_non_active_documents_in_search(
            lifecycle_status=_DELETED,
            rule_id="LI-4",
            title="Deleted document appears in search",
        )

    def _detect_deleted_documents_in_retrieval(self) -> list[dict[str, Any]]:
        return self._detect_non_active_documents_in_retrieval(
            lifecycle_status=_DELETED,
            expected_source_status=_DELETED,
            rule_id="LI-5",
            title="Deleted document appears in retrieval",
        )

    def _detect_inconsistent_lifecycle_status(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        invalid_status_rows = self._session.execute(
            select(Document.id, Document.lifecycle_status)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status.notin_(list(_ALLOWED_LIFECYCLE_STATUSES)),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()
        for row in invalid_status_rows:
            findings.append(
                self._finding(
                    rule_id="LI-6",
                    title="Invalid lifecycle status",
                    description=(
                        f"Document {row.id} has lifecycle_status='{row.lifecycle_status}', "
                        f"expected one of {sorted(_ALLOWED_LIFECYCLE_STATUSES)}."
                    ),
                    document_id=row.id,
                )
            )

        timestamp_rows = self._session.execute(
            select(Document.id, Document.lifecycle_status, Document.archived_at, Document.deleted_at)
            .where(
                Document.workspace_id == self._workspace_id,
                or_(
                    and_(Document.lifecycle_status == _ACTIVE, Document.deleted_at.isnot(None)),
                    and_(Document.lifecycle_status == _ACTIVE, Document.archived_at.isnot(None)),
                    and_(Document.lifecycle_status == _ARCHIVED, Document.archived_at.is_(None)),
                    and_(Document.lifecycle_status == _ARCHIVED, Document.deleted_at.isnot(None)),
                    and_(Document.lifecycle_status == _DELETED, Document.deleted_at.is_(None)),
                ),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()
        for row in timestamp_rows:
            findings.append(
                self._finding(
                    rule_id="LI-6",
                    title="Lifecycle timestamp mismatch",
                    description=(
                        f"Document {row.id} has lifecycle_status='{row.lifecycle_status}' "
                        f"with archived_at={row.archived_at!r} and deleted_at={row.deleted_at!r}."
                    ),
                    document_id=row.id,
                )
            )

        source_status_rows = self._session.execute(
            select(ChatCitation.id, ChatCitation.document_id, ChatCitation.source_status, Document.lifecycle_status)
            .join(ChatMessage, ChatMessage.id == ChatCitation.message_id)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(Document, Document.id == ChatCitation.document_id)
            .where(
                ChatSession.workspace_id == self._workspace_id,
                Document.workspace_id == self._workspace_id,
                ChatCitation.source_status != Document.lifecycle_status,
            )
            .limit(self._config.max_rows_per_rule)
        ).all()
        for row in source_status_rows:
            findings.append(
                self._finding(
                    rule_id="LI-6",
                    title="Citation source status mismatch",
                    description=(
                        f"Citation {row.id} stores source_status='{row.source_status}' "
                        f"but document {row.document_id} has lifecycle_status='{row.lifecycle_status}'."
                    ),
                    document_id=row.document_id,
                )
            )

        return findings

    def _detect_version_lifecycle_violations(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(
                Document.id.label("document_id"),
                Document.current_version_id.label("current_version_id"),
                Chunk.document_version_id.label("chunk_version_id"),
                Chunk.id.label("chunk_id"),
            )
            .join(Chunk, Chunk.document_id == Document.id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == _ACTIVE,
                Chunk.is_searchable.is_(True),
                Document.current_version_id.isnot(None),
                Chunk.document_version_id != Document.current_version_id,
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        findings = [
            self._finding(
                rule_id="LI-7",
                title="Searchable chunk belongs to non-current version",
                description=(
                    f"Active document {row.document_id} has searchable chunk {row.chunk_id} "
                    f"for version {row.chunk_version_id}, but current_version_id is {row.current_version_id}."
                ),
                document_id=row.document_id,
                version_id=row.chunk_version_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

        missing_version_rows = self._session.execute(
            select(Document.id, Document.current_version_id)
            .outerjoin(DocumentVersion, DocumentVersion.id == Document.current_version_id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == _ACTIVE,
                Document.current_version_id.isnot(None),
                DocumentVersion.id.is_(None),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()
        findings.extend(
            self._finding(
                rule_id="LI-7",
                title="Current version missing",
                description=(
                    f"Active document {row.id} points to missing current_version_id={row.current_version_id}."
                ),
                document_id=row.id,
                version_id=row.current_version_id,
            )
            for row in missing_version_rows
        )

        return findings

    def _detect_non_active_documents_in_search(
        self,
        *,
        lifecycle_status: str,
        rule_id: str,
        title: str,
    ) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(
                Document.id.label("document_id"),
                Document.current_version_id.label("version_id"),
                Chunk.id.label("chunk_id"),
            )
            .join(Chunk, Chunk.document_id == Document.id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == lifecycle_status,
                or_(Chunk.is_searchable.is_(True), Chunk.search_vector.isnot(None)),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id=rule_id,
                title=title,
                description=(
                    f"Document {row.document_id} has lifecycle_status='{lifecycle_status}' but chunk {row.chunk_id} "
                    "is still present in the search surface."
                ),
                document_id=row.document_id,
                version_id=row.version_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

    def _detect_non_active_documents_in_retrieval(
        self,
        *,
        lifecycle_status: str,
        expected_source_status: str,
        rule_id: str,
        title: str,
    ) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(ChatCitation.id, ChatCitation.document_id, ChatCitation.chunk_id, ChatCitation.source_status)
            .join(ChatMessage, ChatMessage.id == ChatCitation.message_id)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(Document, Document.id == ChatCitation.document_id)
            .where(
                ChatSession.workspace_id == self._workspace_id,
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == lifecycle_status,
                ChatCitation.source_status != expected_source_status,
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id=rule_id,
                title=title,
                description=(
                    f"Citation {row.id} references {lifecycle_status} document {row.document_id} "
                    f"but source_status is '{row.source_status}'."
                ),
                document_id=row.document_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

    @staticmethod
    def _searchable_case():
        return case((Chunk.is_searchable.is_(True), 1), else_=0)

    @staticmethod
    def _finding(
        *,
        rule_id: str,
        title: str,
        description: str,
        document_id: Any,
        version_id: Any | None = None,
        chunk_id: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "finding_type": _FINDING_TYPE,
            "severity": _SEVERITY,
            "document_id": str(document_id) if document_id is not None else None,
            "version_id": str(version_id) if version_id is not None else None,
            "chunk_id": str(chunk_id) if chunk_id is not None else None,
            "title": title,
            "description": f"{rule_id}: {description}",
            "remediation": _REMEDIATION,
        }
