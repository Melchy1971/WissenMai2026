"""
Queue Aging & Starvation Detection — Truth Tests.

Each test seeds a specific failure mode into background_jobs and verifies that
QueueAgingService detects it correctly with the right severity and alert text.

All tests use truth_session (rolled back after test) so no cleanup is needed.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.queue_aging_service import (
    DEAD_LETTER_CRITICAL,
    DEAD_LETTER_WARNING,
    STALLED_PENDING_SECONDS,
    STUCK_RUNNING_SECONDS,
    QueueAgingService,
)
from tests.postgres_truth.support import TruthIds


pytestmark = [pytest.mark.postgres_truth, pytest.mark.queue_aging]

_PAYLOAD = json.dumps({"filename": "truth-aging.txt", "mime_type": "text/plain", "temp_file_path": "/tmp/x"})


def _insert_job(session: Session, job_id: str, *, workspace_id: str, user_id: str,
                status: str, attempt_count: int = 0, locked_at=None,
                started_at=None, finished_at=None, created_at=None,
                error_code: str | None = None) -> None:
    now = datetime.now(UTC)
    session.execute(
        text(
            """
            insert into background_jobs (
                id, job_type, status, workspace_id, requested_by_user_id, payload, result,
                progress_current, progress_total, progress_message, error_code, error_message,
                attempt_count, locked_at, locked_by, created_at, started_at, finished_at
            ) values (
                :id, 'document_import', :status, :workspace_id, :user_id,
                cast(:payload as jsonb), null, 0, 1, :status, :error_code, null,
                :attempt_count, :locked_at, :locked_by, :created_at, :started_at, :finished_at
            )
            """
        ),
        {
            "id": job_id,
            "status": status,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "payload": _PAYLOAD,
            "error_code": error_code,
            "attempt_count": attempt_count,
            "locked_at": locked_at,
            "locked_by": "test-worker" if locked_at else None,
            "created_at": created_at or now,
            "started_at": started_at,
            "finished_at": finished_at,
        },
    )


# ── 1. Clean queue ────────────────────────────────────────────────────────────

def test_aging_empty_queue_reports_ok(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["severity"] == "ok"
    assert report["alerts"] == []
    assert report["pending_count"] == 0
    assert report["stuck_running_count"] == 0
    assert report["dead_letter_count"] == 0
    assert report["starvation_detected"] is False


# ── 2. Stalled pending jobs ───────────────────────────────────────────────────

def test_aging_detects_stalled_pending_job(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    stale_created_at = datetime.now(UTC) - timedelta(seconds=STALLED_PENDING_SECONDS + 60)
    _insert_job(
        truth_session,
        truth_ids.job_id("stalled-pending"),
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        status="pending",
        created_at=stale_created_at,
    )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["stalled_pending_count"] == 1
    assert report["pending_count"] == 1
    assert report["severity"] in {"warning", "critical"}
    assert any("stalled" in a.lower() for a in report["alerts"])


def test_aging_fresh_pending_job_is_not_stalled(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    fresh_created_at = datetime.now(UTC) - timedelta(seconds=10)
    _insert_job(
        truth_session,
        truth_ids.job_id("fresh-pending"),
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        status="pending",
        created_at=fresh_created_at,
    )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["stalled_pending_count"] == 0
    assert report["pending_count"] == 1


# ── 3. p95 age metric ─────────────────────────────────────────────────────────

def test_aging_p95_covers_oldest_jobs(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    now = datetime.now(UTC)
    # Insert 10 pending jobs with ages 10s, 20s, 30s, ... 100s
    for i in range(1, 11):
        _insert_job(
            truth_session,
            truth_ids.job_id(f"p95-job-{i}"),
            workspace_id=truth_seed["workspace_id"],
            user_id=truth_seed["user_id"],
            status="pending",
            created_at=now - timedelta(seconds=i * 10),
        )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["pending_count"] == 10
    assert report["pending_age_p95_seconds"] is not None
    # p95 of [10,20,...,100] → index 9 (sorted), which is 100s or close
    assert report["pending_age_p95_seconds"] >= 90
    assert report["oldest_pending_age_seconds"] >= 95  # oldest is ~100s


# ── 4. Retry loops ────────────────────────────────────────────────────────────

def test_aging_detects_high_attempt_retryable_job(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    now = datetime.now(UTC)
    _insert_job(
        truth_session,
        truth_ids.job_id("retry-loop"),
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        status="retryable",
        attempt_count=2,  # = max_attempts - 1 (3-1=2) → retry loop
        finished_at=now - timedelta(seconds=60),
        error_code="IMPORT_FAILED",
    )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["retryable_count"] == 1
    assert report["high_retry_count"] == 1
    assert report["max_retry_attempt_count"] == 2
    assert report["severity"] == "critical"
    assert any("retry loop" in a.lower() for a in report["alerts"])
    assert any("IMPORT_FAILED" in a for a in report["alerts"])


def test_aging_low_attempt_retryable_is_not_loop(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    now = datetime.now(UTC)
    _insert_job(
        truth_session,
        truth_ids.job_id("low-attempt-retry"),
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        status="retryable",
        attempt_count=1,
        finished_at=now - timedelta(seconds=60),
        error_code="IMPORT_FAILED",
    )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["retryable_count"] == 1
    assert report["high_retry_count"] == 0
    # severity must not be critical from this alone
    assert report["severity"] in {"ok", "warning"}


# ── 5. Dead letter accumulation ───────────────────────────────────────────────

def test_aging_dead_letter_warning_threshold(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    now = datetime.now(UTC)
    for i in range(DEAD_LETTER_WARNING):
        _insert_job(
            truth_session,
            truth_ids.job_id(f"dead-letter-warn-{i}"),
            workspace_id=truth_seed["workspace_id"],
            user_id=truth_seed["user_id"],
            status="dead_letter",
            attempt_count=3,
            finished_at=now - timedelta(hours=i + 1),
            error_code="IMPORT_FAILED",
        )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["dead_letter_count"] == DEAD_LETTER_WARNING
    assert report["severity"] == "warning"
    assert any("dead-letter" in a.lower() or "dead_letter" in a.lower() for a in report["alerts"])


def test_aging_dead_letter_critical_threshold(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    now = datetime.now(UTC)
    for i in range(DEAD_LETTER_CRITICAL):
        _insert_job(
            truth_session,
            truth_ids.job_id(f"dead-letter-crit-{i}"),
            workspace_id=truth_seed["workspace_id"],
            user_id=truth_seed["user_id"],
            status="dead_letter",
            attempt_count=3,
            finished_at=now - timedelta(hours=i + 1),
            error_code="IMPORT_FAILED",
        )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["dead_letter_count"] == DEAD_LETTER_CRITICAL
    assert report["severity"] == "critical"
    assert any("CRITICAL" in a for a in report["alerts"])
    assert report["dead_letter_oldest_age_seconds"] is not None
    # oldest job was inserted ~DEAD_LETTER_CRITICAL hours ago
    assert report["dead_letter_oldest_age_seconds"] >= (DEAD_LETTER_CRITICAL - 1) * 3600 - 60


# ── 6. Stuck running jobs ─────────────────────────────────────────────────────

def test_aging_detects_stuck_running_job(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    stale_locked_at = datetime.now(UTC) - timedelta(seconds=STUCK_RUNNING_SECONDS + 120)
    _insert_job(
        truth_session,
        truth_ids.job_id("stuck-running"),
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        status="running",
        attempt_count=1,
        locked_at=stale_locked_at,
        started_at=stale_locked_at,
    )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["running_count"] == 1
    assert report["stuck_running_count"] == 1
    assert report["severity"] == "critical"
    assert any("stuck" in a.lower() for a in report["alerts"])
    assert report["oldest_running_age_seconds"] >= STUCK_RUNNING_SECONDS


def test_aging_fresh_running_job_is_not_stuck(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    fresh_locked_at = datetime.now(UTC) - timedelta(seconds=30)
    _insert_job(
        truth_session,
        truth_ids.job_id("fresh-running"),
        workspace_id=truth_seed["workspace_id"],
        user_id=truth_seed["user_id"],
        status="running",
        attempt_count=1,
        locked_at=fresh_locked_at,
        started_at=fresh_locked_at,
    )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    assert report["running_count"] == 1
    assert report["stuck_running_count"] == 0
    assert report["severity"] == "ok"


# ── 7. Workspace isolation ────────────────────────────────────────────────────

def test_aging_report_does_not_count_other_workspace_jobs(
    truth_ids: TruthIds,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    # Seed a dead-letter job in the OTHER workspace
    now = datetime.now(UTC)
    for i in range(DEAD_LETTER_CRITICAL):
        _insert_job(
            truth_session,
            truth_ids.job_id(f"other-ws-dl-{i}"),
            workspace_id=truth_seed["other_workspace_id"],
            user_id=truth_seed["other_user_id"],
            status="dead_letter",
            attempt_count=3,
            finished_at=now - timedelta(hours=1),
            error_code="IMPORT_FAILED",
        )
    truth_session.commit()

    svc = QueueAgingService.from_session(truth_session)
    report = svc.get_aging_report(workspace_id=truth_seed["workspace_id"])

    # Our workspace sees 0 dead letters; other workspace's jobs don't bleed through
    assert report["dead_letter_count"] == 0
    assert report["severity"] == "ok"


# ── 8. API endpoint contract ──────────────────────────────────────────────────

def test_aging_api_endpoint_returns_200_for_admin(
    truth_client,
    truth_seed: dict[str, str],
    truth_session: Session,
) -> None:
    response = truth_client.get("/api/v1/admin/queue/aging")

    assert response.status_code == 200, f"unexpected: {response.text}"
    data = response.json()
    assert data["workspace_id"] == truth_seed["workspace_id"]
    assert data["severity"] in {"ok", "warning", "critical"}
    assert isinstance(data["alerts"], list)
    assert isinstance(data["pending_count"], int)
    assert "thresholds" in data
    assert data["thresholds"]["stalled_pending_seconds"] == STALLED_PENDING_SECONDS
