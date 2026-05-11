# Operations

Stand: 2026-05-07

## M5 Dokumentationsrahmen

M5 ist aktuell nur als Vorbereitungs- und Dokumentationsrahmen beschrieben.

Statuslogik:

- M5 wird in der Betriebsdokumentation nicht als gestartet markiert, solange kein expliziter Startentscheid auf gruener Gate-Basis dokumentiert ist.
- Vorbereitungsdokumente fuer M5 sind keine Implementierungs- oder Betriebsnachweise.
- Aussagen zu gruener M5-Reife duerfen nur aus aktuellem PostgreSQL-Truth-Nachweis abgeleitet werden.

Vorbereitete M5-Dokumente:

- `docs/data-quality.md`
- `docs/drift.md`
- `docs/cleanup.md`
- `docs/health-score.md`

Diese Dokumente beschreiben nur vorbereitete Regeln, Statuslogik und spaetere Nachweisanker. Sie behaupten keine laufende Implementierung, keine freigegebenen Admin-Aktionen und keinen aktiven M5-Betrieb.

## PostgreSQL-Integrationstests

Test-URL:

- `TEST_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:<port>/<database>`

Lokale Aktivierung:

```powershell
cd backend
$env:TEST_DATABASE_URL="postgresql+psycopg://<user>:<password>@<host>:<port>/<database>"
$env:DATABASE_URL=$env:TEST_DATABASE_URL
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m pytest -m postgres -q
```

Verbindungsstatus am 2026-05-06:

- Der zuletzt versuchte echte PostgreSQL-Nachweis war aus dieser Umgebung nicht erfolgreich.
- Der aktuelle lokale Dokumentations- und Hardening-Lauf ersetzte den echten PostgreSQL-Nachweis nicht; die Truth-Suite wurde ohne `TEST_DATABASE_URL` geskippt.
- `alembic current` und `pytest -m postgres` ersetzen ohne erreichbare dedizierte Testdatenbank keinen Freigabenachweis.
- `alembic heads` ist lokal lesbar, zeigt aber aktuell zwei Heads: `20260505_0016` und `20260506_0013`.

Bekannte Einschraenkungen:

- Die Testdatenbank muss dediziert sein, weil die Tests `alembic downgrade base` und `upgrade head` ausfuehren.
- Ohne Netzwerkzugriff auf den Host schlagen die Tests vor dem eigentlichen Fachsetup fehl.
- `DATABASE_URL` sollte fuer Alembic und `TEST_DATABASE_URL` fuer PostgreSQL-Tests auf dieselbe dedizierte Instanz zeigen, wenn der Testpfad lokal verifiziert wird.
- Solange die Migrationskette zwei Heads hat, ist `alembic head aktuell` nicht als linearer Einzelzustand belegbar.

## M4d Read-only Diagnostics im Betrieb

M4d ist aktuell nur als read-only Systemdiagnose vorbereitet. Vollstaendige M4d-Admin-Aktionen bleiben blockiert, bis M4a, M4b und M4c ihre Gates erreicht haben.

Verfuegbarer Betriebsendpunkt:

- `GET /api/v1/admin/diagnostics`

Der Endpunkt liefert:

- Systemstatus
- DB-Erreichbarkeit
- Alembic current/head Revision
- Dokument-, Version-, Chunk-, Chat-Session- und Chat-Message-Zaehler
- Import-Job-Zustand
- Search-Index-Zustand
- Auth-/Workspace-Isolation-Status

Betriebsgrenzen:

- read-only, keine Writes
- keine Reparaturaktionen
- keine Reindex-, Cleanup- oder Backup-Aktionen
- keine User- oder Workspace-Verwaltung
- keine Dokumentreparatur
- Zugriff nur mit Admin- oder Owner-Rolle im aktiven Workspace
- keine Ausgabe von Dokumenttexten, Chunktexten, Chat-Inhalten, Secrets, Tokens, Connection-Strings oder lokalen Dateipfaden

Fehlerverhalten:

- ohne Auth: `401 UNAUTHORIZED`
- ohne Adminrolle oder bei fremdem Workspace: `403 FORBIDDEN`
- Diagnosefehler: `500 DIAGNOSTICS_FAILED` mit redigierten Details

Blockierte Admin-Aktion:

- `POST /api/v1/admin/search-index/rebuild` ist fuer M4d read-only nicht freigegeben und liefert `501 ADMIN_ACTION_NOT_IMPLEMENTED`.

## M4c Dokument-Lifecycle im Betrieb

Dieses Dokument beschreibt nur den aktuell nachgewiesenen Betriebsstand des Dokument-Lifecycle.

## Lifecycle State Machine

- `active -> archived`
- `archived -> active`
- `active -> deleted`
- `archived -> deleted`
- `deleted` ist terminal

Nicht implementiert:

- `deleted -> active`
- `deleted -> archived`
- Hard Delete / Purge

## Search- und Reindex-Verhalten

- Search verarbeitet nur aktive Dokumente.
- Archivierte und geloeschte Dokumente muessen aus neuen Search-Treffern verschwinden.
- Reindex synchronisiert dazu die Chunk-Sichtbarkeit ueber `document_chunks.is_searchable`.
- Reindex setzt aktive Dokumente suchbar und archivierte oder geloeschte Dokumente unsuchbar.

Betriebsgrenze:

- Der Service-Slice fuer Reindex ist getestet.
- Der letzte echte PostgreSQL-Integrationslauf fuer Search und Reindex ist fehlgeschlagen, weil die konfigurierte Test-Datenbank per Connection-Timeout nicht erreichbar war.
- Reindex bleibt als produktive Admin-Aktion fuer M4d blockiert, solange M4a/M4b/M4c nicht gruen sind.

## Chat- und Citation-Verhalten

- Neue Chat-Antworten beziehen ihre Quellen aus dem Retrieval-/Search-Pfad.
- Historische Citations bleiben im Chatverlauf sichtbar, auch wenn das referenzierte Dokument spaeter archiviert oder geloescht wurde.
- Historische Citations tragen dazu Snapshot-Felder wie `document_title`, `quote_preview` und `source_status`.

Betriebsgrenze:

- Die Historie historischer Citations ist direkt getestet.
- Ein eigener Lifecycle-Integrationstest fuer neue Chat-Antworten fehlt derzeit; der Nachweis ist indirekt ueber Retrieval gegeben.

## Soft Delete

- Soft Delete setzt `lifecycle_status = deleted` und `deleted_at`.
- Versionen, Chunks und historische Citations bleiben physisch erhalten.
- `deleted` ist im aktuellen Betrieb nicht wiederherstellbar.
- Lifecycle-Mutationen sind auth-geschuetzt, aber aktuell nicht hart mit `workspace_id` in den Lifecycle-Service-Aufrufen verknuepft. Fremdworkspace-Mutationssicherheit bleibt deshalb ein M4a/M4c-Gatepunkt.

## Bekannte Einschraenkungen

- keine Admin-Ansicht fuer geloeschte Dokumente
- kein Purge-/Hard-Delete-Prozess
- kein gesonderter historischer Retrieval-Modus fuer archivierte oder geloeschte Dokumente
- kein gruener harter Fremdworkspace-Test fuer Lifecycle-Mutationen
- keine gruen verifizierte PostgreSQL-End-to-End-Abdeckung fuer Search/Reindex im letzten Lauf
- kein direkter Lifecycle-End-to-End-Test fuer neue Chat-Antworten
