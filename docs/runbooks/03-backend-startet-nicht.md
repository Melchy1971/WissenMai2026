# Runbook: Backend startet nicht

## Symptom

- `start_backend.ps1` bricht mit Exit 1 (Venv) oder Exit 2 (DATABASE_URL) ab
- `uvicorn` startet nicht, kein Output auf Port 8000
- `PreflightService` wirft Exception beim Startup
- Import-Fehler in Python-Modulen

## Diagnose

```powershell
# 1. Venv vorhanden?
Test-Path backend/.venv/Scripts/python.exe   # Windows
Test-Path backend/.venv/bin/python           # Linux

# 2. DATABASE_URL gesetzt?
Get-Content .env | Select-String "DATABASE_URL"

# 3. Abhängigkeiten installiert?
backend/.venv/Scripts/pip list | Select-String "fastapi|sqlalchemy|uvicorn"

# 4. Direkt starten fuer vollstaendigem Traceback
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload 2>&1 | head -40

# 5. PreflightService-Fehler?
# Typisch: DB nicht erreichbar, Alembic nicht auf HEAD
```

## Sofortmassnahmen

1. Venv fehlt: `cd backend && python -m venv .venv && .venv\Scripts\pip install -e .[dev]`
2. DATABASE_URL fehlt: `.env` ergaenzen, dann `start_backend.ps1` neu starten
3. Alembic-Fehler beim Preflight: `cd backend && alembic upgrade head`
4. Port 8000 belegt: `netstat -ano | findstr 8000`

## Recovery

```powershell
# Vollstaendiger Reset der Umgebung
cd backend
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
alembic upgrade head
.\scripts\start_backend.ps1
curl http://localhost:8000/health
```

## Eskalation

Wenn `alembic upgrade head` fehlschlaegt: Migration-Conflict pruefen (`alembic history`). Wenn PreflightService mit unbekanntem Fehler: vollstaendigen Traceback sichern, DB-Zustand pruefen.
