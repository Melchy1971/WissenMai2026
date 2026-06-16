# Wissensbasis V1

Wissensbasis V1 ist die Startarchitektur fuer eine lokale GUI mit remote angebundener Datenbank, versionierten Dokumentinhalten und klar abgegrenztem V1-Scope.

## Projektziel

Das Projekt schafft die technische und dokumentarische Grundlage fuer eine Single-User-Wissensbasis mit folgenden Leitplanken:

- Backend auf FastAPI.
- Frontend auf React/Vite.
- PostgreSQL als remote betriebene Datenbank.
- Alembic-Migrationen im Backend-Kontext.
- Markdown als kanonische Textquelle.
- Keine Authentifizierung in V1.
- Keine Pflicht zu Vektorsuche in V1.
- Keine Speicherung von Originaldateien als fachlich fuehrende Quelle.

Der aktuelle Stand bildet bewusst die V1-Startstruktur und Architekturentscheidungen ab. Fachlogik ist nur teilweise vorbereitet und wird nicht durch diese Dokumentation vorweggenommen.

## Hauptstruktur

- `backend/`: FastAPI-Anwendung, Services, Modelle, Schemas, Jobs, Tests und Alembic-Migrationen.
- `frontend/`: React/Vite-Oberflaeche, Feature-Struktur und Frontend-Tests.
- `docs/`: Architekturuebersicht, ADRs, API-Notizen, Prompt-Vorlagen, Runbooks und Projektstatus.
- `scripts/`: Leichtgewichtige Hilfsskripte fuer lokale Entwicklung.

## Startpunkt fuer Entwickler

1. Projektziel und V1-Grenzen in dieser Datei lesen.
2. Aktuellen M4/M5-Freigabestand in `docs/m4-m5-freigabefassung.md` lesen.
2. Architekturentscheidungen unter `docs/adr/` lesen.
3. Bereichsspezifische README-Dateien in `backend/`, `frontend/`, `docs/` und `scripts/` verwenden.
4. Danach lokale Entwicklungsumgebung fuer Backend und Frontend einrichten.

## Aktueller Freigabestand

Der aktuelle Gate-Status wird nicht manuell in dieser Datei gepflegt. Verbindlich sind `reports/current/masterplan_status.json` und der daraus erzeugte Abschnitt `docs/generated/status_section.md`.

M3a, M4 und M5 sind getrennte Gates: M3a wird ueber die Frontend-Full-Suite bewertet, M4 ueber die aktuellen M4-Split-Reports plus `reports/current/m4_truth_report.json`, und M5 ueber das M5-Start-Gate aus `reports/current/masterplan_status.json`.

**Stand 2026-06-15:** Release Candidate Decision = **BLOCKED** (`reports/current/release_candidate_decision.json`). Root Cause: `TEST_DATABASE_URL` nicht gesetzt. Vollstaendige Dokumentation: `docs/release-candidate.md`.

Drift Detection (`/drift`) ist implementiert und erreichbar (`drift_v2/DriftDashboard`, UI Truth 29/29 PASS). Formale Freigabe blockiert durch Gate-Kaskade. Cleanup/Repair: NO_GO (PROHIBIT-02, PROHIBIT-06).

## Backend-Setup & Bootstrap (Stand 2026-05-26)

### Bootstrap-Reihenfolge (empfohlen)

1. `.env` laden (inkl. Seed Credentials, siehe unten)
2. DB-Verbindung prÃ¼fen
3. Alembic-Migrationen (`upgrade head`)
4. Auth-Seed (`backend/scripts/seed_auth.py`)
5. Auth Bootstrap Guard (`scripts/check_auth_bootstrap.py`)
6. `/health`-Smoke-Check (optional)
7. Report schreiben

Automatisiert per:

```powershell
.\scripts\dev_bootstrap.ps1
```

Optionale Flags: `-SkipSeed`, `-SkipSmoke`, `-DryRun` (siehe docs/operations.md)

### BenÃ¶tigte Umgebungsvariablen

- `APP_ENV`: Laufzeitumgebung, lokal standardmÃ¤ÃŸig `local`.
- `DATABASE_URL`: PostgreSQL-Verbindungsstring fÃ¼r Remote-DB, z. B. `postgresql+psycopg://user:password@host:5432/dbname`.
- `TEST_DATABASE_URL`: PostgreSQL-Verbindungsstring fÃ¼r Integrationstests.
- `DEFAULT_WORKSPACE_ID`, `DEFAULT_USER_ID`: vorbereitete IDs fÃ¼r V1 Single-User.
- **Seed Credentials:**
	- `SEED_ADMIN_LOGIN` (Default: `admin@localhost`)
	- `SEED_ADMIN_PASSWORD` (Default: `change-me`)
	- `SEED_WORKSPACE_NAME` (Default: `Default Workspace`)

> **Warnung (lokale Entwicklung):** `.env` enthÃ¤lt das Klartext-Passwort. Niemals `.env` committen! In produktiver Dokumentation keine Klartext-Credentials angeben.

Alle Seed-Skripte lesen diese ENV-Variablen. Legacy-Keys werden als Fallback akzeptiert, aber nicht mehr gesetzt.

### Backend starten (manuell)

```powershell
Set-Location H:\WissenMai2026
.\scripts\dev-db.ps1
.\scripts\dev-backend.ps1
```

### Auth Bootstrap Guard

Nach dem Seed prÃ¼ft `scripts/check_auth_bootstrap.py` Login und Workspace-Isolation. Fehler fÃ¼hren zu Exit != 0 und Report in `reports/current/m4a_auth_truth.json`.

Einzeln ausfÃ¼hren:

```powershell
python scripts/check_auth_bootstrap.py --no-start-api
```

### Runtime Connectivity Gate

`scripts/validate_runtime_connectivity_gate.py` prueft DB, Alembic, Seed, Health, Login, Auth, Workspace, Frontend und API. Der aktuelle Gate-Status wird aus `reports/current/masterplan_status.json` gelesen.

```powershell
python scripts/validate_runtime_connectivity_gate.py
```

### Statusmatrix (M3a/M4)

- Aktuelle Statusmatrix: `docs/generated/status_section.md`.
- Maschinenlesbare Quelle: `reports/current/masterplan_status.json`.

Weitere Details: siehe `docs/status.md`, `docs/operations.md`, `docs/security.md`.

Wenn `DATABASE_URL` explizit gesetzt ist, hat dieser Wert Vorrang.

Der Backend-Start fuehrt lokal automatisch `alembic upgrade head` aus und legt den Auth-Seed an. Harte Bootstrap-Invariante: Nach `backend/scripts/seed_auth.py` muss die lokale DB einen funktionierenden Admin-Login besitzen; Legacy-Logins werden migriert oder deaktiviert.

```text
Login: mdickscheit@gmail.com
Passwort: Alex..2026
```

Smoke-Test der Invariante:

```bash
cd backend
pytest tests/test_seed_auth_bootstrap.py -q
```

Tests ausfuehren:

```bash
cd backend
pytest
```

PostgreSQL-Truth-Report lokal erzeugen:

```powershell
Set-Location H:\WissenMai2026
$env:TEST_DATABASE_URL="postgresql+psycopg://appuser:<password>@85.215.131.200:5432/wissen2026"
.\scripts\run-postgres-truth.ps1
```

Die Reports landen in `reports/current/m4_truth_report.json` und `reports/current/m4_truth_report.json`.

Bekannte Einschraenkung:

- Der aktuelle Verifikationslauf gegen `85.215.131.200:5432` ist aus dieser Umgebung per Connection-Timeout fehlgeschlagen. Die Testumgebung ist damit fachlich vorbereitet, aber infrastrukturell erst nutzbar, wenn Netzwerkzugriff auf die Instanz besteht.
- `alembic heads` zeigt aktuell zwei Heads (`20260505_0016`, `20260506_0013`); damit ist der Migrationsstand lokal lesbar, aber nicht als einzelner linearer Head belegbar.

Frontend-Abhaengigkeiten installieren:

```bash
cd ..\frontend
npm install
```

## ADRs

- [Technische Grundentscheidung fuer V1](h:\WissenMai2026\docs\adr\0001-tech-stack-v1.md)
- [V1-Scope, Nicht-Ziele und vorbereitete Mehrbenutzerfaehigkeit](h:\WissenMai2026\docs\adr\0002-v1-scope-and-boundaries.md)

Die aelteren Kurzfassungen unter `docs/adr/0001-tech-stack.md` und `docs/adr/0002-v1-scope.md` existieren weiterhin, die aktuellen Paket-1-Referenzen zeigen jedoch auf die ausfuehrlichen V1-ADRs.

