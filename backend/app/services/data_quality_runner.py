"""M5a Data Quality Runner.

Starts a DataQualityRun, executes the aktiven Detektoren, collects findings,
computes a quality_score, and closes the run.

Seit 2026-07-26 laufen vier statt acht Detektoren — Begruendung im Abschnitt
"Entfernte Detektoren" weiter unten.

Contracts:
- Read-only on document data — no mutations outside data_quality_* tables.
- Workspace-scoped — all queries and writes are filtered by workspace_id.
- Idempotent per run_id — re-invoking with an existing completed/failed run_id
  returns the stored result without re-running.
- Errors set run status to "failed" and propagate.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
UTC = timezone.utc
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.services.lifecycle_integrity_detector import LifecycleIntegrityDetector
from app.services.metadata_quality_detector import MetadataQualityDetector
from app.services.orphan_detector import OrphanObjectDetector
from app.services.quality_score import calculate_quality_score_from_findings
from app.services.source_status_integrity_detector import SourceStatusIntegrityDetector


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunResult:
    run_id: str
    workspace_id: str
    status: str           # completed | failed
    started_at: datetime
    finished_at: datetime
    total_findings: int
    quality_score: float
    findings: list[dict[str, Any]]
    score_explanation: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Detector protocol
# ---------------------------------------------------------------------------

class Detector(Protocol):
    """All detectors implement detect() → list of partial finding kwargs."""

    def detect(self) -> list[dict[str, Any]]:
        ...


# ---------------------------------------------------------------------------
# Entfernte Detektoren (2026-07-26)
# ---------------------------------------------------------------------------
#
# Fuenf der urspruenglich acht Detektoren konnten auf PostgreSQL nie ein Finding
# erzeugen. Vier davon pruefen Zustaende, die das Schema bereits ausschliesst,
# zwei waren nie ueber das Skelett hinausgekommen:
#
#   DuplicateDetector       -> uq_documents_workspace_content_hash (0005)
#   InvalidLifecycleDetector-> ck_documents_lifecycle_status_allowed (0006);
#                              die erlaubte Menge des Detektors war sogar weiter
#                              als die der DB (enthielt 'pending')
#   MissingMetadataDetector -> ck_documents_title_not_blank (0006); dritte Kopie
#                              derselben Titelpruefung neben MQ-1 und dem
#                              MetadataDriftDetector
#   OrphanChunkDetector     -> Skelett, detect() lieferte immer []
#   EmptyChunkDetector      -> Skelett, detect() lieferte immer [];
#                              ck_document_chunks_content_not_blank deckt es ab
#
# Konsequenz fuer den Quality Score: er wurde bisher aus acht Detektoren
# gebildet, von denen fuenf strukturell nie ausschlagen konnten.





# ---------------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------------

def _calculate_score(findings: list[dict[str, Any]]) -> float:
    return calculate_quality_score_from_findings(findings).score


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class DataQualityRunner:
    """Orchestrates a data quality run for one workspace.

    Usage::

        runner = DataQualityRunner.from_session(session, workspace_id="...")
        result = runner.run()
    """

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id

    @classmethod
    def from_session(cls, session: Session, workspace_id: str) -> "DataQualityRunner":
        return cls(session, workspace_id)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        *,
        run_id: str | None = None,
        created_by: str | None = None,
    ) -> RunResult:
        """Execute a data quality run.

        If run_id already exists and is completed or failed, returns the
        stored result without re-running (idempotency).

        Raises ValueError if run_id is already in status 'running'.
        """
        resolved_id = run_id or str(uuid.uuid4())
        existing = self._load_existing(resolved_id)
        if existing is not None:
            return existing

        run = self._create_run(resolved_id, created_by)
        try:
            findings_data = self._execute_detectors()
            score_result = calculate_quality_score_from_findings(findings_data)
            self._persist_findings(run, findings_data)
            return self._complete_run(run, findings_data, score_result.score, score_result.score_explanation)
        except Exception:
            self._fail_run(run)
            raise

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_existing(self, run_id: str) -> RunResult | None:
        row = self._session.get(DataQualityRun, run_id)
        if row is None:
            return None
        if row.status == "running":
            raise ValueError(
                f"Run {run_id} is already in status 'running'. "
                "Wait for it to finish or use a new run_id."
            )
        findings = [
            self._finding_to_dict(f) for f in row.findings
        ]
        score_result = calculate_quality_score_from_findings(findings)
        return RunResult(
            run_id=row.id,
            workspace_id=row.workspace_id,
            status=row.status,
            started_at=row.started_at,
            finished_at=row.finished_at,
            total_findings=row.total_findings or 0,
            quality_score=row.quality_score or 0.0,
            findings=findings,
            score_explanation=score_result.score_explanation,
        )

    def _create_run(self, run_id: str, created_by: str | None) -> DataQualityRun:
        now = datetime.now(UTC)
        run = DataQualityRun(
            id=run_id,
            workspace_id=self._workspace_id,
            status="running",
            started_at=now,
            created_by=created_by,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def _execute_detectors(self) -> list[dict[str, Any]]:
        # DuplicateDetector entfernt (2026-07-26). Er suchte innerhalb eines
        # Workspace nach mehreren aktiven Dokumenten mit gleichem content_hash.
        # Genau das schliesst uq_documents_workspace_content_hash (Migration
        # 20260504_0005) aus; der Import-Pfad meldet Kollisionen bereits beim
        # Anlegen als DUPLICATE_DOCUMENT (import_status='duplicate'). Der
        # Detektor konnte auf PostgreSQL nie ein Finding erzeugen.
        detectors: list[Detector] = [
            MetadataQualityDetector(self._session, self._workspace_id),
            LifecycleIntegrityDetector(self._session, self._workspace_id),
            SourceStatusIntegrityDetector(self._session, self._workspace_id),
            OrphanObjectDetector(self._session, self._workspace_id),
        ]
        findings: list[dict[str, Any]] = []
        for detector in detectors:
            findings.extend(detector.detect())
        return findings

    def _persist_findings(
        self,
        run: DataQualityRun,
        findings_data: list[dict[str, Any]],
    ) -> None:
        now = datetime.now(UTC)
        for f in findings_data:
            finding = DataQualityFinding(
                id=str(uuid.uuid4()),
                run_id=run.id,
                workspace_id=self._workspace_id,
                finding_type=f["finding_type"],
                severity=f["severity"],
                document_id=f.get("document_id"),
                version_id=f.get("version_id"),
                chunk_id=f.get("chunk_id"),
                title=f["title"],
                description=f["description"],
                remediation=f["remediation"],
                created_at=now,
            )
            self._session.add(finding)
        self._session.flush()

    def _complete_run(
        self,
        run: DataQualityRun,
        findings_data: list[dict[str, Any]],
        score: float,
        score_explanation: dict[str, Any],
    ) -> RunResult:
        now = datetime.now(UTC)
        run.status = "completed"
        run.finished_at = now
        run.total_findings = len(findings_data)
        run.quality_score = score
        self._session.flush()
        return RunResult(
            run_id=run.id,
            workspace_id=run.workspace_id,
            status="completed",
            started_at=run.started_at,
            finished_at=now,
            total_findings=len(findings_data),
            quality_score=score,
            findings=findings_data,
            score_explanation=score_explanation,
        )

    def _fail_run(self, run: DataQualityRun) -> None:
        run.status = "failed"
        run.finished_at = datetime.now(UTC)
        self._session.flush()

    @staticmethod
    def _finding_to_dict(f: DataQualityFinding) -> dict[str, Any]:
        return {
            "id": f.id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "document_id": f.document_id,
            "version_id": f.version_id,
            "chunk_id": f.chunk_id,
            "title": f.title,
            "description": f.description,
            "remediation": f.remediation,
            "created_at": f.created_at.isoformat(),
        }
