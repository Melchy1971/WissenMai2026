"""Lifecycle Drift Detector.

Checks (all read-only):
  1. active auffindbar      -- active document with import_status=chunked has at least one
                               searchable chunk (is_searchable=True)
  2. archived nicht auffindbar -- archived document has no searchable chunks
  3. deleted nicht auffindbar  -- deleted document has no searchable chunks

Finding type: LIFECYCLE_DRIFT

Rationale: a document's lifecycle_status must be reflected in its search index exposure.
  - active+chunked    -> at least one chunk must be searchable
  - archived/deleted  -> zero chunks must be searchable
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.documents import Chunk, Document
from app.services.drift_run_engine import BaseDriftDetector, FindingDTO

logger = logging.getLogger(__name__)


class LifecycleDriftDetector(BaseDriftDetector):
    """Detects mismatches between lifecycle_status and search index exposure (is_searchable)."""

    @property
    def name(self) -> str:
        return "LifecycleDriftDetector"

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
            findings.extend(self._check_active_findable(session, doc))
            findings.extend(self._check_archived_not_findable(session, doc))
            findings.extend(self._check_deleted_not_findable(session, doc))

        logger.debug(
            "LifecycleDriftDetector: workspace=%s docs=%d findings=%d",
            workspace_id,
            len(documents),
            len(findings),
        )
        return findings

    # ------------------------------------------------------------------
    # Check 1: active auffindbar
    # ------------------------------------------------------------------

    def _check_active_findable(self, session: Session, doc: Document) -> list[FindingDTO]:
        """active+chunked documents must have at least one searchable chunk."""
        if doc.lifecycle_status != "active" or doc.import_status != "chunked":
            return []

        searchable_count = session.execute(
            select(func.count()).where(
                Chunk.document_id == doc.id,
                Chunk.is_searchable.is_(True),
            )
        ).scalar_one()

        if searchable_count == 0:
            return [
                FindingDTO(
                    finding_type="LIFECYCLE_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="active_findable",
                        reason="active+chunked document has zero searchable chunks",
                        document_id=doc.id,
                        lifecycle_status=doc.lifecycle_status,
                        import_status=doc.import_status,
                        searchable_chunk_count=0,
                    ),
                )
            ]

        return []

    # ------------------------------------------------------------------
    # Check 2: archived nicht auffindbar
    # ------------------------------------------------------------------

    def _check_archived_not_findable(
        self, session: Session, doc: Document
    ) -> list[FindingDTO]:
        """archived documents must have zero searchable chunks."""
        if doc.lifecycle_status != "archived":
            return []

        searchable_count = session.execute(
            select(func.count()).where(
                Chunk.document_id == doc.id,
                Chunk.is_searchable.is_(True),
            )
        ).scalar_one()

        if searchable_count > 0:
            return [
                FindingDTO(
                    finding_type="LIFECYCLE_DRIFT",
                    severity="error",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="archived_not_findable",
                        reason="archived document still has searchable chunks",
                        document_id=doc.id,
                        lifecycle_status=doc.lifecycle_status,
                        searchable_chunk_count=searchable_count,
                    ),
                )
            ]

        return []

    # ------------------------------------------------------------------
    # Check 3: deleted nicht auffindbar
    # ------------------------------------------------------------------

    def _check_deleted_not_findable(
        self, session: Session, doc: Document
    ) -> list[FindingDTO]:
        """deleted documents must have zero searchable chunks."""
        if doc.lifecycle_status != "deleted":
            return []

        searchable_count = session.execute(
            select(func.count()).where(
                Chunk.document_id == doc.id,
                Chunk.is_searchable.is_(True),
            )
        ).scalar_one()

        if searchable_count > 0:
            return [
                FindingDTO(
                    finding_type="LIFECYCLE_DRIFT",
                    severity="critical",
                    entity_type="document",
                    entity_id=doc.id,
                    detail=_detail(
                        check="deleted_not_findable",
                        reason="deleted document still has searchable chunks",
                        document_id=doc.id,
                        lifecycle_status=doc.lifecycle_status,
                        searchable_chunk_count=searchable_count,
                    ),
                )
            ]

        return []


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _detail(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
