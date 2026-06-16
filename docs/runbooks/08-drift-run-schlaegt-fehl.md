# Runbook: Drift Run schlaegt fehl

## Symptom

- `drift_run_failed` Event im Log mit `error_code`
- `python -m drift.cli run` gibt Exit != 0 zurueck
- `drift_report.json` oder `drift_summary.json` fehlen oder sind unvollstaendig
- Dashboard zeigt "Drift Daten nicht verfuegbar"

## Diagnose

```powershell
# 1. Drift CLI direkt ausfuehren
cd backend
.venv\Scripts\python -m drift.cli run 2>&1 | tail -30

# 2. TEST_DATABASE_URL gesetzt? (Drift CLI benoetigt DB-Zugriff)
Get-Content ../.env | Select-String "TEST_DATABASE_URL|DATABASE_URL"

# 3. drift_report.json vorhanden?
Test-Path ../reports/current/drift_report.json
Test-Path ../reports/current/drift_summary.json

# 4. Fehlercode aus Log lesen
# Typische error_codes: UNHANDLED_EXCEPTION, DB_CONNECTION_FAILED, SCHEMA_MISMATCH
```

## Sofortmassnahmen

1. `DB_CONNECTION_FAILED`: `DATABASE_URL` oder `TEST_DATABASE_URL` pruefen (Runbook 01)
2. `SCHEMA_MISMATCH`: `alembic current` pruefen, ggf. `alembic upgrade head` (Runbook 04)
3. `UNHANDLED_EXCEPTION`: Stack-Trace aus Log lesen (kein Dokumentinhalt geloggt — safe)
4. Fehlende JSON-Reports: Drift CLI vollstaendig ohne Unterbrechung laufen lassen

## Recovery

```powershell
# Drift CLI erneut ausfuehren
cd backend
.venv\Scripts\python -m drift.cli run

# Ergebnis pruefen
Test-Path ../reports/current/drift_report.json && Write-Host "OK"
Test-Path ../reports/current/drift_summary.json && Write-Host "OK"
```

PROHIBIT-Regeln beachten:
- Kein manuelles Editieren von `drift_report.json`
- Drift Detection ist Read-Only (PROHIBIT-02, PROHIBIT-06)
- Bei Findings: keine automatische Korrektur — nur Anzeige

## Eskalation

Wenn Drift CLI mit `UNHANDLED_EXCEPTION` fehlschlaegt und Ursache unklar: Log-Payload sichern (enthaelt keine Dokumentinhalte, nur Metadaten), DB-Verbindung und Schema verifizieren. Kein M5c-Cleanup ohne m5c_start_gate PASS und PO-Sign-off.
