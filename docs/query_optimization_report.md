# Query Optimization Report — PRI-7

Stand: 2026-06-17

---

## Kritisch — Sofortmaßnahmen

### QO-01 — GIN-Index auf search_vector fehlt

**Datei:** `backend/migrations/versions/20260504_0011_chunk_search_vector.py`

Migration erstellt die `TSVECTOR`-Spalte, aber keinen Index. Jede FTS-Suchanfrage läuft als Sequential Scan.

**Fix — Migration 0026:**
```sql
CREATE INDEX CONCURRENTLY ix_chunks_search_vector
ON document_chunks USING GIN (search_vector);

CREATE INDEX ix_topics_workspace_status_created
ON topics (workspace_id, status, created_at DESC);

CREATE INDEX ix_analysis_jobs_workspace_created
ON analysis_jobs (workspace_id, created_at DESC);

CREATE INDEX ix_export_jobs_workspace_status
ON export_jobs (workspace_id, status, created_at DESC);
```

---

### QO-02 — Unified Search: Python-seitige Pagination

**Datei:** `backend/app/repositories/search.py: search_unified()`

**Problem:**
```python
records = []
records.extend(self._search_topics(...))   # unbegrenzt
records.extend(self._search_documents(...)) # unbegrenzt
records.extend(self._search_chunks_unified(...)) # limit=200
total = len(records)          # erst HIER begrenzt
page = records[offset:offset+limit]  # Python-Slice
```

**Ursache:** Drei Sub-Queries mit unabhängigen Limits, Python-seitiges Merge, dann Slice.

**Fix:**
```python
# Option A: Pro Sub-Query limit*2 laden, dann merge
chunk_limit = min(limit * 2, 200)
# Option B: Dedizierte Search-Tabelle mit UNION ALL VIEW
# Option C: Elasticsearch/Typesense für Cross-Entity-Suche
```

**Sofort-Mitigation (ohne große Refaktorierung):**
```python
# Harte Limits per Sub-Query setzen
topics_results = self._search_topics(..., limit=limit + offset)
docs_results = self._search_documents(..., limit=limit + offset)
chunks_results = self._search_chunks_unified(..., limit=(limit + offset) * 2)
```

---

## Hoch — Diese Iteration

### QO-03 — Topic-Tag N+1 in Search

**Datei:** `backend/app/repositories/search.py: _search_topics()`

**Problem:**
```python
for t in topics:
    tag_rows = self._session.execute(
        select(TopicTag.tag_id).where(TopicTag.topic_id == t.id)
    ).scalars().all()  # 1 Query pro Topic → N Queries
```

**Fix:**
```python
topic_ids = [t.id for t in topics]
tag_map = {}
for tag_id, topic_id in self._session.execute(
    select(TopicTag.tag_id, TopicTag.topic_id)
    .where(TopicTag.topic_id.in_(topic_ids))
).all():
    tag_map.setdefault(topic_id, []).append(tag_id)
```

---

### QO-04 — Dashboard Activity: UNION ALL statt 5 Queries

**Datei:** `backend/app/services/dashboard_service.py: list_activity()`

**Problem:** 5 separate `session.scalars(select(...))` für verschiedene Entity-Typen, dann Python-seitiges Merge.

**Fix:**
```sql
SELECT 'document' as item_type, id, title, lifecycle_status as status, created_at
FROM documents WHERE workspace_id = :wid
UNION ALL
SELECT 'import', id, payload_->>'filename', status, created_at
FROM background_jobs WHERE workspace_id = :wid AND job_type = 'document_import'
UNION ALL
SELECT 'analysis', id, CAST(id as varchar), status, created_at
FROM analysis_jobs WHERE workspace_id = :wid
ORDER BY created_at DESC LIMIT 20
```

---

### QO-05 — AnalysisJob Lazy-Load bei Listings

**Datei:** `backend/app/models/analysis.py`, `backend/app/api/v1/analysis.py`

**Problem:** `AnalysisJob.result` und `.suggestions` werden beim List-Endpoint lazy-geladen.

**Fix:**
```python
from sqlalchemy.orm import selectinload

stmt = (
    select(AnalysisJob)
    .where(AnalysisJob.workspace_id == workspace_id)
    .options(selectinload(AnalysisJob.result))
    .order_by(AnalysisJob.created_at.desc())
    .limit(limit)
    .offset(offset)
)
```

---

## Mittel — Nächste Iteration

### QO-06 — Cursor-basierte Pagination (Documents)

**Datei:** `backend/app/repositories/documents.py`

**Aktuelle API:** `GET /documents?limit=20&offset=40`

**Ziel-API:** `GET /documents?limit=20&cursor=<token>`

```python
# Cursor = base64(created_at.isoformat() + "|" + id)
import base64

def encode_cursor(created_at: datetime, id: str) -> str:
    raw = f"{created_at.isoformat()}|{id}"
    return base64.b64encode(raw.encode()).decode()

def decode_cursor(cursor: str) -> tuple[datetime, str]:
    raw = base64.b64decode(cursor.encode()).decode()
    ts_str, id = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), id

# Query:
# WHERE (created_at, id) < (cursor_ts, cursor_id)
# ORDER BY created_at DESC, id DESC
# LIMIT limit
```

---

### QO-07 — Response Caching: Dashboard Summary

**Datei:** `backend/app/api/v1/dashboard.py`

```python
import hashlib
from functools import lru_cache
from datetime import datetime, timedelta

_summary_cache: dict[str, tuple[datetime, DashboardSummary]] = {}
CACHE_TTL = timedelta(seconds=30)

def get_cached_summary(workspace_id: str, session: Session) -> DashboardSummary:
    now = datetime.utcnow()
    if workspace_id in _summary_cache:
        cached_at, summary = _summary_cache[workspace_id]
        if now - cached_at < CACHE_TTL:
            return summary
    summary = DashboardSummaryService(session).get_summary(workspace_id=workspace_id)
    _summary_cache[workspace_id] = (now, summary)
    return summary
```

---

### QO-08 — Job-Cleanup Hintergrundjob

**Datei:** `backend/app/services/jobs/background_jobs.py`

Fehlend: Kein Cleanup für alte Jobs.

```python
def cleanup_old_jobs(self, *, max_age_days: int = 7) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    result = self._session.execute(
        delete(BackgroundJob)
        .where(
            BackgroundJob.status.in_(["completed", "failed"]),
            BackgroundJob.finished_at < cutoff,
        )
    )
    self._session.commit()
    return result.rowcount
```

---

## Gesamtstatus

| Optimierung | Status | Aufwand | Priorität |
|------------|--------|---------|-----------|
| GIN-Index (QO-01) | OFFEN | XS | KRITISCH |
| Search Pagination (QO-02) | OFFEN | M | KRITISCH |
| Topic-Tag N+1 (QO-03) | OFFEN | S | HOCH |
| Dashboard UNION ALL (QO-04) | OFFEN | S | HOCH |
| AnalysisJob selectinload (QO-05) | OFFEN | S | HOCH |
| Cursor Pagination (QO-06) | OFFEN | L | MITTEL |
| Response Caching (QO-07) | OFFEN | M | MITTEL |
| Job Cleanup (QO-08) | OFFEN | S | MITTEL |

Migration 0026 ist der kritische nächste Schritt — deckt QO-01 und drei weitere Indexes ab.
