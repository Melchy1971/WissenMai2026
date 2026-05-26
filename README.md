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

Fuer den aktuell zulaessigen Dokumentationsstand zu M4 und M5 gilt die kompakte Freigabefassung in `docs/m4-m5-freigabefassung.md`.

Kurzstand am 2026-05-07:

- M4 ist nicht technisch stabilisiert.
- M4 Hardening Score: `74/100`.
- M4d ist nur read-only freigegeben.
- M5 bleibt blockiert.

## Backend-Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Benötigte Umgebungsvariablen fuer den vollstaendigen Backend-Betrieb:

- `APP_ENV`: Laufzeitumgebung, lokal standardmaessig `local`.
- `DATABASE_URL`: PostgreSQL-Verbindungsstring fuer Remote-DB, z. B. `postgresql+psycopg://user:password@host:5432/dbname`.
- `TEST_DATABASE_URL`: PostgreSQL-Verbindungsstring fuer echte Integrationstests mit `@pytest.mark.postgres` und `@pytest.mark.postgres_truth`.
- `DEFAULT_WORKSPACE_ID`: vorbereitete Workspace-ID fuer V1 Single-User.
- `DEFAULT_USER_ID`: vorbereitete User-ID fuer V1 Single-User.

`/health` funktioniert auch ohne `DATABASE_URL`. `/health/db` und Alembic benoetigen eine
erreichbare PostgreSQL-Datenbank.

Backend starten:

```bash
Set-Location H:\WissenMai2026
.\scripts\dev-db.ps1
.\scripts\dev-backend.ps1
```

Der Dev-Start verwendet lokal standardmaessig:

```text
postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test
```

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

Die Reports landen in `reports/postgres_truth_report.json` und `reports/postgres_truth_report.md`.

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
