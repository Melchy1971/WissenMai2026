# Job State Machine — PRI-7

Stand: 2026-06-17
Quelle: `reports/current/job_framework_report.json`

---

## Unified Job Status

```
                    ┌─────────────┐
                    │   PENDING   │ ◄── enqueue()
                    └──────┬──────┘
                           │ claim()
                    ┌──────▼──────┐
                    │   RUNNING   │
                    └──┬──────┬───┘
                       │      │
               complete()    fail()
                       │      │
              ┌────────▼┐  ┌──▼────────────┐
              │COMPLETED│  │    FAILED     │
              └─────────┘  └──────┬────────┘
                                  │
                    attempt < max_attempts?
                         │         │
                        Yes        No
                         │         │
                  ┌──────▼──┐  ┌───▼───┐
                  │RETRYING │  │  DEAD │
                  └──────┬──┘  └───────┘
                         │ (backoff elapsed)
                         └──► PENDING
```

**CANCELLED** kann aus PENDING oder RUNNING erreicht werden:
```
PENDING ──cancel()──► CANCELLED
RUNNING ──cancel()──► CANCELLED (cooperative, max 30s)
```

---

## Status-Transitions

| Von | Nach | Trigger | Bedingung |
|-----|------|---------|-----------|
| PENDING | RUNNING | claim() | Advisory Lock erhalten |
| RUNNING | COMPLETED | complete() | Ergebnis vorhanden |
| RUNNING | FAILED | fail() | Fehler aufgetreten |
| FAILED | RETRYING | retry() | attempt < max_attempts AND Fehler ist retryable |
| RETRYING | PENDING | (backoff elapsed) | scheduled |
| RUNNING | CANCELLED | cancel() | cancelled_flag gesetzt |
| PENDING | CANCELLED | cancel() | sofort |
| FAILED | DEAD | — | attempt >= max_attempts |

---

## Retry-Backoff (Exponential)

| Attempt | Wartezeit |
|---------|-----------|
| 1. Fehler | 30s |
| 2. Fehler | 60s |
| 3. Fehler | → DEAD |

Nicht retrybar: `VALIDATION_ERROR`, `PERMISSION_DENIED`, `RESOURCE_NOT_FOUND`

---

## Timeout-Strategie

| Job-Typ | Timeout |
|---------|---------|
| import | 300s (5 min) |
| analysis | 600s (10 min) |
| export | 120s (2 min) |
| drift | 180s (3 min) |
| reindex | 900s (15 min) |

Worker prüft Heartbeat alle 30s. Kein Heartbeat nach 2× Interval → Lock freigeben, Status → FAILED.

---

## Progress Events

```
GET /api/v1/jobs/:id/events   (Server-Sent Events)
←  data: {"progress_current": 3, "progress_total": 10, "message": "Parsing..."}\n\n
←  data: {"progress_current": 7, "progress_total": 10, "message": "Chunking..."}\n\n
←  data: {"status": "completed"}\n\n
```

Polling-Fallback: `GET /api/v1/jobs/:id` alle 2s (Frontend-Standard).

---

## Dead Letter Queue

Job wechselt nach letztem fehlgeschlagenen Retry in Status `DEAD`.

Log-Event wird erzeugt:
```json
{
  "event": "JOB_DEAD",
  "job_id": "...",
  "job_type": "analysis",
  "workspace_id": "...",
  "last_error_code": "PROVIDER_TIMEOUT",
  "last_error_message": "...",
  "attempt_count": 3,
  "dead_at": "2026-06-17T..."
}
```

Dead-Jobs werden 30 Tage aufbewahrt, dann durch Cleanup-Job gelöscht.

---

## Status-Historie (Tabelle job_status_history)

```sql
CREATE TABLE job_status_history (
    id          VARCHAR PRIMARY KEY,
    job_id      VARCHAR NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
    from_status VARCHAR(32),
    to_status   VARCHAR(32) NOT NULL,
    changed_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    changed_by  VARCHAR(255),  -- worker_id oder user_id
    reason      TEXT
);
CREATE INDEX ix_job_status_history_job_id ON job_status_history (job_id, changed_at DESC);
```

---

## Job-Cleanup

```
täglich (02:00 UTC):
  DELETE FROM background_jobs
    WHERE status = 'completed' AND finished_at < NOW() - INTERVAL '7 days';
  DELETE FROM background_jobs
    WHERE status IN ('failed', 'cancelled') AND finished_at < NOW() - INTERVAL '14 days';
  DELETE FROM background_jobs
    WHERE status = 'dead' AND finished_at < NOW() - INTERVAL '30 days';
```
