# Backend

FastAPI-Anwendung fuer Wissensbasis V1.

## Zweck

- API, Anwendungslogik und Persistenz liegen ausschliesslich im Backend.
- Alembic-Migrationen bleiben im Backend-Kontext.
- V1 bleibt Single-User ohne Authentifizierung.
- Datenmodelle bereiten `workspace_id`- und `owner_user_id`-Felder fuer spaetere Mehrmandantenfaehigkeit vor.
- Originaldateien werden nicht gespeichert; kanonische Inhaltsquelle ist extrahierter Markdown.

## Struktur

- `app/`: FastAPI-Code, Services, Modelle, Schemas und Jobs.
- `app/api/health.py`: Minimaler Healthcheck ohne Fachlogik.
- `app/core/config.py`: Konfiguration ueber Umgebungsvariablen.
- `app/core/database.py`: PostgreSQL-Verbindungspruefung fuer Betrieb und Healthcheck.
- `migrations/`: Alembic-Umgebung und Revisionsdateien.
- `tests/`: Backend-spezifische Unit- und Integrationstests.
- `requirements*.txt`, `pyproject.toml`, `alembic.ini`: Abhaengigkeiten und Tooling.

## Lokale Installation

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Relevante Umgebungsvariablen:

- `APP_ENV`: optionale Umgebung, Default `local`.
- `DATABASE_URL`: PostgreSQL-URL fuer Remote-DB, erforderlich fuer `/health/db` und Alembic.
- `TEST_DATABASE_URL`: optionale PostgreSQL-Testdatenbank fuer echte Migrationstests.
- `DEFAULT_WORKSPACE_ID`: vorbereitete Workspace-ID fuer V1.
- `DEFAULT_USER_ID`: vorbereitete User-ID fuer V1.

## FastAPI-Start

```powershell
Set-Location H:\WissenMai2026
.\scripts\dev-db.ps1
.\scripts\dev-backend.ps1
```

Lokaler Standard-Fallback fuer `DATABASE_URL`, falls nicht explizit gesetzt:

```text
postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test
```

Beim lokalen Start wird die Datenbank automatisch migriert und mit einem Default-Owner vorbereitet. Harte Bootstrap-Invariante: Nach `scripts/seed_auth.py` muss ein Admin-Login ueber den normalen Auth-Service funktionieren; Legacy-Logins werden migriert oder deaktiviert.

```text
Login: mdickscheit@gmail.com
Passwort: Alex..2026
```

Smoke-Test:

```powershell
pytest tests/test_seed_auth_bootstrap.py -q
```

`GET /health` funktioniert ohne Datenbankkonfiguration. `GET /health/db` erwartet `DATABASE_URL`
fuer eine remote erreichbare PostgreSQL-Datenbank und gibt bei fehlender Konfiguration keinen
geheimen Verbindungsstring aus.

## Import-Endpunkt

Der minimale Importpfad unterstuetzt TXT, Markdown und DOCX:

- `.txt`
- `.md`
- `.docx`

Endpunkt:

```text
POST /documents/import
```

Beispiel:

```bash
curl -F "file=@notes.md" http://127.0.0.1:8000/documents/import
```

Beispielantwort:

```json
{
  "document_id": "00000000-0000-0000-0000-000000000000",
  "version_id": "00000000-0000-0000-0000-000000000000",
  "title": "notes",
  "chunk_count": 3,
  "duplicate_status": "created"
}
```

Bei gleichem `content_hash` wird kein stilles Duplikat erzeugt. Die API gibt
`duplicate_status = "duplicate_existing"` und die bestehende Dokument-/Versionsreferenz zurueck.

Originaldateien werden nicht gespeichert. Persistiert werden Dokument-Metadaten, normalisierter
Markdown, Hashes und Chunks mit Quellenankern.

## Alembic

Migrationen liegen im Backend unter `migrations/` und verwenden dieselbe `DATABASE_URL` wie die
FastAPI-Anwendung. Die URL wird nicht in `alembic.ini` gespeichert.

```bash
cd backend
alembic current
alembic upgrade head
alembic revision -m "describe change"
```

Autogeneration ist nicht vorausgesetzt. SQL-nahe Migrationen koennen in den generierten Dateien
unter `migrations/versions/` manuell mit `op.execute(...)` oder Alembic-Operationen gepflegt werden.

Aktueller M1-Migrationsstand:

- `20260430_0001_initial_document_schema.py`: Workspaces, Users, Documents, DocumentVersions.
- `20260430_0002_document_chunks.py`: versionierte Chunks mit Quellenankern.
- `20260430_0003_categories_tags.py`: Kategorien, Tags und additive DocumentTags.
- `20260430_0004_chat_analysis.py`: Chat- und Analyse-Grundtabellen.

Migration gegen eine konfigurierte PostgreSQL-Datenbank ausfuehren:

```bash
cd backend
alembic upgrade head
```

Aktuellen Stand pruefen:

```bash
cd backend
alembic current
```

## Testausfuehrung

```bash
cd backend
pytest
```

Reproduzierbarer Truth-Teststart mit Report:

```powershell
Set-Location H:\WissenMai2026
$env:TEST_DATABASE_URL="postgresql://..."
.\scripts\run-postgres-truth.ps1
```

Der Lauf schreibt:

- `reports/postgres_truth_report.json`
- `reports/postgres_truth_report.md`

Unit-Tests benoetigen keine Datenbankverbindung und laufen ohne Konfiguration durch.
Integrationstests, die PostgreSQL erfordern, sind mit `@pytest.mark.postgres` markiert.
Sie werden im Standard-`pytest`-Lauf uebersprungen, wenn `TEST_DATABASE_URL` nicht gesetzt ist.

### Postgres-Tests lokal ausfuehren

**Option 1 — dedizierte Test-Datenbank per Docker Compose (empfohlen):**

```bash
# Einmalig starten (Projektverzeichnis, nicht backend/)
docker compose -f docker-compose.test.yml up -d --wait

# Tests ausfuehren
cd backend
$env:TEST_DATABASE_URL="postgresql://testuser:testpass@localhost:5433/wissen_test"
pytest -m postgres -v

# Aufraumen
cd ..
docker compose -f docker-compose.test.yml down
```

**Option 2 — vorhandene PostgreSQL-Instanz:**

```bash
cd backend
$env:TEST_DATABASE_URL="postgresql://user:password@host:5432/test_database"
pytest -m postgres -v
```

**Aktuelle Remote-Testdatenbank fuer lokale Integrationstests:**

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://appuser:<password>@85.215.131.200:5432/wissen2026"
$env:DATABASE_URL=$env:TEST_DATABASE_URL
```

Beispiel mit der aktuell verwendeten Instanz:

```powershell
cd backend
$env:TEST_DATABASE_URL="postgresql+psycopg://appuser:Markus..2026@85.215.131.200:5432/wissen2026"
$env:DATABASE_URL=$env:TEST_DATABASE_URL

# Verbindung pruefen
.\.venv\Scripts\python.exe -c "import os, psycopg; from tests.integration.test_migrations import psycopg_url; conn = psycopg.connect(psycopg_url(os.environ['TEST_DATABASE_URL']), connect_timeout=10); cur = conn.cursor(); cur.execute('select 1'); print(cur.fetchone()[0]); conn.close()"

# Alembic pruefen
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic current

# PostgreSQL-Tests aktivieren
.\.venv\Scripts\python.exe -m pytest -m postgres -q
```

`TEST_DATABASE_URL` muss auf eine **dedizierte Testdatenbank** zeigen.
Der Test fuehrt `alembic downgrade base` aus und entfernt dabei alle Tabellen.

Bekannte Einschraenkungen:

- Die Ziel-Datenbank muss vom lokalen Rechner oder der CI-Umgebung auf `85.215.131.200:5432` erreichbar sein.
- Im aktuellen Verifikationslauf aus dieser Umgebung ist die Verbindung per `psycopg.errors.ConnectionTimeout` fehlgeschlagen.
- Solange die Instanz nicht erreichbar ist, schlagen Alembic und alle `@pytest.mark.postgres`-Tests vor dem eigentlichen Fachtest fehl.
- `alembic heads` zeigt aktuell zwei Heads: `20260505_0016` und `20260506_0013`; damit ist der Alembic-Head-Zustand derzeit nicht linear.
- Die URL enthaelt produktionsnahe Zugangsdaten und darf deshalb nicht in `.env`, `pyproject.toml` oder Git-committete Konfigurationsdateien geschrieben werden.

### Race-Test fuer doppelte Uploads

`tests/integration/test_documents_import.py::test_parallel_duplicate_imports_create_single_document`
prueft, dass zwei gleichzeitige Uploads derselben Datei genau ein Dokument erzeugen und kein
`IntegrityError` nach aussen gelangt:

```bash
cd backend
$env:TEST_DATABASE_URL="postgresql://testuser:testpass@localhost:5433/wissen_test"
pytest tests/integration/test_documents_import.py -v
```

Wichtig: Nur eine fehlende `TEST_DATABASE_URL` ist hier ein legitimer Skip. Wenn `TEST_DATABASE_URL`
gesetzt ist, muessen Alembic-`downgrade base` und `upgrade head` erfolgreich laufen; ein
Migrationsfehler ist ein echter Testfehler.

### CI

Im CI laufen die Postgres-Tests in einem eigenen Job `backend-postgres` mit einem
PostgreSQL-Service-Container. Der Haupt-`backend`-Job (Unit-Tests) laeuft weiterhin ohne
Datenbankabhaengigkeit.

## V1-Grenzen

- Keine Authentifizierung.
- Mehrbenutzerfaehigkeit ist nur ueber Workspace-/User-Felder vorbereitet.
- Keine Vektorsuche.
- Keine Speicherung von Quelldateien ausserhalb abgeleiteter Inhalte und Metadaten.
