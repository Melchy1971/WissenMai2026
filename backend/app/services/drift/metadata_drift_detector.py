"""Metadata Drift Detector.

Checks (all read-only):
  1. Fehlende Kategorie      -- DocumentVersion.metadata_ has no 'category' key or value
  2. Fehlende Zusammenfassung -- DocumentVersion.metadata_ has no 'summary' key or value
  3. Inkonsistente Metadaten  -- version metadata keys differ between versions of the same doc

Entfernt am 2026-07-26: die Pruefung "Fehlender Titel". Sie meldete leere oder
reine Whitespace-Titel — genau das, was ck_documents_title_not_blank
(Migration 20260504_0006) ausschliesst. Auf PostgreSQL konnte sie nie ausloesen.

Finding type: METADATA_DRIFT
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentVersion
from app.services.drift_run_engine import BaseDriftDetector, FindingDTO

logger = logging.getLogger(__name__)

# Keys that must be present and non-empty in DocumentVersion.metadata_
REQUIRED_METADATA_KEYS = ("category", "summary")


class MetadataDriftDetector(BaseDriftDetector):
    """Detects missing and inconsistent metadata on Document and DocumentVersion records."""

    @property
    def name(self) -> str:
        return "MetadataDriftDetector"

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
            versions = (
                session.execute(
                    select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                )
                .scalars()
                .all()
            )

            for ver in versions:
                findings.extend(self._check_required_keys(doc, ver))

            if len(versions) > 1:
                findings.extend(self._check_key_consistency(doc, versions))

        logger.debug(
            "MetadataDriftDetector: workspace=%s docs=%d findings=%d",
            workspace_id,
            len(documents),
            len(findings),
        )
        return findings

    # ------------------------------------------------------------------
    # Check 1 + 2: Fehlende Kategorie / Zusammenfassung
    # ------------------------------------------------------------------

    def _check_required_keys(
        self, doc: Document, ver: DocumentVersion
    ) -> list[FindingDTO]:
        findings = []
        meta = ver.metadata_ or {}

        for key in REQUIRED_METADATA_KEYS:
            value = meta.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                findings.append(
                    FindingDTO(
                        finding_type="METADATA_DRIFT",
                        severity="warning",
                        entity_type="document_version",
                        entity_id=ver.id,
                        detail=_detail(
                            check=f"missing_{key}",
                            reason=f"DocumentVersion.metadata_['{key}'] is absent or empty",
                            document_id=doc.id,
                            version_id=ver.id,
                            version_number=ver.version_number,
                            key=key,
                            value_found=value,
                        ),
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Check 4: Inkonsistente Metadaten
    # ------------------------------------------------------------------

    def _check_key_consistency(
        self, doc: Document, versions: list[DocumentVersion]
    ) -> list[FindingDTO]:
        """Metadata key sets must be identical across all versions of a document."""
        key_sets: list[frozenset[str]] = []
        for ver in versions:
            meta = ver.metadata_ or {}
            key_sets.append(frozenset(meta.keys()))

        reference = key_sets[0]
        inconsistent_versions = []
        for ver, ks in zip(versions[1:], key_sets[1:], strict=False):
            if ks != reference:
                inconsistent_versions.append(
                    {
                        "version_id": ver.id,
                        "version_number": ver.version_number,
                        "keys": sorted(ks),
                        "missing_from_reference": sorted(reference - ks),
                        "extra_vs_reference": sorted(ks - reference),
                    }
                )

        if not inconsistent_versions:
            return []

        return [
            FindingDTO(
                finding_type="METADATA_DRIFT",
                severity="warning",
                entity_type="document",
                entity_id=doc.id,
                detail=_detail(
                    check="inconsistent_metadata",
                    reason="Metadata key sets differ across versions of the same document",
                    document_id=doc.id,
                    reference_version_id=versions[0].id,
                    reference_keys=sorted(reference),
                    inconsistent_versions=inconsistent_versions,
                ),
            )
        ]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _detail(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
