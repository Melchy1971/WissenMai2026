# Installation

**RC-Status: BLOCKED** — Systemstatus vor Installation prüfen: `reports/current/release_candidate_gate.json`

---

## Voraussetzungen

- Python 3.11+
- Node.js 20+
- PostgreSQL (lokal oder remote, z.B. `85.215.131.200:5432/wissen2026`)
- PowerShell (Windows) oder bash (Linux/macOS)

## Umgebungsvariablen

Datei `.env` im Projektroot anlegen (nie committen):

```
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
TEST_DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
APP_ENV=local
DEFAULT_WORKSPACE_ID=<workspace-uuid>
DEFAULT_USER_ID=<user-uuid>
SEED_ADMIN_LOGIN=admin@localhost
SEED_ADMIN_PASSWORD=change-me
```

`TEST_DATABASE_URL` ist Pflicht fuer Gate-Tests (pytest). Ohne diese Variable: `report_integrity_v2` bleibt BLOCKED.

## Backend

```powershell
Set-Location H:\WissenMai2026

# Vollstaendiger Bootstrap (DB-Migration + Seed + Smoke)
.\scripts\dev_bootstrap.ps1

# Alternativ manuell:
.\scripts\dev-db.ps1
.\scripts\dev-backend.ps1
```

Nach Bootstrap: `http://localhost:8000/health` sollte `{"status":"ok"}` zurueckgeben.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## Gate-Tests (optional, erfordert TEST_DATABASE_URL)

```bash
pytest tests/ -m "not external_env_only and not legacy_live_http"
```

Externe Env-Tests (erfordert laufenden Server):

```bash
pytest tests/api -m "external_env_only or legacy_live_http"
```

## Bekannte Installationsprobleme

| Problem | Ursache | Loesung |
|---------|---------|---------|
| `report_integrity_v2` BLOCKED | TEST_DATABASE_URL fehlt | `.env` erganzen, Gate neu ausfuehren |
| `85.215.131.200:5432` Timeout | Remote-DB nicht erreichbar | Lokale PostgreSQL verwenden |
| `npm install` schlaegt fehl | Node.js < 20 | Node 20+ installieren |

## Cleanup / Repair: NO-GO

M5c Cleanup ist gesperrt. Drift Detection ist read-only. Keine Repair-Aktionen vor PO-Freigabe auf `reports/current/cleanup_governance_boundary.json`.
