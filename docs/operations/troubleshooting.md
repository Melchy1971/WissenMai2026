# Troubleshooting

Stand: 2026-06-17
Bezug: `docs/runbooks/`

Kurzreferenz für häufige Störungsbilder. Ausführliche Szenarien: `docs/operations/runbook.md`.

---

## Datenbank nicht erreichbar

**Symptome:** `/health/db` HTTP 503, Logs zeigen `sqlalchemy.exc.OperationalError`, `start_backend.ps1` Exit 2.

**Diagnose:**
```powershell
Get-Content .env | Select-String "DATABASE_URL"
psql $env:DATABASE_URL -c "SELECT 1"
Test-NetConnection -ComputerName localhost -Port 5432
```

**Fixes:**
1. `DATABASE_URL` fehlt oder fehlerhaft in `.env` → korrigieren
2. PostgreSQL-Dienst gestoppt → `Start-Service postgresql*` (Windows) / `systemctl start postgresql` (Linux)
3. IP-Wechsel → `pg_hba.conf` neue IP eintragen, `Restart-Service postgresql*`
4. Port 5432 geblockt → Firewall prüfen

---

## Backend startet nicht

**Symptome:** `start_backend.ps1` Exit 1 (Venv) oder Exit 2 (DATABASE_URL), kein Uvicorn-Output auf Port 8000.

**Diagnose:**
```powershell
Test-Path backend/.venv/Scripts/python.exe
cd backend && .venv\Scripts\python -m uvicorn app.main:app --reload 2>&1 | head -40
```

**Fixes:**
1. Venv fehlt: `cd backend && python -m venv .venv && .venv\Scripts\pip install -e .[dev]`
2. `DATABASE_URL` fehlt → `.env` ergänzen
3. Alembic nicht auf HEAD → `cd backend && .venv\Scripts\python -m alembic upgrade head`
4. Port 8000 belegt → `netstat -ano | findstr 8000`

---

## Frontend startet nicht

**Symptome:** `npm run dev` schlägt fehl, Browser zeigt Fehler statt App.

**Diagnose:**
```powershell
node --version       # muss >= 18
npm --version
npm install          # fehlende node_modules
```

**Fixes:**
1. `node_modules` fehlen → `npm install` im Frontend-Verzeichnis
2. Vite-Port belegt → `VITE_PORT` in `.env.local` setzen
3. API-URL falsch → `VITE_API_URL` in `.env.local` auf laufendes Backend zeigen

---

## Login funktioniert nicht

**Symptome:** Login-Formular gibt Fehler, Session wird nicht erstellt, API antwortet HTTP 401/403.

**Diagnose:**
```powershell
python scripts/check_auth_bootstrap.py --no-start-api
Get-Content .env | Select-String "SEED_ADMIN_LOGIN|SEED_ADMIN_PASSWORD|ADMIN_API_TOKEN"
```

**Fixes:**
1. Seed nicht ausgeführt → `python backend/scripts/seed_auth.py`
2. Admin-User existiert nicht → Seed erneut ausführen
3. `DEFAULT_WORKSPACE_ID` stimmt nicht → `.env` mit korrekter UUID

---

## Migration fehlgeschlagen

**Symptome:** `alembic upgrade head` bricht ab, Schema-Mismatch beim Backend-Start.

**Diagnose:**
```powershell
cd backend
.venv\Scripts\python -m alembic current
.venv\Scripts\python -m alembic history --verbose
```

**Fixes:**
1. Letzten Schritt zurückrollen (nur vor Produktiveinsatz): `.venv\Scripts\python -m alembic downgrade -1`
2. Erneut migrieren: `.venv\Scripts\python -m alembic upgrade head`
3. Nicht behebbar → Backup einspielen (`docs/operations/backup_restore.md`)

---

## Import-Job hängt

**Symptome:** Import seit > 10 Minuten ohne Statuswechsel, `status: running` in DB.

**Diagnose:**
```powershell
cd backend
.venv\Scripts\python -c "
from app.db.session import get_engine
from sqlalchemy import text
with get_engine().connect() as conn:
    rows = conn.execute(text(
        'SELECT id, status, created_at, updated_at FROM import_jobs ORDER BY created_at DESC LIMIT 5'
    )).fetchall()
    for r in rows: print(dict(r))
"
```

**Fixes:**
1. Backend-Log auf Fehler prüfen (Timeout, Speicher)
2. Backend neu starten → Job wird nach `BACKGROUND_JOB_RETRY_BACKOFF_SECONDS` retried
3. Maximale Versuche überschritten (`BACKGROUND_JOB_MAX_ATTEMPTS`) → Job auf `failed` setzen, neu triggern

---

## Analyse-Job hängt

**Symptome:** `/api/v1/analysis/{job_id}` dauerhaft `status: running`.

**Diagnose:**
```powershell
# AI-Provider erreichbar?
Invoke-RestMethod $env:OLLAMA_BASE_URL/api/tags
```

**Fixes:**
1. Ollama nicht erreichbar → `OLLAMA_BASE_URL` prüfen, Ollama starten
2. Modell fehlt → `ollama pull $env:OLLAMA_MODEL`
3. Timeout → Backend neu starten, Job retried automatisch

---

## Drift-Run schlägt fehl

**Symptome:** `drift_report.json` fehlt, Dashboard zeigt "Drift Daten nicht verfügbar".

**Diagnose:**
```powershell
cd backend
.venv\Scripts\python -m drift.cli run 2>&1 | tail -30
```

**Fehler-Codes:**
- `DB_CONNECTION_FAILED` → Datenbank-Troubleshooting (oben)
- `SCHEMA_MISMATCH` → Migrations-Troubleshooting (oben)
- `UNHANDLED_EXCEPTION` → Stack-Trace aus Log lesen

---

## Search gibt keine Ergebnisse

**Symptome:** Suchanfragen geben leeres Ergebnis, obwohl Dokumente vorhanden.

**Diagnose:**
```powershell
psql $env:DATABASE_URL -c "SELECT count(*) FROM chunks WHERE ts_vector IS NOT NULL"
```

**Fix:** FTS-Index neu aufbauen (mutierende Aktion — Audit-Log-Eintrag schreiben):
```powershell
python -m app.cli search rebuild-index
```

---

## Bekannte Limitierungen (RC-Stand)

| Problem | Ursache | Status |
|---------|---------|--------|
| Topics/Documents-Suche langsam bei > 1000 Einträgen | ILIKE ohne GIN-Index | GA-blockend (RISIKO-01) |
| `search_unified` Python-seitiges Sorting | Cursor-Pagination fehlt | GA-blockend (RISIKO-02) |
| Kein Zero-Downtime-Restore | Design-Entscheidung M4e | Bekannt, Post-GA |
| Kein Point-in-Time-Recovery | Scope-Ausschluss | Bekannt, Post-GA |

Vollständige Risikodokumentation: `reports/current/performance_risks.md`.
