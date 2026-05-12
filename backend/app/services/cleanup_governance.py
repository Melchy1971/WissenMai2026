"""
Cleanup Governance Service.

Wraps M5CleanupService with the mandatory governance envelope:

  1. Dry run always executes first — even when execute is requested.
  2. Safety gates block execution if any constraint would be violated:
       A. Active-document chunks in orphan scope     → blocking
       B. Citations referencing orphan-scope chunks  → warning only (SET NULL is safe)
       C. Running jobs in scope                      → blocking
  3. Before/after snapshots of key DB counters.
  4. Drift delta computed from snapshots; citation loss triggers critical alert.
  5. Recovery hints derived from dry-run candidate categories.
  6. Rollback strategy rendered as a static advisory string.

The only way to run execute is: dry_run_only=False + all blocking gates passed.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.documents import (
    AuthSession, BackgroundJob, ChatCitation, ChatMessage, ChatSession,
    Chunk, Document,
)
from app.observability.logging import log_event
from app.services.m5_cleanup import CleanupConfig, M5CleanupService


logger = logging.getLogger(__name__)

_ROLLBACK_STRATEGY = (
    "DB categories (expired_session_cleanup, stale_index_cleanup, orphan_cleanup): "
    "committed in a single transaction — full recovery requires pg_dump restore from "
    "the last backup taken before this cleanup ran. "
    "stale_index_cleanup is individually reversible via POST /admin/reindex/governed. "
    "expired_session_cleanup has no data impact: users simply re-login. "
    "File categories (temp_file_cleanup, old_report_cleanup): deletions are permanent "
    "— recovery requires filesystem backup restore. "
    "Mitigation: always run dry_run first and review candidate_count per category."
)


class CleanupGovernanceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._cleanup_svc = M5CleanupService(session)

    @classmethod
    def from_session(cls, session: Session) -> "CleanupGovernanceService":
        return cls(session)

    def run_governed_cleanup(
        self,
        *,
        config: CleanupConfig,
        dry_run_only: bool = True,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        correlation_id = correlation_id or str(uuid4())
        started_at = datetime.now(UTC)
        start_ms = time.monotonic_ns() // 1_000_000

        log_event(
            "cleanup_governance_started",
            workspace_id=config.workspace_id,
            status="started",
            correlation_id=correlation_id,
        )

        gates = self._run_safety_gates(config=config)
        snapshot_before = self._capture_snapshot(config=config)

        # Dry run is mandatory and always runs first.
        dry_run_result = self._cleanup_svc.dry_run(config=config)
        dry_run_candidate_count = int(dry_run_result["summary"]["candidate_count"])

        execute_applied_count: int | None = None
        mode: str

        if not gates["passed"]:
            mode = "blocked"
        elif dry_run_only:
            mode = "dry_run"
        else:
            execute_result = self._cleanup_svc.execute(config=config)
            execute_applied_count = int(execute_result["summary"]["applied_count"])
            mode = "execute"

        snapshot_after = self._capture_snapshot(config=config)
        delta = _compute_delta(snapshot_before, snapshot_after)
        alerts, severity = _evaluate_alerts(delta=delta, gates=gates)
        duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

        log_event(
            "cleanup_governance_completed",
            workspace_id=config.workspace_id,
            status="blocked" if mode == "blocked" else "completed",
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

        return {
            "correlation_id": correlation_id,
            "mode": mode,
            "started_at": started_at,
            "completed_at": datetime.now(UTC),
            "duration_ms": duration_ms,
            "retention_days": config.retention_days,
            "workspace_id": config.workspace_id,
            "dry_run_only": dry_run_only,
            "safety_gates": gates,
            "snapshot_before": snapshot_before,
            "snapshot_after": snapshot_after,
            "delta": delta,
            "dry_run_candidate_count": dry_run_candidate_count,
            "execute_applied_count": execute_applied_count,
            "severity": severity,
            "alerts": alerts,
            "recovery_hints": _recovery_hints(dry_run_result, mode=mode),
            "rollback_strategy": _ROLLBACK_STRATEGY,
        }

    # ── Safety gates ─────────────────────────────────────────────────────────

    def _run_safety_gates(self, *, config: CleanupConfig) -> dict[str, Any]:
        active_doc_orphan = int(
            self._session.execute(
                _text(
                    """
                    SELECT COUNT(c.id)
                    FROM document_chunks c
                    JOIN documents d ON d.id = c.document_id
                    LEFT JOIN document_versions v ON v.id = c.document_version_id
                    WHERE d.lifecycle_status = 'active'
                      AND v.id IS NULL
                    """
                )
            ).scalar()
            or 0
        )

        citation_orphan = int(
            self._session.execute(
                _text(
                    """
                    SELECT COUNT(cc.id)
                    FROM chat_citations cc
                    JOIN document_chunks c ON c.id = cc.chunk_id
                    LEFT JOIN documents d ON d.id = c.document_id
                    LEFT JOIN document_versions v ON v.id = c.document_version_id
                    WHERE d.id IS NULL OR v.id IS NULL
                    """
                )
            ).scalar()
            or 0
        )

        running_jobs = int(
            self._session.scalar(
                select(func.count(BackgroundJob.id)).where(BackgroundJob.status == "running")
            )
            or 0
        )

        passed = active_doc_orphan == 0 and running_jobs == 0
        blocked_reason: str | None = None
        if active_doc_orphan > 0:
            blocked_reason = (
                f"{active_doc_orphan} active-document chunk(s) have broken version FK "
                f"and would be deleted by orphan_cleanup — manual investigation required"
            )
        elif running_jobs > 0:
            blocked_reason = (
                f"{running_jobs} job(s) currently running — "
                f"defer cleanup until all running jobs complete"
            )

        return {
            "passed": passed,
            "active_doc_refs_in_orphan_scope": active_doc_orphan,
            "citation_refs_in_orphan_scope": citation_orphan,
            "active_job_refs_in_scope": running_jobs,
            "blocked_reason": blocked_reason,
        }

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def _capture_snapshot(self, *, config: CleanupConfig) -> dict[str, Any]:
        ws = config.workspace_id
        now = config.now

        doc_q = select(func.count(Document.id)).where(Document.lifecycle_status == "active")
        if ws:
            doc_q = doc_q.where(Document.workspace_id == ws)

        chunk_q = (
            select(func.count(Chunk.id))
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.lifecycle_status == "active", Chunk.is_searchable.is_(True))
        )
        if ws:
            chunk_q = chunk_q.where(Document.workspace_id == ws)

        cit_q = select(func.count(ChatCitation.id))
        if ws:
            cit_q = (
                cit_q.join(ChatMessage, ChatMessage.id == ChatCitation.message_id)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(ChatSession.workspace_id == ws)
            )

        return {
            "active_document_count": int(self._session.scalar(doc_q) or 0),
            "active_chunk_count": int(self._session.scalar(chunk_q) or 0),
            "citation_count": int(self._session.scalar(cit_q) or 0),
            "active_job_count": int(
                self._session.scalar(
                    select(func.count(BackgroundJob.id)).where(
                        BackgroundJob.status.in_(["pending", "running", "retryable"])
                    )
                )
                or 0
            ),
            "active_auth_session_count": int(
                self._session.scalar(
                    select(func.count(AuthSession.id)).where(
                        AuthSession.expires_at >= now,
                        AuthSession.revoked_at.is_(None),
                    )
                )
                or 0
            ),
        }


# ── Module-level helpers ──────────────────────────────────────────────────────

def _text(sql: str):
    from sqlalchemy import text
    return text(sql)


def _compute_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_document_delta": after["active_document_count"] - before["active_document_count"],
        "active_chunk_delta": after["active_chunk_count"] - before["active_chunk_count"],
        "citation_delta": after["citation_count"] - before["citation_count"],
        "active_job_delta": after["active_job_count"] - before["active_job_count"],
        "active_auth_session_delta": after["active_auth_session_count"] - before["active_auth_session_count"],
        "citation_loss_detected": after["citation_count"] < before["citation_count"],
    }


def _evaluate_alerts(
    *, delta: dict[str, Any], gates: dict[str, Any]
) -> tuple[list[str], str]:
    alerts: list[str] = []
    severity = "ok"

    if not gates["passed"]:
        alerts.append(f"BLOCKED: {gates['blocked_reason']}")
        return alerts, "critical"

    if delta["citation_loss_detected"]:
        loss = abs(int(delta["citation_delta"]))
        alerts.append(
            f"CRITICAL: citation count decreased by {loss} — "
            f"citations were destroyed during cleanup; run CitationLongevityAudit immediately"
        )
        severity = "critical"

    if delta["active_document_delta"] < 0:
        alerts.append(
            f"active document count decreased by {abs(int(delta['active_document_delta']))} "
            f"— verify no active documents were affected"
        )
        if severity == "ok":
            severity = "warning"

    citation_orphan = int(gates["citation_refs_in_orphan_scope"])
    if citation_orphan > 0:
        alerts.append(
            f"{citation_orphan} citation(s) reference orphan-scope chunks — "
            f"chunk deletion will set citation.chunk_id to NULL (anchor becomes unverifiable)"
        )
        if severity == "ok":
            severity = "warning"

    return alerts, severity


def _recovery_hints(dry_run_result: dict[str, Any], *, mode: str) -> list[str]:
    hints: list[str] = []
    cats = dry_run_result.get("categories", {})

    if int(cats.get("orphan_cleanup", {}).get("candidate_count", 0)) > 0:
        hints.append(
            "orphan_cleanup: deleted chunks/versions are not recoverable from DB alone; "
            "re-import original source files to rebuild."
        )
    if int(cats.get("stale_index_cleanup", {}).get("candidate_count", 0)) > 0:
        hints.append(
            "stale_index_cleanup: searchability flags changed; "
            "revert via POST /admin/reindex/governed (reindex_type=workspace)."
        )
    if int(cats.get("temp_file_cleanup", {}).get("candidate_count", 0)) > 0:
        hints.append(
            "temp_file_cleanup: deleted temp files are permanent; "
            "re-upload source files if processing is needed again."
        )
    if int(cats.get("old_report_cleanup", {}).get("candidate_count", 0)) > 0:
        hints.append(
            "old_report_cleanup: deleted report files are permanent; "
            "regenerate via benchmark CLI (scripts/run_retrieval_benchmark.py)."
        )
    if int(cats.get("expired_session_cleanup", {}).get("candidate_count", 0)) > 0:
        hints.append(
            "expired_session_cleanup: auth sessions purged; "
            "no data impact — affected users simply re-login."
        )

    if mode == "dry_run":
        hints.append(
            "dry_run mode: no changes applied; "
            "re-run with dry_run_only=false to execute."
        )

    if not hints:
        hints.append("No cleanup candidates found; no recovery actions needed.")

    return hints
