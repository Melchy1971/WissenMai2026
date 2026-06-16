# Testplan: Externe Umgebung

Stand: 2026-06-15
Status: NOT_RUN (72 Tests)
Quelle: `reports/current/external_env_testplan.json`

Zweck: Tests, die lokal bewusst nicht blockieren, separat in produktionsaehnlicher Umgebung validieren.
Phase: OPT-2 — nach RC-Stabilisierung (OPT-1 abgeschlossen).

---

## Voraussetzungen

Alle Punkte muessen vor dem Test-Run erfuellt sein:

1. Backend laeuft und ist erreichbar (`API_BASE_URL`)
2. `TEST_DATABASE_URL` gesetzt und PostgreSQL erreichbar
3. Seed-Daten vorhanden (`dev_bootstrap.ps1` oder aequivalent)
4. HTTPS mit gueltigem Zertifikat (fuer Produktionstests)
5. Reverse Proxy konfiguriert (CORS, SSL-Termination)

Umgebungsvariablen:

```
TEST_DATABASE_URL=postgresql+psycopg://user:pw@host:5432/dbname
API_BASE_URL=https://api.example.com
TEST_ENV=external
```

---

## Ausfuehren

```bash
# Vorpruefung (nur Collect, kein Run)
pytest tests/api -m 'external_env_only or legacy_live_http' --collect-only

# Vollstaendiger Run
pytest tests/api -m 'external_env_only or legacy_live_http' -v --tb=short
```

Erwartete Dauer: ~5 Minuten.
Erwartetes Ergebnis bei PASS: 72/72, `reports/current/external_env_gate.json` auf PASS.

---

## Test-Gruppen

### TG-01: GUI Backend Endpoints (`test_gui_backend_endpoints.py`)

Alle vom Frontend genutzten REST-Endpunkte gegen reales Backend:

- `GET /api/v1/status` — HTTP 200, Schema korrekt
- `GET /api/v1/documents` — HTTP 200, Pagination-Header vorhanden
- `POST /api/v1/documents/import` — Datei-Upload, HTTP 202 oder 200
- `GET /api/v1/rag/documents` — HTTP 200
- `POST /api/v1/rag/retrieve` — HTTP 200, `results`-Array vorhanden
- `GET /api/v1/data-quality/summary` — HTTP 200
- `GET /api/v1/drift/summary` — HTTP 200 (read-only)
- `GET /api/v1/settings` — HTTP 200
- `PATCH /api/v1/settings` — HTTP 200, Aenderung persistiert

**Pass-Kriterium:** Alle Endpunkte HTTP 2xx, kein 5xx.

### TG-02: GUI Contracts (`test_gui_contracts.py`)

API-Vertraege zwischen Frontend und Backend:

- Response-Schemas stimmen mit Frontend-Erwartungen ueberein
- Pflichtfelder (`id`, `workspace_id`, `created_at`) in allen Responses
- Fehler-Response-Format einheitlich (`code`, `message`, `technicalCode`)
- Pagination-Format: `items`, `total`, `page`, `page_size`
- Workspace-Isolation: `X-Workspace-Id` wird korrekt verarbeitet

### TG-03: GUI Secret Masking (`test_gui_secret_masking.py`, Marker: `legacy_live_http`)

- Kein `password`/`token`/`api_key` in JSON-Response-Bodies
- `DATABASE_URL` nicht in `/health`- oder `/status`-Response
- Seed-Credentials nicht in API-Response sichtbar

### TG-04: Secret Masking API (`test_secret_masking_api.py`, Marker: `legacy_live_http`)

- Fehlermeldungen enthalten keine DB-Credentials
- 500-Responses zeigen keinen Raw-Stacktrace
- Log-Ausgaben maskieren sensitive Werte

### TG-05: Settings Endpoints (`test_settings_endpoints.py`)

- `GET /api/v1/settings` liefert aktuellen Stand
- `PATCH` mit gueltigen Werten: HTTP 200, Aenderung persistiert
- `PATCH` mit ungueltigen Werten: HTTP 422
- Workspace-Isolation: Aenderung betrifft nur eigenen Workspace

### TG-06: Settings Patch (`test_settings_patch.py`)

- `PATCH` aendert nur angegebene Felder
- Nicht angegebene Felder bleiben unveraendert
- `PATCH` auf read-only Felder: HTTP 422 oder 403

---

## Infrastruktur-Checks

| ID | Check | Pass-Kriterium |
|----|-------|----------------|
| IC-01 | CORS: OPTIONS-Request vom Frontend-Origin | `Access-Control-Allow-Origin` korrekt |
| IC-02 | SSL/HTTPS: Gueltiges Zertifikat | TLS erfolgreich, nicht abgelaufen, HSTS vorhanden |
| IC-03 | Reverse Proxy: Request via Proxy weitergeleitet | Responses identisch zu direktem Backend |
| IC-04 | Auth Flow: Login mit Seed-Credentials | HTTP 200, Token zurueck, Token in naechstem Request akzeptiert |
| IC-05 | Workspace-Header: Isolation in externer Umgebung | HTTP 400/403 bei fehlendem/falschem Workspace |

---

## Abgrenzung

Diese Tests blockieren `local_final_gate` und RC Gate **nicht**.
`NOT_RUN` ist erlaubter Zustand bis zur externen Testentscheidung (OPT-2).

Drift Detection bleibt read-only. Kein Cleanup/Repair in externem Test-Lauf (PROHIBIT-02, PROHIBIT-06).
