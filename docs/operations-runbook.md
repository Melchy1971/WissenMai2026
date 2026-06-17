# Operations Runbook

Stand: 2026-06-17 (aktualisiert PRI-6)
Bezug: `docs/m4e-operations-release.md`, `reports/current/m4e_operations_release_gate.json`, `reports/current/conditional_rc_decision.json`

**PRI-6 Aenderung:** `/admin/diagnostics` ist durch `AdminRoute`-Guard gesichert. Zugriff erfordert `user.role === 'admin'`. Member-Requests erhalten HTTP 403. DevOps-Anforderung: `TEST_DATABASE_URL` muss in CI/CD-Umgebung gesetzt werden (SCGB-01, noch offen).

> Jede mutierende Aktion (Restore, Reindex, Seed) erfordert eine Dry-Run-Pruefung,
> einen Audit-Log-Eintrag und — bei Restore — eine Zweitperson als Review.
> GUI-Buttons loesen keine Mutationen aus (M4d ist read-only).

---

## Allgemeine Validierungsprozedur nach jeder Intervention

Immer in dieser Reihenfolge ausfuehren:

```powershell
# 1. Backend-Health
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8001/health/db

# 2. Auth Bootstrap Guard
python scripts/check_auth_bootstrap.py --no-start-api

# 3. Dokumentliste (requires running backend)
# GET /api/documents -> erwarte HTTP 200, documents-Array

# 4. Optionaler Smoke-Subset (PostgreSQL)
pytest -m postgres_truth tests/postgres_truth/test_smoke.py -vv
```

Die Intervention endet erst nach Auswertung der zutreffenden Nachweise unter `reports/current/`, insbesondere `reports/current/operations_selftest_report.json`.

---

## Szenario 1 — DB neu aufsetzen

**Symptom:** Keine Datenbankverbindung, leere oder korrumpierte DB, Entwicklungsumgebung neu initialisieren.

**Ursache:** Neue lokale Instanz, Reset nach Test, DB-Datenverlust oder Host-Wechsel.

**Fix:**

```powershell
# Schritt 1: Leere Ziel-DB anlegen (PostgreSQL)
psql -U postgres -c "CREATE DATABASE wissen_v1;"
# oder bestehende DB leeren:
psql -U postgres -c "DROP DATABASE IF EXISTS wissen_v1; CREATE DATABASE wissen_v1;"

# Schritt 2: .env sicherstellen
# DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/wissen_v1

# Schritt 3: Schema migrieren
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head

# Schritt 4: Seed Admin-User und Workspace
python backend/scripts/seed_auth.py

# Schritt 5: Bootstrap validieren
python scripts/check_auth_bootstrap.py --no-start-api
```

**Validierungsbefehl:**

```powershell
.\scripts\dev_bootstrap.ps1
# Erwartung: Alle Schritte gruener Exit-Code 0
```

**Report-Artefakt:** `reports/current/m4a_auth_truth.json` (muss PASS sein, collected > 0)

---

## Szenario 2 — pg_hba.conf IP-Wechsel

**Symptom:** `psycopg2.OperationalError: could not connect to server` oder `FATAL: no pg_hba.conf entry for host`.

**Ursache:** IP-Adresse des Entwicklungsrechners hat sich geaendert (DHCP, VPN, Netzwerkwechsel). `pg_hba.conf` erlaubt den neuen Absender nicht.

**Fix:**

```powershell
# Schritt 1: Aktuelle IP ermitteln
ipconfig | Select-String "IPv4"

# Schritt 2: pg_hba.conf lokalisieren
# Standard: C:\Program Files\PostgreSQL\<version>\data\pg_hba.conf
#           /etc/postgresql/<version>/main/pg_hba.conf (Linux)

# Schritt 3: Neue IP oder Subnetz eintragen
# Beispieleintrag fuer alle lokalen IPv4-Adressen:
# host  all  all  127.0.0.1/32  scram-sha-256
# host  all  all  192.168.0.0/24  scram-sha-256

# Schritt 4: PostgreSQL neu laden (kein Restart noetig)
# Windows (PowerShell als Admin):
Restart-Service postgresql*
# Linux:
# sudo systemctl reload postgresql
# oder: sudo pg_ctlcluster <version> main reload

# Schritt 5: Verbindung testen
python -c "import psycopg; psycopg.connect('postgresql://<user>:<pw>@localhost/wissen_v1').close(); print('OK')"
```

**Validierungsbefehl:**

```powershell
python scripts/check_auth_bootstrap.py --no-start-api
```

**Report-Artefakt:** `reports/current/m4a_auth_truth.json`

---

## Szenario 3 — Alembic Migration ausfuehren

**Symptom:** Backend startet, aber Endpoints liefern DB-Schema-Fehler (fehlende Spalten, Tabellen nicht gefunden).

**Ursache:** Code wurde aktualisiert, Migration wurde noch nicht ausgefuehrt. Oder: Migrationsskript wurde erneut erstellt ohne die vorherige zu revisen.

**Fix:**

```powershell
cd backend

# Schritt 1: Aktuellen Revisionsstand pruefen
.\.venv\Scripts\python.exe -m alembic current

# Schritt 2: Ausstehende Heads pruefen
.\.venv\Scripts\python.exe -m alembic heads

# Schritt 3: Migration ausfuehren
.\.venv\Scripts\python.exe -m alembic upgrade head

# Schritt 4: Ergebnis bestaetigen
.\.venv\Scripts\python.exe -m alembic current
# Erwartung: kein "(head)" hinter einem alten Revision-Hash

# Schritt 5: Seed-Zustand erhalten (falls Tabellen neu)
python backend/scripts/seed_auth.py
```

**Wenn Migration fehlschlaegt (Konflikt):**

```powershell
# Merge-Migration erzeugen (nur wenn zwei Heads):
.\.venv\Scripts\python.exe -m alembic merge heads -m "merge"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

**Validierungsbefehl:**

```powershell
.\scripts\dev_bootstrap.ps1
```

**Report-Artefakt:** `reports/current/m4a_auth_truth.json`

---

## Szenario 4 — Seed/Auth reparieren

**Symptom:** `check_auth_bootstrap.py` schlaegt fehl. Login liefert `AUTH_INVALID_CREDENTIALS`. `GET /auth/me` liefert 401.

**Ursache:** Seed-Skript wurde nicht ausgefuehrt, ENV-Variablen fehlen, Passwort-Hash inkonsistent, oder Workspace fehlt.

**Fix:**

```powershell
# Schritt 1: ENV-Variablen pruefen
# .env muss enthalten:
# DATABASE_URL=...
# SEED_ADMIN_LOGIN=admin@localhost   (oder WISSEN_DEV_LOGIN)
# SEED_ADMIN_PASSWORD=change-me       (oder WISSEN_DEV_PASSWORD)
# SEED_WORKSPACE_NAME=Default Workspace

# Schritt 2: Seed neu ausfuehren (idempotent)
python backend/scripts/seed_auth.py

# Schritt 3: Bootstrap pruefen
python scripts/check_auth_bootstrap.py --no-start-api

# Schritt 4: Login manuell testen (wenn Backend laeuft)
$body = @{ email = "admin@localhost"; password = "change-me" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/auth/login -Method POST -Body $body -ContentType "application/json"
```

**Wenn Workspace fehlt:**

```powershell
# Seed anlegt Workspace automatisch; bei Fehler:
python -c "
import asyncio
from backend.app.db.session import get_session_context
from backend.app.services.workspace_service import ensure_default_workspace
asyncio.run(ensure_default_workspace())
"
```

**Validierungsbefehl:**

```powershell
python scripts/check_auth_bootstrap.py --no-start-api
```

**Report-Artefakt:** `reports/current/m4a_auth_truth.json` (PASS, 43/43)

---

## Szenario 5 — Backend startet nicht

**Symptom:** `uvicorn` bricht mit Traceback ab. `GET /health` liefert Connection refused.

**Ursache (haeufigste Faelle):**
- `DATABASE_URL` fehlt oder falsch
- Port 8001 belegt
- Migrations nicht ausgefuehrt (DB-Schema fehlt)
- Python-Import-Fehler nach Code-Aenderung

**Fix:**

```powershell
# Schritt 1: Backend direkt starten und Fehler lesen
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload 2>&1 | head -50

# Schritt 2: Haeufige Ursachen pruefen
#   a) DB nicht erreichbar:
python -c "import psycopg; psycopg.connect('$env:DATABASE_URL').close()"
#   b) Port belegt:
netstat -ano | findstr :8001
#      -> PID ermitteln, mit taskkill /PID <pid> /F beenden
#   c) Migrations fehlen:
.\.venv\Scripts\python.exe -m alembic current

# Schritt 3: Nach Fix erneut starten
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

**Validierungsbefehl:**

```powershell
Invoke-RestMethod http://localhost:8001/health
# Erwartung: { "status": "ok" }
Invoke-RestMethod http://localhost:8001/health/db
# Erwartung: { "status": "ok", "db": "connected" }
```

**Report-Artefakt:** `reports/current/m4a_auth_truth.json` (erneuter Bootstrap-Lauf nach Fix)

---

## Szenario 6 — Frontend zeigt API_UNREACHABLE

**Symptom:** Alle API-Calls schlagen fehl. Browser-Konsole zeigt `API_UNREACHABLE` oder `net::ERR_CONNECTION_REFUSED`. Kein Inhalt geladen.

**Ursache:**
- Backend nicht gestartet oder abgestuerzt
- Falscher Port in `VITE_API_URL` / Proxy-Konfiguration
- CORS-Fehler (Backend erlaubt Frontend-Origin nicht)
- Firewall oder Antivirus blockiert Port 8001

**Fix:**

```powershell
# Schritt 1: Backend-Erreichbarkeit direkt pruefen
Invoke-RestMethod http://localhost:8001/health

# Schritt 2: Falls nicht erreichbar -> Szenario 5 (Backend startet nicht)

# Schritt 3: Falls erreichbar -> CORS pruefen
# .env FRONTEND_ORIGIN muss mit dem Vite-Dev-Server (z.B. http://localhost:5173) uebereinstimmen
# backend/app/config.py: CORS_ORIGINS pruefen

# Schritt 4: Proxy-Konfiguration pruefen
# frontend/vite.config.ts -> proxy target muss auf http://localhost:8001 zeigen

# Schritt 5: Frontend neu starten nach .env-Aenderung
cd frontend
npm run dev
```

**Validierungsbefehl:**

```powershell
# Im Browser oder curl:
Invoke-RestMethod http://localhost:8001/health
# Dann Frontend-Reload; API_UNREACHABLE darf nicht mehr erscheinen
```

**Report-Artefakt:** `reports/archive/legacy/20260605T100000Z/frontend_full_suite_staged_report.json` (nach erneutem Truth-Lauf)

---

## Szenario 7 — Login zeigt AUTH_INVALID_CREDENTIALS

**Symptom:** POST `/auth/login` liefert `{"error": "AUTH_INVALID_CREDENTIALS"}`. Frontend bleibt auf Login-Screen.

**Ursache:**
- Seed nicht ausgefuehrt oder mit falschem Passwort ausgefuehrt
- ENV-Variablen `SEED_ADMIN_LOGIN` / `SEED_ADMIN_PASSWORD` und Login-Eingabe stimmen nicht ueberein
- Falscher Hashing-Algorithmus nach Code-Aenderung (bcrypt vs. argon2)
- User existiert nicht in DB

**Fix:**

```powershell
# Schritt 1: Tatsaechliche ENV-Variablen pruefen (DryRun)
.\scripts\dev_bootstrap.ps1 -DryRun

# Schritt 2: Seed mit bekannten Credentials neu ausfuehren
# Sicherstellen: .env enthaelt korrekte SEED_ADMIN_LOGIN und SEED_ADMIN_PASSWORD
python backend/scripts/seed_auth.py

# Schritt 3: Login mit denselben Credentials testen
$body = @{ email = $env:SEED_ADMIN_LOGIN; password = $env:SEED_ADMIN_PASSWORD } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/auth/login -Method POST -Body $body -ContentType "application/json"

# Schritt 4: Falls User nicht existiert
# seed_auth.py legt User an falls nicht vorhanden (idempotent)
```

**Validierungsbefehl:**

```powershell
python scripts/check_auth_bootstrap.py --no-start-api
```

**Report-Artefakt:** `reports/current/m4a_auth_truth.json`

---

## Szenario 8 — Backup erzeugen

**Symptom / Anlass:** Geplanter Backup, vor Restore, vor Reindex, vor Deployment.

**Voraussetzung:** Backend in ruhigem Betriebszustand (kein laufender Upload, kein aktiver Restore).

**Fix:**

```powershell
# Schritt 1: Backup-Verzeichnis festlegen
$BACKUP_PATH = "C:\backups\wissen-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# Schritt 2: Backup erzeugen
cd backend
.\.venv\Scripts\python.exe -m app.cli backup create --output $BACKUP_PATH

# Schritt 3: Manifest pruefen
Get-Content "$BACKUP_PATH\manifest.json" | ConvertFrom-Json | Format-List

# Schritt 4: Backup validieren (Checksummen + Vollstaendigkeit)
.\.venv\Scripts\python.exe -m app.cli backup validate --input $BACKUP_PATH

# Schritt 5: Backup an getrennten Speicherort kopieren
Copy-Item -Recurse $BACKUP_PATH "D:\backup-store\"
```

**Erwartetes Manifest:**

- `alembic_revision` ist aktuell
- `workspace_count` > 0
- `document_count` entspricht Erwartung
- `created_at` aktuell

**Validierungsbefehl:**

```powershell
.\.venv\Scripts\python.exe -m app.cli backup verify-backup --input $BACKUP_PATH
# Erwartung: alle Checks PASS, Exit-Code 0
```

**Report-Artefakt:** `$BACKUP_PATH\manifest.json` + `$BACKUP_PATH\checksums.json`

---

## Szenario 9 — Restore durchfuehren

**Symptom / Anlass:** DB zerstoert, Host-Wechsel, Disaster-Recovery, geplante Umgebungswiederherstellung.

**Voraussetzung:**
- Gueltiges Backup mit PASS-Validierung liegt vor
- Ziel-DB ist leer oder kann geleert werden
- Zweitperson (Review-Rolle) ist benachrichtigt

**Fix:**

```powershell
# Schritt 1: Backup validieren (nie ohne Validierung restoren)
.\.venv\Scripts\python.exe -m app.cli backup validate --input $BACKUP_PATH

# Schritt 2: Ziel-DB leeren
psql -U postgres -c "DROP DATABASE IF EXISTS wissen_v1; CREATE DATABASE wissen_v1;"

# Schritt 3: Restore ausfuehren
.\.venv\Scripts\python.exe -m app.cli backup restore --input $BACKUP_PATH

# Schritt 4: Schema auf aktuellen Stand bringen (falls App-Version neuere Migrations hat)
.\.venv\Scripts\python.exe -m alembic upgrade head

# Schritt 5: Seed (falls Admin-User nach Restore fehlt)
python backend/scripts/seed_auth.py

# Schritt 6: Auth-Bootstrap pruefen
python scripts/check_auth_bootstrap.py --no-start-api
```

**Nach Restore zwingend Szenario 10 (Reindex) ausfuehren.**

**Validierungsbefehl:**

```powershell
# DB-Inhalt stichprobenartig pruefen
psql -U postgres -d wissen_v1 -c "SELECT COUNT(*) FROM documents;"
psql -U postgres -d wissen_v1 -c "SELECT COUNT(*) FROM document_chunks;"
python scripts/check_auth_bootstrap.py --no-start-api
```

**Report-Artefakt:** `reports/current/m4e_backup_restore_truth.json` (nach erneutem Truth-Lauf)

---

## Szenario 10 — Reindex nach Restore

**Symptom / Anlass:** Pflichtschritt nach jedem Restore. Search liefert leere oder inkonsistente Ergebnisse nach Restore.

**Warum zwingend:** Der Search-Index wird nicht im Backup mitgefuehrt (rekonstruierbar). Ohne Reindex sind Suche und Retrieval entweder leer oder zeigen stale Eintraege.

**Fix:**

```powershell
# Schritt 1: Bestehenden Index leeren und neu aufbauen
cd backend
.\.venv\Scripts\python.exe -m app.cli search rebuild-index
# Alternativ ueber governed Reindex-Pfad (wenn verfuegbar):
# POST /api/v1/admin/reindex/governed  (Dry-Run zuerst)

# Schritt 2: Drift nach Reindex pruefen
.\.venv\Scripts\python.exe -m app.cli m5 drift-check --workspace <workspace_id>
# Erwartung: stale_index_growth = 0

# Schritt 3: Retrieval-Qualitaet nach Reindex messen
.\.venv\Scripts\python.exe -m app.cli m5 retrieval-benchmark --trigger restore
# Erwartung: kein Benchmark-Failure, keine Baseline-Regression > 0.05

# Schritt 4: Lifecycle-Konsistenz pruefen
# archivierte/geloeschte Dokumente duerfen nicht im Index erscheinen
```

**Stop-Regel:** Wenn `retrieval-benchmark` `failed` zurueckgibt oder `stale_index_growth > 0` nach Reindex — Betrieb nicht aufnehmen, Ursache isolieren.

**Validierungsbefehl:**

```powershell
.\.venv\Scripts\python.exe -m app.cli m5 retrieval-benchmark --trigger restore
# Erwartung: status = pass
```

**Report-Artefakt:**
- Geplantes Artefakt `m5_drift_report.json` (Drift-Check nach Reindex)
- Retrieval-Benchmark-Report (implizit durch CLI-Ausgabe)

---

## Validierungscheckliste

Nach jeder Intervention alle zutreffenden Punkte abhaken, bevor der Normalbetrieb wiederhergestellt wird.

### Pflicht nach allen Szenarien

- [ ] `python scripts/check_auth_bootstrap.py --no-start-api` — Exit-Code 0
- [ ] `GET /health` liefert `{"status": "ok"}`
- [ ] `GET /health/db` liefert `{"status": "ok"}`
- [ ] Kein aktiver Fehler in `reports/current/m4a_auth_truth.json`

### Pflicht nach DB-Aenderungen (Szenarien 1, 3, 4)

- [ ] `alembic current` zeigt korrekten Head
- [ ] Dokumentanzahl in DB entspricht Erwartung
- [ ] Seed-Admin-Login funktioniert
- [ ] `reports/current/m4a_auth_truth.json` enthaelt den aktuellen Auth-Nachweis

### Pflicht nach Restore (Szenario 9)

- [ ] Backup-Validierung wurde anhand `reports/current/m4e_backup_restore_truth.json` vor Restore bewertet
- [ ] Zweitperson hat Restore-Entscheid bestaetigt
- [ ] DB-Cardinality (Dokumente, Chunks, Citations) entspricht Manifest
- [ ] `check_auth_bootstrap.py` wurde ueber `reports/current/m4a_auth_truth.json` bewertet
- [ ] Reindex wurde ausgefuehrt (Szenario 10)

### Pflicht nach Reindex (Szenario 10)

- [ ] `m5 drift-check` zeigt `stale_index_growth = 0`
- [ ] `m5 retrieval-benchmark --trigger restore` ist `pass`
- [ ] Archivierte/geloeschte Dokumente erscheinen nicht in Suchergebnissen
- [ ] Lifecycle-Exclusion-Violations = 0

### Pflicht nach Backend-Neustart (Szenario 5)

- [ ] `GET /health` und `GET /health/db` — beide `ok`
- [ ] Kein `API_UNREACHABLE` im Frontend (erster manueller Test)
- [ ] Login mit Seed-Credentials funktioniert

### Pflicht nach Frontend-Fix (Szenario 6)

- [ ] Kein `API_UNREACHABLE` in Browser-Konsole
- [ ] Dokumentliste laedt
- [ ] Login-Flow funktioniert durch

---

## Grenzen dieses Runbooks

| Thema | Status |
|---|---|
| Automatische Cloud-Backups | Out-of-Scope (M4e Minimal) |
| Inkrementelle Backups | Out-of-Scope |
| Zero-Downtime Restore | Out-of-Scope |
| Vollautomatische Repair Actions | Nicht erlaubt ohne Governance-Freigabe |
| Web-Admin-Mutationen (Cleanup, Reindex per GUI) | Blockiert (M4d ist read-only) |
| Multi-Workspace-Migration | Kein Standardpfad in V1 |

Jede Aktion, die ueber dieses Runbook hinausgeht, braucht ein eigenes Freigabedokument und Audit-Log.
