"""
Reindex Governance Service.

Every reindex operation must go through this service to guarantee:
- correlation_id tracking on every run
- audit events at start and completion
- drift snapshot taken before and after
- advisory lock preventing parallel full reindexes
- lifecycle consistency check post-reindex
- regression_check_required flag signalling operators to run the benchmark CLI

Forbidden paths enforced here:
  - parallel full reindexes (global advisory lock)
  - untracked repairs (all callers must go through run_governed_reindex)
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.observability.logging import log_event
from app.services.advisory_lock import AdvisoryLockService
from app.services.search_index_service import SearchIndexRebuildService


logger = logging.getLogger(__name__)

ReindexType = Literal["full", "workspace", "document"]
START_AUDIT_EVENT = "reindex_governance_started"
COMPLETED_AUDIT_EVENT = "reindex_governance_completed"
POST_REINDEX_CHECKS = {
    "drift_detection": "executed",
    "retrieval_regression": "required",
    "lifecycle_consistency": "executed",
}


class ReindexGovernanceViolation(ValueError):
    """Raised when a reindex request violates governance constraints."""


class ReindexGovernanceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._index_svc = SearchIndexRebuildService(session)
        self._lock_svc = AdvisoryLockService.from_session(session)

    @classmethod
    def from_session(cls, session: Session) -> "ReindexGovernanceService":
        return cls(session)

    def run_governed_reindex(
        self,
        *,
        reindex_type: ReindexType,
        workspace_id: str | None = None,
        document_id: str | None = None,
        correlation_id: str | None = None,
        reason: str,
    ) -> dict[str, Any]:
        correlation_id = correlation_id or str(uuid4())
        started_at = datetime.now(UTC)
        start_ms = time.monotonic_ns() // 1_000_000

        self._validate_constraints(
            reindex_type=reindex_type,
            workspace_id=workspace_id,
            document_id=document_id,
        )
        self._acquire_governance_lock(
            reindex_type=reindex_type,
            workspace_id=workspace_id,
            document_id=document_id,
        )

        log_event(
            START_AUDIT_EVENT,
            workspace_id=workspace_id,
            status="started",
            correlation_id=correlation_id,
        )

        drift_before = self._index_svc.inspect_drift(workspace_id=workspace_id)
        rebuild_result = self._index_svc.rebuild_search_index(workspace_id=workspace_id)
        drift_after = self._index_svc.inspect_drift(workspace_id=workspace_id)

        lifecycle_report = self._index_svc.inspect_inconsistencies(workspace_id=workspace_id)
        lifecycle_inconsistency_count = (
            int(lifecycle_report["missing_index_entries"]["count"])
            + int(lifecycle_report["deleted_documents_in_index"]["count"])
            + int(lifecycle_report["archived_documents_in_active_index"]["count"])
        )
        lifecycle_ok = lifecycle_inconsistency_count == 0

        duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        completed_at = datetime.now(UTC)

        log_event(
            COMPLETED_AUDIT_EVENT,
            workspace_id=workspace_id,
            status="completed",
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

        return {
            "correlation_id": correlation_id,
            "reindex_type": reindex_type,
            "workspace_id": workspace_id,
            "document_id": document_id,
            "reason": reason,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "audit_event_names": [START_AUDIT_EVENT, COMPLETED_AUDIT_EVENT],
            "audit_event_count": 2,
            "drift_score_before": int(drift_before["drift_score"]),
            "drift_score_after": int(drift_after["drift_score"]),
            "drift_delta": int(drift_after["drift_score"]) - int(drift_before["drift_score"]),
            "drift_severity_before": str(drift_before["severity"]),
            "drift_severity_after": str(drift_after["severity"]),
            "drift_status_before": str(drift_before["status"]),
            "drift_status_after": str(drift_after["status"]),
            "drift_snapshot_before_taken": True,
            "drift_snapshot_after_taken": True,
            "lifecycle_ok": lifecycle_ok,
            "lifecycle_inconsistency_count": lifecycle_inconsistency_count,
            "reindexed_chunk_count": int(rebuild_result["reindexed_chunk_count"]),
            "reindexed_document_count": int(rebuild_result["reindexed_document_count"]),
            "index_action": str(rebuild_result["index_action"]),
            "regression_check_required": True,
            "retrieval_regression_trigger": "reindex",
            "post_reindex_checks": POST_REINDEX_CHECKS,
            "status": "completed",
        }

    def _validate_constraints(
        self,
        *,
        reindex_type: ReindexType,
        workspace_id: str | None,
        document_id: str | None,
    ) -> None:
        if reindex_type == "full":
            if workspace_id is not None or document_id is not None:
                raise ReindexGovernanceViolation(
                    "full reindex must not specify workspace_id or document_id"
                )
        elif reindex_type == "workspace":
            if workspace_id is None:
                raise ReindexGovernanceViolation("workspace reindex requires workspace_id")
            if document_id is not None:
                raise ReindexGovernanceViolation(
                    "workspace reindex must not specify document_id"
                )
        elif reindex_type == "document":
            if document_id is None:
                raise ReindexGovernanceViolation("document reindex requires document_id")

    def _acquire_governance_lock(
        self,
        *,
        reindex_type: ReindexType,
        workspace_id: str | None,
        document_id: str | None,
    ) -> None:
        if reindex_type == "full":
            self._lock_svc.acquire_reindex_lock(workspace_id="__global__")
        elif reindex_type == "workspace":
            self._lock_svc.acquire_reindex_lock(workspace_id=workspace_id)  # type: ignore[arg-type]
        else:
            effective_workspace = workspace_id or "__global__"
            self._lock_svc.acquire_reindex_lock(
                workspace_id=effective_workspace, document_id=document_id
            )
