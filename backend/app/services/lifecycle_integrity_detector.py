"""Lifecycle Integrity Detector - M5a Slice 3.

Detects lifecycle/search/retrieval inconsistencies for one workspace.

Rules:
  LI-1 archived documents must not remain searchable
  LI-2 deleted documents must not remain searchable
  LI-3 active documents with chunks should remain retrievable
  LI-4 archived/deleted chunks must not appear in retrieval surface
  LI-5 chat citation source_status must match current document lifecycle_status

Contracts:
- Read-only: no document/chunk/citation mutation.
- Workspace-scoped.
- Returns list[dict] compatible with DataQualityRunner findings shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.documents import ChatCitation, ChatMessage, ChatSession, Chunk, Document


_FINDING_RETRIEVAL = "RETRIEVAL_RISK"
_FINDING_SOURCE_STATUS = "INVALID_SOURCE_STATUS"


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
        findings.extend(self._detect_non_active_searchable_chunks())
        findings.extend(self._detect_active_not_retrievable_documents())
        findings.extend(self._detect_source_status_drift())
        return findings

    def _detect_non_active_searchable_chunks(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(Document.id, Document.lifecycle_status, Chunk.id)
            .join(Chunk, Chunk.document_id == Document.id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status.in_(("archived", "deleted")),
                Chunk.is_searchable.is_(True),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        findings: list[dict[str, Any]] = []
        for doc_id, lifecycle_status, chunk_id in rows:
            status = str(lifecycle_status)
            findings.append(
                {
                    "finding_type": _FINDING_RETRIEVAL,
                    "severity": "error",
                    "document_id": str(doc_id),
                    "version_id": None,
                    "chunk_id": str(chunk_id),
                    "title": f"{status.title()} document remains searchable",
                    "description": (
                        f"Document {doc_id} has lifecycle_status='{status}' but chunk {chunk_id} "
                        "is still marked searchable."
                    ),
                    "remediation": (
                        "Set chunk is_searchable=false for non-active documents and verify index state."
                    ),
                }
            )
        return findings

    def _detect_active_not_retrievable_documents(self) -> list[dict[str, Any]]:
        searchable_chunks = func.sum(case((Chunk.is_searchable.is_(True), 1), else_=0))

        rows = self._session.execute(
            select(Document.id, func.count(Chunk.id).label("chunk_count"), searchable_chunks.label("searchable_count"))
            .join(Chunk, Chunk.document_id == Document.id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == "active",
            )
            .group_by(Document.id)
            .having(and_(func.count(Chunk.id) > 0, searchable_chunks == 0))
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            {
                "finding_type": _FINDING_RETRIEVAL,
                "severity": "warning",
                "document_id": str(row.id),
                "version_id": None,
                "chunk_id": None,
                "title": "Active document not retrievable",
                "description": (
                    f"Active document {row.id} has {int(row.chunk_count)} chunks but none searchable."
                ),
                "remediation": (
                    "Reconcile chunk searchability for active documents and re-run search index checks."
                ),
            }
            for row in rows
        ]

    def _detect_source_status_drift(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
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

        return [
            {
                "finding_type": _FINDING_SOURCE_STATUS,
                "severity": "warning",
                "document_id": str(row.document_id),
                "version_id": None,
                "chunk_id": None,
                "title": "Citation source_status drift",
                "description": (
                    f"Citation {row.id} stores source_status='{row.source_status}' "
                    f"but document lifecycle_status is '{row.lifecycle_status}'."
                ),
                "remediation": (
                    "Resync citation source_status with document lifecycle transitions."
                ),
            }
            for row in rows
        ]
