"""
Queue Aging & Starvation Detection Service.

Detects: stalled pending jobs, retry loops, stuck running jobs,
dead-letter accumulation, and workspace starvation.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.documents import BackgroundJob


# Alert thresholds (seconds unless noted)
STALLED_PENDING_SECONDS = 300          # pending > 5 min → stalled
STUCK_RUNNING_SECONDS = 600            # running lock > 10 min → stuck
DEAD_LETTER_WARNING = 5
DEAD_LETTER_CRITICAL = 20
HIGH_RETRY_MIN_ATTEMPTS = 2            # attempt_count >= this → retry-loop candidate


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = max(0, int(len(sorted_vals) * 0.95) - 1)
    return round(sorted_vals[idx], 1)


class QueueAgingService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "QueueAgingService":
        return cls(session)

    def get_aging_report(self, *, workspace_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        stalled_threshold = timedelta(seconds=STALLED_PENDING_SECONDS)
        stuck_threshold = timedelta(seconds=STUCK_RUNNING_SECONDS)

        # ── 1. Pending jobs ──────────────────────────────────────────────────
        pending_rows = self._session.execute(
            select(BackgroundJob.id, BackgroundJob.created_at)
            .where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "pending",
            )
        ).all()

        pending_ages = [
            (now - row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None
             else now - row.created_at).total_seconds()
            for row in pending_rows
        ]
        pending_count = len(pending_ages)
        oldest_pending = max(pending_ages, default=None)
        stalled_pending_count = sum(1 for a in pending_ages if a > STALLED_PENDING_SECONDS)

        # ── 2. Retryable / retry loops ───────────────────────────────────────
        retryable_rows = self._session.execute(
            select(BackgroundJob.id, BackgroundJob.attempt_count, BackgroundJob.error_code)
            .where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "retryable",
            )
        ).all()

        retryable_count = len(retryable_rows)
        max_attempt = max((r.attempt_count for r in retryable_rows), default=0)
        high_retry_count = sum(
            1 for r in retryable_rows
            if r.attempt_count >= max(HIGH_RETRY_MIN_ATTEMPTS, settings.background_job_max_attempts - 1)
        )
        retry_error_codes: dict[str, int] = {}
        for r in retryable_rows:
            if r.error_code:
                retry_error_codes[r.error_code] = retry_error_codes.get(r.error_code, 0) + 1

        # ── 3. Dead letters ──────────────────────────────────────────────────
        dead_rows = self._session.execute(
            select(BackgroundJob.id, BackgroundJob.finished_at)
            .where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "dead_letter",
            )
        ).all()

        dead_letter_count = len(dead_rows)
        dead_letter_oldest: float | None = None
        if dead_rows:
            oldest_ts = min(
                r.finished_at for r in dead_rows if r.finished_at is not None
            ) if any(r.finished_at for r in dead_rows) else None
            if oldest_ts:
                ts = oldest_ts.replace(tzinfo=UTC) if oldest_ts.tzinfo is None else oldest_ts
                dead_letter_oldest = round((now - ts).total_seconds(), 1)

        # ── 4. Stuck running jobs ────────────────────────────────────────────
        running_rows = self._session.execute(
            select(BackgroundJob.id, BackgroundJob.locked_at, BackgroundJob.started_at)
            .where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "running",
            )
        ).all()

        running_count = len(running_rows)
        stuck_running_count = 0
        oldest_running: float | None = None
        for r in running_rows:
            ref = r.locked_at or r.started_at
            if ref is not None:
                ref_utc = ref.replace(tzinfo=UTC) if ref.tzinfo is None else ref
                age = (now - ref_utc).total_seconds()
                if oldest_running is None or age > oldest_running:
                    oldest_running = round(age, 1)
                if age > STUCK_RUNNING_SECONDS:
                    stuck_running_count += 1

        # ── 5. Workspace starvation (global view) ────────────────────────────
        starvation_notes, starvation_detected = self._detect_starvation(
            workspace_id=workspace_id, now=now
        )

        # ── Alerts + severity ────────────────────────────────────────────────
        alerts: list[str] = []
        if stuck_running_count > 0:
            alerts.append(
                f"{stuck_running_count} running job(s) stuck "
                f"(locked_at >{STUCK_RUNNING_SECONDS}s ago) — stale advisory lock suspected"
            )
        if high_retry_count > 0:
            codes = ", ".join(f"{k}×{v}" for k, v in sorted(retry_error_codes.items()))
            alerts.append(
                f"{high_retry_count} job(s) in retry loop "
                f"(attempt_count ≥ {settings.background_job_max_attempts - 1}) "
                f"[{codes or 'no error code'}]"
            )
        if dead_letter_count >= DEAD_LETTER_CRITICAL:
            alerts.append(
                f"CRITICAL: {dead_letter_count} dead-letter jobs awaiting replay "
                f"(threshold: {DEAD_LETTER_CRITICAL})"
            )
        elif dead_letter_count >= DEAD_LETTER_WARNING:
            alerts.append(
                f"{dead_letter_count} dead-letter jobs awaiting replay "
                f"(threshold: {DEAD_LETTER_WARNING})"
            )
        if stalled_pending_count > 0:
            alerts.append(
                f"{stalled_pending_count} pending job(s) stalled "
                f"(age >{STALLED_PENDING_SECONDS}s) — worker may not be running"
            )
        if starvation_detected:
            alerts.extend(starvation_notes)

        severity = "ok"
        if stuck_running_count > 0 or dead_letter_count >= DEAD_LETTER_CRITICAL or high_retry_count > 0:
            severity = "critical"
        elif stalled_pending_count > 0 or dead_letter_count >= DEAD_LETTER_WARNING or starvation_detected:
            severity = "warning"

        return {
            "checked_at": now,
            "workspace_id": workspace_id,
            "pending_count": pending_count,
            "pending_age_p95_seconds": _p95(pending_ages),
            "oldest_pending_age_seconds": round(oldest_pending, 1) if oldest_pending is not None else None,
            "stalled_pending_count": stalled_pending_count,
            "retryable_count": retryable_count,
            "max_retry_attempt_count": max_attempt,
            "high_retry_count": high_retry_count,
            "dead_letter_count": dead_letter_count,
            "dead_letter_oldest_age_seconds": dead_letter_oldest,
            "running_count": running_count,
            "stuck_running_count": stuck_running_count,
            "oldest_running_age_seconds": oldest_running,
            "starvation_detected": starvation_detected,
            "starvation_notes": starvation_notes,
            "severity": severity,
            "alerts": alerts,
            "thresholds": {
                "stalled_pending_seconds": STALLED_PENDING_SECONDS,
                "stuck_running_seconds": STUCK_RUNNING_SECONDS,
                "dead_letter_warning": DEAD_LETTER_WARNING,
                "dead_letter_critical": DEAD_LETTER_CRITICAL,
                "max_attempts": settings.background_job_max_attempts,
            },
        }

    def _detect_starvation(
        self, *, workspace_id: str, now: datetime
    ) -> tuple[list[str], bool]:
        """
        A workspace is starved if it has pending jobs older than STALLED_PENDING_SECONDS
        while other workspaces currently have running jobs.
        """
        stale_cutoff = now - timedelta(seconds=STALLED_PENDING_SECONDS)

        # Workspaces with stale pending jobs (including ours)
        stale_pending = self._session.execute(
            text(
                """
                SELECT workspace_id, count(*) as cnt
                FROM background_jobs
                WHERE status = 'pending' AND created_at < :cutoff
                GROUP BY workspace_id
                """
            ),
            {"cutoff": stale_cutoff},
        ).all()

        if not stale_pending:
            return [], False

        # Workspaces with currently running jobs
        running_workspaces = {
            row[0]
            for row in self._session.execute(
                text(
                    "SELECT DISTINCT workspace_id FROM background_jobs WHERE status = 'running'"
                )
            ).all()
        }

        notes: list[str] = []
        for row in stale_pending:
            ws_id = str(row[0])
            if ws_id != workspace_id:
                continue
            if running_workspaces and ws_id not in running_workspaces:
                notes.append(
                    f"Workspace starvation: {row[1]} pending job(s) stalled while "
                    f"{len(running_workspaces)} other workspace(s) have running jobs"
                )

        return notes, bool(notes)
