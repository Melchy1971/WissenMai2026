"""M5a Data Quality Runner.

Starts a DataQualityRun, executes skeleton detectors, collects findings,
computes a placeholder quality_score, and closes the run.

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

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityFinding, DataQualityRun
from app.models.documents import Chunk, Document, DocumentVersion
from app.services.duplicate_detector import DuplicateDetector
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
# Skeleton detectors
# ---------------------------------------------------------------------------

class OrphanChunkDetector:
    """Chunks whose document_id has no matching row in documents."""

    _FINDING_TYPE = "ORPHAN_CHUNK"
    _SEVERITY = "error"

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id

    def detect(self) -> list[dict[str, Any]]:
        # Skeleton: full cross-join deferred to M5a detector slice.
        # PostgreSQL-specific query (IS DISTINCT FROM) omitted intentionally.
        return []  # TODO: implement full cross-join in M5a slice


class EmptyChunkDetector:
    """Chunks with empty or whitespace-only content."""

    _FINDING_TYPE = "EMPTY_CHUNK"
    _SEVERITY = "warning"

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id

    def detect(self) -> list[dict[str, Any]]:
        # Skeleton: workspace join requires document → version → chunk.
        # Full implementation deferred to dedicated slice.
        return []  # TODO


class InvalidLifecycleDetector:
    """Documents with lifecycle_status outside the allowed set."""

    _ALLOWED = frozenset({"active", "archived", "deleted", "pending"})
    _FINDING_TYPE = "INVALID_LIFECYCLE"
    _SEVERITY = "error"

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id

    def detect(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(Document.id, Document.lifecycle_status)
            .where(
                Document.workspace_id == self._workspace_id,
                Document.lifecycle_status.notin_(list(self._ALLOWED)),
            )
            .limit(200)
        ).all()
        return [
            {
                "finding_type": self._FINDING_TYPE,
                "severity": self._SEVERITY,
                "document_id": str(row.id),
                "version_id": None,
                "chunk_id": None,
                "title": "Invalid lifecycle_status",
                "description": (
                    f"Document {row.id} has lifecycle_status='{row.lifecycle_status}', "
                    f"which is not in {sorted(self._ALLOWED)}."
                ),
                "remediation": (
                    "Inspect document and correct lifecycle_status. "
                    "No automated repair — manual review required."
                ),
            }
            for row in rows
        ]


class MissingMetadataDetector:
    """Documents with an empty title."""

    _FINDING_TYPE = "MISSING_METADATA"
    _SEVERITY = "warning"

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id

    def detect(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(Document.id)
            .where(
                Document.workspace_id == self._workspace_id,
                func.trim(Document.title) == "",
            )
            .limit(200)
        ).all()
        return [
            {
                "finding_type": self._FINDING_TYPE,
                "severity": self._SEVERITY,
                "document_id": str(row.id),
                "version_id": None,
                "chunk_id": None,
                "title": "Missing document title",
                "description": f"Document {row.id} has an empty title.",
                "remediation": (
                    "Set a meaningful title on the document. "
                    "No automated repair — manual update required."
                ),
            }
            for row in rows
        ]


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
        detectors: list[Detector] = [
            DuplicateDetector(self._session, self._workspace_id),
            MetadataQualityDetector(self._session, self._workspace_id),
            LifecycleIntegrityDetector(self._session, self._workspace_id),
            SourceStatusIntegrityDetector(self._session, self._workspace_id),
            OrphanObjectDetector(self._session, self._workspace_id),
            EmptyChunkDetector(self._session, self._workspace_id),
            InvalidLifecycleDetector(self._session, self._workspace_id),
            MissingMetadataDetector(self._session, self._workspace_id),
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
