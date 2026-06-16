# Runbook: Analyse haengt

## Symptom

- Analyse-Job laeuft seit > 10 Minuten ohne Ergebnis
- `analysis_job_completed` fehlt im Log
- API `/api/v1/analysis/{job_id}` gibt dauerhaft `status: running` zurueck
- Frontend zeigt Ladeindikator ohne Fortschritt

## Diagnose

```powershell
# 1. Analysis-Job-Status
cd backend
.venv\Scripts\python -c "
from app.db.session import get_engine
from sqlalchemy import text
with get_engine().connect() as conn:
    rows = conn.execute(text(
        'SELECT id, status, created_at, updated_at FROM analysis_jobs ORDER BY created_at DESC LIMIT 5'
    )).fetchall()
    for r in rows: print(dict(r))
"

# 2. AI-Provider erreichbar?
# Analyse-Jobs benoetigen externen AI-Provider (aus .env: OPENAI_API_KEY o.ae.)
# Log auf timeout oder ConnectionError pruefen

# 3. Backend-Log auf analysis_job_failed
```

## Sofortmassnahmen

1. AI-Provider-Timeout: Netzwerkverbindung zum Provider pruefen, API-Key in `.env` gueltig?
2. Analyse mit grossem Dokument: Timeout-Konfiguration im Service pruefen
3. Backend blockiert: Neustart

## Recovery

```powershell
# Backend neu starten
.\scripts\start_backend.ps1

# Analyse erneut ausfuehren (Frontend oder API direkt)
# Job-ID des fehlgeschlagenen Jobs aus Log sichern fuer Fehleranalyse
```

Wenn AI-Provider nicht erreichbar: `.env` auf gueltigen API-Key und korrekten Endpoint pruefen. Rate-Limit des Providers pruefen (HTTP 429 im Log).

## Eskalation

Wenn Analyse-Job dauerhaft haengt trotz gueltiger Konfiguration: Backend-Log vollstaendig sichern (ohne Credentials), AI-Provider-Status-Page pruefen. Wenn DB-seitig blockiert: `pg_locks` pruefen (wie Runbook 06).
