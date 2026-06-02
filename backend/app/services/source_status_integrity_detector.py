"""M5a Source Status Integrity Detector.

Detects stored citation source_status drift and retrieval-surface conflicts.

Contract:
- read-only: no document, chunk, or citation mutation
- workspace-scoped via chat_sessions.workspace_id
- finding_type: INVALID_SOURCE_STATUS
- severity: error
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.documents import ChatCitation, ChatMessage, ChatSession, Chunk, Document


_FINDING_TYPE = "INVALID_SOURCE_STATUS"
_SEVERITY = "error"
_REMEDIATION = "Source-Status korrigieren"
_ACTIVE = "active"
_ARCHIVED = "archived"
_DELETED = "deleted"
_MISSING = "missing"
_READABLE_IMPORT_STATUSES = ("parsed", "chunked")


@dataclass(frozen=True)
class SourceStatusIntegrityConfig:
    max_rows_per_rule: int = 500


class SourceStatusIntegrityDetector:
    def __init__(
        self,
        session: Session,
        workspace_id: str,
        config: SourceStatusIntegrityConfig | None = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._config = config or SourceStatusIntegrityConfig()

    def detect(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        findings.extend(self._detect_live_source_status_mismatches())
        findings.extend(self._detect_historical_source_mismatches())
        findings.extend(self._detect_citation_chunk_mismatches())
        findings.extend(self._detect_active_source_retrieval_violations())
        findings.extend(self._detect_non_active_source_retrieval_violations())
        return findings

    def _detect_live_source_status_mismatches(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            self._base_select()
            .where(
                ChatSession.workspace_id == self._workspace_id,
                Document.workspace_id == self._workspace_id,
                ChatCitation.chunk_id.isnot(None),
                Document.lifecycle_status.in_((_ACTIVE, _ARCHIVED, _DELETED)),
                ChatCitation.source_status != Document.lifecycle_status,
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        findings: list[dict[str, Any]] = []
        for row in rows:
            title = {
                _ACTIVE: "Active source status mismatch",
                _ARCHIVED: "Archived source status mismatch",
                _DELETED: "Deleted source status mismatch",
            }.get(row.lifecycle_status, "Citation source status mismatch")
            findings.append(
                self._finding(
                    rule_id="SSI-1",
                    title=title,
                    description=(
                        f"Citation {row.citation_id} stores source_status='{row.source_status}' "
                        f"but document {row.document_id} has lifecycle_status='{row.lifecycle_status}'."
                    ),
                    document_id=row.document_id,
                    chunk_id=row.chunk_id,
                )
            )
        return findings

    def _detect_historical_source_mismatches(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            self._base_select()
            .where(
                ChatSession.workspace_id == self._workspace_id,
                ChatCitation.chunk_id.is_(None),
                ChatCitation.source_status != _MISSING,
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id="SSI-4",
                title="Historical source missing marker mismatch",
                description=(
                    f"Citation {row.citation_id} has no live chunk reference but "
                    f"source_status='{row.source_status}', expected '{_MISSING}'."
                ),
                document_id=row.document_id,
            )
            for row in rows
        ]

    def _detect_citation_chunk_mismatches(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            self._base_select()
            .where(
                ChatSession.workspace_id == self._workspace_id,
                Document.workspace_id == self._workspace_id,
                Chunk.id.isnot(None),
                Chunk.document_id != ChatCitation.document_id,
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id="SSI-5",
                title="Citation chunk document mismatch",
                description=(
                    f"Citation {row.citation_id} references document {row.document_id} "
                    f"but chunk {row.chunk_id} belongs to document {row.chunk_document_id}."
                ),
                document_id=row.document_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

    def _detect_active_source_retrieval_violations(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            self._base_select()
            .where(
                ChatSession.workspace_id == self._workspace_id,
                Document.workspace_id == self._workspace_id,
                ChatCitation.source_status == _ACTIVE,
                ChatCitation.chunk_id.isnot(None),
                Document.lifecycle_status == _ACTIVE,
                or_(
                    Document.import_status.notin_(_READABLE_IMPORT_STATUSES),
                    Chunk.id.is_(None),
                    Chunk.document_id != ChatCitation.document_id,
                    Chunk.is_searchable.is_(False),
                ),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id="SSI-6",
                title="Active source not retrievable",
                description=(
                    f"Citation {row.citation_id} is marked active but its retrieval source is not "
                    "an active readable searchable source."
                ),
                document_id=row.document_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

    def _detect_non_active_source_retrieval_violations(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            self._base_select()
            .where(
                ChatSession.workspace_id == self._workspace_id,
                Document.workspace_id == self._workspace_id,
                Chunk.id.isnot(None),
                ChatCitation.source_status.in_((_ARCHIVED, _DELETED, _MISSING)),
                Document.lifecycle_status.in_((_ARCHIVED, _DELETED)),
                Chunk.document_id == ChatCitation.document_id,
                Chunk.is_searchable.is_(True),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                rule_id="SSI-6",
                title="Non-active source remains retrievable",
                description=(
                    f"Citation {row.citation_id} is marked source_status='{row.source_status}' "
                    "but still points to an active searchable retrieval source."
                ),
                document_id=row.document_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

    @staticmethod
    def _base_select():
        return (
            select(
                ChatCitation.id.label("citation_id"),
                ChatCitation.document_id.label("document_id"),
                ChatCitation.chunk_id.label("chunk_id"),
                ChatCitation.source_status.label("source_status"),
                Document.lifecycle_status.label("lifecycle_status"),
                Document.import_status.label("import_status"),
                Chunk.document_id.label("chunk_document_id"),
                Chunk.is_searchable.label("is_searchable"),
            )
            .join(ChatMessage, ChatMessage.id == ChatCitation.message_id)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .outerjoin(Document, Document.id == ChatCitation.document_id)
            .outerjoin(Chunk, Chunk.id == ChatCitation.chunk_id)
        )

    @staticmethod
    def _finding(
        *,
        rule_id: str,
        title: str,
        description: str,
        document_id: Any,
        chunk_id: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "finding_type": _FINDING_TYPE,
            "severity": _SEVERITY,
            "document_id": str(document_id) if document_id is not None else None,
            "version_id": None,
            "chunk_id": str(chunk_id) if chunk_id is not None else None,
            "title": title,
            "description": f"{rule_id}: {description}",
            "remediation": _REMEDIATION,
        }
