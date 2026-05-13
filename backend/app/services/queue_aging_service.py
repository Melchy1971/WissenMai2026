"""
Queue Aging & Starvation Detection Service.

Detects stalled pending jobs, retry loops, stuck running jobs,
dead-letter accumulation, backlog pressure, and workspace starvation.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.documents import BackgroundJob


STALLED_PENDING_SECONDS = 300
STUCK_RUNNING_SECONDS = 600
DEAD_LETTER_WARNING = 5
DEAD_LETTER_CRITICAL = 20
HIGH_RETRY_MIN_ATTEMPTS = 2
BACKLOG_WARNING = 15
BACKLOG_CRITICAL = 25
RETRY_RATE_WARNING_PER_HOUR = 5.0
DEAD_LETTER_GROWTH_WINDOW_HOURS = 24


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = max(0, int(len(sorted_vals) * 0.95) - 1)
    return round(sorted_vals[idx], 1)


def _age_seconds(now: datetime, value: datetime | None) -> float | None:
    if value is None:
        return None
    ref = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return round((now - ref).total_seconds(), 1)


def _after(value: datetime | None, cutoff: datetime) -> bool:
    if value is None:
        return False
    ref = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return ref >= cutoff


class QueueAgingService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "QueueAgingService":
        return cls(session)

    def get_aging_report(self, *, workspace_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)

        pending_rows = self._session.execute(
            select(BackgroundJob.id, BackgroundJob.created_at).where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "pending",
            )
        ).all()
        pending_ages = [
            age
            for row in pending_rows
            if (age := _age_seconds(now, row.created_at)) is not None
        ]
        pending_count = len(pending_ages)
        oldest_pending = max(pending_ages, default=None)
        stalled_pending_count = sum(1 for age in pending_ages if age > STALLED_PENDING_SECONDS)

        retryable_rows = self._session.execute(
            select(
                BackgroundJob.id,
                BackgroundJob.attempt_count,
                BackgroundJob.error_code,
                BackgroundJob.created_at,
                BackgroundJob.finished_at,
            ).where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "retryable",
            )
        ).all()
        retryable_count = len(retryable_rows)
        retryable_ages = [
            age
            for row in retryable_rows
            if (age := _age_seconds(now, row.finished_at or row.created_at)) is not None
        ]
        max_attempt = max((row.attempt_count for row in retryable_rows), default=0)
        high_retry_count = sum(
            1
            for row in retryable_rows
            if row.attempt_count
            >= max(HIGH_RETRY_MIN_ATTEMPTS, settings.background_job_max_attempts - 1)
        )
        retry_window_start = now - timedelta(hours=1)
        retry_rate_per_hour = float(
            sum(
                1
                for row in retryable_rows
                if row.attempt_count > 0
                and _after(row.finished_at or row.created_at, retry_window_start)
            )
        )
        retry_error_codes: dict[str, int] = {}
        for row in retryable_rows:
            if row.error_code:
                retry_error_codes[row.error_code] = retry_error_codes.get(row.error_code, 0) + 1

        dead_rows = self._session.execute(
            select(
                BackgroundJob.id,
                BackgroundJob.created_at,
                BackgroundJob.finished_at,
            ).where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "dead_letter",
            )
        ).all()
        dead_letter_count = len(dead_rows)
        dead_letter_ages = [
            age
            for row in dead_rows
            if (age := _age_seconds(now, row.finished_at or row.created_at)) is not None
        ]
        dead_letter_growth_start = now - timedelta(hours=DEAD_LETTER_GROWTH_WINDOW_HOURS)
        dead_letter_growth_24h = sum(
            1
            for row in dead_rows
            if _after(row.finished_at or row.created_at, dead_letter_growth_start)
        )
        dead_letter_oldest: float | None = None
        if dead_letter_ages:
            dead_letter_oldest = max(dead_letter_ages)

        running_rows = self._session.execute(
            select(
                BackgroundJob.id,
                BackgroundJob.created_at,
                BackgroundJob.locked_at,
                BackgroundJob.started_at,
            ).where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "running",
            )
        ).all()
        running_count = len(running_rows)
        running_ages: list[float] = []
        stuck_running_count = 0
        oldest_running: float | None = None
        for row in running_rows:
            age = _age_seconds(now, row.locked_at or row.started_at or row.created_at)
            if age is None:
                continue
            running_ages.append(age)
            oldest_running = age if oldest_running is None else max(oldest_running, age)
            if age > STUCK_RUNNING_SECONDS:
                stuck_running_count += 1

        queue_backlog_count = pending_count + retryable_count + dead_letter_count + running_count
        queue_age_p95_seconds = _p95(pending_ages + retryable_ages + dead_letter_ages + running_ages)
        backlog_growth_24h = self._count_recent_backlog(
            workspace_id=workspace_id,
            created_since=now - timedelta(hours=24),
        )
        workspace_queue_distribution = self._workspace_queue_distribution()

        starvation_notes, starvation_detected = self._detect_starvation(
            workspace_id=workspace_id, now=now
        )

        alerts: list[str] = []
        if stuck_running_count > 0:
            alerts.append(
                f"{stuck_running_count} running job(s) stuck "
                f"(locked_at >{STUCK_RUNNING_SECONDS}s ago) - stale advisory lock suspected"
            )
        if high_retry_count > 0:
            codes = ", ".join(f"{key}x{value}" for key, value in sorted(retry_error_codes.items()))
            alerts.append(
                f"{high_retry_count} job(s) in retry loop "
                f"(attempt_count >= {settings.background_job_max_attempts - 1}) "
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
        if queue_backlog_count >= BACKLOG_CRITICAL:
            alerts.append(
                f"CRITICAL: queue backlog contains {queue_backlog_count} active job(s) "
                f"(threshold: {BACKLOG_CRITICAL})"
            )
        elif queue_backlog_count >= BACKLOG_WARNING:
            alerts.append(
                f"Queue backlog contains {queue_backlog_count} active job(s) "
                f"(threshold: {BACKLOG_WARNING})"
            )
        if retry_rate_per_hour > RETRY_RATE_WARNING_PER_HOUR:
            alerts.append(
                f"Retry rate is {retry_rate_per_hour:.1f}/h "
                f"(threshold: {RETRY_RATE_WARNING_PER_HOUR:.1f}/h)"
            )
        if dead_letter_growth_24h > 0:
            alerts.append(
                f"Dead-letter growth: {dead_letter_growth_24h} new job(s) in the last "
                f"{DEAD_LETTER_GROWTH_WINDOW_HOURS}h"
            )
        if stalled_pending_count > 0:
            alerts.append(
                f"{stalled_pending_count} pending job(s) stalled "
                f"(age >{STALLED_PENDING_SECONDS}s) - worker may not be running"
            )
        if starvation_detected:
            alerts.extend(starvation_notes)

        severity = "ok"
        if (
            stuck_running_count > 0
            or dead_letter_count >= DEAD_LETTER_CRITICAL
            or high_retry_count > 0
            or queue_backlog_count >= BACKLOG_CRITICAL
        ):
            severity = "critical"
        elif (
            stalled_pending_count > 0
            or dead_letter_count >= DEAD_LETTER_WARNING
            or starvation_detected
            or queue_backlog_count >= BACKLOG_WARNING
            or retry_rate_per_hour > RETRY_RATE_WARNING_PER_HOUR
            or dead_letter_growth_24h > 0
        ):
            severity = "warning"

        return {
            "checked_at": now,
            "workspace_id": workspace_id,
            "queue_backlog_count": queue_backlog_count,
            "queue_age_p95_seconds": queue_age_p95_seconds,
            "backlog_growth_24h": backlog_growth_24h,
            "pending_count": pending_count,
            "pending_age_p95_seconds": _p95(pending_ages),
            "oldest_pending_age_seconds": oldest_pending,
            "stalled_pending_count": stalled_pending_count,
            "retryable_count": retryable_count,
            "max_retry_attempt_count": max_attempt,
            "high_retry_count": high_retry_count,
            "retry_rate_per_hour": retry_rate_per_hour,
            "dead_letter_count": dead_letter_count,
            "dead_letter_oldest_age_seconds": dead_letter_oldest,
            "dead_letter_growth_24h": dead_letter_growth_24h,
            "running_count": running_count,
            "stuck_running_count": stuck_running_count,
            "oldest_running_age_seconds": oldest_running,
            "starvation_detected": starvation_detected,
            "starvation_notes": starvation_notes,
            "workspace_queue_distribution": workspace_queue_distribution,
            "severity": severity,
            "alerts": alerts,
            "thresholds": {
                "stalled_pending_seconds": STALLED_PENDING_SECONDS,
                "stuck_running_seconds": STUCK_RUNNING_SECONDS,
                "dead_letter_warning": DEAD_LETTER_WARNING,
                "dead_letter_critical": DEAD_LETTER_CRITICAL,
                "max_attempts": settings.background_job_max_attempts,
                "backlog_warning": BACKLOG_WARNING,
                "backlog_critical": BACKLOG_CRITICAL,
                "retry_rate_warning_per_hour": RETRY_RATE_WARNING_PER_HOUR,
                "dead_letter_growth_window_hours": DEAD_LETTER_GROWTH_WINDOW_HOURS,
            },
        }

    def _count_recent_backlog(self, *, workspace_id: str, created_since: datetime) -> int:
        return int(
            self._session.execute(
                text(
                    """
                    SELECT count(*)
                    FROM background_jobs
                    WHERE workspace_id = :workspace_id
                      AND status IN ('pending', 'running', 'retryable', 'dead_letter')
                      AND created_at >= :created_since
                    """
                ),
                {"workspace_id": workspace_id, "created_since": created_since},
            ).scalar_one()
        )

    def _workspace_queue_distribution(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT workspace_id, status, count(*) AS cnt
                FROM background_jobs
                WHERE status IN ('pending', 'running', 'retryable', 'dead_letter')
                GROUP BY workspace_id, status
                ORDER BY workspace_id
                """
            )
        ).all()

        by_workspace: dict[str, dict[str, Any]] = {}
        for workspace_id, status, count in rows:
            item = by_workspace.setdefault(
                str(workspace_id),
                {
                    "workspace_id": str(workspace_id),
                    "pending": 0,
                    "running": 0,
                    "retryable": 0,
                    "dead_letter": 0,
                    "backlog": 0,
                    "backlog_share": 0.0,
                },
            )
            item[str(status)] = int(count)
            item["backlog"] += int(count)

        total_backlog = sum(item["backlog"] for item in by_workspace.values())
        for item in by_workspace.values():
            item["backlog_share"] = (
                round(item["backlog"] / total_backlog, 4) if total_backlog else 0.0
            )

        return sorted(by_workspace.values(), key=lambda item: item["workspace_id"])

    def _detect_starvation(
        self, *, workspace_id: str, now: datetime
    ) -> tuple[list[str], bool]:
        """
        A workspace is starved if it has pending jobs older than STALLED_PENDING_SECONDS
        while other workspaces currently have running jobs.
        """
        stale_cutoff = now - timedelta(seconds=STALLED_PENDING_SECONDS)

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

        running_workspaces = {
            row[0]
            for row in self._session.execute(
                text("SELECT DISTINCT workspace_id FROM background_jobs WHERE status = 'running'")
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
