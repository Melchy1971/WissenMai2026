# Wissensbasis V1 - Masterplan

**Stand:** 2026-05-08  
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

Der aktuelle Report weist `pytest_exit_code = 1`, `failed = 3`, `skipped = 0` und `passed = 26` aus. Damit gilt:

- `M4 Truth Gate = FAIL`
- M4 bleibt blockiert.
- M5 bleibt blockiert.
- Manuelle Score-Freigaben sind fuer M4 unzulaessig, solange der Validator FAIL liefert.

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

- Der aktuelle Validator-Status ist FAIL; daraus folgt keine M4-Freigabe.
- Fachliche Teilbewertungen koennen nur Kontext liefern, aber keine Gate-Freigabe.
- M4 ist damit noch **nicht vollstaendig technisch stabilisiert**.
- M5 bleibt blockiert bis `M4 Truth Gate = PASS`.
- Die kompakte Freigabefassung steht in `docs/m4-m5-freigabefassung.md`.

Aktueller M4c-Befund:

- Backend-Lifecycle-, Soft-Delete- und Citation-Slices sind fachlich implementiert; ob der PostgreSQL-Truth-Nachweis aktuell gruen ist, muss aus `reports/postgres_truth_report.json` gelesen und mit `scripts/validate_m4_truth_gate.py` geprueft werden.
- source_status Live-Lookup liefert `active|archived|deleted|missing` direkt aus der Datenbank — Chaos-Test verifiziert Zustandsuebergaenge.
- Advisory-Lock-, Crash-, M4-Truth- und weitere PostgreSQL-Nachweise liegen als `postgres_truth`-Suite vor; der konkrete Status muss aus einem aktuellen Report kommen.
- Search-, Reindex-, Crash- und Chaos-Nachweise gegen PostgreSQL sind nur mit gesetzter `TEST_DATABASE_URL` belastbar.
- Admin- und Diagnoseansicht sind als read-only Diagnostics real vorhanden; Replay-Endpoint ist implementiert; weitergehende Reparatur-, Cleanup- und Backup-Aktionen sind nicht freigegeben.
- Backup und Restore sind aktuell als Konzept und Runbook beschrieben, aber nicht real implementiert oder getestet.
- Performance- und Betriebsdokumentation sind vorhanden, ersetzen aber keinen aktuellen Restore-Nachweis.

### Risiken

- Authentifizierung wird zu schwergewichtig und zieht ein unnoetiges Enterprise-Modell nach sich.
- Workspace-Isolation bleibt partiell und fuehrt zu Datenleckagen zwischen lokalen Bereichen.
- Upload-GUI fuehrt neue Fehlerpfade ein, die den bestehenden stabilen Importpfad unterlaufen.
- Observability bleibt zu schwach, sodass lokale Betriebsprobleme nur indirekt sichtbar werden.
- Backup/Restore wird dokumentiert, aber nicht real getestet.
- Performance-Haertung verschiebt sich auf spaeter und laesst produktionsnahe lokale Lastprobleme bestehen.
- M4 verwischt die Grenze zu M5 und zieht wieder neue Fachlogik statt Produktisierung nach.

Freigabeentscheidung:

- Go fuer M4d: `Read-only Go`, vollstaendiges M4d `No-Go`
- Go fuer M4e: `No-Go`
- Go fuer M5: `No-Go`

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

## M5 - Analyse, Merge, Refine und Commit

**Status:** missing.

**Ziel:** Dokumente vergleichen, konsolidieren, bearbeiten, freigeben und als neues Dokument committen.

### Tasks

- Analysegruppen fachlich nutzbar machen.
- Dokumentauswahl fuer Analyse.
- Merge erzeugt konsolidierte Zusammenfassung.
- Refine erlaubt Ton, Struktur, Detailgrad, Quellengewichtung, Inhalte und Tags.
- UI fuer Quellen-/Abschnittsabwahl.
- Freigabeschritt vor Commit.
- Commit erzeugt neues Dokument mit Version 1.
- Commit erzeugt Chunks, Tags und Quellenmetadaten.
- Tests fuer Merge, Refine, Commit und Rollback.

### Akzeptanzkriterien

- Kein Analyseergebnis wird ohne Freigabe als Wissensdokument gespeichert.
- Nutzer kann Quellen/Abschnitte vor Commit abwaehlen.
- Commit erzeugt immer ein neues Dokument.
- Quellenbezug bleibt nachvollziehbar.

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
