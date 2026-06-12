"""Document Drift Detector.

Checks (all read-only):
  1. Dokument vorhanden     — active+chunked document has current_version_id and chunks
  2. Version vorhanden      — current_version_id resolves to an existing DocumentVersion
  3. Chunkstruktur konsistent — current version's chunks are sequential without gaps
  4. Dokumentstatus konsistent — lifecycle_status matches audit timestamp fields

Finding type: DOCUMENT_DRIFT
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.documents import Chunk, Document, DocumentVersion
from app.services.drift_run_engine import BaseDriftDetector, FindingDTO

logger = logging.getLogger(__name__)


class DocumentDriftDetector(BaseDriftDetector):
    """Detects structural and status drift on Document records."""

    @property
    def name(self) -> str:
        return "DocumentDriftDetector"

    def detect(self, session: Session, workspace_id: str) -> list[FindingDTO]:
        findings: list[FindingDTO] = []
        documents = (
            session.execute(
                select(Document).where(Document.workspace_id == workspace_id)
            )
            .scalars()
            .all()
        )

        for doc in documents:
            findings.extend(self._check_document_present(session, doc))
            findings.extend(self._check_version_present(session, doc))
            findings.extend(self._check_chunk_structure(session, doc))
            findings.extend(self._check_status_consistent(doc))

        logger.debug(
            "DocumentDriftDetector: workspace=%s docs=%d findings=%d",
            workspace_id,
            len(documents),
            len(findings),
        )
        return findings

    # ------------------------------------------------------------------
    # Check 1: Dokument vorhanden
    # ------------------------------------------------------------------

    def _check_document_present(
        self, session: Session, doc: Document
    ) -> list[FindingDTO]:
        """An active+chunked document must have current_version_id and at least one chunk."""
        if doc.lifecycle_status != "active" or doc.import_status != "chunked":
            return []

        findings = []

        if doc.current_version_id is None:
            findings.append(
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="document_present",
                        reason="active+chunked document has no current_version_id",
                        document_id=doc.id,
                        lifecycle_status=doc.lifecycle_status,
                        import_status=doc.import_status,
                    ),
                )
            )

        chunk_count = session.execute(
            select(func.count()).where(Chunk.document_id == doc.id)
        ).scalar_one()

        if chunk_count == 0:
            findings.append(
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="document_present",
                        reason="active+chunked document has zero chunks",
                        document_id=doc.id,
                        lifecycle_status=doc.lifecycle_status,
                        import_status=doc.import_status,
                        chunk_count=0,
                    ),
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Check 2: Version vorhanden
    # ------------------------------------------------------------------

    def _check_version_present(
        self, session: Session, doc: Document
    ) -> list[FindingDTO]:
        """current_version_id must resolve to an existing DocumentVersion."""
        if doc.current_version_id is None:
            return []

        version = session.get(DocumentVersion, doc.current_version_id)
        if version is None:
            return [
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="version_present",
                        reason="current_version_id references a non-existent DocumentVersion",
                        document_id=doc.id,
                        current_version_id=doc.current_version_id,
                    ),
                )
            ]

        # Version exists but belongs to a different document
        if version.document_id != doc.id:
            return [
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="version_present",
                        reason="current_version_id references a version owned by a different document",
                        document_id=doc.id,
                        current_version_id=doc.current_version_id,
                        version_owner=version.document_id,
                    ),
                )
            ]

        return []

    # ------------------------------------------------------------------
    # Check 3: Chunkstruktur konsistent
    # ------------------------------------------------------------------

    def _check_chunk_structure(
        self, session: Session, doc: Document
    ) -> list[FindingDTO]:
        """Chunks for the current version must be sequential (0..n-1) without gaps."""
        if doc.current_version_id is None:
            return []
        if doc.import_status != "chunked":
            return []

        chunks = (
            session.execute(
                select(Chunk.chunk_index)
                .where(Chunk.document_version_id == doc.current_version_id)
                .order_by(Chunk.chunk_index)
            )
            .scalars()
            .all()
        )

        if not chunks:
            return []

        expected = list(range(len(chunks)))
        actual = list(chunks)
        if actual != expected:
            return [
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="warning",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="chunk_structure",
                        reason="chunk_index sequence is non-sequential or has gaps",
                        document_id=doc.id,
                        version_id=doc.current_version_id,
                        expected_indices=expected,
                        actual_indices=actual,
                    ),
                )
            ]

        return []

    # ------------------------------------------------------------------
    # Check 4: Dokumentstatus konsistent
    # ------------------------------------------------------------------

    def _check_status_consistent(self, doc: Document) -> list[FindingDTO]:
        """lifecycle_status must be consistent with archived_at / deleted_at fields."""
        findings = []
        status = doc.lifecycle_status

        if status == "archived" and doc.archived_at is None:
            findings.append(
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="warning",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="status_consistent",
                        reason="lifecycle_status=archived but archived_at is NULL",
                        document_id=doc.id,
                        lifecycle_status=status,
                    ),
                )
            )

        if status == "deleted" and doc.deleted_at is None:
            findings.append(
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="warning",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="status_consistent",
                        reason="lifecycle_status=deleted but deleted_at is NULL",
                        document_id=doc.id,
                        lifecycle_status=status,
                    ),
                )
            )

        if status == "active" and doc.deleted_at is not None:
            findings.append(
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="status_consistent",
                        reason="lifecycle_status=active but deleted_at is set",
                        document_id=doc.id,
                        lifecycle_status=status,
                        deleted_at=str(doc.deleted_at),
                    ),
                )
            )

        if status == "active" and doc.archived_at is not None:
            findings.append(
                FindingDTO(
                    finding_type="DOCUMENT_DRIFT",
                    severity="warning",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="status_consistent",
                        reason="lifecycle_status=active but archived_at is set",
                        document_id=doc.id,
                        lifecycle_status=status,
                        archived_at=str(doc.archived_at),
                    ),
                )
            )

        return findings


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _detail(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
