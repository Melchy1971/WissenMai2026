# Wissensbasis V1 - Masterplan

**Stand:** 2026-05-12  
**Ground Truth:** Code und Migrationen sind verbindlich. Dokumentation beschreibt den Stand, entscheidet ihn aber nicht.  
**Ziel:** Eine robuste Wissensbasis, in der Dokumente importiert, normalisiert, versioniert, als Chunks lesbar gemacht, spaeter durchsucht und im Chat/Analysekontext verwendet werden koennen.

Paket 5 hat die stabile Dokument-Read-API und Datenkonsistenz vor M3 Suche/Retrieval hergestellt. Der dokumentierte M4a-Zielzustand fordert Authentifizierung und serverseitige Workspace-Isolation, ist im vorliegenden Code aber noch nicht konsistent abgeschlossen.

---

## 1. Leitentscheidungen

| Bereich | Entscheidung | Aktueller Stand |
|---|---|---|
| Backend | FastAPI | ✅ implementiert |
| Frontend | React/Vite | ✅ M3a-Grundlage und M3c-Chat-UI sind implementiert |
| Datenbank | PostgreSQL als Ziel-DB | ✅ Schema und Alembic-Migrationen vorhanden; echter Ziel-DB-Lauf aktuell infra-blockiert |
| Test-DB | SQLite fuer lokale API-/Unit-Tests, optional PostgreSQL via `TEST_DATABASE_URL` | ✅ implementiert |
| Migrationen | Alembic | ✅ implementiert |
| Auth V1 | M4a fuehrt Auth und Workspace-Isolation als Produktthema ein | Zielbild definiert, im Code nicht konsistent abgeschlossen |
| Mehrbenutzer | Datenmodell vorbereiten, Logik spaeter | Auth-Sessions und Workspace-Memberships sind im Backend vorhanden; die Workspace-Isolation ist wegen offener Mutationspfade nicht durchgaengig freigegeben |
| Originaldateien | Nicht speichern | gilt weiterhin |
| Kanonischer Inhalt | `document_versions.normalized_markdown` | ✅ implementiert |
| Versionierung | Dokument zeigt ueber `current_version_id` auf aktuelle Version | ✅ implementiert |
| Chunking | Chunks aus normalisiertem Markdown | ✅ implementiert |
| Quellenanker | normalisiertes `source_anchor` fuer API | ✅ implementiert |
| Duplicate Protection | DB-seitig per `(workspace_id, content_hash)` | ✅ implementiert |
| Upload-Ausfuehrung | persistierte interne Queue mit `202 + job_id + polling`; `BackgroundTasks` nur Bruecke | teilweise implementiert |
| Dokument-Lifecycle | `active`, `archived`, `deleted` mit Soft Delete und historischer Citation-Stabilitaet | teilweise implementiert |
| Fehlerstandard | einheitliches API-Error-Envelope | ✅ implementiert fuer Paket-5-Pfade |
| OCR | explizit nicht Teil von Paket 5 | fehlt |
| GUI-Start | M3a erst nach erfolgreichem Paket-5-Gate mit Score >= 90 | ✅ gestartet und als read-only GUI-Basis umgesetzt |
| Suche/Retrieval | M3, nur auf stabile Read-API und GUI-Foundation aufsetzen | ✅ M3b fachlich implementiert; letzter echter PostgreSQL-Lauf aktuell infra-blockiert |
| Chat | nach M3 | ✅ M3c Chat/RAG Foundation abgeschlossen |
| Analyse | nach Chat/Retrieval-Grundlage | vorbereitet im Datenmodell, Fachlogik fehlt |
| Vektorsuche | optional, nicht V1-kritisch | fehlt |
| Backup/Restore | Teil der M4-Produktisierung, weitergehende Automatisierung spaeter | fehlt |

---

## 2. Aktueller Scope-Stand

### Implemented

- FastAPI-App mit Healthchecks.
- ✅ Alembic-Migrationen fuer Dokumente, Versionen, Chunks, Tags, Chat-/Analyse-Grundtabellen.
- ✅ Parser fuer TXT, MD, DOCX, DOC und PDF ohne OCR.
- ✅ Importpipeline mit Parser-Auswahl, Markdown-Normalisierung, Persistenz und Chunking.
- ✅ Harte Duplicate Protection ueber Unique Constraint `(workspace_id, content_hash)`.
- ✅ Expliziter `import_status` fuer Dokumente.
- Dokument-Read-API:
  - ✅ `GET /documents`
  - ✅ `GET /documents/{document_id}`
  - ✅ `GET /documents/{document_id}/versions`
  - ✅ `GET /documents/{document_id}/chunks`
  - ✅ `POST /documents/import`
- API-Fehlerstandard:
  - ✅ `DOCUMENT_NOT_FOUND`
  - ✅ `WORKSPACE_REQUIRED`
  - ✅ `INVALID_PAGINATION`
  - ✅ `DOCUMENT_STATE_CONFLICT`
  - ✅ `DUPLICATE_DOCUMENT`
  - ✅ `UNSUPPORTED_FILE_TYPE`
  - ✅ `OCR_REQUIRED`
  - ✅ `PARSER_FAILED`
  - ✅ `SERVICE_UNAVAILABLE`
- Paket-5-Dokumentation:
  - ✅ Statusdokument
  - ✅ API-Vertrag
  - ✅ Datenmodell-Dokumentation
  - ✅ ADR
  - ✅ Definition of Done
- ✅ Auth-Kern mit Login/Me-Endpunkten sowie serverseitigem Workspace-Kontext ist implementiert.
- ✅ Jobbasierter Upload-Vertrag `POST /documents/import -> 202 -> Job-Polling` ist implementiert.
- ✅ Dokument-Lifecycle mit `active`, `archived`, `deleted` und Soft Delete ist implementiert.
- ✅ Historische Chat-Citations mit `source_status` sind implementiert.
- ✅ M4d read-only Diagnostics-Aggregat, Search-Index-Inkonsistenzpruefung und blockierter Rebuild-Pfad sind implementiert.
- ✅ RC-3 Advisory-Lock-Service mit 5 Scopes (`document_import`, `lifecycle_transition`, `reindex`, `job_claim`, `job_replay`) via `pg_try_advisory_xact_lock` implementiert.
- ✅ Dead-Letter-Replay-Endpoint `POST /api/v1/admin/jobs/{job_id}/replay` (admin-only) implementiert.
- ✅ source_status Live-Lookup fuer Chat Citations implementiert (`active|archived|deleted|missing`).
- ✅ postgres_truth-Testsuite ist vorhanden unter `backend/tests/postgres_truth/`.
- Der massgebliche Laufstatus fuer M4-Freigabe darf nur aus `reports/postgres_truth_report.json` abgeleitet werden.
- `scripts/validate_m4_truth_gate.py` ist der verbindliche Validator fuer diese JSON-Datei.
- Ohne aktuellen Report sind nur Strukturaussagen ueber die vorhandene Suite zulaessig; statische Gruen-Zaehler sind unzulaessig.
- API-Fehlerstandard erweitert:
  - ✅ `RESOURCE_LOCKED` (409)
  - ✅ `JOB_NOT_REPLAYABLE` (409)
  - ✅ `REPLAY_FAILED` (500)
- ✅ M5 Governance-Services implementiert:
  - ✅ `ReindexGovernanceService` mit Safety-Gates, Audit-Trail und Rollback-Strategie.
  - ✅ `CitationLongevityAuditService` fuer Snapshot-Stabilitaet und Orphan-Rate-Monitoring.
  - ✅ `QueueAgingService` fuer Backlog, Starvation-Detection und Dead-Letter-Auswertung.
  - ✅ `CleanupGovernanceService` mit Dry-Run-First, 3 Safety-Gates und Before/After-Snapshot.
- ✅ Admin-API-Endpunkte fuer M5: `GET /queue/aging`, `GET /citations/longevity`, `POST /reindex/governed`, `POST /cleanup/governed`.
- ✅ Entropy-Test-Suite mit `EntropyMetrics` und Multi-Epoch-Chaos-Recovery-Simulation implementiert.
- ✅ Governance-Envelope-Prinzip: correlation_id, dry_run_only, Safety-Gates, Delta-Snapshot, rollback_strategy.
- Truth-Nachweis fuer M5-Governance-Tests steht noch aus (letzter Report: 2026-05-11, 33 Tests, M4-only).

### Partial

- M4a Auth und Workspace-Isolation sind nur teilweise abgeschlossen.
- M4b Upload/API-Stabilitaet ist nur teilweise abgeschlossen.
- M4a Auth und Workspace-Isolation sind nur teilweise abgeschlossen.
- M4b Upload/API-Stabilitaet ist nur teilweise abgeschlossen.
- M4c Lifecycle ist fachlich implementiert, aber fuer den Abschluss nicht vollstaendig hart nachgewiesen.
- M4d Diagnostics ist nur read-only vorbereitet; vollstaendige Admin-Aktionen bleiben blockiert.
- PDF-Parser erkennt OCR-Bedarf, fuehrt aber kein OCR aus.
- DOC-Parser haengt von lokal verfuegbarem LibreOffice ab.
- Quellenanker sind API-seitig normalisiert, aber Parser liefern nicht fuer alle Formate vollstaendige Positionsdaten.
- `/api/v1/documents` ist als Zielpfad dokumentiert, aktuell ist `/documents` implementiert.

### Missing

- OCR-Engine.
- vollstaendig freigegebener M4a-Produktflow fuer Auth/Logout/Frontend-Route-Guards.
- produktreife Workspace-/User-Verwaltung oberhalb der vorhandenen Membership- und Sessiontabellen.
- Embeddings.
- Analyse-/Merge-/Refine-Fachlogik.
- Backup-/Restore-Automatisierung.
- verpflichtende PostgreSQL-CI-Integrationstests.
- direkter Lifecycle-End-to-End-Nachweis fuer neue Chat-Antworten.

---

## 3. V1-Scope

### Muss in V1

- ✅ Dokumentimport fuer TXT, MD, DOCX, DOC und PDF.
- ✅ Sichtbarer OCR-Bedarf fuer PDFs ohne extrahierbaren Text.
- ✅ Speicherung als normalisierter Markdown in PostgreSQL.
- ✅ Dokumentversionierung.
- ✅ Chunking mit stabiler Reihenfolge.
- ✅ Normalisierte Quellenanker fuer Chunks.
- ✅ Harte DB-Deduplizierung.
- ✅ Stabile Read-API fuer Dokumente, Versionen und Chunks.
- ✅ Einheitlicher Fehlerstandard.
  - Volltextsuche in M3.
  - Chat und Analyse sind fuer M4 kein aktiver Ausbaupfad.
- Produktionsnahe Tests fuer Kernpfade.

### Explizit nicht in V1

- Vollausbau von Login-/Logout-UX.
- OAuth, SSO und externe Identity Provider.
- komplexe Rollen-/Rechteverwaltung.
- Vektorsuche als Pflichtbestandteil.
- VPS-Deployment von GUI/API als Muss.
- vollstaendiges Alerting.
- Speicherung der Originaldateien.

### Explizit nicht in Paket 5

- Suche.
- Chat.
- UI.
- OCR.
- Embeddings.
- Ranking.
- Analysefachlogik.

Vor M3 gelten diese Grenzen als harte Systemgrenzen. Details und Durchsetzungsregeln stehen in `docs/m3-system-boundaries.md`.

---

## 4. Architekturzielbild

### Backend

FastAPI stellt klare Schichten bereit:

- Router: HTTP, Request/Response-Mapping, Dependency Injection.
- Services: fachliche Regeln und Zustandsentscheidungen.
- Repositories: Datenbankzugriff.
- Schemas: stabile Pydantic-Request-/Response-Modelle.
- Models: SQLAlchemy-Persistenzmodell.
- Migrations: Alembic.

Aktuell umgesetzt fuer Paket 5:

- Dokument-Router.
- Dokument-Read-Service.
- Dokument-Repository.
- Dokument-Schemas.
- Fehlerklassen und Exception Handler.
- Import-Persistenz mit DB-Duplicate-Sicherung.

Noch zu vereinheitlichen:

- Import-Persistenz vollstaendig in die gleiche Repository-/Session-Struktur ueberfuehren.
- `/api/v1/documents` als kompatiblen Alias implementieren, wenn M3 strikt versionierte Pfade nutzen soll.

### Frontend

React/Vite ist die gesetzte V1-GUI-Basis. Der GUI-Start war bewusst an das Paket-5-Gate gekoppelt und wurde danach fuer M3a umgesetzt. Aktuell existieren eine Dokument-GUI, Retrieval-Suche, Chat-Oberflaeche, Upload-Job-UI und read-only Admin-Diagnostik gegen die echte API. M4a ist dabei noch nicht konsistent abgeschlossen, weil Login, Sessionkontext und echte Workspace-Isolation in der GUI nicht nachweisbar umgesetzt sind.

### Datenbank

PostgreSQL bleibt zentrale Persistenz:

- Dokumente.
- Dokumentversionen.
- normalisierter Markdown.
- Chunks.
- Chunk-Metadaten und Quellenanker.
- Kategorien und Tags.
- Dokument-Tag-Verknuepfungen.
- Chat-Persistenztabellen, vorbereitete Analyse-Tabellen.

---

## 5. Datenmodell-Prinzipien

### Muss-Felder Dokument

- `id`
- `workspace_id`
- `owner_user_id`
- `title`
- `source_type`
- `mime_type`
- `content_hash`
- `current_version_id`
- `import_status`
- `created_at`
- `updated_at`

Constraints:

- Unique Constraint auf `(workspace_id, content_hash)`.
- Check Constraint fuer erlaubte `import_status`-Werte.

### Muss-Felder Dokumentversion

- `id`
- `document_id`
- `version_number`
- `normalized_markdown`
- `markdown_hash`
- `parser_version`
- `ocr_used`
- `ki_provider`
- `ki_model`
- `metadata`
- `created_at`

### Chunk-Prinzipien

- Chunks entstehen aus `normalized_markdown`.
- Chunks werden ueber `chunk_index ASC` gelesen.
- API nennt die Position `position`.
- Fulltext wird nicht in Dokument-Detail-Responses ausgeliefert.
- Chunk-Endpoint liefert `text_preview` statt Volltext.
- Jeder API-Chunk hat ein normalisiertes `source_anchor`.

Normalisiertes `source_anchor`:

```json
{
  "type": "text",
  "page": null,
  "paragraph": null,
  "char_start": 0,
  "char_end": 200
}
```

Erlaubte Typen:

- `text`
- `pdf_page`
- `docx_paragraph`
- `legacy_unknown`

### Tag-Prinzipien

- Kategorien und Tags getrennt modellieren.
- KI-Tags und manuelle Tags als unterschiedliche Herkunft speichern.
- Manuelle Tags ergaenzen KI-Tags, kein automatisches Ueberschreiben.

---

## 6. Meilensteinplan

## M0 - Projektgrundlage und Architekturvertrag

**Status:** ✅ implemented.

**Ziel:** Neubeginn sauber fixieren, Toolgrenzen definieren, Repo-Struktur festlegen.

### Ergebnis

- ✅ ADRs fuer Tech-Stack und V1-Scope vorhanden.
- ✅ Backend-/Frontend-/Docs-Struktur vorhanden.
- ✅ FastAPI/Alembic-Grundlage vorhanden.

---

## M1 - Datenbank, Migrationen und Dokumentmodell

**Status:** ✅ implemented mit offenen Betriebsdetails.

**Ziel:** Schema fuer Dokumente, Versionen, Tags, Chunks und spaetere Mehrbenutzerfaehigkeit.

### Ergebnis

- ✅ Workspaces und Users vorbereitet.
- ✅ Documents und DocumentVersions implementiert.
- ✅ Chunks implementiert.
- ✅ Categories, Tags und DocumentTags implementiert.
- ✅ Chat- und Analyse-Grundtabellen vorbereitet.
- ✅ DB-Healthcheck vorhanden.
- ✅ Alembic ist gesetztes Migrationstool.

### Offen

- Pflichtlauf der PostgreSQL-Integrationstests in CI.
- Betriebsrunbook fuer echte Ziel-DB.

---

## M2 - Import, Parser und Markdown-Normalisierung

**Status:** partial.

**Ziel:** Importpipeline fuer Dokumente mit Parsern, Normalisierung und Persistenz.

### Implementiert

- ✅ Parser-Interface.
- ✅ TXT- und MD-Parser.
- ✅ DOCX-Parser.
- ✅ DOC-Parser via LibreOffice-Konvertierung.
- ✅ PDF-Parser ohne OCR.
- ✅ Markdown-Normalizer.
- ✅ Chunking.
- ✅ Import erzeugt Dokument, Version und Chunks.
- ✅ Duplicate Detection und DB-seitige Duplicate Protection.

### Nicht implementiert

- OCR-Ausfuehrung.
- KI-/Ollama-Normalisierung als aktiver Importschritt.
- Parser-Confidence.
- Vollstaendige Quellenpositionsdaten fuer alle Parser.

---

## M4 - Neuaufsetzung auf Basis des realen Zustands

**Status:** aktiv neu geschnitten.

**Ground Rule:** M4 wird auf den belegten Kern reduziert. Alte Parallelmodelle, halbfertige Produktpfade und Scope-Erweiterungen gelten nicht als M4-Fortschritt.

### Neue Reihenfolge

1. `M4a - Auth (hart)`
2. `M4b - Upload (stabil)`
3. `Gate fuer M4a + M4b`
4. erst danach Entscheidung ueber `M4c+`

### Harte Stop-Regel fuer ganz M4

- Kein Start von `M4c+`, solange `M4a` und `M4b` nicht beide freigegeben sind.
- Kein Ausbau von Chat, Admin-UX, Backup/Restore oder weiterer Produktisierung, solange alte Parallelannahmen im System aktiv sind.
- Dokumentation darf nicht ueber den belegten Code- und Teststand hinausgehen.

---

## M4a - Auth (hart)

**Status:** partial, nicht freigegeben.

**Ziel:** Ein einziges, durchgesetztes Sicherheitsmodell ohne Fallbacks oder Sonderpfade.

### Scope

- verpflichtende Authentifizierung fuer geschuetzte Endpunkte
- eindeutige Benutzeridentitaet
- serverseitige Workspace-Zuordnung aus Auth-Kontext
- Membership-Pruefung pro Workspace
- kein Endpoint vertraut `workspace_id` aus Query oder Body
- Admin-Rechte nur ueber Rollenmodell
- Mutationen muessen ebenso workspace-scoped sein wie Read-Pfade

### Nicht-Scope

- Login-UI
- Logout-UX
- OAuth, SSO und externe Identity Provider
- feingranulare Enterprise-Rollenmodelle

### Aktueller realer Stand

- Auth-Middleware und Header-basierter Request-Kontext sind implementiert.
- `POST /api/v1/auth/login` und `GET /api/v1/auth/me` existieren als technischer Kern.
- Search, Dokument-Read, Upload und Teile der Admin-/Chat-Pfade nutzen bereits den Auth-Kontext.
- M4a ist trotzdem nicht abgeschlossen, weil die Sicherheitsgrenze noch nicht fuer alle Mutationen konsistent durchgezogen ist; insbesondere Lifecycle-Mutationen uebergeben aktuell keinen Workspace an den Service.

### Freigabekriterien

- alle geschuetzten Endpunkte verlangen gueltige Authentifizierung
- kein produktiver Fachendpoint vertraut `workspace_id` aus Query oder Body
- keine produktive Nutzung von `x-admin-token`
- keine produktiven Default-Workspace-/Default-User-Pfade
- Lifecycle- und sonstige Mutationen sind workspace-scoped
- Angriffstests fuer unautorisierte, fremde und manipulierte Requests sind gruen

### Stop-Regeln fuer M4a

- irgendein geschuetzter Endpoint funktioniert ohne gueltige Auth
- irgendeine Mutation ist nicht workspace-scoped
- irgendein produktiver Endpoint nutzt `workspace_id` als Vertrauensquelle aus Query oder Body
- `x-admin-token` ist noch Teil des produktiven Vertrags
- Default-Workspace oder Default-User beeinflusst noch produktive Requests

---

## M4b - Upload (stabil)

**Status:** partial, nicht freigegeben.

**Ziel:** Ein robuster Einzelupload mit genau einem kanonischen Vertrag und nachvollziehbaren Zustandswechseln.

### Scope

- genau ein Uploadvertrag: `POST /documents/import -> 202 Accepted -> Job-Polling`
- saubere Fehlerpfade fuer Typ, Groesse, Parserfehler, OCR-Bedarf und Job-404
- korrektes Duplicate-Handling auch unter Parallelitaet
- GUI zeigt den echten Job- und Importzustand
- Frontend nutzt den zentralen Auth-/Workspace-Kontext
- Dokumentliste wird nach erfolgreichem Import korrekt aktualisiert

### Nicht-Scope

- OCR-Produktflow
- Upload aus Chat
- Multi-Upload
- ausgebaute Diagnostik oder Komfortfeatures
- Polling-Optimierung vor Stabilisierung des Kernvertrags

### Aktueller realer Stand

- Der jobbasierte Uploadpfad ist im Backend und in Teilen der GUI implementiert.
- Standardfehler, Auth-Bindung und einfache Erfolgsfaelle sind nachweisbar.
- Der Upload ist auth-gebunden; Workspace und Benutzer kommen aus dem serverseitigen Auth-Kontext.
- Default-Workspace-/Default-User-Fallbacks sind im Upload-Flow nicht aktiv.
- Ein PostgreSQL-Race-Test fuer parallele Duplicate-Uploads ist im Repository vorhanden.
- Dieser Test ist aktuell nicht gruen verifiziert; der letzte echte PostgreSQL-Lauf endete nicht mit fachlichem Ergebnis, sondern an DB-Erreichbarkeit und Migrationsvoraussetzungen.
- Nach aktuellem Gate-Stand ist M4b mit realer PostgreSQL-Bewertung **nicht freigegeben**.

### Freigabekriterien

- keine zweite Upload-Semantik im Code, in Tests oder in der Doku
- Integrationstests pruefen den echten jobbasierten Vertrag
- Duplicate-Verhalten ist auch unter Parallelitaet sauber
- GUI und Backend-Vertrag sind deckungsgleich
- Fehlercodes sind sichtbar, korrekt gemappt und stabil
- Dokumentation behauptet kein nicht implementiertes Upload-Verhalten
- Der PostgreSQL-Race-Test ist entweder verpflichtend gruen oder bewusst als externer Infrastrukturblocker ausgelagert.

### Nachweisstand

- `tests/integration/test_documents_import.py` enthaelt den Race-Test `test_parallel_duplicate_imports_create_single_document`.
- Der Test ist mit `@pytest.mark.postgres` markiert.
- Er benoetigt `TEST_DATABASE_URL`.
- Im letzten echten Lauf wurde er wegen nicht verfuegbarer PostgreSQL-Migrationsvoraussetzungen `skipped`.
- Damit liegt aktuell **kein gruener echter PostgreSQL-Nachweis** fuer paralleles Duplicate-Handling vor.

### Stop-Regeln fuer M4b

- Upload hat mehr als einen aktiven Vertragsmodus
- Duplicate-Verhalten ist unter Parallelitaet nicht belastbar korrekt
- GUI zeigt nicht den realen Backend-Zustand
- Tests pruefen veraltete Upload-Semantik statt des echten Job-Flows

---

## M4c+ - Gate-Abhaengigkeit

**Status:** teilweise vorbereitet, nicht vollstaendig freigegeben.

Seit der urspruenglichen Stop-Regel wurden M4c und M4d in begrenzten Slices vorbereitet:

- M4c Lifecycle ist fachlich implementiert, bleibt aber Gate-pflichtig.
- Lifecycle-Mutationen brauchen noch einen harten workspace-scoped Service-/API-Nachweis.
- M4d Diagnostics ist nur read-only vorbereitet.
- M4e Backup/Restore bleibt Konzept.

Nicht freigegeben vor erfolgreichen M4a/M4b/M4c-Gates:

- produktive Reindex-/Repair-/Cleanup-/Backup-Admin-Aktionen
- vollstaendige Admin-UX
- weitere Produktisierung, Komfortfeatures und Ausbaupfade

M5 bleibt blockiert, solange M4a, M4b und M4c ihre Ziel-Gates nicht erreichen.

---

## Paket 5 - Dokument-Read-API und Datenkonsistenz vor Retrieval

**Status:** ✅ implemented.

**Ziel:** Dokumente stabil lesbar machen und API-Stabilitaet herstellen, bevor M3 Suche/Retrieval startet.

### Implementiert

- ✅ `GET /documents`.
- ✅ `GET /documents/{document_id}`.
- ✅ `GET /documents/{document_id}/versions`.
- ✅ `GET /documents/{document_id}/chunks`.
- ✅ `POST /documents/import` stabilisiert.
- ✅ Pydantic Response Models.
- ✅ Service-/Repository-Trennung fuer Read-Pfade.
- ✅ Keine direkte DB-Nutzung im Dokument-Router fuer Read-Endpunkte.
- ✅ Importstatus.
- ✅ Normalisierte Chunk-Source-Anchors.
- ✅ DB Unique Constraint fuer Duplicate Protection.
- ✅ Deterministisches Duplicate Handling.
- ✅ Einheitlicher API-Fehlerstandard.
- ✅ Unit-, API- und optionale Integrationstests.
- ✅ API-Vertrag und ADR.

### Akzeptanzstatus

- ✅ Paket 5 ist fachlich abgeschlossen.
- ✅ Paket 5 ist technisch als Abschluss-Gate verifiziert.
- Restpunkte sind als technische Schulden dokumentiert:
  - `/api/v1/documents` Alias fehlt.
  - Import-Persistenz nutzt teilweise direkten `psycopg`-Zugriff.
  - Parser liefern Quellenpositionen noch uneinheitlich.

### Abschlussnachweis

- ✅ Standardlauf verifiziert: `42 passed, 1 skipped`.
- ✅ PostgreSQL-Integrationslauf verifiziert: `6 passed`.
- ✅ Ruecklauf fuer beruehrte Read-/Import-Pfade verifiziert: `19 passed`.
- ✅ PostgreSQL-Benchmark auf Referenzdaten verifiziert:
  - `GET /documents = 3.1ms`
  - `GET /documents/{id} = 3.4ms`
  - `GET /documents/{id}/chunks = 2.1ms`
- ✅ Finale Paketbewertung: `96/100`.
- ✅ Finale Entscheidung: `abgeschlossen`.

---

## M3a - GUI Foundation

**Status:** partial.

**Ziel:** Read-only Web-GUI zur Sichtbarmachung des Backend-Zustands auf stabiler Backend- und API-Basis, ohne Such-, Chat- oder Analysefachlogik vorzuziehen.

### Harte Startbedingungen

- Paket 5 ist im Abschluss-Gate erfolgreich freigegeben.
- Paket-5-Gesamtscore ist `>= 90`.
- Der Dokument-API-Vertrag fuer Read- und Import-Pfade ist mit dem Code synchronisiert.
- Read-API, Fehlerstandard und Datenkonsistenz sind auf PostgreSQL praktisch verifiziert.
- Offene Restpunkte aus Paket 5 sind dokumentierte Nicht-Blocker und nicht contract-critical fuer die GUI-Basis.

### Scope

- Technische GUI-Grundstruktur mit React/Vite stabilisieren.
- API-Client-Schicht strikt gegen den dokumentierten Dokument-API-Vertrag aufbauen.
- Basisnavigation und App-Shell fuer Dokumentliste und Dokumentdetail bereitstellen.
- Lade-, Leer- und Fehlerzustaende passend zum API-Error-Envelope definieren.
- Frontend-Typen, DTO-Mapping und Vertragsgrenzen zwischen Backend und GUI festziehen.
- Read-only Sicht auf Dokumentliste, Dokumentdetail, Versionen, Chunks und Importstatus ueber vorhandene Endpunkte anbinden.
- Fehlerzustaende und Zustandskonflikte sichtbar machen, ohne fachliche Korrektur- oder Schreibpfade einzufuehren.

### Nicht-Scope

- Keine Suche, kein Ranking und kein Retrieval.
- Kein Chat und keine Chat-UI.
- Kein Upload.
- Kein Bearbeiten von Dokumenten, Versionen oder Chunks.
- Keine Rollen- und Rechteverwaltung.
- Keine Analyse-, Merge-, Refine- oder Commit-Oberflaechen.
- Keine OCR-UI oder parsernahen Sonderlogiken ausser sichtbarer Status- und Fehlerdarstellung.
- Keine Embeddings oder embeddingnahe Oberflaechen.
- Keine direkte Kopplung an DB-Strukturen, Parser-Interna oder undokumentierte Response-Felder.

### Zielbild

- Die GUI ist ein lesender Beobachter des Backend-Zustands.
- Nutzer sehen, welche Dokumente im System vorhanden sind, in welchem Importzustand sie sich befinden und welche Versionen und Chunks aktuell lesbar sind.
- Die GUI bildet nur bereits vorhandene Backend-Faehigkeiten ab und fuehrt keine neue Fachlogik ein.
- Jeder sichtbare Zustand in der GUI muss direkt aus einem dokumentierten API-Response ableitbar sein.

### Screens

- Dokumentliste
  - Tabelle oder Kartenansicht mit `title`, `mime_type`, `created_at`, `updated_at`, `import_status`, `version_count`, `chunk_count`.
  - Leerstates und Fehlerstate fuer fehlende `workspace_id`, ungueltige Pagination oder Backend-Fehler.
- Dokumentdetail
  - Stammdaten des Dokuments, `import_status`, `latest_version`, Parser-Metadaten und Chunk-Summary.
  - Sichtbarer Hinweis bei inkonsistentem Dokumentzustand oder nicht lesbarem Dokument.
- Versionen-Ansicht
  - Read-only Liste der vorhandenen Versionen in API-Reihenfolge.
  - Anzeige von `version_number`, `created_at`, `content_hash` und relevanten Metadaten aus dem Vertrag.
- Chunks-Ansicht
  - Read-only Liste der Chunks der aktuellen Version in `position ASC`.
  - Anzeige von `position`, `text_preview` und normalisiertem `source_anchor`.
- Fehler- und Statusdarstellung
  - Gemeinsame UI-Komponente fuer API-Fehler, Leerstates und Konfliktzustaende.
  - Sichtbare Darstellung von `OCR_REQUIRED`, `DOCUMENT_STATE_CONFLICT`, `DOCUMENT_NOT_FOUND`, `WORKSPACE_REQUIRED` und `INVALID_PAGINATION`, soweit sie ueber die M3a-Screens auftreten.

### User Flows

- Nutzer oeffnet die Dokumentliste fuer einen Workspace und sieht alle lesbaren Dokumente mit Importstatus.
- Nutzer waehlt ein Dokument aus der Liste und gelangt in die Dokumentdetailansicht.
- Nutzer oeffnet von dort die Versionen-Ansicht und sieht die Versionshistorie read-only.
- Nutzer oeffnet die Chunks-Ansicht und sieht die Chunks der aktuellen Version mit Quellenanker und Vorschautext.
- Nutzer trifft auf einen Fehler- oder Konfliktzustand und bekommt den Backend-Status sichtbar, ohne dass die GUI versucht, ihn still zu reparieren.

### API-Abhaengigkeiten

- Dokumentliste haengt an `GET /documents`.
- Dokumentdetail haengt an `GET /documents/{document_id}`.
- Versionen-Ansicht haengt an `GET /documents/{document_id}/versions`.
- Chunks-Ansicht haengt an `GET /documents/{document_id}/chunks`.
- Importstatus wird ausschliesslich aus dokumentierten Response-Feldern wie `import_status` gelesen.
- Fehlerdarstellung haengt am standardisierten Error-Envelope `{"error": {"code": "...", "message": "...", "details": {...}}}`.
- M3a fuehrt keine neue API ein; sie konsumiert ausschliesslich vorhandene Paket-5-Endpunkte.

### Begruendung fuer den spaeten GUI-Start

- Vor Paket 5 waere die GUI gegen instabile Read-Pfade, uneinheitliche Fehlerfaelle und wechselnde Datenzustandsregeln entwickelt worden.
- Fruehe GUI-Entwicklung haette Backend-Unschaerfen kaschiert statt den API-Vertrag zu haerten.
- Paket 5 definiert die stabile Integrationsgrenze fuer Dokumentliste, Dokumentdetail, Versionen, Chunks, Import und Fehlerbehandlung.
- Erst nach erfolgreichem Paket-5-Gate lohnt sich GUI-Arbeit, weil dann Backend, Datenmodell und Vertragsgrenzen belastbar genug sind und teure UI-Nacharbeit durch API-Brueche vermieden wird.

### Abhaengigkeiten zwischen Backend, API-Vertrag und GUI

- Backend liefert die fachliche Wahrheit fuer Dokumentzustand, Versionen, Chunks und Fehlercodes.
- Der API-Vertrag ist die einzige erlaubte Kopplung zwischen GUI und Backend.
- GUI konsumiert nur dokumentierte Endpunkte und contract-critical Felder.
- Backend-Aenderungen mit GUI-Auswirkung muessen zuerst im API-Vertrag beschrieben werden, bevor die GUI sie konsumiert.
- M3 baut fuer Suchfunktionen auf derselben GUI-Foundation auf, erweitert sie aber erst nach stabiler Such-API.

### Gate-Regel

- Start von M3a nur, wenn Paket 5 im Abschluss-Gate den Score `>= 90` erreicht und als `freigegeben` bzw. `abgeschlossen` dokumentiert ist.

### Akzeptanzkriterien

- Die GUI zeigt eine Dokumentliste fuer einen Workspace auf Basis von `GET /documents` an.
- Die GUI zeigt fuer ein Dokument eine Detailansicht auf Basis von `GET /documents/{document_id}` an.
- Die GUI zeigt Versionen read-only auf Basis von `GET /documents/{document_id}/versions` an.
- Die GUI zeigt Chunks read-only auf Basis von `GET /documents/{document_id}/chunks` an.
- `import_status` ist in Liste und Detail sichtbar.
- Relevante Fehlerzustaende aus dem API-Vertrag werden sichtbar angezeigt und nicht verdeckt.
- M3a fuehrt keine Schreiboperationen, keinen Upload, keine Suche, keinen Chat, keine OCR-Logik und keine Embedding-Logik ein.
- Die GUI koppelt nur an dokumentierte Endpunkte und contract-critical Felder.

### Aktueller Abschlussstand

- ✅ Minimaler read-only GUI-Prototyp ist implementiert.
- ✅ Dokumentliste ist unter `/documents` sichtbar.
- ✅ Dokumentdetail ist unter `/documents/:id` sichtbar.
- ✅ Versionen und Chunk-Vorschau werden im Detailscreen angezeigt.
- ✅ Importstatus und Fehlercodes sind sichtbar.
- ✅ Suche, Chat, Upload und Mutation sind nicht implementiert.
- ✅ Frontend-Testlauf verifiziert: `5 passed`.
- ✅ Frontend-Build verifiziert: `vite build` erfolgreich.
- Offen fuer harten Abschluss:
  - Unit-Tests fuer ViewModel-Mapping und Fehlerabbildung.
  - dedizierte API-Mock-Tests fuer `404`, `409` und API down.
  - E2E-Smoke-Test fuer Liste -> Detail -> Chunks.

### Vorlaeufige Entscheidung

- M3a ist als Prototyp umgesetzt, aber nicht als final abgeschlossen freigegeben.
- M3b Retrieval startet erst nach Schliessung der offenen Testluecken.

---

## M3b - Retrieval Foundation

**Status:** implemented.

**Ziel:** Such- und Retrieval-Basis auf Chunk-Ebene einfuehren, ohne Chat, LLM-Antwortgenerierung oder semantische Suche vorzuziehen.

### Vorbedingungen

- M3a GUI Foundation ist als Prototyp umgesetzt, aber noch nicht als final abgeschlossen freigegeben.
- M3 nutzt dokumentierte Read-Endpunkte und contract-critical Felder.
- M3 greift nicht direkt auf Parser-Interna oder freie Chunk-Metadaten zu.
- Chunks werden ueber `chunk_id`, `position` und `source_anchor` referenziert.
- Duplicate-Dokumente sind DB-seitig verhindert.
- Parser-/OCR-Fehler sind sichtbar.

### Zielbild

- Volltextsuche arbeitet auf Chunk-Ebene.
- Jede Trefferzeile enthaelt Dokumentbezug, Version, Chunk und Quellenanker.
- Retrieval bleibt read-only und nachvollziehbar.
- Ranking startet mit einer einfachen technischen Baseline.
- `workspace_id` begrenzt den Suchraum explizit.

### API-Endpunkte

- Neuer Query-Endpunkt `GET /api/v1/search/chunks`.
- Query-Parameter:
  - `workspace_id` required
  - `q` required
  - `limit` optional, Default `20`, Range `1..100`
  - `offset` optional, Default `0`, Range `>= 0`
- Fehlerfaelle:
  - `WORKSPACE_REQUIRED`
  - `INVALID_QUERY`
  - `INVALID_PAGINATION`
  - `SERVICE_UNAVAILABLE`

### Ranking-Strategie

- PostgreSQL-Fulltextsuche ueber Chunk-Inhalt.
- Ranking-Baseline ueber native Rank-Funktion wie `ts_rank`.
- Sortierung primär nach `rank DESC`.
- Sekundaere Sortierung fuer Stabilitaet ueber Dokumentzeitstempel und Chunk-Position.
- Kein komplexes Re-Ranking in M3b.

### Datenmodelländerungen

- Volltextindex oder TSVECTOR-basierter Suchpfad fuer `document_chunks.content`.
- Keine Embedding-Tabellen.
- Keine Vektorindizes.
- Keine Chat- oder Zusammenfassungstabellen.
- Suchpfad durchsucht nur lesbare Dokumente und gueltige aktuelle Versionen.

### Tasks

- Such-Contract fuer M3b definieren.
- PostgreSQL-Fulltext-Suche auf Chunks implementieren.
- Ergebnisliste mit Dokumentbezug implementieren.
- Ranking-Baseline fuer Volltexttreffer implementieren.
- Filterung nach `workspace_id` implementieren.
- Quellenanker im Suchergebnis ausgeben.
- Query API bauen.
- Tests fuer Ranking, Filter, Quellenanker und PostgreSQL-Suchpfad.
- Optional: kompatiblen `/api/v1/documents`-Alias vor M3-Clientbindung einfuehren.

### Tests

- Unit Tests fuer Query-Validierung, Ranking-Baseline und Ergebnis-Mapping.
- API-Tests fuer erfolgreichen Suchlauf, `workspace_id`-Filter, Pagination und Fehlerfaelle.
- PostgreSQL-Integrationstests fuer Chunk-Volltextsuche und Ausschluss nicht lesbarer Dokumente.

### Aktueller Abschlussstand

- ✅ `GET /api/v1/search/chunks` ist implementiert.
- ✅ PostgreSQL-FTS-Ranking-Baseline ist implementiert.
- ✅ Migration fuer `search_vector` und `GIN`-Index ist vorhanden.
- ✅ GUI-Suche auf `/documents` ist implementiert.
- ✅ Lade-, Leer- und Fehlerzustaende fuer Suche sind sichtbar.
- ✅ Failure-Mode-Matrix und minimales Evaluation-Dataset sind dokumentiert.
- PostgreSQL-Integrationsnachweis fuer echte Suchtreffer und Filterung ist vorhanden.
- Ranking-Regressionstest fuer stabile Reihenfolge ist vorhanden.

### Entscheidung

- M3b ist abgeschlossen.
- Score: `92/100`
- Go fuer M3c Chat/RAG: `Go`

### Akzeptanzkriterien

- Suche findet Inhalte ueber Chunks.
- Treffer enthalten Dokumentbezug, Version, Chunk und normalisierten Quellenanker.
- Ergebnisse sind nach einer technischen Ranking-Baseline sortiert.
- `workspace_id`-Filter funktioniert.
- Query API bleibt read-only.
- Suche indexiert oder liefert keine Dokumente mit `failed`, `pending` oder OCR-pflichtigem Fehlerzustand.

### Out of Scope

- Chat.
- LLM-Antwortgenerierung.
- komplexes Re-Ranking.
- semantische Suche, solange Embeddings nicht stabil sind.
- automatische Zusammenfassungen.

---

## M3c - Chat/RAG Foundation

**Status:** implemented.

**Ziel:** Die Chat-/RAG-Grundlage bereitstellen, damit Fragen spaeter ueber Retrieval-Kontext beantwortet, Quellen maschinenlesbar zugeordnet und unzureichender Kontext deterministisch abgefangen werden kann.

### Tasks

- Chat-HTTP-Vertrag definieren.
- Context Builder fuer Retrieval-Kontext implementieren.
- Prompt Builder fuer dokumentbasierte Antworten implementieren.
- Citation Mapper fuer maschinenlesbare Quellen implementieren.
- Insufficient-Context-Policy definieren und implementieren.
- Chat-Session-, Message- und Citation-Persistenz implementieren.
- Frontend-Chatseite gegen den Zielvertrag anbinden.
- Tests fuer Halluzinationsschutz, Persistenz und Quellenlogik ergaenzen.
- RagChatService fuer den integrierten Antwortpfad implementieren.
- Fake LLM Provider fuer deterministische Tests implementieren.
- Chat-API- und Frontend-Tests gegen den echten Vertrag abschliessen.

### Aktueller Abschlussstand

- ✅ Prompt-Vertrag fuer dokumentbasierte Antworten ist dokumentiert.
- ✅ Context Builder ist implementiert.
- ✅ Prompt Builder ist implementiert.
- ✅ Citation Mapper ist implementiert.
- ✅ Insufficient-Context-Policy ist implementiert.
- ✅ Chat-Session-, Message- und Citation-Persistenz ist implementiert.
- ✅ Frontend-Chatseite ist implementiert.
- ✅ Fokustests fuer die neuen M3c-Bausteine sind vorhanden.
- Chat-HTTP-API fuer Sessions und Messages ist implementiert.
- Message API ist mit `RagChatService` verdrahtet.
- End-to-End-RAG-Flow ueber echten API-Pfad ist mit Fake LLM getestet.
- Fehlercodes fuer Chat/RAG sind implementiert und getestet.
- Frontend ist gegen den echten Chat-Vertrag aktualisiert.

### Finale Entscheidung

- M3c Chat/RAG Foundation ist abgeschlossen.
- Score: `94/100`
- Go fuer M4-Folgearbeit: `Go`

### Begruendung

- Die Kernbausteine, stabile API, RAG-Orchestrierung, Fehlerstandard, Fake-LLM-Testbarkeit und GUI-Vertrag sind vorhanden und getestet.
- Produktiver LLM Provider, Streaming, Agenten, Tool Use, Embeddings und Dokumentmutation bleiben ausserhalb von M3c.

### Akzeptanzkriterien

- Retrieval-Kontext kann deterministisch zu einem Kontextpaket aufgebaut werden.
- Der Prompt fuer dokumentgestuetzte Antworten ist deterministisch erzeugbar.
- Quellen koennen aus einer Antwort strukturiert auf Chunks und Dokumente abgebildet werden.
- Unzureichender Kontext fuehrt zu einer festen No-Answer-Entscheidung statt zu freier Halluzination.
- Chat-Sessions, Messages und Citations sind persistierbar.
- Die Chat-GUI kann Sessionliste, Verlauf, Antworten, Citations und Insufficient-Context-Zustaende darstellen.

### M3c-Nicht-Scope

- produktiver LLM Provider
- Streaming
- Agenten
- Tool Use
- Dokumentmutation
- Embeddings
- Analyse- und Commit-Funktionen

---

## M4 - Produktisierung und Betriebsfaehigkeit

**Status:** missing.

**Ziel:** Aus dem funktionalen lokalen Wissenssystem ein belastbares Produkt fuer den lokalen Betrieb machen. M4 fuehrt keine neue Intelligenz-Schicht ein, sondern haertet Betrieb, Qualitaet, Sicherheit, Isolation, Lifecycle und Dokumentation auf Basis der abgeschlossenen M3-Fundamente.

### M4 Zielbild

- Das System ist nicht nur funktional, sondern lokal belastbar betreibbar.
- Benutzerzugriff, Workspace-Grenzen, Dokument-Lifecycle und Diagnosepfade sind explizit modelliert.
- Upload, Chat und Retrieval sind ueber GUI und API konsistent in einen kontrollierten Produktfluss eingebettet.
- Betriebssicht, Backup/Restore, Beobachtbarkeit und Performance sind fuer den lokalen Einsatz dokumentiert und nachweisbar.
- M4 verbessert Robustheit, Sicherheit und Wartbarkeit, ohne neue agentische oder workflowgetriebene Produktlogik zu erzwingen.

### Scope

- Authentifizierung und klares Benutzerkonzept fuer lokalen Betrieb.
- Workspace-Isolation ueber API, Persistenz und GUI.
- Upload-GUI fuer den bestehenden Importpfad.
- Dokument-Lifecycle mit sichtbaren Statusuebergaengen und kontrollierten Bedienpfaden.
- Admin- und Diagnoseansicht fuer lokalen Systemzustand.
- Observability fuer Backend, Jobs, Fehler und zentrale Betriebskennzahlen.
- Backup/Restore fuer lokale Betriebs- und Wiederherstellungsfaehigkeit.
- Performance-Haertung fuer die bereits vorhandenen Read-, Retrieval- und Chat-Pfade.
- Deployment- und Betriebsdokumentation fuer reproduzierbaren lokalen Betrieb.

### Nicht-Scope

- Agenten.
- automatische Aktionen.
- komplexe Workflows.
- Multi-User-Collaboration.
- Enterprise-Rollenmodell.
- externe Integrationen.
- neue semantische oder agentische Intelligenz-Schichten.

### Tasks

- Authentifizierung und Benutzerkonzept auf den bestehenden lokalen Produktfluss aufsetzen.
- Workspace-Isolation in API, Datenmodell, Query-Pfaden und GUI hart absichern.
- Upload-GUI fuer den bestehenden Dokumentimport bereitstellen.
- Dokument-Lifecycle fuer Import, Lesbarkeit, Fehlerzustand, Archivierung oder Sichtbarkeit konsistent modellieren.
- Lifecycle-State-Machine fuer `active`, `archived` und `deleted` dokumentieren und gegen Read-, Search-, Chat- und GUI-Verhalten pruefen.
- Admin- und Diagnoseansicht fuer Health, Fehler, Queue- oder Jobstatus und Betriebszustand bereitstellen.
- Observability fuer Backend, Import, Retrieval und Chat standardisieren.
- Backup/Restore fuer lokalen Betrieb definieren, dokumentieren und pruefen.
- Performance-Haertung fuer Paket-5-, M3b- und M3c-Pfade mit messbaren Budgets abschliessen.
- Deployment- und Betriebsdokumentation fuer lokale Zielumgebungen vervollstaendigen.

### Abhaengigkeiten zu M3

- M3a liefert die GUI-Grundstruktur, auf der Upload-, Admin- und Diagnoseansichten aufsetzen.
- M3b liefert den Retrieval-Pfad, dessen Performance und Isolation in M4 gehaertet werden.
- M3c liefert Chat-API, RAG-Orchestrierung und Fehlerstandard, die in M4 betrieblich abgesichert werden.
- M4 setzt voraus, dass M3b und M3c funktional abgeschlossen oder nur noch in nicht-blockierenden Restpunkten offen sind.
- M4 darf keine neuen fachlichen Antworten oder neue Intelligenzlogik erzwingen, sondern stabilisiert die vorhandenen M3-Faehigkeiten.
- M4d ist vor Abschluss von M4a/M4b/M4c nur als read-only Diagnostics-Slice freigegeben; Admin-Aktionen bleiben blockiert.

### Akzeptanzkriterien

- Zugriff auf das lokale System ist ueber ein definiertes Benutzerkonzept abgesichert.
- Workspaces sind in API, Datenhaltung und GUI wirksam voneinander isoliert.
- Dokumente koennen ueber eine GUI hochgeladen und ueber ihren Lifecycle nachvollziehbar verfolgt werden.
- Historische Citations bleiben bei archivierten oder geloeschten Dokumenten lesbar; neue Retrieval-Treffer bleiben auf `active` beschraenkt.

Aktueller M4-Gate-Stand am 2026-05-11:

M4-Freigabe wird nicht mehr ueber manuelle Scores abgeleitet. Die einzige Gate-Quelle ist `reports/postgres_truth_report.json`, geprueft durch `scripts/validate_m4_truth_gate.py`.

Der aktuelle Report weist `pytest_exit_code = 0`, `failed = 0`, `skipped = 0` und `passed = 33` aus. Damit gilt:

- `M4 Truth Gate = PASS`
- Das PostgreSQL-Truth-Gate ist aktuell gruen.
- M4 bleibt dennoch insgesamt blockiert.
- M5 bleibt blockiert.
- Manuelle Score-Freigaben bleiben fuer M4 unzulaessig; der Validator ist Gate-Quelle, ersetzt aber keine offenen Restgates ausserhalb des Truth-Reports.

RC-3-Hardening-Nachweis (2026-05-08):

| Komponente | Status |
|---|---|
| Advisory Lock Service (5 Scopes) | ✅ implementiert |
| `pg_try_advisory_xact_lock` transaction-scoped | ✅ implementiert |
| Lifecycle-Lock in `DocumentLifecycleService` | ✅ integriert |
| Reindex-Lock in `SearchIndexRebuildService` | ✅ integriert |
| Job-Claim-Lock in `BackgroundJobService` | ✅ integriert |
| Dead-Letter-Replay mit Job-Replay-Lock | ✅ implementiert |
| `POST /api/v1/admin/jobs/{job_id}/replay` | ✅ implementiert |
| source_status Live-Lookup fuer Chat Citations | ✅ implementiert |
| postgres_truth-Suite | vorhanden unter `backend/tests/postgres_truth/` |
| Letzter beweisbarer Lauf | nur mit gesetzter `TEST_DATABASE_URL` und beigefuegtem aktuellem Report |
| Ergebnisregel | kein statisches `gruen` ohne aktuellen Report |

Gate-Regel fuer M5:

- `scripts/validate_m4_truth_gate.py` muss `M4 Truth Gate = PASS` liefern.
- Die Basis dafuer ist ausschliesslich `reports/postgres_truth_report.json`.
- Manuelle M4a/M4b/M4c-Scores koennen den Validator nicht ersetzen.

Aktuelles Ergebnis:

- Der aktuelle Validator-Status ist PASS; das Truth-Gate selbst blockiert M4 derzeit nicht.
- Der reale M4e-Minimal-Nachweis ist erbracht.
- M4 ist fuer den lokalen Produktbetrieb nun technisch abgeschlossen.
- M5-Vorbereitung ist erlaubt.
- Die kompakte Freigabefassung steht in `docs/m4-m5-freigabefassung.md`.

M4e Restore-Truth-Nachweis am 2026-05-11:

- Ein echter isolierter Backup/Restore-Truth-Test wurde gegen temporaere PostgreSQL-Datenbanken erfolgreich ausgefuehrt.
- Geprueft wurden Workspaces, Dokumente, Chunks, Chat-Sessions, Citations, Queue-Jobs, Search-Paritaet und Lifecycle-Paritaet.
- Ergebnis: kein nachweisbarer Datenverlust im geprueften Scope, keine nachweisbare Drift im Restore-Ziel.
- Referenzen:
  - `reports/restore_truth_report.md`
  - `docs/runbooks/backup-restore.md`
  - `docs/runbooks/disaster-recovery.md`

Finale M4 Matrix am 2026-05-11:

Formale Gate-Quellen:

- `reports/postgres_truth_report.json`
- `docs/status.md`
- `docs/m4-m5-freigabefassung.md`
- dieser Masterplan

Gate-Report:

| Voraussetzung | Soll | Ist | Ergebnis |
|---|---|---|---|
| postgres_truth `passed = collected` | Pflicht | `33 = 33` | PASS |
| postgres_truth `failed = 0` | Pflicht | `0` | PASS |
| postgres_truth `errors = 0` | Pflicht | `0` | PASS |
| postgres_truth `skipped = 0` | Pflicht | `0` | PASS |
| pytest `exit_code = 0` | Pflicht | `0` | PASS |
| M4a Auth/Workspace | Truth-Gate ohne offene Blocker | `ja` | PASS |
| M4b Upload/Queue | Truth-Gate ohne offene Blocker | `ja` | PASS |
| M4c Lifecycle/Retrieval | Truth-Gate ohne offene Blocker | `ja` | PASS |
| M4d read-only | read-only Slice nachgewiesen | `ja` | PASS |
| M4e Minimal | Restore-Truth-Nachweis erbracht | `ja` | PASS |
| Masterplan aktuell | Pflicht | `ja` | PASS |
| `docs/status.md` aktuell | Pflicht | `ja` | PASS |
| keine falschen gruenen Aussagen | Pflicht | `ja` | PASS |
| Truth-Report referenziert | Pflicht | `ja` | PASS |
| Restore-Truth-Report referenziert | Pflicht | `ja` | PASS |

Scorematrix:

| Bereich | Ist | Gate | Ergebnis |
|---|---:|---:|---|
| M4a Auth/Workspace Isolation | 96 | 95 | PASS |
| M4b Upload/Queue | 92 | 90 | PASS |
| M4c Lifecycle/Retrieval | 95 | 90 | PASS |
| M4d Diagnostics read-only | 88 | 85 | PASS |
| M4e Backup/Restore minimal | 86 | 85 | PASS |

Entscheidung:

- M4 abgeschlossen: `ja`
- M4 technisch abgeschlossen: `ja`
- M4 blockiert: `nein`

Begruendung:

- Das PostgreSQL-Truth-Gate ist formal gruen.
- Der reale Restore-Truth-Nachweis schliesst den vorher offenen M4e-Minimal-Blocker.
- Es gibt keine offenen Truth-Gate-Blocker, keine nachgewiesenen Cross-Workspace-Leaks und keine nachgewiesenen Restore-Inkonsistenzen im geprueften Scope.
- Weiter offene Produktionshaertungen bleiben bewusst ausserhalb dieses lokalen M4-Abschlusses.

Go/No-Go fuer M5:

- M5-Vorbereitung: `Go`

Ableitung:

- Truth-Gate und M4e-Minimal-Nachweis sind gemeinsam gruen.
- Der lokale M4-Minimalscope ist damit technisch abgeschlossen.
- Fuer Produktionsfreigaben bleiben Sicherheits- und Betriebsnachlaufpunkte separat zu behandeln.

Formales Transition Gate M4 -> M5 am 2026-05-11:

| Voraussetzung | Soll | Ist | Bewertung |
|---|---|---|---|
| M4a | `>= 95` | `96` | erfuellt |
| M4b | `>= 90` | `92` | erfuellt |
| M4c | `>= 90` | `95` | erfuellt |
| M4d read-only | akzeptiert | read-only Slice freigabefaehig | erfuellt |
| M4e minimal | `>= 85` | `86` | erfuellt |
| `postgres_truth` vollstaendig gruen | Pflicht | `33/33`, `failed = 0`, `errors = 0`, `skipped = 0`, `exit_code = 0` | erfuellt |
| Restore-Truth-Test | Pflicht | `PASS` | erfuellt |
| Dokumentation aktuell | Pflicht | zentrale Gate-Dokumente synchronisiert | erfuellt |
| keine offenen RC-Blocker | Pflicht | `m4_gate_blockers = []` | erfuellt |

Transition-Entscheidung:

- M5 Vorbereitung erlaubt: `ja`
- M5 Implementierung erlaubt: `ja`
- M5 bleibt blockiert: `nein`

Regel:

- M5-Implementierung ist nur erlaubt, wenn alle Transition-Voraussetzungen erfuellt sind.
- Diese Bedingung ist mit dem aktuellen Nachweisstand erfuellt.

Aktueller M4c-Befund:

- Backend-Lifecycle-, Soft-Delete- und Citation-Slices sind fachlich implementiert; ob der PostgreSQL-Truth-Nachweis aktuell gruen ist, muss aus `reports/postgres_truth_report.json` gelesen und mit `scripts/validate_m4_truth_gate.py` geprueft werden.
- source_status Live-Lookup liefert `active|archived|deleted|missing` direkt aus der Datenbank — Chaos-Test verifiziert Zustandsuebergaenge.
- Advisory-Lock-, Crash-, M4-Truth- und weitere PostgreSQL-Nachweise liegen als `postgres_truth`-Suite vor; der konkrete Status muss aus einem aktuellen Report kommen.
- Search-, Reindex-, Crash- und Chaos-Nachweise gegen PostgreSQL sind nur mit gesetzter `TEST_DATABASE_URL` belastbar.
- Admin- und Diagnoseansicht sind als read-only Diagnostics real vorhanden; Replay-Endpoint ist implementiert; weitergehende Reparatur-, Cleanup- und Backup-Aktionen sind nicht freigegeben.
- Backup und Restore sind als CLI-first Minimalpfad real implementiert, fokussiert getestet und durch einen echten Restore-Truth-Nachweis gegen leere PostgreSQL-Ziel-DB belegt.
- Performance- und Betriebsdokumentation bleiben eigenstaendige Nachlaufpunkte, ersetzen aber weiterhin keinen produktionsnahen Vollbetriebsnachweis.

### Risiken

- Authentifizierung wird zu schwergewichtig und zieht ein unnoetiges Enterprise-Modell nach sich.
- Workspace-Isolation bleibt partiell und fuehrt zu Datenleckagen zwischen lokalen Bereichen.
- Upload-GUI fuehrt neue Fehlerpfade ein, die den bestehenden stabilen Importpfad unterlaufen.
- Observability bleibt zu schwach, sodass lokale Betriebsprobleme nur indirekt sichtbar werden.
- Backup/Restore ist fuer den lokalen Minimal-Scope real getestet; offen bleiben Produktionshaertung und Sicherheitsnachlauf.
- Performance-Haertung verschiebt sich auf spaeter und laesst produktionsnahe lokale Lastprobleme bestehen.
- M4 verwischt die Grenze zu M5 und zieht wieder neue Fachlogik statt Produktisierung nach.

Freigabeentscheidung:

- Go fuer M4d: `Read-only Go`, vollstaendiges M4d `No-Go`
- Go fuer M4e: `Go` nur fuer den manuellen Minimal-Scope, `No-Go` fuer erweiterten Ausbau
- Go fuer M5-Vorbereitung: `Go`

Entscheidungsmatrix fuer mutierende Admin-Aktionen:

| Aktion | Status in M4d | Entscheidung | Einordnung |
|---|---|---|---|
| Reindex ausloesen | nicht freigegeben | blockiert | operative Nutzung erst nach M5; vor M5 nur als M4e-Restore-Folgeschritt erforderlich |
| Cleanup ausloesen | nicht freigegeben | blockiert | nach M5 verschoben |
| Backup ausloesen | nicht freigegeben | blockiert als allgemeine Admin-Aktion | fuer M4e-Minimal vor M5 fachlich noetig, aber vorzugsweise ueber CLI/Runbook statt M4d-Web-Admin |
| Repair Jobs | nicht freigegeben | blockiert | nach M5 verschoben |
| Userverwaltung | nicht freigegeben | blockiert | nach M5 verschoben |

Dokumentationsregel fuer M4d:

- M4d read-only ist abgeschlossen bzw. vorbereitet, soweit reale Diagnose-Endpunkte ohne Mutation vorliegen.
- M4d full mit mutierenden Admin-Aktionen ist nicht freigegeben.
- Die fuer M4e-Minimal noetigen Betriebsaktionen zaehlen nicht als Freigabe eines allgemeinen M4d-Full-Admin-Slices.

Produktionsreife-Score am 2026-05-11:

Hinweis:

- Dieser Score ist ein Management- und Reifeindikator.
- Er ersetzt nicht das formale Gate aus `reports/postgres_truth_report.json` plus `scripts/validate_m4_truth_gate.py`.

| Komponente | Gewicht | Score | Gewichteter Beitrag |
|---|---:|---:|---:|
| PostgreSQL Truth Tests | 30 % | 95 | 28.5 |
| Auth/Workspace Isolation | 20 % | 96 | 19.2 |
| Recovery/Queue | 15 % | 92 | 13.8 |
| Lifecycle/Retrieval Konsistenz | 15 % | 95 | 14.3 |
| Observability/Dokumentation | 10 % | 72 | 7.2 |
| Backup/Restore | 10 % | 86 | 8.6 |

Gesamtscore:

- `91.6 / 100`

Gate-Einordnung fuer den Management-Score:

- `>= 90`: produktionsnah
- `75-89`: stabilisiert, aber nicht final
- `< 75`: nicht produktionsreif

Aktuelle Einordnung:

- `86.3 / 100` = stabilisiert, aber nicht final

Differenz zu Feature-Fortschritt:

- Feature-Fortschritt als Liefer-/Scope-Proxy: `84.1 / 100`
- Produktionsreife: `86.3 / 100`
- Differenz: `-2.2` Punkte

Begruendung fuer die Differenz:

- Features sind in grossen Teilen sichtbar oder implementiert.
- Der praktische Restore-Nachweis hat den frueheren Reifeverlust in M4e deutlich reduziert.
- Produktionsreife bleibt weiter unter `produktionsnah`, weil Observability, explizite Reindex-Ausgabe im Restore-Nachweis und vollstaendige End-to-End-Nachweise noch offen sind.
- Der groesste verbleibende Reifeverlust kommt aktuell aus unvollstaendiger Observability und nicht voll abgeschlossenen End-to-End-Nachweisen.

Priorisierte Restblocker fuer `>= 90 / 100` Produktionsreife:

1. M4e-Minimal real implementieren und praktisch nachweisen.
  - Backup erzeugbar
  - Restore auf leere Datenbank lokal nachgewiesen
  - `alembic upgrade head` nach Restore erfolgreich
  - Reindex-Ergebnis im Restore-Pfad noch explizit ausgabeseitig absichern

2. Observability und Betriebsnachweise auf Abschlussniveau heben.
  - Lifecycle/Retrieval/Reindex-Instrumentierung vollstaendig und belastbar
  - Dokumentation ohne Widerspruch zwischen Truth-Report, Freigabefassung und Statusmatrix
  - klare operative Nachweise statt nur Konzept-/Runbook-Stand

3. Auth/Workspace-Isolation bis zum Endzustand schliessen.
  - vollstaendiger Login-/Logout-/Session-Produktfluss
  - harter Workspace-Scope-Nachweis fuer angrenzende Mutationspfade
  - kein Abschluss nur ueber Backend-Teilstuecke

4. Lifecycle/Retrieval-Konsistenz mit harten End-to-End-Nachweisen abrunden.
  - gruener Integrationsnachweis fuer Lifecycle/Reindex/Search auf realer PostgreSQL-Testumgebung
  - expliziter Nachweis, dass neue Chat-Antworten archivierte/geloeschte Inhalte nicht mehr retrieven

5. Recovery/Queue von stark gehaertet auf operativ voll abgesichert bringen.
  - Replay-/Dead-Letter-/Queue-Verhalten bleibt nachweisbar stabil
  - keine Freigabe allgemeiner Repair-Admin-Aktionen vor M5, aber klarer Betriebsnachweis der Minimalpfade

Erwartete Hebelwirkung auf den Score:

- Der groesste verbleibende Hebel ist Observability/Dokumentation.
- M4e Backup/Restore ist vom Konzept-Blocker zu einem partiell nachgewiesenen Minimalpfad geworden.
- Auth/Workspace und Lifecycle/Retrieval entscheiden danach ueber den Sprung von `stabilisiert` zu `produktionsnah`.

M4 Stabilization Sprint Board:

Sprint-Regeln:

- keine neuen Features
- nur Fixes an bestehenden Masterplan-Bestandteilen
- Errors vor Failures
- Flakiness nach Failures
- Doku erst nach Testgruen finalisieren

| Ticket | Titel | Status | Reihenfolge | Check | Done-Definition |
|---|---|---|---|---|---|
| T1 | Truth-Gate Repro sichern | todo | 1 | `pytest -m postgres_truth tests/postgres_truth -q` | `errors = 0`, `failures = 0`, `skipped = 0`, `exit_code = 0` |
| T2 | Truth-Errors sofort schliessen | todo | 2 | neue `errors` isolieren | kein offener Infrastruktur-, Schema-, Loader- oder Import-Error |
| T3 | Deterministische Failures schliessen | todo | 3 | rote Assertions vor weiterer Sprintarbeit beheben | keine offenen deterministischen Testfailures |
| T4 | Recovery-/Queue-Flakiness pruefen | todo | 4 | Replay-, Dead-Letter- und Claim-Slices mehrfach laufen lassen | keine intermittierenden Race-/Timing-Ausfaelle |
| T5 | M4e-Minimal final absichern | todo | 5 | `backup create`, `backup validate`, `backup restore`, `search rebuild-index` | lokaler Restore auf leere PostgreSQL-DB nachgewiesen, `reindex_result` explizit belegt |
| T6 | Observability-Luecken schliessen | todo | 6 | Backup/Restore/Reindex/Lifecycle/Retrieval-Events pruefen | kritische M4-Pfade haben belastbare Events ohne blinde Stellen |
| T7 | Auth/Workspace-Endzustand absichern | todo | 7 | Login, Logout, Bootstrap, Route-Guard, Fremdworkspace-Mutation | vorhandener Produktfluss ist durch Tests und reale Request-Kontexte hart belegt |
| T8 | Lifecycle/Retrieval PostgreSQL E2E | todo | 8 | Lifecycle, Reindex, Search, Retrieval unter realer PostgreSQL-Testumgebung | archivierte/geloeschte Inhalte werden fuer neue Antworten nicht mehr retrievt |
| T9 | Browsernahe Stabilitaetskanten pruefen | todo | 9 | bestehende Frontend-Slices fuer Auth/Lifecycle/Diagnostics pruefen | keine offene UI-Regressionskante im bestehenden Scope |
| T10 | Completion Matrix einfrieren | todo | 10 | Matrix gegen Report, Tests und Code abgleichen | keine unbelegten `Go`, `PASS`, `abgeschlossen`-Aussagen |
| T11 | Finaldoku nach Testgruen | todo | 11 | Masterplan, Status, Freigabefassung, Runbooks synchronisieren | alle Quellen sind widerspruchsfrei und nur auf gruener Evidenz aufgebaut |

Abnahmekriterien fuer den Sprint:

- Truth-Gate bleibt gruen
- keine offenen Errors
- keine offenen deterministischen Failures
- keine offene Flakiness in kritischen M4-Pfaden
- M4e-Minimal praktisch und explizit belegt
- Observability ausreichend fuer Betriebsnachweis
- Finaldoku erst nach stabilem Testgruen

Stop-Regeln fuer den Sprint:

- Stop bei neuem `error`
- Stop bei neuem `failure`
- Stop bei neuem Scope ausserhalb des Masterplans
- Stop bei Doku-Finalisierung vor Testgruen
- Stop bei Architekturdrift Richtung neue Features, neue Admin-Aktionen oder neues Betriebsmodell

Empfohlene 3-Phasen-Ausfuehrung:

- Phase 1 `Gate Protection`: `T1-T4`
- Phase 2 `Hard Proofs`: `T5-T9`
- Phase 3 `Final Freeze`: `T10-T11`

### M4a - Authentifizierung und Workspace-Isolation

**Status:** partial, nicht freigegeben.

**Ziel:** Jede API-Anfrage muss eindeutig einem Benutzer und einem autorisierten Workspace-Kontext zugeordnet sein.

Kurzscope:

- lokales Benutzerkonto
- Login
- Session-basierte Authentifizierung als Primärpfad
- Workspace-Zugriffspruefung
- API-Guards
- Frontend Login Screen
- Logout

Nicht-Scope:

- OAuth
- SSO
- Rollenmodell ueber Owner/Admin hinaus
- externe Identity Provider

Artefakt:

- Detaildefinition in `docs/m4a-auth-workspace-isolation.md`

### M4b - Upload-GUI

**Status:** missing.

**Ziel:** Dokumente koennen ueber die Web-GUI importiert werden.

Kurzscope:

- Datei auswaehlen
- Upload starten
- Importstatus anzeigen
- Parserfehler anzeigen
- Duplicate anzeigen
- `OCR_REQUIRED` anzeigen
- Dokumentdetail nach erfolgreichem Import oeffnen

Nicht-Scope:

- Drag-and-drop Mehrfachupload
- Ordnerimport
- Hintergrundjobs mit Queue
- OCR-Ausfuehrung
- externe Speicher

Artefakt:

- Detaildefinition in `docs/m4b-upload-gui.md`

---

## M5 - Systemreife Vorbereitung

**Status:** vorbereitet, Implementierung noch nicht gestartet.

Statuslogik:

- Dieser Abschnitt dokumentiert ausschliesslich M5-Vorbereitung.
- M5 gilt durch diese Dokumentation nicht als gestartet.
- Auch bei gruener Transition-Gate-Lage darf ein M5-Start erst dann behauptet werden, wenn ein expliziter Startentscheid und belastbare PostgreSQL-Nachweise fuer die jeweiligen M5-Slices vorliegen.
- Dokumentierte Konzepte, Platzhalter und Spezifikationen sind keine Implementierungsbehauptungen.

**Ziel:**

- M5 als reine Systemreife- und Governanceschicht strukturieren.
- Keine neuen Produktfeatures vorziehen.
- Bestehende M4-Grundlage fuer Datenqualitaet, Drift-Kontrolle, Cleanup, Health Score, RAG-Qualitaet und Langzeitbetrieb systemisch vorbereiten.

### M5 Scope

- Data Quality
  - Regeln fuer konsistente Dokument-, Versions-, Chunk- und Citation-Daten definieren.
  - Pflichtmetriken fuer Duplikate, orphaned Daten, inkonsistente Lifecycle-Zustaende und unvollstaendige Metadaten festlegen.
- Drift Detection
  - Suchindex-, Versions-, Lifecycle- und Konfigurationsdrift als eigene M5-Pruefebene ausformulieren.
  - Drift nicht nur als Restore-Nachpruefung, sondern als regulaeren Systemreife-Indikator behandeln.
- Cleanup
  - Cleanup nur als kontrollierter, dry-run-faehiger M5-Betriebspfad vorbereiten.
  - Fokus auf orphaned Chunks, inkonsistente Versionen, stale Index-Eintraege und alte technische Artefakte.
- Health Score
  - Einen System-Health-Score aus Datenqualitaet, Fehlerquote, Performance, Retrieval-Stabilitaet und RAG-Qualitaet vorbereiten.
  - Der Score ist M5-Steuerungsinstrument, nicht Ersatz fuer Truth-Gates.
- RAG-Qualitaet
  - Bewertungsrahmen fuer Retrieval-Qualitaet, Citation-Qualitaet, Kontextnutzung und Antworttreue definieren.
  - M5 soll Qualitaetsmessung und Regressionserkennung vorbereiten, nicht neue Antwortlogik einfuehren.
- Langzeitbetrieb
  - Langzeitstabilitaet fuer Storage, Queue-Recovery, Restore-Wiederholbarkeit, Drift-Trends und wiederkehrende Betriebspruefungen vorbereiten.

### Abhaengigkeiten aus M4

- Backup/Restore
  - M5 setzt auf dem real nachgewiesenen M4e-Minimalpfad auf.
  - M5 erweitert diesen Pfad nicht sofort funktional, sondern nutzt ihn als Basis fuer Wiederholbarkeit, Integritaet und Langzeitpruefungen.
- Observability
  - M5 braucht die in M4 etablierte Observability als Datenquelle fuer Drift, Health Score und Betriebsbewertungen.
  - Offene Observability-Luecken aus M4 bleiben bekannte M5-Eingangsschulden.
- Truth Reports
  - `reports/postgres_truth_report.json` bleibt formaler Wahrheitsanker fuer Kernstabilitaet.
  - `reports/restore_truth_report.md` bleibt Referenz fuer Wiederherstellbarkeit und Nachweisgrenze.
- Queue Recovery
  - M5 baut auf M4b/M4c-Nachweisen fuer Retry-, Replay- und Recovery-Stabilitaet auf.
  - Cleanup- und Langzeitbetrieb duerfen Queue-Konsistenz nicht unterlaufen.
- Lifecycle
  - M5 setzt stabile `active|archived|deleted|missing`-Semantik voraus.
  - Data Quality, Drift und Cleanup muessen Lifecycle-Regeln respektieren und duerfen historische Citations nicht beschaedigen.

### Nicht-Scope fuer M5-Vorbereitung

- keine neue Endnutzerfunktion fuer Analyse, Merge, Refine oder Commit
- keine neuen Admin-Write-Aktionen im freigegebenen UI-Scope
- keine Produktivfreigabe fuer allgemeine Cleanup-, Repair-, Reindex- oder Restore-Web-Aktionen
- keine neue RAG-Fachlogik oder neue Antwortprodukte
- kein Enterprise-Betriebsmodell mit Multi-Region, externer Orchestrierung oder Vollautomatisierung

### Startbedingungen fuer M5

- M4-Transition-Gate ist formal bestanden.
- M4a, M4b und M4c sind ueber den aktuellen Truth-Nachweis gruen.
- M4d ist im read-only Scope akzeptiert.
- M4e-Minimal ist praktisch nachgewiesen.
- `postgres_truth` ist vollstaendig gruen.
- Restore-Truth-Test ist bestanden.
- Zentrale Gate-Dokumente sind synchronisiert.

### Arbeitsregel fuer den Start von M5

- M5 startet als Strukturierungs- und Bewertungsphase.
- Der erste M5-Schritt ist Dokumentation, Messlogik und Priorisierung.
- Implementierung einzelner M5-Massnahmen folgt erst nach expliziter Freigabe pro Slice.

### Erwartete M5-Artefakte zum Start

- M5-Scope-Dokument fuer Systemreife
- Abhaengigkeiten- und Eingangsschuldenliste aus M4
- definierte Nicht-Scope-Grenzen gegen Feature-Drift
- Startbedingungen und spaetere Gate-Kriterien fuer Data Quality, Drift, Cleanup, Health Score, RAG-Qualitaet und Langzeitbetrieb

### M5 Dokumentationsstruktur

- `docs/data-quality.md`
- `docs/drift.md`
- `docs/cleanup.md`
- `docs/health-score.md`
- `docs/operations.md`
- `masterplan.md`

Dokumentationsregel:

- Alle genannten Dateien beschreiben aktuell nur Vorbereitung, Statuslogik und spaetere Nachweisanker.
- Keine dieser Dateien darf ohne neuen Nachweislauf eine Implementierung, einen aktiven Betrieb oder ein grünes M5-Gate behaupten.

### M5 Risikomatrix

| Risiko | Ursache | Wahrscheinlichkeit | Auswirkung | Frueherkennung | Mitigation | Metrik | Prioritaet |
|---|---|---|---|---|---|---|---|
| Datenwachstum | steigende Anzahl an Dokumenten, Versionen, Chunks, Citations und Originaldateien ohne aktive Qualitaets- oder Storage-Regeln | hoch | Suchpfade, Reindex, Restore und Betriebsfenster werden langsamer; Storage-Kosten und manuelle Recovery-Dauer steigen | steigende Dokument-, Chunk- und Dateizaehler; laengere Reindex- oder Restore-Zeiten | M5 Data-Quality- und Storage-Regeln definieren; Growth-Budgets und Archivierungs-/Dedup-Strategien vorbereiten | Dokumentanzahl, Chunkanzahl, Dateianzahl, Backup-Groesse, Restore-Dauer | hoch |
| Lange Laufzeit | Reindex, Drift-Pruefungen, Restore, Truth-Laeufe und Queue-Recovery wachsen mit dem Datenbestand | mittel bis hoch | Betriebsfenster werden unplanbar; Recovery und Validierung dauern zu lange | deutlicher Anstieg von Laufzeiten in Truth-, Restore- oder Reindex-Nachweisen | Laufzeitbudgets fuer Reindex, Truth-Smoke, Restore und Cleanup festlegen; dry-run und segmentierte Ausfuehrung vorbereiten | Reindex-Dauer, Restore-Dauer, Truth-Laufzeit, Queue-Recovery-Dauer | hoch |
| Drift zwischen DB und Index | Lifecycle-Aenderungen, Teilfehler bei Rebuilds, stale Indexeintraege oder inkonsistente Sichtbarkeit | mittel | Search und Retrieval liefern falsche oder fehlende Treffer; Health Score sinkt | Drift-Check, Inconsistency-Report, Search-Stichproben nach Restore oder Recovery | Drift Detection als regulaere M5-Pruefebene definieren; Rebuild- und Verifikationspfade standardisieren | Drift-Score, stale_index_entries, orphaned Eintraege, reindexed_chunk_count | hoch |
| RAG-Qualitaetsverlust | schlechtere Retrieval-Qualitaet, driftende Citations, Kontextueberladung oder Datenqualitaetsfehler in Chunks | mittel | Antworttreue sinkt; falsche oder schwache Quellenbelege; Vertrauen in den RAG-Pfad nimmt ab | haeufigere Insufficient-Context-Faelle, schwache Trefferqualitaet, mehr manuelle Reklamationen | Bewertungsrahmen fuer Retrieval-, Citation- und Antwortqualitaet definieren; Regressionserkennung vorbereiten | Trefferqualitaet, Citation-Konsistenz, Insufficient-Context-Rate, Health-Score-Anteil RAG | hoch |
| Cleanup-Risiken | aggressive oder fachlich falsch abgegrenzte Cleanup-Regeln entfernen noch benoetigte Daten oder historische Artefakte | mittel | Datenverlust, Citation-Brueche, Queue- oder Lifecycle-Inkonsistenzen | dry-run-Abweichungen, unerwartete Delta-Zaehler, nachgelagerte Restore- oder Drift-Fehler | Cleanup nur als dry-run-faehigen, dokumentierten M5-Pfad vorbereiten; Lifecycle- und Citation-Schutzregeln verpflichtend machen | Anzahl geplanter vs. freigegebener Cleanup-Aenderungen, Drift nach Cleanup, Citation-Fehler nach Cleanup | hoch |
| Backup-Veralterung | Backups werden nicht regelmaessig erneuert oder nicht gegen aktuelle Konfiguration und Datenlage verifiziert | mittel | Restore fuehrt zu unakzeptablem Datenverlust; DR verliert praktische Aussagekraft | altes `created_at` im Manifest, fehlende aktuelle Verify-/Restore-Nachweise | Backup-Frische, Verify-Backup und periodische Restore-Stichproben als M5-Betriebsregel vorbereiten | Backup-Alter, letzter Verify-Status, letzter Restore-Truth-Nachweis | hoch |
| Queue-Stau | haengende Jobs, Retry-Schleifen, Dead-Letter-Anstieg oder langsame Recovery bei wachsendem Bestand | mittel | Uploads, Rebuilds und Recovery-Pfade stauen sich; Betriebszustand wird intransparent | mehr `retryable`/`dead_letter`, laenger laufende Jobs, wachsende Queue-Zaehler | Queue-Recovery als M5-Langzeitbetriebsthema behandeln; Grenzwerte und Stau-Indikatoren festlegen | running_jobs, failed_jobs_last_24h, dead_letter_count, mittlere Job-Laufzeit | mittel bis hoch |
| Nutzerfehler | falscher Cleanup-, Restore- oder Diagnoseeinsatz; falsches Backup; Bedienung ausserhalb des vorgesehenen Runbooks | mittel | unnoetige Stoerungen, Teilverluste oder Verwechslung zwischen Diagnose und mutierendem Betriebspfad | Abweichung vom Runbook, fehlende Verify-/Validation-Schritte, ungeplante Teilrestores | Runbooks, Checklisten, dry-run-Pflicht und klar getrennte Admin-Grenzen beibehalten; M5-Operationen nur mit expliziten Startbedingungen vorbereiten | Anzahl ungeplanter Recovery-Eingriffe, Verify-Fehler vor Restore, dokumentierte Bedienabweichungen | mittel |

### Prioritaeten fuer M5

- Prioritaet 1
  - Drift zwischen DB und Index
  - RAG-Qualitaetsverlust
  - Backup-Veralterung
  - Datenwachstum
- Prioritaet 2
  - Lange Laufzeit
  - Cleanup-Risiken
  - Queue-Stau
- Prioritaet 3
  - Nutzerfehler

Prioritaetslogik:

- Prioritaet 1 betrifft Risiken, die direkt Wahrheitsgehalt, Wiederherstellbarkeit oder Retrieval-Vertrauen beschaedigen koennen.
- Prioritaet 2 betrifft Risiken, die den Langzeitbetrieb instabil oder unplanbar machen.
- Prioritaet 3 betrifft vor allem Governance- und Operator-Disziplin und wird ueber Runbooks, Checklisten und Freigaberegeln begrenzt.

### M5 Data Quality Scope

Ziel:

- M5 definiert einen festen Qualitaetsrahmen fuer Dokumente, Versionen, Chunks und Citations.
- Die Regeln dienen der Frueherkennung von Konsistenzfehlern und der spaeteren Health-Score- und Drift-Bewertung.
- Das Regelwerk fuehrt noch keine automatische Reparatur ein.

#### Data Quality Regelwerk

| Regel | Beschreibung | Einstufung |
|---|---|---|
| Dokument ohne Version = Fehler | Jedes fachlich vorhandene Dokument muss mindestens eine referenzierbare `document_version` besitzen. Dokumente ohne Version gelten als inkonsistent. | Fehler |
| Version ohne Chunks = Fehler ausser `failed import` | Jede normale Version muss mindestens einen Chunk besitzen. Ausnahme: Dokumente im Importfehlerpfad duerfen temporär Versionen ohne verwertbare Chunks aufweisen, wenn der Zustand fachlich als fehlgeschlagener Import markiert ist. | Fehler |
| Chunk ohne `source_anchor` = Fehler | Jeder Chunk muss einen fachlich nutzbaren `source_anchor` besitzen. Fehlende oder leere Anker sind ein Data-Quality-Fehler. | Fehler |
| orphaned chunks = Fehler | Chunks ohne gueltige referenzierte Version oder ohne gueltiges referenziertes Dokument sind inkonsistent. | Fehler |
| orphaned versions = Fehler | Versionen ohne gueltiges referenziertes Dokument sind inkonsistent. | Fehler |
| duplicate `content_hash` = Fehler | Doppelte `content_hash`-Werte innerhalb desselben Workspace-Scope sind unzulaessig. Der Datenbestand muss die fachliche Eindeutigkeit wahren. | Fehler |
| dangling citations = Warnung oder Fehler je Status | Citations mit fehlendem Chunk oder Dokument sind mindestens auffaellig. Fuer historische, bewusst erhaltene Citations mit `source_status = deleted|missing` ist dies primaer eine Warnung; fuer aktive Retrieval-Pfade oder unerwartet fehlende Referenzen ist es ein Fehler. | Warnung oder Fehler |

#### Severity-Modell

- `Fehler`
  - verletzt ein Dateninvariante
  - darf den Health Score direkt verschlechtern
  - ist fuer Cleanup oder operative Freigaben blockierend, bis der Befund geklaert ist
- `Warnung`
  - ist fachlich auffaellig, aber in einem bekannten und dokumentierten Sonderfall noch tolerierbar
  - muss sichtbar gemacht und trendbar gemacht werden
  - darf nicht still ignoriert werden, insbesondere bei historischen Citations mit erwartetem `source_status`

Severity-Regel fuer Citations:

- `Warnung`, wenn die Citation historisch erhalten bleiben soll und `source_status` den fehlenden Ursprung fachlich erklaert (`deleted` oder `missing`).
- `Fehler`, wenn aktive Retrieval-Pfade, aktuelle Antworten oder unerwartete Referenzbrueche betroffen sind.

#### Pruefstrategie

- Regelpruefung zunaechst als dokumentierter M5-Read-Pfad, nicht als mutierende Automatik.
- Pruefungen sollen auf echten DB-Bestaenden laufen und nicht nur auf Mock- oder UI-Sichten.
- Ergebnisse sollen in drei Ebenen ausgewertet werden:
  - Punktueller Lauf fuer lokale Diagnose und Betriebsstichprobe
  - wiederholbarer Qualitaetslauf fuer M5-Health- und Drift-Bewertung
  - Restore-Nachpruefung nach groesseren Recovery- oder Cleanup-Eingriffen
- Jede Regel braucht spaeter:
  - zaehlbare Befunde
  - Schweregrad
  - betroffenen Scope
  - trendbare Verlaufsdaten

Empfohlene Pruefbloecke fuer M5:

- Dokument/Version-Konsistenz
- Version/Chunk-Konsistenz
- Anchor-Qualitaet
- Referenzielle Orphan-Pruefung
- `content_hash`-Eindeutigkeit
- Citation-Integritaet mit Sonderfallbewertung fuer historische `source_status`

#### Nicht-Scope fuer das Data-Quality-Regelwerk

- keine automatische Datenreparatur im ersten M5-Schritt
- kein automatischer Cleanup basierend nur auf einem Regelverstoss
- keine verdeckte Mutation von Citations, Lifecycle oder Versionen waehrend der Pruefung
- keine neue Endnutzerfunktion fuer Qualitaetskorrekturen
- keine Produktionsfreigabe fuer aggressive Cleanup- oder Repair-Aktionen ohne eigenen Folgescope

### M5 Drift Detection Scope

Ziel:

- M5 behandelt Drift als eigene Systemreife-Dimension zwischen Soll-Zustand und effektivem Laufzeitzustand.
- Drift Detection bleibt zunaechst read-only, trendfaehig und auswertbar.
- Repair bleibt ein nachgelagerter, explizit freizugebender Betriebspfad und nicht Teil der ersten M5-Freigabe.

#### Drift Detection Konzept

| Drift-Art | Detektion | Schwelle | Severity | Repair-Strategie | Metrik |
|---|---|---|---|---|---|
| DB vs Search Index | Vergleich von suchbaren Chunks, Search-Index-Eintraegen und Drift-Buckets ueber bestehenden Drift-/Inconsistency-Report | `0` ist Soll; jeder persistente Drift-Befund ausserhalb eines aktiven Rebuild-/Restore-Fensters ist relevant | hoch | Ursache isolieren, Rebuild-/Restore-Kontext pruefen, danach gezielten Reindex als separaten Betriebspfad ausfuehren | `drift_score`, `stale_index_entries`, `chunks_without_index`, `index_without_chunk`, `duplicate_index_entries` |
| Lifecycle vs Searchbarkeit | Abgleich von `documents.lifecycle_status` gegen `document_chunks.is_searchable` | `0` Abweichungen ist Soll; jede aktive Abweichung ist ein Fehler | hoch | Lifecycle-Sync-Pfad pruefen, inkonsistente Dokumente isolieren, Searchbarkeit kontrolliert neu synchronisieren | Anzahl Chunks mit `active && is_searchable = false`, Anzahl Chunks mit `non-active && is_searchable = true` |
| Citation Snapshot vs Live Status | Vergleich von Citation-`source_status` gegen aktuellen Dokument-Lifecycle und Existenz des referenzierten Ursprungs | `0` fuer unerwartete Abweichungen; historische, erwartete `deleted|missing`-Faelle duerfen nur als bekannte Sonderfaelle auftreten | mittel bis hoch | zwischen historischem Sonderfall und echtem Referenzbruch unterscheiden; Snapshot nur ueber kontrollierten Lifecycle-/Repair-Pfad anpassen | Anzahl Citations mit Snapshot/Live-Mismatch, Anzahl unerwarteter `missing`, Anteil historisch erwarteter Sonderfaelle |
| Queue State vs tatsaechlicher Worker-Zustand | Vergleich von Job-Status in `background_jobs` mit real beobachtbaren Laufzeitindikatoren, Retry-/Dead-Letter-Mustern und festhaengenden `running`-Jobs | kleine kurzfristige Differenzen tolerierbar; persistente `running`-Jobs ohne Worker-Fortschritt oder wachsender `retryable|dead_letter`-Bestand sind relevant | hoch | Worker-Zustand und Replay-Faehigkeit pruefen, haengende Jobs isolieren, Recovery oder Replay explizit und dokumentiert ausfuehren | `running_jobs`, `failed_jobs_last_24h`, `retryable_count`, `dead_letter_count`, mittlere Job-Laufzeit, Alter laengster `running`-Job |
| Backup Manifest vs aktuelle Daten | Vergleich zwischen Manifest-Angaben und aktuellem technischen Zustand des Backup-Artefakts via `validate` und `verify-backup` | `status != ok` ist Fehler; Manifest-/Dateiabweichung ist ausserhalb eines laufenden Backups nicht tolerierbar | hoch | Backup nicht freigeben, neues Backup erzeugen oder Artefakt verwerfen; Restore nur nach erneutem Vollcheck | `verify_backup.status`, Anzahl `error_classes`, Manifest-Dateizaehler vs Ist-Dateizaehler, Backup-Alter |
| Retrieval-Qualitaet ueber Zeit | Trendvergleich von Retrieval-Scores, Insufficient-Context-Raten und Citation-Stabilitaet ueber wiederholte M5-Qualitaetslaeufe | kein einzelner fester Absolutwert als einziges Gate; relevant ist negative Trendbewegung oder wiederholter Schwellenunterschritt gegen Baseline | mittel bis hoch | Regression gegen Baseline bestaetigen, Datenqualitaet und Indexzustand pruefen, Retrieval-Konfiguration separat nachziehen | `retrieval_score_max`, `retrieval_score_avg`, `insufficient_context_rate`, Citation-Konsistenzrate, Anteil low-confidence-Citations |

#### Schwellenmodell

- `Sofortfehler`
  - DB vs Search Index
  - Lifecycle vs Searchbarkeit
  - Backup Manifest vs aktuelle Daten
  - diese Drifts verletzen einen technischen Sollzustand und sind ausserhalb klar markierter Betriebsfenster nicht tolerierbar
- `Beobachten mit Eskalation`
  - Citation Snapshot vs Live Status
  - Queue State vs tatsaechlicher Worker-Zustand
  - Retrieval-Qualitaet ueber Zeit
  - diese Drifts brauchen Verlaufsbeobachtung, Sonderfallbewertung oder Baseline-Vergleich, eskalieren aber bei Persistenz oder Trendbruch

#### Severity-Modell fuer Drift

- `hoch`
  - betrifft Wahrheitsgehalt, Wiederherstellbarkeit oder laufende Betriebsfaehigkeit direkt
  - blockiert spaetere Cleanup-, Recovery- oder Freigabeentscheidungen, bis die Ursache geklaert ist
- `mittel bis hoch`
  - betrifft Antwortqualitaet oder Queue-Stabilitaet mit moeglicher Eskalation zum Betriebsproblem
  - verlangt Trendbeobachtung und nachvollziehbare Eskalationsregel
- `mittel`
  - ist sichtbar und relevant, aber haeufig nur im Zusammenspiel mit weiteren Signalen freigaberelevant

#### Repair-Strategie

- Drift Detection selbst bleibt read-only.
- Repair wird strikt getrennt behandelt:
  - Diagnose und Scope-Isolation
  - Sonderfallpruefung gegen Lifecycle-, Restore- oder Historienregeln
  - explizite Freigabe fuer Reindex, Replay, Restore oder Snapshot-Korrektur
  - Nachpruefung ueber denselben Drift-Check
- Kein automatischer Repair nur aufgrund eines einzelnen Drift-Befunds im ersten M5-Slice.

#### Priorisierung

- Prioritaet 1
  - DB vs Search Index
  - Lifecycle vs Searchbarkeit
  - Backup Manifest vs aktuelle Daten
  - Queue State vs tatsaechlicher Worker-Zustand
- Prioritaet 2
  - Citation Snapshot vs Live Status
  - Retrieval-Qualitaet ueber Zeit

Prioritaetslogik:

- Prioritaet 1 deckt Drift ab, die direkt zu falscher Suche, betrieblichem Stau oder ungueltigen Restore-Annahmen fuehrt.
- Prioritaet 2 deckt Drift ab, die staerker ueber Qualitaetsverlust, Historieninkonsistenz oder Trendverschlechterung sichtbar wird und deshalb baseline- und kontextabhaengig bewertet werden muss.

### M5 Cleanup Scope

Ziel:

- M5 definiert Cleanup als kontrollierten, dokumentierten und reversibel vorbereiteten Betriebspfad.
- Cleanup dient der Beseitigung technischer Altlasten und inkonsistenter Artefakte, nicht der stillen Datenmutation.
- Der erste M5-Slice erlaubt nur Dry-Run, Berichtserstellung und spaetere explizite Freigabe je Cleanup-Klasse.

#### Cleanup-Regelwerk

| Cleanup-Kandidat | Regel | Voraussetzung | Ergebnis im ersten M5-Slice |
|---|---|---|---|
| orphaned chunks | Chunks ohne gueltige Version oder ohne gueltiges Dokument sind Cleanup-Kandidaten | referenzielle Inkonsistenz muss im Report nachgewiesen sein | nur Dry-Run und Bericht |
| orphaned versions | Versionen ohne gueltiges Dokument sind Cleanup-Kandidaten | referenzielle Inkonsistenz muss im Report nachgewiesen sein | nur Dry-Run und Bericht |
| stale index entries | Search-Index-Eintraege ohne gueltige DB-Basis oder mit falscher Sichtbarkeit sind Cleanup-Kandidaten | Drift-/Inconsistency-Report muss den Befund bestaetigen | nur Dry-Run und Bericht; spaeter eher Reindex als direkte Loeschung |
| alte `dead_letter` Jobs | alte, terminale Jobs ohne legitimen Replay-Bedarf sind Cleanup-Kandidaten | Queue-Kontext, Alter und fehlende operative Relevanz muessen dokumentiert sein | nur Dry-Run und Bericht |
| alte Reports | veraltete technische Reports ausserhalb des definierten Aufbewahrungsfensters sind Cleanup-Kandidaten | Report-Typ, Alter und fehlende Gate-Relevanz muessen dokumentiert sein | nur Dry-Run und Bericht |
| temporaere Upload-Dateien | Temp-Dateien ohne aktive Job-Referenz und ohne weitere technische Verwendung sind Cleanup-Kandidaten | Pfad muss als Temp-Artefakt klassifiziert und als unreferenziert nachgewiesen sein | nur Dry-Run und Bericht |
| abgelaufene Sessions | abgelaufene Auth-Sessions sind Cleanup-Kandidaten | Session muss fachlich beendet bzw. abgelaufen und nicht mehr fuer aktiven Zugriff nutzbar sein | nur Dry-Run und Bericht |

Verbindliche Regeln:

- Dry Run zuerst.
- keine Loeschung ohne Report.
- keine Chat-Citation zerstoeren.
- keine Originaldatei loeschen, wenn sie noch referenziert ist.

#### Safety Constraints

- Cleanup bleibt read-only, bis pro Cleanup-Klasse ein eigener freigegebener Mutationspfad existiert.
- Jeder Cleanup-Lauf braucht einen maschinenlesbaren und menschenlesbaren Report vor jeder Loeschentscheidung.
- Historische Chat-Citations haben Vorrang vor Cleanup-Bequemlichkeit:
  - keine Loeschung von Daten oder Snapshots, die historische Nachvollziehbarkeit zerstoert
  - keine Mutation, die `source_status` oder historische Citation-Lesbarkeit still bricht
- Originaldateien sind geschuetzt:
  - keine Loeschung, solange eine DB-Referenz, eine Restore-Relevanz oder ein belegter technischer Bezug besteht
  - Temp-Dateien und Originaldateien muessen strikt getrennt bewertet werden
- Stale Index Entries sollen primaer ueber kontrollierten Reindex und nicht ueber ungezielte Einzelbereinigung behandelt werden.
- Queue-Cleanup darf keine noch untersuchungsrelevanten `retryable`- oder `dead_letter`-Faelle still entfernen.
- Cleanup darf keine Truth-Nachweise, Restore-Artefakte oder aktuelle Gate-Reports vernichten, solange sie noch Freigaberelevanz haben.
- Nach jedem spaeter freigegebenen Cleanup muss dieselbe Klasse erneut per Report validiert werden.

#### Dry-Run-Format

Jeder Dry-Run-Report soll mindestens die folgenden Felder enthalten:

- `cleanup_type`
- `generated_at`
- `scope`
- `candidate_count`
- `protected_count`
- `blocked_count`
- `status`
- `items`
- `summary`

Feldbedeutung:

- `cleanup_type`: z. B. `orphaned_chunks`, `stale_index_entries`, `expired_sessions`
- `scope`: Workspace-, globaler oder Dateisystem-Scope des Laufs
- `candidate_count`: alle gefundenen Kandidaten
- `protected_count`: Kandidaten, die durch Safety Constraints nicht angetastet werden duerfen
- `blocked_count`: Kandidaten mit unklarer Referenzlage oder fehlender Freigabebasis
- `status`: `ok`, `review_required` oder `blocked`
- `items`: Liste der konkreten Kandidaten mit Identifikator, Grund, Schutzstatus und empfohlener Aktion
- `summary`: verdichtete Gesamtbewertung fuer Operator und spaetere Freigabeentscheidung

Empfohlene Item-Felder im Dry-Run:

- `id`
- `category`
- `reason`
- `evidence`
- `risk`
- `protected`
- `recommended_action`

Beispielstatus:

- `ok`: Kandidaten sind sauber identifiziert und fachlich eindeutig bewertet, aber noch nicht geloescht
- `review_required`: Kandidaten brauchen menschliche Sichtpruefung oder Querkontrolle gegen Citation-, Queue- oder Dateireferenzen
- `blocked`: Cleanup darf fuer diese Kandidaten nicht erfolgen, weil Schutzregeln oder fehlende Nachweise entgegenstehen

### M5 Health Score Spezifikation

Ziel:

- Der M5 Health Score verdichtet die wichtigsten Systemreife-Signale in einen vergleichbaren Wert von `0` bis `100`.
- Der Score ersetzt keine Truth-Gates, sondern dient als laufendes Steuerungs- und Priorisierungsinstrument.
- Der Score ist nur belastbar, wenn die zugrunde liegenden Reports und Metriken aktuell sind.

#### Formel

Gesamtformel:

```text
health_score =
  data_quality_score * 0.25 +
  drift_score_component * 0.20 +
  queue_health_score * 0.15 +
  search_retrieval_health_score * 0.15 +
  backup_freshness_score * 0.10 +
  error_rate_score * 0.10 +
  documentation_truth_score * 0.05
```

Regeln:

- Jede Komponente liefert einen Teilscore von `0` bis `100`.
- Der Gesamtwert wird auf `0..100` begrenzt und als ganzzahliger Score gerundet.
- Fehlende oder veraltete Messgrundlagen duerfen den Score nicht kuenstlich hoch halten; in solchen Faellen ist die betroffene Komponente konservativ als `degraded` zu behandeln.

#### Komponenten und Gewichtung

| Komponente | Gewicht | Begruendung |
|---|---:|---|
| Data Quality | 25 % | Datenqualitaet ist die Grundlage fuer Search, Retrieval, Cleanup, Restore und alle spaeteren M5-Bewertungen. Wenn die Basisdaten inkonsistent sind, sind nachgelagerte Signale nur begrenzt vertrauenswuerdig. |
| Drift | 20 % | Drift zwischen Soll- und Laufzeitzustand ist der naechstwichtigste Fruehindikator fuer fachliche und technische Erosion. Search-, Lifecycle- und Snapshot-Drift wirken direkt auf Wahrheitsgehalt. |
| Queue Health | 15 % | Queue-Stabilitaet bestimmt, ob Import, Recovery und Betriebsprozesse ueberhaupt verlässlich weiterlaufen. Ein Stau wirkt schnell systemweit, ist aber etwas indirekter als Basisdaten- oder Driftfehler. |
| Search/Retrieval Health | 15 % | Retrieval-Qualitaet ist fuer M3c/M4-RAG zentral. Sie haengt jedoch teilweise bereits von Data Quality und Drift ab und wird deshalb bewusst nicht hoeher als diese gewichtet. |
| Backup Freshness | 10 % | Backup-Frische ist fuer Wiederherstellbarkeit entscheidend, aber kein permanentes Live-Signal jeder einzelnen Nutzerinteraktion. |
| Error Rate | 10 % | Fehlerquote zeigt operative Instabilitaet schnell an, ist aber ohne Daten- und Driftkontext allein nicht ausreichend fuer Systemreife. |
| Documentation Truth | 5 % | Dokumentationswahrheit ist wichtig fuer Governance und Freigaben, aber kein primaerer Laufzeitindikator. Deshalb bewusst geringstes Gewicht. |

#### Komponentenlogik

`data_quality_score`:

- basiert auf den in M5 definierten Data-Quality-Regeln
- Startwert `100`
- Abzuege fuer nachgewiesene Fehlerklassen wie orphaned Daten, fehlende `source_anchor`, doppelte `content_hash` oder unerwartete dangling citations
- harte Invariantenverletzungen sollen staerker gewichtet werden als Warnungen

`drift_score_component`:

- basiert auf den in M5 definierten Drift-Checks
- nutzt insbesondere Search-Index-Drift, Lifecycle/Searchability-Abweichungen, Citation-Snapshot-Abweichungen, Queue-Drift und Backup-Manifest-Abweichungen
- persistente Drift ausserhalb markierter Betriebsfenster fuehrt zu deutlichen Abzuegen

`queue_health_score`:

- basiert auf `running_jobs`, `failed_jobs_last_24h`, `retryable`, `dead_letter`, Job-Alter und sichtbarem Fortschritt
- laenger haengende `running`-Jobs und wachsender Dead-Letter-Bestand verschlechtern den Teilscore deutlich

`search_retrieval_health_score`:

- basiert auf `retrieval_score_max`, `retrieval_score_avg`, `insufficient_context_rate`, Citation-Konsistenz und Search-Stichproben
- Baseline- und Trendbewertung sind wichtiger als ein isolierter Einzelwert

`backup_freshness_score`:

- basiert auf letztem gueltigen `verify-backup`, Backup-Alter und letztem Restore-Nachweis
- alte oder nicht verifizierte Backups ziehen den Teilscore ab, auch wenn der Live-Betrieb aktuell ruhig wirkt

`error_rate_score`:

- basiert auf dokumentierter Fehlerquote, insbesondere Import-/DB-/Diagnostics-/Retrieval-Fehlern
- Fehlerhaeufungen ueber kurze Zeitfenster verschlechtern den Teilscore schneller als einzelne sporadische Fehler

`documentation_truth_score`:

- basiert auf Synchronitaet zwischen Gate-Dokumenten, Reports und tatsaechlich nachgewiesenem Systemzustand
- veraltete, ueberschriebene oder unbelegte Freigabeaussagen ziehen den Teilscore ab

#### Schwellenwerte

- `>= 90` = `healthy`
- `75-89` = `degraded`
- `< 75` = `unhealthy`

Interpretation:

- `healthy`
  - der Systemzustand ist fuer M5-Steuerung stabil
  - kleinere Defizite koennen vorhanden sein, sind aber nicht dominierend
- `degraded`
  - relevante Abweichungen oder Alterungstendenzen sind sichtbar
  - M5-Priorisierung und Gegenmassnahmen muessen aktiv nachgezogen werden
- `unhealthy`
  - der Zustand ist fuer Systemreife nicht ausreichend stabil
  - Cleanup-, Repair- oder weitere Freigabeschritte duerfen nicht auf einem ungeprueften Score aufbauen

#### Bewertungsleitlinien

- Ein hoher Score darf keinen formalen Truth-Gate-Pass ersetzen.
- Eine einzelne schwere Invariantenverletzung in Data Quality oder Drift kann trotz rechnerisch noch brauchbarem Gesamtwert eine separate Eskalation erfordern.
- Documentation Truth bleibt bewusst niedrig gewichtet, darf aber fuer Freigabetexte nicht ignoriert werden.
- Wenn eine Komponente mangels aktueller Evidenz nicht belastbar messbar ist, soll sie nicht mit `100` angesetzt werden, sondern konservativ auf einen degradierenden Standardwert fallen.

### M5 Truth-Test-Erweiterungskonzept

Ziel:

- M5 darf keine rein dokumentarische Phase bleiben.
- Jeder M5-Kernbereich braucht einen belastbaren Nachweis in der bestehenden `postgres_truth`-Logik.
- SQLite bleibt fuer M5 nur Fast Feedback und ersetzt keinen PostgreSQL-Wahrheitsnachweis.

#### Truth-Test-Erweiterungskonzept

`postgres_truth` wird fuer M5 um folgende Pruefbloecke erweitert:

- `data_quality`
  - prueft die M5-Datenqualitaetsregeln gegen echte PostgreSQL-Daten
  - umfasst Dokument/Version/Chunk-Invarianten, `source_anchor`, Orphans, `content_hash` und Citation-Sonderfaelle
- `drift_detection`
  - prueft die definierten Drift-Arten gegen echte Laufzeit- und DB-Zustaende
  - umfasst mindestens DB-vs-Index, Lifecycle-vs-Searchbarkeit, Citation Snapshot vs Live Status, Queue-Drift und Backup-Manifest-Abgleich
- `cleanup_dry_run`
  - prueft Dry-Run-Berichte und Schutzregeln fuer Cleanup-Kandidaten
  - beweist insbesondere: keine stillen Mutationen, keine zerstoerten Chat-Citations, keine Loeschung referenzierter Originaldateien
- `health_score`
  - prueft die Berechenbarkeit und Plausibilitaet des M5 Health Score gegen reale Teilmetriken
  - umfasst Teilscore-Bildung, Konservativregel bei fehlender Evidenz und Statusklassifikation `healthy|degraded|unhealthy`
- `backup_freshness`
  - prueft, dass Backup-Frische nicht nur dokumentiert, sondern ueber echte Verify-/Restore-Artefakte nachweisbar ist

Pruefprinzip:

- Alle M5-Truth-Tests laufen gegen echte PostgreSQL-Transaktionen.
- Jeder M5-Bereich braucht einen maschinenlesbaren Nachweis im Truth-Report.
- Dokumentierte M5-Konzepte ohne gruene Truth-Tests bleiben Planungsstand und gelten nicht als betriebliche Reife.

#### Gate-Regeln

- M5-Tests zaehlen nur mit echter PostgreSQL-DB.
- `TEST_DATABASE_URL` ist Pflicht fuer jeden freigaberelevanten M5-Truth-Lauf.
- SQLite, In-Memory oder Mock-basierte Laeufe gelten fuer M5 nur als Fast Feedback.
- Fast-Feedback-Ergebnisse duerfen lokale Entwicklung beschleunigen, aber nie ein M5-Gate auf `PASS` setzen.
- Ein M5-Gate darf nur dann als bestanden gelten, wenn die erweiterten `postgres_truth`-Bereiche `data_quality`, `drift_detection`, `cleanup_dry_run`, `health_score` und `backup_freshness` in einem aktuellen PostgreSQL-Report gruen sind.
- Skips bei gesetzter `TEST_DATABASE_URL`, Migrationsfehler, Setup-Fehler oder einzelne rote M5-Truth-Bloecke sind Gate-Blocker.
- M5-Dokumentationsaussagen duerfen nur den Status behaupten, der durch den aktuellen PostgreSQL-Truth-Report belegbar ist.

---

## M6 - Erweiterte Betriebsautomatisierung

**Status:** missing.

**Ziel:** Weitergehende Betriebsautomatisierung nach der M4-Produktisierung, falls ueber den lokalen belastbaren Zielzustand hinaus weitere Automatisierung noetig wird.

### Tasks

- weitergehende Automatisierung fuer Backups, Rotation und externe Speicher.
- erweiterte Betriebs-Healthchecks und wiederkehrende Verifikation.
- optionales Betriebsrunbook fuer erhoehte Wiederherstellungs- und Wartungsanforderungen.

### Akzeptanzkriterien

- Zusaetzliche Betriebsautomatisierung geht ueber den in M4 erreichten lokalen Produktisierungsstand hinaus.

---

## 7. Naechste sequenzielle Schritte

1. Paket-5-Aenderungen committen.
2. Optionalen `/api/v1/documents`-Alias implementieren, falls M3 direkt versionierte Pfade verwenden soll.
3. PostgreSQL-Integrationstests fuer Paket-5-Read-API in CI oder lokalem Standardlauf absichern.
4. Offene M3a-Testluecken fuer finalen GUI-Abschluss schliessen.
5. PostgreSQL-Integrationsnachweis fuer M3b-Suchtreffer, Filterung und Ranking ergaenzen.
6. Ranking-Regressionstest fuer M3b einfuehren.
7. Benutzerkonzept und Workspace-Isolation fuer M4 fachlich und technisch festziehen.
8. Upload-GUI, Diagnoseansicht, Observability sowie Backup/Restore fuer M4 spezifizieren und priorisieren.
9. M4 auf der verifizierten M3-Grundlage als Produktisierungsphase starten.

---

## 8. Risiken und Gegenmassnahmen

| Risiko | Auswirkung | Gegenmassnahme |
|---|---|---|
| OCR fehlt | gescannte PDFs sind fuer Suche/Chat nicht nutzbar | `OCR_REQUIRED` sichtbar halten, OCR als eigenes Paket planen |
| Parser-Qualitaet uneinheitlich | schlechte Chunks oder Quellenanker | Parser-Metriken und Format-spezifische Tests ergaenzen |
| Quellenpositionen unvollstaendig | Zitate koennen grob bleiben | `source_anchor` weiter anreichern, Legacy sauber kennzeichnen |
| GUI startet vor stabilem API-Gate | UI koppelt gegen instabile Backend-Vertraege | GUI-Start strikt erst nach Paket-5-Gate mit Score >= 90 |
| `/api/v1/documents` Alias fehlt | M3 koennte spaeter auf unversionierten Pfad koppeln | Alias vor M3-Clientbindung implementieren |
| Import-Persistenz nutzt direkten `psycopg` | uneinheitliche DB-Schicht | nach Paket 5 in Repository-/Session-Struktur ueberfuehren |
| PostgreSQL-Tests optional | DB-spezifische Fehler koennen unbemerkt bleiben | `TEST_DATABASE_URL` in CI setzen |
| Allgemeiner Chat halluziniert | falsche Antworten | M3c-Quellenpflicht beibehalten, M4-Provider nur hinter Policy und Citation-Gate betreiben |
| Remote-DB-Latenz | langsame Suche/Importe | Indizes, Projektionen, Pagination und Batch-Strategien |

---

## 9. Referenzdokumente

- [Projektstatus](docs/status.md)
- [Datenmodell V1](docs/data-model.md)
- [V1 Dokument-API Contract](docs/api/v1-document-api-contract.md)
- [M3b Retrieval Foundation](docs/m3b-retrieval-foundation.md)
- [M3a GUI Implementierungsplan](docs/m3a-implementation-plan.md)
- [M3a GUI ViewModels](docs/m3a-viewmodels.md)
- [M4a Authentifizierung und Workspace-Isolation](docs/m4a-auth-workspace-isolation.md)
- [M4b Upload-GUI](docs/m4b-upload-gui.md)
- [Definition of Done: Paket 5](docs/paket-5-definition-of-done.md)
- [ADR: Dokument-Read-API und Datenkonsistenz vor Retrieval](docs/adr/0003-document-read-api-before-retrieval.md)
