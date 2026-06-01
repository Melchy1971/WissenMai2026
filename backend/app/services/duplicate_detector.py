"""Duplicate Detector V1.

Detects documents within a workspace that share the same content_hash.
Only active documents are considered (lifecycle_status = 'active').

Contracts:
- Read-only: no document mutations, no deletions, no merges,
  no lifecycle_status changes.
- Returns one Finding per duplicate document (all members of each
  duplicate group), identified by document_id.
- Finding type:  DUPLICATE_DOCUMENT
- Severity:      warning
- Remediation:   "Dokumente prüfen und ggf. zusammenführen"
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.documents import Document

_FINDING_TYPE = "DUPLICATE_DOCUMENT"
_SEVERITY = "warning"
_REMEDIATION = "Dokumente prüfen und ggf. zusammenführen"
_ACTIVE_STATUS = "active"


class DuplicateDetector:
    """Detects content_hash duplicates among active workspace documents.

    Usage::

        detector = DuplicateDetector(session, workspace_id="...")
        findings = detector.detect()  # list[dict] — partial finding kwargs
    """

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id

    def detect(self) -> list[dict[str, Any]]:
        """Return one finding dict per duplicate document.

        For each content_hash shared by ≥ 2 active documents in the
        workspace, every member of the group receives a finding.
        The description references all sibling IDs in the group.
        """
        groups = self._find_duplicate_groups()
        findings: list[dict[str, Any]] = []
        for content_hash, doc_ids in groups.items():
            siblings = sorted(doc_ids)
            for doc_id in siblings:
                others = [d for d in siblings if d != doc_id]
                findings.append(
                    self._make_finding(doc_id, content_hash, others)
                )
        return findings

    # ── Internal ──────────────────────────────────────────────────────────────

    def _find_duplicate_groups(self) -> dict[str, list[str]]:
        """Query: active docs grouped by content_hash, groups with count > 1.

        Two-step approach for DB compatibility (PostgreSQL + SQLite):
        1. Find content_hash values shared by ≥ 2 active documents.
        2. Fetch all doc IDs for each such hash.
        """
        dup_hashes = self._session.scalars(
            select(Document.content_hash)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == _ACTIVE_STATUS,
                Document.content_hash.isnot(None),
                func.trim(Document.content_hash) != "",
            )
            .group_by(Document.content_hash)
            .having(func.count(Document.id) > 1)
        ).all()

        if not dup_hashes:
            return {}

        groups: dict[str, list[str]] = {}
        for content_hash in dup_hashes:
            doc_ids = self._session.scalars(
                select(Document.id)
                .where(
                    Document.workspace_id == self._workspace_id,
                    Document.lifecycle_status == _ACTIVE_STATUS,
                    Document.content_hash == content_hash,
                )
                .order_by(Document.created_at)
            ).all()
            groups[content_hash] = list(doc_ids)
        return groups

    def _make_finding(
        self,
        doc_id: str,
        content_hash: str,
        sibling_ids: list[str],
    ) -> dict[str, Any]:
        sibling_str = ", ".join(sibling_ids) if sibling_ids else "—"
        return {
            "finding_type": _FINDING_TYPE,
            "severity": _SEVERITY,
            "document_id": doc_id,
            "version_id": None,
            "chunk_id": None,
            "title": "Duplikat: gleicher content_hash",
            "description": (
                f"Dokument {doc_id} teilt content_hash '{content_hash}' "
                f"mit: {sibling_str}. "
                f"Nur aktive Dokumente werden berücksichtigt."
            ),
            "remediation": _REMEDIATION,
        }
