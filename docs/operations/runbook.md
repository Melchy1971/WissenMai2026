# Operations Runbook

Stand: 2026-06-17
Bezug: PRI-5 Release Hardening

> Jede mutierende Aktion (Restore, Reindex, Seed, Migration) erfordert:
> 1. Dry-Run-Prüfung vor dem Live-Lauf
> 2. Audit-Log-Eintrag (Zeitpunkt, Operator, Aktion, Ergebnis)
> 3. Restore zusätzlich: Zweitperson als Review
>
> GUI-Buttons lösen keine Mutationen aus (M4d ist read-only).
> M5c-Cleanup: NO_GO bis `m5c_start_gate=PASS` + PO-Sign-off.

---

## Validierungsprozedur nach jeder Intervention

Immer in dieser Reihenfolge:

```powershell
# 1. Backend-Health
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/db

# 2. Auth Bootstrap Guard
python scripts/check_auth_bootstrap.py --no-start-api

# 3. Dokumentliste
# GET /api/documents -> erwarte HTTP 200, documents-Array nicht leer

# 4. Smoke-Subset (PostgreSQL)
pytest -m postgres_truth tests/postgres_truth/test_smoke.py -vv
```

Intervention gilt als abgeschlossen erst nach Auswertung von `reports/current/operations_selftest_report.json`.

---

## Szenario 1 — Neue Instanz / DB-Reset

**Symptom:** Leere oder neue Umgebung, kein Admin-User, Migrations fehlen.

```powershell
# 1. DB anlegen
psql -U postgres -c "CREATE DATABASE wissensbasis;"

# 2. .env pruefen
# DATABASE_URL muss gesetzt sein (siehe .env.example)

# 3. Migrationen
cd backend
.venv\Scripts\python -m alembic upgrade head

# 4. Seed
python backend/scripts/seed_auth.py

# 5. Bootstrap validieren
python scripts/check_auth_bootstrap.py --no-start-api
.\scripts\dev_bootstrap.ps1
```

Report-Artefakt: `reports/current/m4a_auth_truth.json` — muss `PASS` sein.

---

## Szenario 2 — DB-Verbindung unterbrochen

**Symptom:** `/health/db` gibt HTTP 503, Logs zeigen `OperationalError`.

```powershell
# Verbindung testen
psql $env:DATABASE_URL -c "SELECT 1"
Test-NetConnection -ComputerName localhost -Port 5432

# PostgreSQL-Dienst starten
Start-Service postgresql*          # Windows
# systemctl start postgresql       # Linux

# pg_hba.conf bei IP-Wechsel
# neue IP unter host-Eintraegen ergaenzen, dann:
Restart-Service postgresql*
```

---

## Szenario 3 — Alembic-Migration fehlgeschlagen

**Symptom:** `alembic upgrade head` bricht ab, Schema-Mismatch.

```powershell
# Aktuellen Stand pruefen
cd backend
.venv\Scripts\python -m alembic current
.venv\Scripts\python -m alembic history --verbose

# Letzte Migration rueckgaengig (NUR wenn Migration noch nicht in Produktion)
.venv\Scripts\python -m alembic downgrade -1

# Migration erneut ausfuehren
.venv\Scripts\python -m alembic upgrade head
```

Fehlschlag ohne Rollback-Option: Backup einspielen (siehe `docs/operations/backup_restore.md`).

---

## Szenario 4 — Backend startet nicht

```powershell
# Venv pruefen
Test-Path backend/.venv/Scripts/python.exe

# Direkt starten fuer Traceback
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload 2>&1 | head -60
```

Typische Ursachen: DB nicht erreichbar, fehlende `.env`-Variablen, Alembic nicht auf HEAD.
Abhilfeschritte: Szenario 1 oder 2 ausführen, dann Backend neu starten.

---

## Szenario 5 — Import-Job hängt

**Symptom:** Import seit > 10 Minuten ohne Statuswechsel.

```powershell
# Job-Status aus DB
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

# Backend-Log auf ERROR pruefen
# Bei Hang: Backend neu starten (Job wird beim naechsten Start retried)
```

Lock-Timeout: `BACKGROUND_JOB_LOCK_TIMEOUT_SECONDS` (Default: 300).
Nach Backend-Neustart startet der Job erneut (max. `BACKGROUND_JOB_MAX_ATTEMPTS` Versuche).

---

## Szenario 6 — Analyse-Job hängt

**Symptom:** `/api/v1/analysis/{job_id}` liefert dauerhaft `status: running`.

```powershell
# Wie Szenario 5, aber Tabelle analysis_jobs
# Zusaetzlich: AI-Provider erreichbar?
Invoke-RestMethod $env:OLLAMA_BASE_URL/api/tags
```

---

## Szenario 7 — Drift-Run schlägt fehl

**Symptom:** `drift_report.json` fehlt, Dashboard zeigt "Drift Daten nicht verfuegbar".

```powershell
cd backend
.venv\Scripts\python -m drift.cli run 2>&1 | tail -30
```

Typische `error_code`-Werte: `DB_CONNECTION_FAILED`, `SCHEMA_MISMATCH`, `UNHANDLED_EXCEPTION`.
Behebung: Szenario 1–4 je nach Fehlerursache, dann Drift-CLI erneut ausführen.

---

## Szenario 8 — Search liefert keine Ergebnisse

**Symptom:** Suchanfragen geben leere Ergebnisse zurück, obwohl Dokumente vorhanden.

```powershell
# FTS-Konfiguration pruefen (PostgreSQL)
psql $env:DATABASE_URL -c "SELECT count(*) FROM chunks WHERE ts_vector IS NOT NULL"

# Index neu aufbauen (ACHTUNG: mutierende Aktion)
python -m app.cli search rebuild-index
```

Nach Reindex: Standard-Validierung ausführen (Abschnitt oben).

---

## Eskalation

| Stufe | Bedingung | Massnahme |
|-------|-----------|-----------|
| 1 | Szenario lösbar in < 15 min | Selbst beheben + Audit-Log |
| 2 | > 15 min oder Datenverlust-Risiko | Zweite Person hinzuziehen |
| 3 | Produktive Daten betroffen | DR-Prozess einleiten (`docs/operations/backup_restore.md`) |

---

## Release-Gate Constraints (PRI-5)

- BLOCKED hat Vorrang vor FAIL, FAIL vor WARNING
- Snapshots sind immutable — alte Snapshots bleiben erhalten
- Kein RepairButton, kein CleanupButton in der GUI (PROHIBIT-02, PROHIBIT-06)
- M5c-Ausführung erfordert PO-Sign-off (PROHIBIT-08)
