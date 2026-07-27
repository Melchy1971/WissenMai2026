"""Metadata Quality Detector — M5a Slice 2.

Erkennt Dokumente mit fehlenden oder leeren Pflichtmetadaten.

Regeln:
  MQ-2  metadata["tags"] fehlt oder leer           → MISSING_METADATA  warning
  MQ-3  metadata["category"] fehlt oder leer       → MISSING_METADATA  warning
  MQ-4  metadata["doc_type"] fehlt oder leer       → MISSING_METADATA  warning
  MQ-5  metadata["summary"] fehlt oder leer        → MISSING_METADATA  info

Contracts:
- Read-only. Keine Mutations.
- Workspace-scoped. Nur aktive Dokumente (lifecycle_status='active').
- Dokumente ohne current_version_id werden für MQ-2..5 übersprungen.
- Limit je Regel konfigurierbar (default: 500).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentVersion

_FINDING_TYPE = "MISSING_METADATA"
_ACTIVE_STATUS = "active"
_DEFAULT_LIMIT = 500


@dataclass(frozen=True)
class MetadataQualityConfig:
    limit_per_rule: int = _DEFAULT_LIMIT


# ---------------------------------------------------------------------------
# Internal rule descriptors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _MetadataRule:
    id: str
    key: str            # Schluessel in DocumentVersion.metadata_
    severity: str
    title: str
    description_tmpl: str  # {doc_id} and optionally {key} are substituted
    remediation: str


# MQ-1 (leerer Dokumenttitel) wurde am 2026-07-26 entfernt, siehe Kommentar an
# der Stelle von _check_title(). Die Regel ist durch ck_documents_title_not_blank
# abgedeckt und konnte auf PostgreSQL nie ausloesen.
_RULES: tuple[_MetadataRule, ...] = (
    _MetadataRule(
        id="MQ-2",
        key="tags",
        severity="warning",
        title="Fehlende Tags",
        description_tmpl=(
            "Dokument {doc_id} (Version {version_id}) hat kein 'tags'-Feld "
            "in den Versions-Metadaten oder das Feld ist leer."
        ),
        remediation="Tags in den Dokumentmetadaten ergaenzen. Keine automatische Befuellung.",
    ),
    _MetadataRule(
        id="MQ-3",
        key="category",
        severity="warning",
        title="Fehlende Kategorie",
        description_tmpl=(
            "Dokument {doc_id} (Version {version_id}) hat kein 'category'-Feld "
            "in den Versions-Metadaten oder das Feld ist leer."
        ),
        remediation="Kategorie in den Dokumentmetadaten ergaenzen. Keine automatische Befuellung.",
    ),
    _MetadataRule(
        id="MQ-4",
        key="doc_type",
        severity="warning",
        title="Fehlender Dokumenttyp",
        description_tmpl=(
            "Dokument {doc_id} (Version {version_id}) hat kein 'doc_type'-Feld "
            "in den Versions-Metadaten oder das Feld ist leer."
        ),
        remediation="Dokumenttyp in den Metadaten ergaenzen. Keine automatische Befuellung.",
    ),
    _MetadataRule(
        id="MQ-5",
        key="summary",
        severity="info",
        title="Fehlende Zusammenfassung",
        description_tmpl=(
            "Dokument {doc_id} (Version {version_id}) hat kein 'summary'-Feld "
            "in den Versions-Metadaten oder das Feld ist leer."
        ),
        remediation="Zusammenfassung in den Metadaten ergaenzen. Keine automatische Befuellung.",
    ),
)


def _is_empty(value: Any) -> bool:
    """True wenn Wert fehlt, None, leerer String, leere Liste oder leeres Dict."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class MetadataQualityDetector:
    """Erkennt fehlende Pflichtmetadaten in aktiven Dokumenten.

    Usage::

        detector = MetadataQualityDetector(session, workspace_id="...")
        findings = detector.detect()  # list[dict] — partial finding kwargs
    """

    def __init__(
        self,
        session: Session,
        workspace_id: str,
        config: MetadataQualityConfig | None = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._config = config or MetadataQualityConfig()

    def detect(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        findings.extend(self._check_version_metadata())
        return findings

    # ── MQ-1 entfernt (2026-07-26) ───────────────────────────────────────────
    #
    # Die Regel meldete leere oder reine Whitespace-Titel. Genau das verbietet
    # ck_documents_title_not_blank (Migration 20260504_0006, "length(trim(title)) > 0").
    # Auf PostgreSQL konnte die Regel nie ein Finding erzeugen; sie war nur in der
    # SQLite-Testbasis sichtbar, weil dort die Constraints fehlten.

    # ── MQ-2..5: version metadata keys ───────────────────────────────────────

    def _check_version_metadata(self) -> list[dict[str, Any]]:
        # Fetch active docs that have a current_version_id (skip NULL)
        rows = self._session.execute(
            select(Document.id, Document.current_version_id)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status == _ACTIVE_STATUS,
                Document.current_version_id.isnot(None),
            )
            .limit(self._config.limit_per_rule)
        ).all()

        if not rows:
            return []

        # Load versions in bulk
        version_ids = [r[1] for r in rows]
        versions: dict[str, DocumentVersion] = {}
        for vid in version_ids:
            v = self._session.get(DocumentVersion, vid)
            if v is not None:
                versions[vid] = v

        findings: list[dict[str, Any]] = []
        for doc_id, version_id in rows:
            if version_id not in versions:
                continue
            version = versions[version_id]
            metadata = version.metadata_ or {}

            for rule in _RULES:  # MQ-2..5
                if _is_empty(metadata.get(rule.key)):
                    findings.append(self._make_finding(
                        rule=rule,
                        doc_id=str(doc_id),
                        version_id=str(version_id),
                    ))

        return findings

    # ── Builder ───────────────────────────────────────────────────────────────

    def _make_finding(
        self,
        rule: _MetadataRule,
        doc_id: str,
        version_id: str | None,
    ) -> dict[str, Any]:
        description = rule.description_tmpl.format(
            doc_id=doc_id,
            version_id=version_id or "—",
            key=rule.key,
        )
        return {
            "finding_type": _FINDING_TYPE,
            "severity": rule.severity,
            "document_id": doc_id,
            "version_id": version_id,
            "chunk_id": None,
            "title": rule.title,
            "description": description,
            "remediation": rule.remediation,
        }
