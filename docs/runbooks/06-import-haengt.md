# Runbook: Import haengt

## Symptom

- Dokument-Import laeuft seit > 5 Minuten ohne Statusaenderung
- Job-Status bleibt `running` oder `retryable`
- `m5_queue_backlog_age_seconds` ueberschreitet Warning-Threshold (> 900s)
- Kein `import_job_completed` Event im Log

## Diagnose

```powershell
# 1. Job-Status in DB (direkt)
cd backend
.venv\Scripts\python -c "
from app.db.session import get_engine
from sqlalchemy import text
with get_engine().connect() as conn:
    result = conn.execute(text(
        'SELECT id, status, created_at, updated_at FROM background_jobs ORDER BY created_at DESC LIMIT 10'
    ))
    for row in result: print(dict(row))
"

# 2. Backend-Log auf import_job_failed oder UNHANDLED_EXCEPTION
# Suche: event_name=import_job_failed, error_code=*

# 3. Haengt der Worker-Prozess?
# Bei uvicorn --reload: Worker-Thread blockiert?
```

## Sofortmassnahmen

1. Job im Status `dead_letter`: Ursache aus Log lesen (error_code), Dokument pruefen
2. Worker blockiert: Backend-Neustart (Daten bleiben in DB erhalten)
3. Wiederholter `retryable`-Status: Maximale Retry-Anzahl pruefen

## Recovery

```powershell
# Backend neu starten (jobs in DB bleiben, haengender Worker wird beendet)
# CTRL+C in Backend-Terminal, dann:
.\scripts\start_backend.ps1

# Job manuell neu ausloesen (wenn GUI verfuegbar):
# Dokument erneut hochladen oder Import-Endpoint direkt aufrufen
```

Nach Neustart: Job-Status erneut pruefen, Log auf `import_job_started` warten.

## Eskalation

Wenn Job dauerhaft `dead_letter` mit gleichem `error_code`: Dokument-Format pruefen (Parser-Typ aus Log). Wenn Backend-Neustart nicht hilft: DB-Lock pruefen (`SELECT * FROM pg_locks WHERE NOT granted`).
