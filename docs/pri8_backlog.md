# PRI-8 Backlog — Blockerbehebung

Stand: 2026-06-17
Trigger: GA Final Gate = BLOCKED
Ziel: GA_READY (Maturity >= 90)
Quelle: `reports/current/ga_final_gate_report.json`, `reports/current/release_gate.json`

---

## Blocker-Übersicht

| ID | Typ | Titel | Aufwand | Priorität | Entsperrt |
|----|-----|-------|---------|-----------|-----------|
| SCGB-01 | EXTERN | TEST_DATABASE_URL (DevOps) | — | 1 (Blocker-Kette) | GA-06, GA-07, GA-10 |
| GA-PERF-01 | INTERN | GIN-Index auf search_vector | S | 2 | GA-05, Maturity +15 |
| GA-SEC-01 | INTERN | Content Security Policy | S | 3 | GA-03 |
| GA-OBS-01 | INTERN | Prometheus /metrics + JSON-Logging | M | 4 | GA-08, Maturity +25 |
| GA-TEST-01 | INTERN+EXTERN | Integrations-Test-Suite | M | 5 (nach SCGB-01) | GA-10 |
| SCGB-02 | EXTERN | NAV_ITEMS (PO) | — | 6 | — |

---

## Detailbeschreibungen

### SCGB-01 — TEST_DATABASE_URL (DevOps)

**Problem:** Netzwerkzugriff auf Test-PostgreSQL-Instanz nicht konfiguriert.
**Auswirkung:** Integrations-Tests, Backup-Tests, Restore-Tests gesperrt.
**Aktion:** DevOps stellt `TEST_DATABASE_URL` in CI-Umgebung bereit.
**Kein Code-Aufwand** auf Anwendungsseite.

---

### GA-PERF-01 — GIN-Index auf document_chunks.search_vector

**Problem:** Volltext-Index fehlt. Suchanfragen führen zu O(n)-Tabellen-Scan.
**Auswirkung:** Performance-Kriterium FAIL. Maturity-Dimension "search_quality": 45/100.

**Migration (neu anlegen):**
```sql
-- backend/migrations/versions/20260618_0027_gin_index_search_vector.py
CREATE INDEX CONCURRENTLY ix_document_chunks_search_vector_gin
  ON document_chunks USING GIN (search_vector);
```

**Geschätzter Impact:** Suchanfragen bei 10k+ Chunks: von mehreren Sekunden auf < 100ms.

---

### GA-SEC-01 — Content Security Policy

**Problem:** HTTP-Header `Content-Security-Policy` fehlt.
**Auswirkung:** Security-Kriterium FAIL. XSS-Risiko erhöht.

**Implementierung:**
```python
# backend/app/core/security_headers.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response
```

---

### GA-OBS-01 — Prometheus /metrics + Strukturiertes Logging

**Problem:** Kein Monitoring-Endpoint, kein strukturiertes Logging.
**Auswirkung:** Monitoring-Kriterium FAIL. Observability-Dimension: 35/100.

**Implementierung:**
```python
# pip install prometheus-client python-json-logger
# backend/app/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["method", "path"])
JOB_QUEUE_DEPTH = Gauge("job_queue_depth", "Jobs in queue", ["job_type"])

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
```

---

### GA-TEST-01 — Integrations-Test-Suite

**Abhängigkeit:** SCGB-01 muss zuerst geschlossen sein.

**Nach SCGB-01:**
```bash
export TEST_DATABASE_URL="postgresql+psycopg://..."
cd backend
pytest tests/integration/ -v
```

**Geschätzte Coverage-Verbesserung:** test_coverage-Dimension: 65 → 85

---

## Maturity-Prognose nach PRI-8

| Dimension | PRI-7 | PRI-8 (Prognose) | Delta |
|-----------|-------|-----------------|-------|
| search_quality | 45 | 85 | +40 |
| observability | 35 | 80 | +45 |
| scalability | 55 | 75 | +20 |
| test_coverage | 65 | 85 | +20 |
| security | 84 | 92 | +8 |
| performance | 60 | 85 | +25 |
| functional_coverage | 82 | 85 | +3 |
| documentation | 88 | 90 | +2 |
| approval_workflow | 90 | 90 | 0 |
| export_pipeline | 80 | 82 | +2 |
| operational_readiness | 72 | 85 | +13 |

**Prognose Gesamtscore:** ~85.8/100 (**GA_READY > 90 möglich mit vollständiger Umsetzung**)

---

## Abschlussregel PRI-8

Wenn alle Blocker geschlossen → GA Final Gate erneut ausführen.

- Maturity >= 90 → **GA_READY**: Version 1.0 markieren, Release-Tag v1.0, CHANGELOG aktualisieren, Installationsanleitung finalisieren.
- Maturity < 90 → **PRI-9 Qualitätserhöhung**: verbleibende Dimensions-Gaps adressieren.
