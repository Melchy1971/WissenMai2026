"""M5a Orphan Object Detector.

Reports orphaned data-quality and document objects.

Contract:
- report only; no automatic repair
- severity: warning
- document chunk/version orphans are global because those rows do not carry workspace_id
- citation/finding/metric checks are workspace-scoped when their rows expose workspace_id
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, or_, select, text
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.models.documents import ChatCitation, ChatMessage, ChatSession, Chunk, Document, DocumentVersion


_SEVERITY = "warning"
_REMEDIATION = "Nur melden. Keine automatische Reparatur."


@dataclass(frozen=True)
class OrphanObjectDetectorConfig:
    max_rows_per_rule: int = 500


class OrphanObjectDetector:
    def __init__(
        self,
        session: Session,
        workspace_id: str,
        config: OrphanObjectDetectorConfig | None = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._config = config or OrphanObjectDetectorConfig()

    def detect(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        findings.extend(self._detect_chunks_without_document())
        findings.extend(self._detect_versions_without_document())
        findings.extend(self._detect_citations_without_source())
        findings.extend(self._detect_findings_without_run())
        findings.extend(self._detect_metrics_without_snapshot())
        return findings

    def _detect_chunks_without_document(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(Chunk.id, Chunk.document_id, Chunk.document_version_id)
            .outerjoin(Document, Document.id == Chunk.document_id)
            .where(Document.id.is_(None))
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                finding_type="ORPHAN_CHUNK",
                title="Chunk without document",
                description=(
                    f"Chunk {row.id} references missing document_id={row.document_id}."
                ),
                document_id=row.document_id,
                version_id=row.document_version_id,
                chunk_id=row.id,
            )
            for row in rows
        ]

    def _detect_versions_without_document(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(DocumentVersion.id, DocumentVersion.document_id)
            .outerjoin(Document, Document.id == DocumentVersion.document_id)
            .where(Document.id.is_(None))
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                finding_type="ORPHAN_VERSION",
                title="Version without document",
                description=(
                    f"DocumentVersion {row.id} references missing document_id={row.document_id}."
                ),
                document_id=row.document_id,
                version_id=row.id,
            )
            for row in rows
        ]

    def _detect_citations_without_source(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(
                ChatCitation.id.label("citation_id"),
                ChatCitation.document_id,
                ChatCitation.chunk_id,
                Document.id.label("live_document_id"),
                Chunk.id.label("live_chunk_id"),
            )
            .join(ChatMessage, ChatMessage.id == ChatCitation.message_id)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .outerjoin(Document, Document.id == ChatCitation.document_id)
            .outerjoin(Chunk, Chunk.id == ChatCitation.chunk_id)
            .where(
                ChatSession.workspace_id == self._workspace_id,
                or_(
                    Document.id.is_(None),
                    ChatCitation.chunk_id.isnot(None) & Chunk.id.is_(None),
                ),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                finding_type="ORPHAN_CITATION",
                title="Citation without source",
                description=(
                    f"Citation {row.citation_id} references document_id={row.document_id} "
                    f"and chunk_id={row.chunk_id}, but at least one source row is missing."
                ),
                document_id=row.document_id,
                chunk_id=row.chunk_id,
            )
            for row in rows
        ]

    def _detect_findings_without_run(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(DataQualityFinding.id, DataQualityFinding.run_id, DataQualityFinding.document_id)
            .outerjoin(DataQualityRun, DataQualityRun.id == DataQualityFinding.run_id)
            .where(
                DataQualityFinding.workspace_id == self._workspace_id,
                DataQualityRun.id.is_(None),
            )
            .limit(self._config.max_rows_per_rule)
        ).all()

        return [
            self._finding(
                finding_type="ORPHAN_FINDING",
                title="Finding without run",
                description=(
                    f"DataQualityFinding {row.id} references missing run_id={row.run_id}."
                ),
                document_id=row.document_id,
            )
            for row in rows
        ]

    def _detect_metrics_without_snapshot(self) -> list[dict[str, Any]]:
        inspector = inspect(self._session.connection())
        tables = set(inspector.get_table_names())
        if "data_quality_metrics" not in tables or "data_quality_snapshots" not in tables:
            return []

        metric_columns = {col["name"] for col in inspector.get_columns("data_quality_metrics")}
        snapshot_columns = {col["name"] for col in inspector.get_columns("data_quality_snapshots")}
        if "snapshot_id" not in metric_columns or "id" not in snapshot_columns:
            return []

        filters = ["s.id IS NULL"]
        params: dict[str, Any] = {"limit": self._config.max_rows_per_rule}
        if "workspace_id" in metric_columns:
            filters.append("m.workspace_id = :workspace_id")
            params["workspace_id"] = self._workspace_id

        rows = self._session.execute(
            text(
                "SELECT m.id AS metric_id, m.snapshot_id AS snapshot_id "
                "FROM data_quality_metrics m "
                "LEFT JOIN data_quality_snapshots s ON s.id = m.snapshot_id "
                f"WHERE {' AND '.join(filters)} "
                "LIMIT :limit"
            ),
            params,
        ).mappings().all()

        return [
            self._finding(
                finding_type="ORPHAN_FINDING",
                title="Metric without snapshot",
                description=(
                    f"DataQualityMetric {row['metric_id']} references missing "
                    f"snapshot_id={row['snapshot_id']}."
                ),
            )
            for row in rows
        ]

    @staticmethod
    def _finding(
        *,
        finding_type: str,
        title: str,
        description: str,
        document_id: Any | None = None,
        version_id: Any | None = None,
        chunk_id: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "finding_type": finding_type,
            "severity": _SEVERITY,
            "document_id": str(document_id) if document_id is not None else None,
            "version_id": str(version_id) if version_id is not None else None,
            "chunk_id": str(chunk_id) if chunk_id is not None else None,
            "title": title,
            "description": description,
            "remediation": _REMEDIATION,
        }
