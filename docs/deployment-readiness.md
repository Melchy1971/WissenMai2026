# Deployment Readiness Checklist

Stand: 2026-06-15
Quelle: `reports/current/deployment_readiness_checklist.json`
Verdict: **BLOCKED** — 2 BLOCKED, 6 HIGH, 3 UNKNOWN

---

## Ergebnis-Uebersicht

| ID | Check | Status | Severity |
|----|-------|--------|----------|
| DRC-01 | ENV Variablen vollstaendig | BLOCKED | blocking |
| DRC-02 | DATABASE_URL gesetzt und erreichbar | UNKNOWN | blocking_if_unset |
| DRC-03 | TEST_DATABASE_URL gesetzt | BLOCKED | blocking |
| DRC-04 | Alembic Head: Schema aktuell | PASS | — |
| DRC-05 | Seed/Auth: Admin-User anlegen und pruefen | PASS | — |
| DRC-06 | Backup erzeugbar | UNKNOWN | high |
| DRC-07 | Restore in leere DB verifizierbar | UNKNOWN | high |
| DRC-08 | Static Build: Frontend Build-Artefakt | PASS | — |
| DRC-09 | API Health: /health erreichbar | UNKNOWN | blocking_if_failing |
| DRC-10 | Frontend Routing: SPA-Fallback konfiguriert | UNKNOWN | high |
| DRC-11 | Reverse Proxy: Konfiguriert und funktional | UNKNOWN | high |
| DRC-12 | SSL/HTTPS: Gueltiges Zertifikat | UNKNOWN | high |
| DRC-13 | CORS: Konfiguriert fuer Frontend-Origin | UNKNOWN | high |

---

## BLOCKED

### DRC-01 — ENV Variablen vollstaendig

`.env.example` vorhanden. Pflichtfelder dokumentiert. Aber `TEST_DATABASE_URL` fehlt in laufender Umgebung.

**Fix:** `TEST_DATABASE_URL=postgresql+psycopg://user:pw@host:5432/dbname` in `.env` setzen.
Vollstaendige Pflichtfelder:

```
DATABASE_URL=postgresql+psycopg://...
TEST_DATABASE_URL=postgresql+psycopg://...
APP_ENV=local
DEFAULT_WORKSPACE_ID=...
DEFAULT_USER_ID=...
SEED_ADMIN_LOGIN=admin@localhost
SEED_ADMIN_PASSWORD=change-me
```

### DRC-03 — TEST_DATABASE_URL gesetzt

Root Cause von RC-PREREQ-01. `pytest collected=0, errors=1` fuer alle PostgreSQL-Truth-Tests.

**Fix:** Identisch mit DRC-01.

---

## PASS

### DRC-04 — Alembic Head

`dev_bootstrap.ps1` Schritt 3 fuehrt `alembic upgrade head` mit Exit-Code-Pruefung aus.

Manuell:

```powershell
cd H:\WissenMai2026
.\.venv\Scripts\python.exe -m alembic --config backend/alembic.ini upgrade head
```

### DRC-05 — Seed/Auth

`dev_bootstrap.ps1` fuehrt `seed_auth.py` aus und prueft Auth-Bootstrap ohne API-Start.

Manuell:

```powershell
.\.venv\Scripts\python.exe backend/scripts/seed_auth.py
.\.venv\Scripts\python.exe scripts/check_auth_bootstrap.py --no-start-api
```

### DRC-08 — Static Build

```bash
cd frontend
npm install
npm run build
# dist/ muss existieren und index.html enthalten
```

---

## HIGH — Erfordern Implementierung oder Live-System

### DRC-06 — Backup erzeugbar

Kein `run_backup.ps1` vorhanden. Muss erstellt werden (Task #23).

Erwarteter Ablauf:

```powershell
# pg_dump gegen DATABASE_URL
# Ausgabe: backups/YYYY-MM-DD_HH-mm.dump
# Exit-Code-Pruefung: 0 = PASS
```

### DRC-07 — Restore in leere DB

Kein `run_restore_test.ps1` vorhanden. Muss erstellt werden (Task #23).

Erwarteter Ablauf:

```powershell
# pg_restore in leere Test-DB
# alembic current == head pruefen
# Login-Test mit Seed-Credentials
# Exit-Code-Pruefung
```

### DRC-10 — Frontend Routing: SPA-Fallback

Vite-Dev-Server hat automatischen SPA-Fallback. Fuer Produktions-Reverse-Proxy:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

Keine nginx.conf im Repository. Muss vor Produktions-Deployment dokumentiert werden.

### DRC-11 — Reverse Proxy

Keine Reverse-Proxy-Konfiguration im Repository. Validierung ueber IC-03 in External Env Tests (OPT-2).

### DRC-12 — SSL/HTTPS

Lokale Entwicklung: HTTP. Produktions-Deployment: HTTPS erforderlich.
Validierung ueber IC-02 in External Env Tests (OPT-2).

### DRC-13 — CORS

FastAPI-CORSMiddleware muss `allow_origins` mit Frontend-Domain enthalten.
Validierung ueber IC-01 in External Env Tests (OPT-2).

---

## Naechste Schritte

1. **RC-PREREQ-01** (DRC-01, DRC-03): `TEST_DATABASE_URL` setzen
2. **Task #23** (DRC-06, DRC-07): `run_backup.ps1` + `run_restore_test.ps1` erstellen
3. **Reverse-Proxy-Dokumentation** (DRC-10, DRC-11): nginx.conf-Template
4. **External Env Tests** (DRC-09, DRC-12, DRC-13): OPT-2 durchfuehren

**Deployment-Readiness kann erst nach RC-Stabilisierung und External Env Tests vollstaendig bewertet werden.**
