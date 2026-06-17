# Health Check Matrix — Ruflo v0.1.0

Sprint PRI-7 | Task #42 | Stand: 2026-06-17

---

## Endpunkte

| Endpunkt | Zweck | Erfolg | Fehler |
|---|---|---|---|
| `GET /health` | Basis-Check (bestehend) | HTTP 200, `status: ok` | — |
| `GET /health/live` | Liveness — Prozess läuft | HTTP 200, `status: UP` | — (immer 200) |
| `GET /health/ready` | Readiness — alle Komponenten | HTTP 200, `status: UP/DEGRADED` | HTTP 503, `status: DOWN` |
| `GET /health/db` | DB-Only-Check (bestehend) | HTTP 200, `status: ok` | HTTP 503 |
| `GET /health/preflight` | Preflight-Checks (bestehend) | HTTP 200 | HTTP 503 |

---

## Komponenten-Matrix

| Komponente | Check-Methode | UP | DEGRADED | DOWN |
|---|---|---|---|---|
| **database** | psycopg `SELECT 1` | Verbindung ok | — | Verbindung fehlgeschlagen |
| **filesystem** | Write/Delete `.healthcheck` | Upload-Dir beschreibbar | Dir nicht vorhanden | Exception |
| **metrics** | `_PROMETHEUS_AVAILABLE` Flag | prometheus_client installiert | Nicht installiert | — |
| **job_queue** | `SELECT status, COUNT(*) FROM background_jobs` | running ≤ 10 | running 11–50 | running > 50 |
| **storage** | `psutil.disk_usage('/')` | Disk ≤ 80% | 80% < Disk ≤ 90% | Disk > 90% |
| **reports** | `os.path.isdir('reports/current')` | Verzeichnis vorhanden | Nicht vorhanden | — |
| **provider** | Stub (kein Live-Ping) | immer UP | — | — |

---

## Aggregationsregel

```
DOWN > DEGRADED > UP
```

- Mindestens eine Komponente DOWN → Gesamt DOWN → HTTP 503
- Mindestens eine Komponente DEGRADED → Gesamt DEGRADED → HTTP 200
- Alle UP → Gesamt UP → HTTP 200

---

## Response-Beispiel (Readiness, Normalfall)

```json
{
  "status": "UP",
  "version": "0.1.0",
  "uptime_seconds": 3742.1,
  "timestamp": "2026-06-17T08:31:22.441Z",
  "components": {
    "database":   {"status": "UP", "detail": "connection ok"},
    "filesystem": {"status": "UP", "detail": "uploads les- und schreibbar"},
    "metrics":    {"status": "UP", "detail": "prometheus_client verfügbar"},
    "storage":    {"status": "UP", "detail": "62.4% used"},
    "reports":    {"status": "UP", "detail": "reports/current vorhanden"},
    "job_queue":  {"status": "UP", "detail": "running=0, pending=3"},
    "provider":   {"status": "UP", "detail": "provider check skipped (no live ping in health)"}
  }
}
```

## Response-Beispiel (Readiness, Database DOWN)

```json
{
  "status": "DOWN",
  "version": "0.1.0",
  "uptime_seconds": 12.3,
  "timestamp": "2026-06-17T08:31:22.441Z",
  "components": {
    "database":   {"status": "DOWN", "detail": "connection to server failed: Connection refused"},
    "filesystem": {"status": "UP", "detail": "uploads les- und schreibbar"},
    "metrics":    {"status": "UP", "detail": "prometheus_client verfügbar"},
    "storage":    {"status": "UP", "detail": "62.4% used"},
    "reports":    {"status": "UP", "detail": "reports/current vorhanden"},
    "job_queue":  {"status": "DEGRADED", "detail": "connection to server failed: Connection refused"},
    "provider":   {"status": "UP", "detail": "provider check skipped (no live ping in health)"}
  }
}
```

---

## Testszenarien

| Szenario | Betroffene Komponente | Erwartetes Verhalten |
|---|---|---|
| DATABASE_URL nicht konfiguriert | database | DOWN → Gesamt DOWN → HTTP 503 |
| Upload-Verzeichnis fehlt | filesystem | DEGRADED → Gesamt DEGRADED → HTTP 200 |
| prometheus_client nicht installiert | metrics | DEGRADED → Gesamt DEGRADED → HTTP 200 |
| Disk > 90% | storage | DOWN → Gesamt DOWN → HTTP 503 |
| > 50 running Jobs | job_queue | DOWN → Gesamt DOWN → HTTP 503 |
| Alles normal | alle | UP → HTTP 200 |

---

## Alert-Schwellenwerte

| Metrik | Warning | Critical |
|---|---|---|
| cpu_usage_percent | > 70% | > 90% |
| memory_usage_mb | > 800 MB | > 950 MB |
| disk_usage_percent | > 80% | > 90% |
| http_request_duration_p95 | > 2s | > 5s |
| job_queue running | > 10 | > 50 |
| provider_error_total (rate/min) | > 5 | > 20 |

---

## Implementierungsnachweis

- Implementierung: `backend/app/api/health_extended.py`
- Router eingebunden: `backend/app/main.py` via `app.include_router(health_extended_router)`
- Schließt GA-Blocking-Item: GA-OPS-03
