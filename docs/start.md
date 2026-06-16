# Start

Voraussetzung: Installation abgeschlossen (`docs/install.md`), `.env` vollstaendig gesetzt.

## Schnellstart (Anfaenger)

```powershell
# 1. Bootstrap (DB + Migrationen + Seed + Auth-Pruefung)
.\scripts\dev_bootstrap.ps1

# 2. Backend starten (zweites Terminal)
.\scripts\start_backend.ps1

# 3. Frontend starten (drittes Terminal)
.\scripts\start_frontend.ps1
```

Danach: `http://localhost:5173` im Browser aufrufen.

---

## Backend starten

```powershell
# Neu: Mit Exit-Code-Pruefung und klarer Fehlermeldung
.\scripts\start_backend.ps1

# Alternativ (klassisch)
.\scripts\dev-backend.ps1
```

FastAPI laeuft auf `http://localhost:8000`.
Health-Check: `http://localhost:8000/health`
API Docs: `http://localhost:8000/docs`

Fehlermeldungen:
- `FAIL: DATABASE_URL nicht gesetzt` -> DATABASE_URL in `.env` pruefen
- `FAIL: Backend-Venv nicht gefunden` -> `cd backend && python -m venv .venv && .venv\Scripts\pip install -e .[dev]`

## Frontend starten

```powershell
# Neu: Mit Exit-Code-Pruefung
.\scripts\start_frontend.ps1

# Alternativ (klassisch)
.\scripts\dev-frontend.ps1
```

Vite laeuft auf `http://localhost:5173`.

Fehlermeldungen:
- `FAIL: node_modules nicht gefunden` -> `cd frontend && npm install`

---

## Login / Seed

Seed-Daten werden beim Bootstrap automatisch angelegt.

```
URL:      http://localhost:5173/login
Login:    admin@localhost    (SEED_ADMIN_LOGIN in .env)
Passwort: change-me          (SEED_ADMIN_PASSWORD in .env)
```

Produktive Credentials immer ueber `.env` setzen. Passwort nach erstem Login aendern. Niemals `.env` committen.

Auth-Bootstrap-Pruefung (ohne API-Start):

```powershell
python scripts/check_auth_bootstrap.py --no-start-api
```

---

## Gate-Tests ausfuehren

```powershell
# Local Final Gate (erfordert TEST_DATABASE_URL)
.\scripts\run_final_gate.ps1
```

Voraussetzung: `TEST_DATABASE_URL` in `.env` gesetzt.
Fehlermeldung: `TEST_DATABASE_URL ist nicht gesetzt` -> TEST_DATABASE_URL in `.env` pruefen.

---

## Backup und Restore

```powershell
# Backup erstellen
.\scripts\run_backup.ps1
# Ausgabe: backups/YYYY-MM-DD_HH-mm.dump + reports/current/backup_report.json

# Restore-Test (in Test-DB, erfordert TEST_DATABASE_URL)
.\scripts\run_restore_test.ps1
# Ausgabe: reports/current/restore_test_report.json
```

---

## Enduser-Flows nach Start

Verfuegbare Bereiche nach Login: `docs/enduser-flows.md`
Bekannte Einschraenkungen: `docs/known-limitations.md`

---

## Systemstatus pruefen

Dashboard zeigt nach Login: Release-Status, System-Health, Governance-Gate, Security-Gate, GUI-Gate.
Gate-Reports: `reports/current/release_candidate_gate.json`

---

## Bekannte Start-Probleme

| Problem | Ursache | Loesung |
|---------|---------|---------|
| `FAIL: TEST_DATABASE_URL ist nicht gesetzt` | Gate-Tests brauchen Test-DB | TEST_DATABASE_URL in `.env` setzen |
| `FAIL: DATABASE_URL ist nicht gesetzt` | Backend-Start fehlgeschlagen | DATABASE_URL in `.env` setzen |
| Weisser Bildschirm nach Login | Token-Validierung fehlgeschlagen | `localStorage.clear()` im Browser, neu einloggen |
| API-Fehler 401 | Session abgelaufen | Abmelden + neu einloggen |
| Drift-Dashboard leer | Drift CLI noch nicht ausgefuehrt | `python -m drift.cli run` einmalig ausfuehren |
| `pg_dump: Befehl nicht gefunden` | PostgreSQL-Client-Tools fehlen | PostgreSQL-Client installieren (winget install PostgreSQL) |
| Backup FAIL: DB nicht erreichbar | DATABASE_URL zeigt auf nicht erreichbares System | Netzwerkverbindung pruefen, DB starten |
