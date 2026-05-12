"""
Reindex Governance — Truth Tests.

Each test verifies a specific governance constraint or report field against
a real PostgreSQL database. Tests use truth_session (rolled back after test).

Safety constraint coverage:
  - full reindex blocks parallel full reindexes (advisory lock)
  - full reindex rejects workspace_id / document_id
  - workspace reindex requires workspace_id
  - document reindex requires document_id

Audit/report coverage:
  - correlation_id present and matches request
  - drift_score_before / drift_score_after captured
  - lifecycle_ok and lifecycle_inconsistency_count populated
  - regression_check_required always True
  - API endpoint returns 200 with full report schema
"""
from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.errors import ResourceLockedApiError
from app.services.reindex_governance import ReindexGovernanceService, ReindexGovernanceViolation
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.reindex_governance]


def _advisory_hash(value: str) -> int:
    digest = hashlib.sha256(value.encode()).digest()
    raw = int.from_bytes(digest[:4], "big", signed=False)
    return raw - 0x100000000 if raw > 0x7FFFFFFF else raw


# ── 1. Full reindex produces complete report ──────────────────────────────────

def test_governance_full_reindex_produces_report(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    report = svc.run_governed_reindex(
        reindex_type="full",
        correlation_id="cid-full-test-001",
        reason="governance truth test - full",
    )

    assert report["correlation_id"] == "cid-full-test-001"
    assert report["reindex_type"] == "full"
    assert report["workspace_id"] is None
    assert report["document_id"] is None
    assert report["reason"] == "governance truth test - full"
    assert report["status"] == "completed"
    assert isinstance(report["duration_ms"], int)
    assert report["duration_ms"] >= 0
    assert report["regression_check_required"] is True
    assert report["started_at"] is not None
    assert report["completed_at"] is not None


# ── 2. Workspace reindex scoped correctly ─────────────────────────────────────

def test_governance_workspace_reindex_scoped_correctly(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    report = svc.run_governed_reindex(
        reindex_type="workspace",
        workspace_id=truth_seed["workspace_id"],
        correlation_id="cid-ws-test-001",
        reason="governance truth test - workspace",
    )

    assert report["reindex_type"] == "workspace"
    assert report["workspace_id"] == truth_seed["workspace_id"]
    assert report["document_id"] is None
    assert report["status"] == "completed"


# ── 3. Document reindex scoped correctly ──────────────────────────────────────

def test_governance_document_reindex_scoped_correctly(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    doc_id = truth_ids.document_id("governance-doc")
    svc = ReindexGovernanceService.from_session(truth_session)
    report = svc.run_governed_reindex(
        reindex_type="document",
        workspace_id=truth_seed["workspace_id"],
        document_id=doc_id,
        correlation_id="cid-doc-test-001",
        reason="governance truth test - document",
    )

    assert report["reindex_type"] == "document"
    assert report["document_id"] == doc_id
    assert report["status"] == "completed"


# ── 4. Constraint: full reindex rejects workspace_id ─────────────────────────

def test_governance_full_reindex_rejects_workspace_id(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    with pytest.raises(ReindexGovernanceViolation, match="workspace_id"):
        svc.run_governed_reindex(
            reindex_type="full",
            workspace_id=truth_seed["workspace_id"],
            reason="should fail",
        )


def test_governance_full_reindex_rejects_document_id(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    with pytest.raises(ReindexGovernanceViolation, match="document_id"):
        svc.run_governed_reindex(
            reindex_type="full",
            document_id=truth_ids.document_id("bad"),
            reason="should fail",
        )


# ── 5. Constraint: workspace reindex requires workspace_id ────────────────────

def test_governance_workspace_reindex_requires_workspace_id(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    with pytest.raises(ReindexGovernanceViolation, match="requires workspace_id"):
        svc.run_governed_reindex(
            reindex_type="workspace",
            reason="should fail",
        )


def test_governance_workspace_reindex_rejects_document_id(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    with pytest.raises(ReindexGovernanceViolation, match="document_id"):
        svc.run_governed_reindex(
            reindex_type="workspace",
            workspace_id=truth_seed["workspace_id"],
            document_id=truth_ids.document_id("bad"),
            reason="should fail",
        )


# ── 6. Constraint: document reindex requires document_id ──────────────────────

def test_governance_document_reindex_requires_document_id(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    with pytest.raises(ReindexGovernanceViolation, match="requires document_id"):
        svc.run_governed_reindex(
            reindex_type="document",
            workspace_id=truth_seed["workspace_id"],
            reason="should fail",
        )


# ── 7. Safety: parallel full reindex blocked by advisory lock ─────────────────

def test_governance_parallel_full_reindex_blocked(
    postgres_truth_engine: Engine,
    truth_session: Session,
    truth_seed: dict[str, str],
) -> None:
    # Scope 3 = reindex; key = "__global__" (full reindex lock)
    scope_id = 3
    resource_id = _advisory_hash("__global__")

    # Acquire the global reindex lock in a separate transaction
    with postgres_truth_engine.connect() as blocking_conn:
        blocking_conn.execute(
            text("SELECT pg_try_advisory_xact_lock(:scope, :resource)"),
            {"scope": scope_id, "resource": resource_id},
        )
        # Lock is now held by blocking_conn's transaction.
        # truth_session runs in a different transaction and cannot acquire it.
        svc = ReindexGovernanceService.from_session(truth_session)
        with pytest.raises(ResourceLockedApiError):
            svc.run_governed_reindex(
                reindex_type="full",
                correlation_id="cid-parallel-blocked",
                reason="must be blocked by advisory lock",
            )


# ── 8. Drift snapshots captured before and after ──────────────────────────────

def test_governance_drift_snapshots_in_report(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    report = svc.run_governed_reindex(
        reindex_type="workspace",
        workspace_id=truth_seed["workspace_id"],
        correlation_id="cid-drift-test",
        reason="drift snapshot coverage",
    )

    assert isinstance(report["drift_score_before"], int)
    assert isinstance(report["drift_score_after"], int)
    assert 0 <= report["drift_score_before"] <= 100
    assert 0 <= report["drift_score_after"] <= 100
    assert isinstance(report["drift_delta"], int)
    assert report["drift_delta"] == report["drift_score_after"] - report["drift_score_before"]
    assert report["drift_severity_before"] in {"ok", "info", "low", "medium", "high", "critical"}
    assert report["drift_severity_after"] in {"ok", "info", "low", "medium", "high", "critical"}
    assert report["drift_status_before"] in {"ok", "drifted"}
    assert report["drift_status_after"] in {"ok", "drifted"}


# ── 9. Post-reindex lifecycle check in report ─────────────────────────────────

def test_governance_lifecycle_check_in_report(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    report = svc.run_governed_reindex(
        reindex_type="workspace",
        workspace_id=truth_seed["workspace_id"],
        correlation_id="cid-lifecycle-test",
        reason="lifecycle consistency check coverage",
    )

    assert isinstance(report["lifecycle_ok"], bool)
    assert isinstance(report["lifecycle_inconsistency_count"], int)
    assert report["lifecycle_inconsistency_count"] >= 0
    # Clean workspace → lifecycle must be consistent
    assert report["lifecycle_ok"] is True
    assert report["lifecycle_inconsistency_count"] == 0


# ── 10. Correlation ID auto-generated when not provided ───────────────────────

def test_governance_auto_generates_correlation_id(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = ReindexGovernanceService.from_session(truth_session)
    report = svc.run_governed_reindex(
        reindex_type="workspace",
        workspace_id=truth_seed["workspace_id"],
        reason="auto correlation id test",
    )

    assert report["correlation_id"] is not None
    assert len(report["correlation_id"]) > 0
    # UUID format: 8-4-4-4-12 chars separated by dashes
    parts = report["correlation_id"].split("-")
    assert len(parts) == 5


# ── 11. API endpoint returns 200 with full report ────────────────────────────

def test_governance_api_endpoint_returns_report(
    truth_client,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    response = truth_client.post(
        "/api/v1/admin/reindex/governed",
        json={
            "reindex_type": "workspace",
            "workspace_id": truth_seed["workspace_id"],
            "reason": "api contract test",
            "correlation_id": "cid-api-contract-001",
        },
    )

    assert response.status_code == 200, f"unexpected: {response.text}"
    data = response.json()
    assert data["correlation_id"] == "cid-api-contract-001"
    assert data["reindex_type"] == "workspace"
    assert data["workspace_id"] == truth_seed["workspace_id"]
    assert data["status"] == "completed"
    assert data["regression_check_required"] is True
    assert isinstance(data["drift_score_before"], int)
    assert isinstance(data["drift_score_after"], int)
    assert isinstance(data["lifecycle_ok"], bool)


def test_governance_api_endpoint_rejects_constraint_violation(
    truth_client,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    # full reindex must not specify workspace_id
    response = truth_client.post(
        "/api/v1/admin/reindex/governed",
        json={
            "reindex_type": "full",
            "workspace_id": truth_seed["workspace_id"],
            "reason": "should be rejected",
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "REINDEX_CONSTRAINT_VIOLATION"
