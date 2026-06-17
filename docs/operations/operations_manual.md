# Operations Manual — Ruflo

Stand: 2026-06-17 | Sprint: PRI-7 | Release-Status: CONDITIONAL_RC

---

## 1. Systemübersicht

**Ruflo** ist eine lokale Wissensbasis-Anwendung mit Web-Frontend.

| Komponente | Technologie | Port |
|-----------|-------------|------|
| Backend | FastAPI (Python 3.10) | 8000 |
| Frontend | React/Vite | 5173 (dev) / 80 (prod) |
| Datenbank | PostgreSQL | 5432 |

Alle Komponenten laufen Single-User. Keine Loginpflicht in V1.

---

## 2. Architektur

```
Browser → Frontend (React/Vite)
             ↓ HTTP/JSON
          Backend (FastAPI)
             ↓ SQLAlchemy
          PostgreSQL (Remote)
             ↓
          Alembic Migrations
```

Background-Jobs (Import, Analyse, Export) laufen als async Tasks im FastAPI-Prozess.
Provider-Anbindungen (LLM) werden über `settings.PROVIDER_*` konfiguriert.

---

## 3. Deployment

### Voraussetzungen

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- `.env` mit allen Pflichtfeldern (siehe unten)

### Pflicht-ENV-Variablen

```
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
APP_ENV=production
DEFAULT_WORKSPACE_ID=<uuid>
DEFAULT_USER_ID=<uuid>
SEED_ADMIN_LOGIN=admin@localhost
SEED_ADMIN_PASSWORD=<sicheres-passwort>
```

### Backend starten

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Oder via Script:
```powershell
.\scripts\dev-backend.ps1
```

### Frontend starten (Produktion)

```bash
cd frontend
npm install
npm run build
# Build-Artefakte unter frontend/dist/
```

### Bootstrap-Reihenfolge

1. `.env` laden
2. DB-Verbindung prüfen
3. `alembic upgrade head`
4. `python scripts/seed_auth.py`
5. `python scripts/check_auth_bootstrap.py`
6. `/health` Smoke-Check
7. Report schreiben

---

## 4. Migration (Alembic)

```bash
# Aktuelle Migrations-Version
alembic current

# Alle ausstehenden Migrationen anwenden
alembic upgrade head

# Migration zurückrollen
alembic downgrade -1

# Neue Migration erstellen
alembic revision --autogenerate -m "beschreibung"
```

**Hinweis:** Aktuell zwei Alembic-Heads (20260505_0016, 20260506_0013). Vor produktivem Deployment mergen.

---

## 5. Backup

```bash
# Vollständiges DB-Backup
pg_dump --format=custom $DATABASE_URL > backup_db_$(date +%Y%m%d_%H%M%S).dump

# Uploads
tar -czf backup_uploads_$(date +%Y%m%d_%H%M%S).tar.gz uploads/

# Exports
tar -czf backup_exports_$(date +%Y%m%d_%H%M%S).tar.gz exports/
```

**Strategie:** Full Backup täglich 02:00 UTC, 30 Tage Aufbewahrung.
**Blocker:** SCGB-01 — Backup-Tests nicht ausführbar bis TEST_DATABASE_URL konfiguriert.

---

## 6. Restore

```bash
# DB wiederherstellen
pg_restore -d $TARGET_DB backup_db_*.dump

# Schema (bei leerem System)
alembic upgrade head

# Dateien
tar -xzf backup_uploads_*.tar.gz -C uploads/
tar -xzf backup_exports_*.tar.gz -C exports/

# Integritätsprüfung
python scripts/validate_restore.py
```

**RTO:** 30 Minuten | **RPO:** 1 Stunde

---

## 7. Fehleranalyse

### Backend antwortet nicht

```bash
# Prozess prüfen
ps aux | grep uvicorn

# Logs
journalctl -u ruflo-backend -n 100

# Health-Check
curl http://localhost:8000/health
```

### Datenbank-Verbindung fehlgeschlagen

```bash
# Verbindung testen
psql $DATABASE_URL -c "SELECT 1"

# Alembic-Stand prüfen
alembic current
```

### Job hängt (Status RUNNING seit > 10 min)

```sql
-- Stuck Jobs identifizieren
SELECT id, job_type, status, started_at, attempt_count
FROM background_jobs
WHERE status = 'running'
  AND started_at < NOW() - INTERVAL '10 minutes';

-- Job zurücksetzen
UPDATE background_jobs SET status = 'pending', started_at = NULL
WHERE id = '<job_id>';
```

### 403 bei /admin/diagnostics

AdminRoute-Guard aktiv. Nur Admin-Benutzer (role='admin') können /admin/* aufrufen. Prüfen: Benutzer-Rolle in DB.

---

## 8. Monitoring

**IST:** `/health` Endpoint vorhanden.

**SOLL (PRI-8):**
- `/health/ready` — DB + Alembic-Stand
- `/metrics` — Prometheus-Format
- Strukturiertes JSON-Logging
- Alert-Schwellenwerte (siehe `docs/health_matrix.md`)

---

## 9. Logs

**Lokation:** Systemd-Journal (`journalctl -u ruflo-backend`) oder stdout.

**Log-Level:** Über ENV `LOG_LEVEL=INFO|DEBUG|WARNING|ERROR`.

**Struktur (SOLL, PRI-8):**
```json
{
  "timestamp": "2026-06-17T14:00:00Z",
  "level": "ERROR",
  "correlation_id": "req-abc123",
  "message": "Provider timeout",
  "service": "ruflo-backend"
}
```

---

## 10. Provider-Konfiguration

Provider-Zugangsdaten werden über ENV gesetzt:

```
PROVIDER_OPENAI_API_KEY=...
PROVIDER_ANTHROPIC_API_KEY=...
PROVIDER_DEFAULT=openai
```

Kein Klartext in Code oder Git. `.env` nicht committen.

---

## 11. Updates

```bash
# Backend
git pull
pip install -r requirements.txt
alembic upgrade head
# Backend neu starten

# Frontend
npm install
npm run build
```

---

## 12. Rollback

```bash
# Code-Rollback
git checkout <previous-tag>

# DB-Rollback
alembic downgrade -1
# Oder: Restore aus Backup (Abschnitt 6)

# Frontend-Rollback: vorheriges Build-Artefakt deployen
```

---

## 13. Testbetrieb

```bash
# Backend-Tests
cd backend && pytest

# Frontend-Tests
cd frontend && npm test

# Integrations-Gate
python scripts/validate_runtime_connectivity_gate.py
```

Test-Datenbank: `TEST_DATABASE_URL` (SCGB-01: von DevOps bereitzustellen).

---

## 14. Releaseprozess

1. Sprint-Abschluss: alle Deliverables in `reports/current/` vorhanden
2. Gold Path (8/8) PASS
3. Product Maturity Gate prüfen (Schwellenwert: GA ≥ 90)
4. `rc_decision.md` / `ga_decision.md` erzeugen
5. `masterplan_status.json` auf neue Version setzen
6. CHANGELOG aktualisieren
7. Git-Tag setzen: `git tag -a v1.0 -m "GA Release"`
8. Deployment-Freigabe durch PO
