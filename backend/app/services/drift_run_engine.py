"""Drift Run Engine.

Ablauf:
  1. DriftRun starten         — erzeugt DriftRun-Record, Status: running
  2. Detectoren registrieren  — Liste von BaseDriftDetector-Instanzen
  3. Detectoren ausführen     — read-only, kein Repair
  4. Findings speichern       — DriftFinding-Records pro Ergebnis
  5. Snapshot speichern       — post_run DriftSnapshot mit entity_count
  6. Report erzeugen          — DriftRunReport (Dict) aus dem abgeschlossenen Run

Regeln:
- idempotent: ein Run mit derselben run_id kann nicht zweimal gestartet werden
- read only: keine Schreibzugriffe auf documents, chunks, versions oder andere
  Nicht-Drift-Tabellen
- keine Repair Aktionen: Detectoren dürfen nur Findings erzeugen, nicht beheben
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.drift import (
    DRIFT_FINDING_TYPES,
    DRIFT_SEVERITY_VALUES,
    DriftFinding,
    DriftRun,
    DriftSnapshot,
)

logger = logging.getLogger(__name__)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Finding DTO
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FindingDTO:
    """Immutable value object produced by a detector.

    Detectors yield FindingDTO instances — the engine persists them.
    Detectors must not modify database state.
    """

    finding_type: str
    severity: str
    entity_type: str | None = None
    entity_id: str | None = None
    detail: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.finding_type not in DRIFT_FINDING_TYPES:
            raise ValueError(
                f"Invalid finding_type '{self.finding_type}'. "
                f"Allowed: {DRIFT_FINDING_TYPES}"
            )
        if self.severity not in DRIFT_SEVERITY_VALUES:
            raise ValueError(
                f"Invalid severity '{self.severity}'. "
                f"Allowed: {DRIFT_SEVERITY_VALUES}"
            )


# ---------------------------------------------------------------------------
# Detector base
# ---------------------------------------------------------------------------

class BaseDriftDetector(ABC):
    """All detectors must subclass this.

    Contract:
    - detect() receives a read-only session and workspace_id.
    - detect() yields FindingDTO instances.
    - detect() must NOT write to any table.
    - detect() must NOT raise exceptions for expected drift conditions;
      only raise for unrecoverable errors (e.g. DB connection lost).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier for this detector (used in reports and logs)."""

    @abstractmethod
    def detect(self, session: Session, workspace_id: str) -> list[FindingDTO]:
        """Run detection and return a list of findings. Read-only."""


# ---------------------------------------------------------------------------
# Run result
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    run_id: str
    workspace_id: str
    status: str
    findings: list[FindingDTO] = field(default_factory=list)
    detector_results: dict[str, int] = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def total_findings(self) -> int:
        return len(self.findings)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DriftRunEngine:
    """Orchestrates a full drift detection run.

    Usage::

        engine = DriftRunEngine(session, workspace_id="ws-123")
        engine.register(DocumentDriftDetector())
        engine.register(MetadataDriftDetector())
        result = engine.run()

    The session must be managed by the caller (commit / rollback).
    """

    def __init__(self, session: Session, workspace_id: str) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._detectors: list[BaseDriftDetector] = []

    # ------------------------------------------------------------------
    # Step 2: Register detectors
    # ------------------------------------------------------------------

    def register(self, detector: BaseDriftDetector) -> None:
        """Register a detector. Order of registration = order of execution."""
        if not isinstance(detector, BaseDriftDetector):
            raise TypeError(f"Expected BaseDriftDetector, got {type(detector)}")
        self._detectors.append(detector)

    # ------------------------------------------------------------------
    # Main entry point (Steps 1-6)
    # ------------------------------------------------------------------

    def run(self, run_id: str | None = None, triggered_by: str = "system") -> RunResult:
        """Execute the full pipeline. Returns RunResult.

        Idempotency: if run_id is provided and already exists in the DB
        the call raises RuntimeError without modifying any state.
        """
        run_id = run_id or str(uuid.uuid4())

        # Step 1: Start DriftRun
        drift_run = self._start_run(run_id, triggered_by)

        result = RunResult(
            run_id=run_id,
            workspace_id=self._workspace_id,
            status="running",
            started_at=drift_run.started_at,
        )

        try:
            # Step 2 already done via register(); Step 3: Execute detectors
            all_findings: list[FindingDTO] = []
            for detector in self._detectors:
                try:
                    findings = detector.detect(self._session, self._workspace_id)
                    all_findings.extend(findings)
                    result.detector_results[detector.name] = len(findings)
                    logger.debug(
                        "detector=%s workspace=%s findings=%d",
                        detector.name,
                        self._workspace_id,
                        len(findings),
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Detector %s raised an exception: %s", detector.name, exc
                    )
                    result.detector_results[detector.name] = -1
                    raise

            result.findings = all_findings

            # Step 4: Save findings
            self._save_findings(drift_run, all_findings)

            # Step 5: Save snapshot
            self._save_snapshot(drift_run, entity_count=len(all_findings))

            # Step 6: Complete run
            completed_at = datetime.now(UTC)
            drift_run.status = "completed"
            drift_run.completed_at = completed_at
            drift_run.total_findings = len(all_findings)
            drift_run.updated_at = completed_at
            self._session.flush()

            result.status = "completed"
            result.completed_at = completed_at

        except Exception as exc:
            error_message = str(exc)
            drift_run.status = "failed"
            drift_run.error_message = error_message
            drift_run.updated_at = datetime.now(UTC)
            self._session.flush()
            result.status = "failed"
            result.error_message = error_message
            raise

        return result

    # ------------------------------------------------------------------
    # Step 1: Start run
    # ------------------------------------------------------------------

    def _start_run(self, run_id: str, triggered_by: str) -> DriftRun:
        existing = self._session.get(DriftRun, run_id)
        if existing is not None:
            raise RuntimeError(
                f"DriftRun '{run_id}' already exists (status={existing.status}). "
                "Provide a new run_id for each execution."
            )

        now = datetime.now(UTC)
        drift_run = DriftRun(
            id=run_id,
            workspace_id=self._workspace_id,
            status="running",
            triggered_by=triggered_by,
            detector_names=[d.name for d in self._detectors],
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(drift_run)
        self._session.flush()
        logger.info(
            "DriftRun started: run_id=%s workspace=%s detectors=%s",
            run_id,
            self._workspace_id,
            drift_run.detector_names,
        )
        return drift_run

    # ------------------------------------------------------------------
    # Step 4: Save findings
    # ------------------------------------------------------------------

    def _save_findings(self, drift_run: DriftRun, findings: list[FindingDTO]) -> None:
        now = datetime.now(UTC)
        for dto in findings:
            self._session.add(
                DriftFinding(
                    id=str(uuid.uuid4()),
                    run_id=drift_run.id,
                    workspace_id=drift_run.workspace_id,
                    finding_type=dto.finding_type,
                    severity=dto.severity,
                    entity_type=dto.entity_type,
                    entity_id=dto.entity_id,
                    detail=dto.detail,
                    created_at=now,
                )
            )
        self._session.flush()
        logger.debug(
            "Saved %d findings for run_id=%s", len(findings), drift_run.id
        )

    # ------------------------------------------------------------------
    # Step 5: Save snapshot
    # ------------------------------------------------------------------

    def _save_snapshot(self, drift_run: DriftRun, entity_count: int) -> None:
        snap = DriftSnapshot(
            id=str(uuid.uuid4()),
            run_id=drift_run.id,
            workspace_id=drift_run.workspace_id,
            snapshot_type="post_run",
            entity_count=entity_count,
            data={
                "run_id": drift_run.id,
                "detector_names": drift_run.detector_names,
                "findings_by_type": self._count_by_type(drift_run),
            },
            created_at=datetime.now(UTC),
        )
        self._session.add(snap)
        self._session.flush()

    def _count_by_type(self, drift_run: DriftRun) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in drift_run.findings:
            counts[finding.finding_type] = counts.get(finding.finding_type, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Step 6: Generate report (returns dict — no DB writes)
    # ------------------------------------------------------------------

    @staticmethod
    def build_report(result: RunResult) -> dict[str, Any]:
        """Produce a serialisable report dict from a completed RunResult.

        This is a pure function — no DB access, no side effects.
        """
        return {
            "run_id": result.run_id,
            "workspace_id": result.workspace_id,
            "status": result.status,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_findings": result.total_findings,
            "findings_by_type": {
                ft: sum(1 for f in result.findings if f.finding_type == ft)
                for ft in DRIFT_FINDING_TYPES
                if any(f.finding_type == ft for f in result.findings)
            },
            "findings_by_severity": {
                sev: sum(1 for f in result.findings if f.severity == sev)
                for sev in DRIFT_SEVERITY_VALUES
                if any(f.severity == sev for f in result.findings)
            },
            "detector_results": result.detector_results,
            "error_message": result.error_message,
        }
