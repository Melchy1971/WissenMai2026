# Health Checks

Stand: 2026-06-17

Referenz aller Health-Check-Endpunkte und Monitoring-Verfahren für den RC-Betrieb.

---

## Primäre Health-Endpunkte

| Endpunkt | Methode | Erwarteter Status | Prüft |
|----------|---------|-------------------|-------|
| `/health` | GET | HTTP 200 | Backend erreichbar, Grundkonfiguration |
| `/health/db` | HTTP 503 = DB-Fehler | GET | PostgreSQL-Verbindung, Schema auf HEAD |

### Schnellcheck

```powershell
# Backend
Invoke-RestMethod http://localhost:8000/health
# Erwartung: {"status": "ok", "version": "..."}

# Datenbank
Invoke-RestMethod http://localhost:8000/health/db
# Erwartung: {"status": "ok", "alembic_revision": "..."}
# Fehler: HTTP 503 -> Datenbank pruefen (docs/operations/troubleshooting.md)
```

---

## Erweiterte Systemvalidierung

```powershell
# 1. Auth Bootstrap Guard (DB-only, kein Backend noetig)
python scripts/check_auth_bootstrap.py --no-start-api
# Erwartung: Exit 0, Admin-User und Workspace vorhanden

# 2. PostgreSQL Truth Smoke
pytest -m postgres_truth tests/postgres_truth/test_smoke.py -vv
# Erwartung: alle Tests PASS

# 3. Drift-Status
cd backend && .venv\Scripts\python -m drift.cli run
# Erwartung: Exit 0, drift_report.json aktualisiert
```

---

## Automatisierte CI-Checks (Release Gate)

| Check | Befehl | Exit-Code |
|-------|--------|-----------|
| UI ID-Leak-Audit | `python3 scripts/audit_ui_technical_ids.py --quiet` | 0=PASS, 1=BLOCKED |
| Backend ID-Leak Tests | `pytest backend/tests/test_id_leak_gate.py -m unit_fast --noconftest` | 0=PASS, 1=FAIL |
| Performance Baseline | `python3 scripts/perf_baseline.py --dry-run` | 0=PASS, 1=FAIL, 2=Infra |

RC-Limits (p95):
- `/api/documents`: ≤ 800 ms
- `/api/search`: ≤ 1500 ms
- Export PDF: ≤ 10000 ms
- Frontend Load: ≤ 3000 ms

Reports: `reports/current/`

---

## Manuelle Stichproben nach Deployment

### Dokumentliste

```powershell
$headers = @{ Authorization = "Bearer $env:ADMIN_API_TOKEN" }
Invoke-RestMethod http://localhost:8000/api/documents -Headers $headers
# Erwartung: HTTP 200, documents-Array nicht leer
```

### Such-Funktionalität

```powershell
$body = @{ query = "test" } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/search -Method Post -Body $body -ContentType "application/json" -Headers $headers
# Erwartung: HTTP 200, results-Array (kann leer sein, kein Error)
```

### Export-Verfügbarkeit

```powershell
Invoke-RestMethod http://localhost:8000/api/exports -Headers $headers
# Erwartung: HTTP 200
# DRAFT-Exports: Hinweis mit Freigabeanforderung sichtbar
# Export nur moeglich wenn Status=APPROVED
```

### AI-Provider

```powershell
Invoke-RestMethod "$env:OLLAMA_BASE_URL/api/tags"
# Erwartung: HTTP 200, models-Liste enthaelt $env:OLLAMA_MODEL
```

---

## Report-Artefakte

| Datei | Inhalt | Wann prüfen |
|-------|--------|-------------|
| `reports/current/operations_selftest_report.json` | Selftest-Ergebnisse | nach jeder Intervention |
| `reports/current/m4a_auth_truth.json` | Auth Bootstrap Ergebnis | nach Seed/Reset |
| `reports/current/ui_technical_id_leak_audit.json` | ID-Leak-Audit | nach Frontend-Änderungen |
| `reports/current/technical_id_leak_gate.json` | Gate-Report Task #18 | RC-Freigabe |
| `reports/current/performance_baseline_report.json` | Performance-Messung | RC-Freigabe |
| `reports/current/drift_report.json` | Drift-Analyse | nach Drift-Run |

---

## Statusmodell

Status-Priorität (absteigend): `BLOCKED` > `FAIL` > `WARNING` > `PASS`

- `BLOCKED`: CI blockierend, kein Release möglich
- `FAIL`: Funktionsfehler, Release nicht empfohlen
- `WARNING`: Fehlende Daten oder Degradierung, RC möglich bei Dokumentation
- `PASS`: Alle Checks bestanden

Fehlende Daten ergeben `WARNING`, nicht `PASS`.
`BLOCKED` hat Vorrang vor `FAIL` — ein einzelnes BLOCKED-Ergebnis setzt den Gesamtstatus auf BLOCKED.

---

## Betrieb nach RC-Freigabe

Regelmäßige Validierung empfohlen:
- täglich: `/health` + `/health/db`
- wöchentlich: Auth Bootstrap Guard + Drift-Run
- nach jedem Deployment: vollständige Validierungsprozedur (`docs/operations/runbook.md`)
- nach jedem Backup: Backup validieren (`python -m app.cli backup validate`)
