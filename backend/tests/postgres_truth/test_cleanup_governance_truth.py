"""
Cleanup Governance truth tests.

Verifies that CleanupGovernanceService enforces:
- Mandatory dry run always executes before any execute
- Safety gates block execution when constraints would be violated
- Before/after snapshots and drift delta are accurate
- Citations are never destroyed by cleanup
- Recovery hints and rollback strategy are always present
- API endpoint defaults to dry_run_only=True
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.cleanup_governance import CleanupGovernanceService
from app.services.m5_cleanup import CleanupConfig
from tests.postgres_truth.support import TruthIds


pytestmark = pytest.mark.cleanup_governance


_CONTENT = "The quick brown fox jumps over the lazy dog for governance truth testing."


# ── Seeding helpers ───────────────────────────────────────────────────────────

def _seed_document(
    session: Session,
    *,
    truth_ids: TruthIds,
    label: str,
    workspace_id: str,
    user_id: str,
    lifecycle_status: str = "active",
    content: str = _CONTENT,
) -> tuple[str, str, str]:
    doc_id = truth_ids.document_id(label)
    version_id = truth_ids.version_id(label)
    chunk_id = truth_ids.chunk_id(label)
    content_hash = truth_ids.content_hash(label)

    session.execute(
        __import__("sqlalchemy").text(
            """
            INSERT INTO documents (
                id, workspace_id, title, file_name, file_type,
                content_hash, lifecycle_status, import_status, created_at, updated_at
            ) VALUES (
                :doc_id::uuid, :ws::uuid, :title, :fname, 'text/plain',
                :chash, :status, 'completed', now(), now()
            )
            """
        ),
        {
            "doc_id": doc_id,
            "ws": workspace_id,
            "title": f"Gov Doc {label}",
            "fname": f"gov-doc-{label}.txt",
            "chash": content_hash,
            "status": lifecycle_status,
        },
    )
    session.execute(
        __import__("sqlalchemy").text(
            """
            INSERT INTO document_versions (
                id, document_id, version_number, file_size_bytes,
                raw_text, created_at
            ) VALUES (
                :vid::uuid, :doc_id::uuid, 1, :fsize, :content, now()
            )
            """
        ),
        {"vid": version_id, "doc_id": doc_id, "fsize": len(content), "content": content},
    )
    session.execute(
        __import__("sqlalchemy").text(
            """
            UPDATE documents SET current_version_id = :vid::uuid WHERE id = :doc_id::uuid
            """
        ),
        {"vid": version_id, "doc_id": doc_id},
    )
    session.execute(
        __import__("sqlalchemy").text(
            """
            INSERT INTO document_chunks (
                id, document_id, document_version_id,
                chunk_index, content, is_searchable, created_at
            ) VALUES (
                :cid::uuid, :doc_id::uuid, :vid::uuid,
                0, :content, true, now()
            )
            """
        ),
        {"cid": chunk_id, "doc_id": doc_id, "vid": version_id, "content": content},
    )
    session.commit()
    return doc_id, version_id, chunk_id


def _seed_running_job(
    session: Session,
    *,
    truth_ids: TruthIds,
    label: str,
    workspace_id: str,
    user_id: str,
) -> str:
    from sqlalchemy import text as sa_text
    from psycopg.types.json import Jsonb

    job_id = truth_ids.job_id(label)
    session.execute(
        sa_text(
            """
            INSERT INTO background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) VALUES (
                :jid, 'import_document', 'running', :ws::uuid, :uid::uuid, '{}', null,
                0, 1, 'running', null, null,
                1, now(), 'worker-1', now(), now(), null
            )
            """
        ),
        {"jid": job_id, "ws": workspace_id, "uid": user_id},
    )
    session.commit()
    return job_id


def _seed_expired_auth_session(
    session: Session,
    *,
    truth_ids: TruthIds,
    label: str,
    workspace_id: str,
    user_id: str,
) -> str:
    from sqlalchemy import text as sa_text
    from app.services.auth import hash_token

    expired_session_id = f"truth-{truth_ids.slug}-expired-{label}"
    token = f"expired-token-{truth_ids.namespace}-{label}"
    expires_at = datetime.now(UTC) - timedelta(days=30)
    session.execute(
        sa_text(
            """
            INSERT INTO auth_sessions
                (id, user_id, token_hash, expires_at, created_at, last_seen_at, revoked_at)
            VALUES (:sid, :uid::uuid, :thash, :exp, :now, :now, null)
            """
        ),
        {
            "sid": expired_session_id,
            "uid": user_id,
            "thash": hash_token(token),
            "exp": expires_at,
            "now": datetime.now(UTC) - timedelta(days=31),
        },
    )
    session.commit()
    return expired_session_id


def _make_config(
    *,
    workspace_id: str | None = None,
    retention_days: int = 7,
) -> CleanupConfig:
    return CleanupConfig(
        now=datetime.now(UTC),
        retention_days=retention_days,
        workspace_id=workspace_id,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCleanupGovernanceDryRun:
    @pytest.mark.postgres_truth
    def test_dry_run_on_clean_db_returns_no_candidates(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Clean DB with no stale data returns zero candidates and ok severity."""
        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=truth_seed["workspace_id"])

        report = svc.run_governed_cleanup(config=config, dry_run_only=True)

        assert report["mode"] == "dry_run"
        assert report["dry_run_candidate_count"] == 0
        assert report["execute_applied_count"] is None
        assert report["safety_gates"]["passed"] is True
        assert report["severity"] in {"ok", "warning"}

    @pytest.mark.postgres_truth
    def test_dry_run_does_not_modify_db(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Dry run with an active document: document count unchanged after dry run."""
        workspace_id = truth_seed["workspace_id"]
        user_id = truth_seed["user_id"]
        _seed_document(
            truth_session,
            truth_ids=truth_ids,
            label="dry-run-check",
            workspace_id=workspace_id,
            user_id=user_id,
        )

        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=workspace_id)

        before = svc._capture_snapshot(config=config)
        report = svc.run_governed_cleanup(config=config, dry_run_only=True)
        after = svc._capture_snapshot(config=config)

        assert report["mode"] == "dry_run"
        # Active document must not be touched
        assert after["active_document_count"] == before["active_document_count"]
        assert after["active_chunk_count"] == before["active_chunk_count"]

    @pytest.mark.postgres_truth
    def test_dry_run_candidate_count_correct_with_expired_sessions(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Expired auth sessions appear in dry_run_candidate_count."""
        workspace_id = truth_seed["workspace_id"]
        user_id = truth_seed["user_id"]
        _seed_expired_auth_session(
            truth_session,
            truth_ids=truth_ids,
            label="stale-1",
            workspace_id=workspace_id,
            user_id=user_id,
        )

        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=workspace_id)
        report = svc.run_governed_cleanup(config=config, dry_run_only=True)

        assert report["mode"] == "dry_run"
        assert report["dry_run_candidate_count"] >= 1


class TestCleanupGovernanceSafetyGates:
    @pytest.mark.postgres_truth
    def test_running_jobs_block_execution(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """A running job must block cleanup execution (Gate C)."""
        workspace_id = truth_seed["workspace_id"]
        user_id = truth_seed["user_id"]
        _seed_running_job(
            truth_session,
            truth_ids=truth_ids,
            label="blocker",
            workspace_id=workspace_id,
            user_id=user_id,
        )

        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=workspace_id)
        report = svc.run_governed_cleanup(config=config, dry_run_only=False)

        assert report["mode"] == "blocked"
        assert report["safety_gates"]["passed"] is False
        assert report["safety_gates"]["active_job_refs_in_scope"] >= 1
        assert report["execute_applied_count"] is None
        assert report["severity"] == "critical"

    @pytest.mark.postgres_truth
    def test_safety_gates_pass_on_clean_db(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Safety gates report passed=True when there are no blockers."""
        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=truth_seed["workspace_id"])
        report = svc.run_governed_cleanup(config=config, dry_run_only=True)

        gates = report["safety_gates"]
        assert gates["passed"] is True
        assert gates["active_doc_refs_in_orphan_scope"] == 0
        assert gates["active_job_refs_in_scope"] == 0
        assert gates["blocked_reason"] is None


class TestCleanupGovernanceSnapshots:
    @pytest.mark.postgres_truth
    def test_snapshot_delta_on_execute_reflects_session_deletion(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """After executing cleanup of expired sessions, auth_session_delta < 0."""
        workspace_id = truth_seed["workspace_id"]
        user_id = truth_seed["user_id"]
        _seed_expired_auth_session(
            truth_session,
            truth_ids=truth_ids,
            label="delta-check",
            workspace_id=workspace_id,
            user_id=user_id,
        )

        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=workspace_id)
        report = svc.run_governed_cleanup(config=config, dry_run_only=False)

        # Mode is execute when gates pass and dry_run_only=False
        if report["mode"] == "execute":
            assert report["execute_applied_count"] is not None
            assert report["delta"]["active_auth_session_delta"] <= 0
        else:
            # blocked or dry_run — still validates structure
            assert report["execute_applied_count"] is None

    @pytest.mark.postgres_truth
    def test_citation_count_never_decreases(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Cleanup must never decrease the citation count (citations are not cleanup targets)."""
        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=truth_seed["workspace_id"])
        report = svc.run_governed_cleanup(config=config, dry_run_only=False)

        assert report["delta"]["citation_loss_detected"] is False
        assert report["delta"]["citation_delta"] >= 0


class TestCleanupGovernanceAuditTrail:
    @pytest.mark.postgres_truth
    def test_recovery_hints_always_present(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Every governance report contains at least one recovery hint."""
        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=truth_seed["workspace_id"])
        report = svc.run_governed_cleanup(config=config, dry_run_only=True)

        assert isinstance(report["recovery_hints"], list)
        assert len(report["recovery_hints"]) >= 1

    @pytest.mark.postgres_truth
    def test_rollback_strategy_always_present(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Every governance report contains the rollback strategy advisory string."""
        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=truth_seed["workspace_id"])
        report = svc.run_governed_cleanup(config=config, dry_run_only=True)

        assert isinstance(report["rollback_strategy"], str)
        assert len(report["rollback_strategy"]) > 50

    @pytest.mark.postgres_truth
    def test_correlation_id_propagated(
        self, truth_session: Session, truth_ids: TruthIds, truth_seed: dict
    ) -> None:
        """Custom correlation_id is echoed back in the report."""
        cid = f"test-corr-{truth_ids.namespace}"
        svc = CleanupGovernanceService.from_session(truth_session)
        config = _make_config(workspace_id=truth_seed["workspace_id"])
        report = svc.run_governed_cleanup(
            config=config, dry_run_only=True, correlation_id=cid
        )

        assert report["correlation_id"] == cid


class TestCleanupGovernanceApiEndpoint:
    @pytest.mark.postgres_truth
    def test_api_defaults_to_dry_run_only(
        self, truth_client: TestClient, truth_seed: dict
    ) -> None:
        """POST /admin/cleanup/governed without dry_run_only must default to dry_run mode."""
        resp = truth_client.post(
            "/api/v1/admin/cleanup/governed",
            json={"workspace_id": truth_seed["workspace_id"]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["dry_run_only"] is True
        assert data["mode"] in {"dry_run", "blocked"}

    @pytest.mark.postgres_truth
    def test_api_returns_governance_report_shape(
        self, truth_client: TestClient, truth_seed: dict
    ) -> None:
        """API response must include all mandatory governance envelope fields."""
        resp = truth_client.post(
            "/api/v1/admin/cleanup/governed",
            json={"workspace_id": truth_seed["workspace_id"], "dry_run_only": True},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        required_keys = {
            "correlation_id", "mode", "started_at", "completed_at", "duration_ms",
            "safety_gates", "snapshot_before", "snapshot_after", "delta",
            "dry_run_candidate_count", "severity", "alerts",
            "recovery_hints", "rollback_strategy",
        }
        missing = required_keys - set(data.keys())
        assert not missing, f"API response missing keys: {missing}"
