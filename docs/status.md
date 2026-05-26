
# Projektstatus

Stand: 2026-05-26

## Bootstrap- und Statusmatrix (Seed-/Runtime-Fix)

### Bootstrap-Reihenfolge (dev_bootstrap.ps1)

1. `.env` laden (inkl. Seed Credentials)
2. DB-Verbindung prüfen
3. Alembic-Migrationen (`upgrade head`)
4. Auth-Seed (`backend/scripts/seed_auth.py`)
5. Auth Bootstrap Guard (`scripts/check_auth_bootstrap.py`)
6. `/health`-Smoke-Check (optional)
7. Report schreiben

### Seed Credentials ENV

- `SEED_ADMIN_LOGIN` (Default: `admin@localhost`)
- `SEED_ADMIN_PASSWORD` (Default: `change-me`)
- `SEED_WORKSPACE_NAME` (Default: `Default Workspace`)

> **Warnung (lokale Entwicklung):** `.env` enthält das Klartext-Passwort. Niemals `.env` committen! In produktiver Dokumentation keine Klartext-Credentials angeben.

### Auth Bootstrap Guard

Nach dem Seed prüft `scripts/check_auth_bootstrap.py` Login und Workspace-Isolation. Fehler führen zu Exit != 0 und Report in `reports/auth_bootstrap_guard.json`.

### Runtime Connectivity Gate

`scripts/validate_runtime_connectivity_gate.py` prüft 9 Kernchecks (DB, Alembic, Seed, Health, Login, Auth, Workspace, Frontend, API). Score >= 95 % = PASS (M3a grün), darunter = FAIL (blockiert M3a/M4).

Letzter Run (2026-05-26): **9/9 = 100 % → PASS**

## Aktueller Gate-Status (2026-05-26)

| Gate | Status | Score | Entscheidung |
|---|---|---|---|
| Runtime Connectivity | PASS | 9/9 = 100 % | grün |
| M3a Frontend Truth | PASS | 100/100 | abgeschlossen |
| M4 Backend | NO-GO | 120/138, 16 failed, 2 errors | blockiert |
| M4d Diagnostics | read-only | — | nur read-only freigegeben |
| M5 Vorbereitung | erlaubt | — | Implementierung blockiert bis M4 grün |

## M3a Status

- Login, Workspace-Bootstrap, Contracts, GUI-Chaos: alle grün
- Frontend Truth: Full-Suite PASS, Score 100/100
- Nächster Schritt: Frontend-Truth-Failures analysieren und beheben (falls neue Reports rot)

## M4 Backend Status

- M4b (Upload/Queue): 100 % — PASS
- M4c (Lifecycle/Search/Chat): 100 % — PASS
- M4e (Backup/Restore): DECIDED_PASS (KL-NB-002)
- M4a (Auth/Workspace): >= 95 % Schwelle, aber blockiert durch offene Fehler
- Blocker: KL-M4-003 — 1 unklassifizierter Setup-/Collect-Error in m4a_auth_truth

Weitere Details: siehe `docs/operations.md`, `docs/security.md`, aktuelle Reports.

## Paket-5-Abschlussstand

Paket 5 ist historisch als fachlich und technisch abgeschlossen dokumentiert. Diese Aussage gilt nicht als aktueller Ersatz fuer die M4-PostgreSQL-Truth- und Hardening-Nachweise.

- Historisch dokumentierter Standardlauf: `42 passed, 1 skipped`
- Historisch dokumentierter PostgreSQL-Integrationslauf: `6 passed`
- Historisch dokumentierter Read-/Import-API-Ruecklauf nach PostgreSQL-Fixes: `19 passed`
- Verifizierte Migrationskette: `20260430_0001` bis `20260504_0010`
- Dokumentation ist mit dem heutigen Code- und Migrationsstand aktualisiert.
- Verifizierter Performance-Lauf auf PostgreSQL-Referenzdaten: alle Zielwerte eingehalten.
- Abschlussbewertung: `96/100`
- Entscheidung: `abgeschlossen`.

## GUI-Startregel nach Paket 5

Die GUI wird bewusst nicht vor Abschluss von Paket 5 entwickelt.

- GUI-Start erfolgt erst nach erfolgreichem Paket-5-Gate.
- Mindestbedingung ist ein Paket-5-Gesamtscore von `>= 90`.
- Grundlage fuer GUI-Arbeit ist der synchronisierte Dokument-API-Vertrag, nicht direkte Kopplung an Datenbank oder Parser-Interna.
- Vor M3 startet zuerst `M3a - GUI Foundation`; Suche, Chat und Analyse bleiben ausserhalb dieses GUI-Starts.

Begruendung:

- Erst Paket 5 liefert stabile Read-Pfade, konsistente Dokumentzustaende und einen belastbaren Fehlerstandard.
- Fruehere GUI-Entwicklung wuerde gegen instabile Vertragsgrenzen koppeln und teure UI-Nacharbeit erzeugen.

## M3a GUI Foundation

Stand des Abgleichs mit Code, Frontend Truth Report und M3a Gate am 2026-05-19:

- Minimaler read-only GUI-Prototyp ist implementiert.
- Route `/documents` zeigt die Dokumentliste.
- Route `/documents/{id}` zeigt Metadaten, Versionen und Chunk-Vorschau.
- Importstatus und Fehlercodes sind sichtbar.
- Spaetere GUI-Slices fuer Suche, Chat, Upload, Lifecycle und read-only Diagnostics sind vorhanden. Sie zeigen, dass GUI-Funktionalitaet existiert, ersetzen aber keinen stabilisierten M3a-Abschluss.
- Eine einfache Suche ist mittlerweile als M3b-Erweiterung vorhanden, gehoert aber nicht zum urspruenglichen M3a-Kernscope.
- Aktueller Full-Suite-Frontend-Truth-Lauf: `reports/frontend_truth_report.json` und `reports/gui_truth/latest.json` vom 2026-05-19 mit `82 collected`, `82 passed`, `0 failed`, `0 skipped`, echter API, echter PostgreSQL-Testdatenbank und gruenem `/health/db`.
- Aktueller GUI-Chaos-Nachweis: `reports/gui_truth/gui_chaos_suite_report.json` mit `8 collected`, `8 passed`, `0 failed`.
- Aktueller M3a-Gate-Report: `reports/m3a_gate_result.json` mit `PASS`, Score `100.0`.
- Finaler M3a-Gate-Report: `reports/m3a_final_gate_report.json` mit `PASS`, Score `100.0`.
- Contract-Test-Nachweis ist gruen: `reports/contract_test_report.json` weist `8 collected`, `8 passed`, `0 failed`, `0 skipped` aus.
- Der verbindliche Full-Suite-Frontend-Truth-Scope ist in `docs/frontend-truth-full-suite-scope.md` finalisiert. Kuenftige Full-Suite-Aussagen brauchen alle 15 Pflichtflows; ein Auth-/Bootstrap-Slice reicht nicht.
- PostgreSQL-Truth ist nicht gruen: `reports/postgres_truth_report.json` weist `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1` aus. Dieser Report ist M4 Backend Truth/M5 Operational Truth und blockiert M3a nicht.

Bewertung:

- GUI vorhanden: ja.
- GUI stabilisiert: ja fuer M3a Frontend Foundation.
- Tests/Gates: M3a gruen; M4/M5 bleiben separat ueber `postgres_truth` zu bewerten.

Offene Nicht-M3a-Blocker:

- Roter PostgreSQL Truth Report bleibt M4/M5-Blocker.
- M5 Entropy, Queue Aging, Drift, Cleanup und Longevity sind keine M3a-Blocker.

Entscheidung:

- M3a ist als Frontend Foundation abgeschlossen.
- Der fruehere formale Blocker fuer M3b ist durch spaetere Implementierungen historisch ueberholt; M3a ist als eigener Meilenstein jetzt durch den aktuellen Gate-Report abgeschlossen.
- M3a darf nur auf Basis des gruenen `scripts/validate_m3a_gate.py` und `reports/m3a_gate_result.json` als abgeschlossen dokumentiert werden.

## M3b Retrieval Foundation

Stand des Abgleichs mit Code, Backend-Tests, Frontend-Tests und Build am 2026-05-05:

- Search API unter `/api/v1/search/chunks` ist implementiert.
- Ranking-Baseline ist im Query-Pfad ueber PostgreSQL FTS und `ts_rank` angelegt.
- Stabile Sortierung ist technisch umgesetzt ueber `rank DESC`, `documents.created_at DESC`, `chunk_index ASC`, `chunk_id ASC`.
- Indexierung fuer PostgreSQL ist ueber Migration `20260504_0011_chunk_search_vector.py` implementiert.
- GUI-Suche ist in der Dokumentuebersicht als einfache Chunk-Suche sichtbar.
- Lade-, Leer- und Fehlerzustaende fuer die GUI-Suche sind implementiert.
- Out-of-Scope-Themen bleiben eingehalten: kein Chat, keine LLM-Antwort, kein komplexes Re-Ranking.

Verifizierter Nachweis:

- Backend-Suche und Migrationspfad: `14 passed`
- Frontend-Screens inklusive Suche: `8 passed`
- Frontend-Build: `vite build` gruen

Restliche Hinweise nach hartem Abschluss:

- PostgreSQL-Retrieval-Integrationstests und Ranking-Regressionstests existieren, laufen aber nur mit gesetzter `TEST_DATABASE_URL`.
- SQLite bleibt fuer diese Tests ausgeschlossen.
- Der Search-Vertrag ist in `docs/api.md` und `docs/retrieval.md` dokumentiert.

Abschlussbewertung:

- Score: `92/100`
- Entscheidung fuer M3b: `abgeschlossen`
- Go fuer M3c Chat/RAG: `Go`

Begruendung:

- Der fachliche Scope von M3b ist weitgehend geliefert.
- PostgreSQL-Integrationstests und Ranking-Regressionstests sind vorhanden, laufen aber nur mit gesetzter `TEST_DATABASE_URL`.
- M3c setzt auf diesen Search-Service-Vertrag auf und mockt Retrieval in Standardtests deterministisch.

## M3c Chat/RAG Foundation

Stand des Abgleichs mit Code, Backend-Tests, Frontend-Tests und Build am 2026-05-05:

- Chat Sessions API ist implementiert und getestet:
  - `POST /api/v1/chat/sessions`
  - `GET /api/v1/chat/sessions`
  - `GET /api/v1/chat/sessions/{session_id}`
- Message API ist implementiert und getestet:
  - `POST /api/v1/chat/sessions/{session_id}/messages`
  - Request: `question`, `retrieval_limit`; der Workspace kommt serverseitig aus AuthContext und `X-Workspace-Id`
  - Response: Assistant-`ChatMessageResponse` mit Citations und Confidence
- `RagChatService` ist implementiert und verdrahtet:
  - User-Frage speichern
  - Retrieval ausfuehren
  - Context Builder ausfuehren
  - Insufficient-Context-Policy pruefen
  - Prompt Builder ausfuehren
  - LLM Provider aufrufen
  - Assistant-Antwort speichern
  - Citations speichern
  - API Response erzeugen
- Context Builder ist implementiert und getestet.
- Prompt Builder ist implementiert und getestet.
- Citation Mapper ist implementiert und getestet.
- Insufficient-Context-Policy ist implementiert und getestet.
- Fake LLM Provider ist implementiert und getestet.
- Chat-UI mit Sessionliste, neuer Session, Nachrichtenverlauf, Frageformular, Antwortanzeige, Quellenanzeige und Fehlerzustaenden ist implementiert und gegen den echten Vertrag getestet.

Fehlercodes:

- `CHAT_SESSION_NOT_FOUND`
- `CHAT_MESSAGE_INVALID`
- `CHAT_PERSISTENCE_FAILED`
- `RETRIEVAL_FAILED`
- `INSUFFICIENT_CONTEXT`
- `LLM_UNAVAILABLE`

Nicht-Scope-Pruefung:

- keine Agenten: eingehalten.
- kein Tool Use im Produktflow: eingehalten.
- keine Dokumentmutation: eingehalten.
- kein Streaming: eingehalten.
- keine Embeddings: eingehalten.
- kein produktiver LLM Provider: bleibt M4-Scope.

Verifizierter Nachweis:

- Backend-Fokuslauf fuer Chat/RAG, Context, Prompt, Citation, Policy und Persistenz: `74 passed`.
- Frontend-Gesamtlauf: `14 passed`.
- Frontend-Build: erfolgreich.

Abschlussbewertung:

- Score: `94/100`
- Entscheidung fuer M3c: `abgeschlossen`
- Go fuer M4: `Go`

Begruendung:

- Die stabilen Chat-HTTP-Endpunkte sind vorhanden und API-getestet.
- Der RAG-Antwortpfad ist ueber Service- und API-Tests nachgewiesen.
- Quellenpflicht und Insufficient-Context-Schutz sind technisch umgesetzt.
- Die GUI konsumiert den echten Chat-Vertrag.
- Restpunkte wie produktiver LLM Provider, Streaming, Agenten, Embeddings und Browser-E2E sind M4- oder spaetere Scope-Themen und blockieren M3c nicht.

## M4 Produktisierung und Betriebsfaehigkeit

Stand des aktuellen Gesamt-Abgleichs am 2026-05-19:

- M4 ist teilweise implementiert.
- Die dafuer benoetigte M3c-Foundation ist abgeschlossen.
- M3a Frontend Foundation ist abgeschlossen (`reports/m3a_gate_result.json`: `PASS`, Score `100.0`).
- Der aktuelle PostgreSQL Truth Report ist nicht gruen (`138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1`).

M4 Statusmatrix am 2026-05-19:

| Bereich | Gate-Quelle | Status |
|---|---|---|
| M3a Gate | `reports/m3a_gate_result.json` | PASS, Score `100.0` |
| Frontend Truth | `reports/frontend_truth_report.json` plus `reports/gui_truth/latest.json` | Full-Suite PASS (`82/82`, `0 failed`, `0 skipped`) |
| M4 Truth Gate | `reports/postgres_truth_report.json` | FAIL (`120/138`, `16 failed`, `2 errors`) |
| M4a Auth & Workspace Isolation | `reports/postgres_truth_report.json` (`gate_scores.m4a_gate`) | Teilbefund `100.0%`, aber Gesamtstatus blockiert |
| M4b Upload/API Stabilitaet | `reports/postgres_truth_report.json` (`gate_scores.m4b_gate`) | Teilbefund `91.7%`, aber Gesamtstatus blockiert |
| M4c Lifecycle | `reports/postgres_truth_report.json` (`gate_scores.m4c_gate`) | Teilbefund `100.0%`, aber Gesamtstatus blockiert |
| M4d Diagnostics | read-only Slice + fokussierte Tests | vorhanden im read-only Scope, keine Gesamtfreigabe |
| M4e Backup/Restore | Restore-Truth-Report + Runbook + Tests | Entscheidung dokumentiert, aber keine Kompensation fuer rote Gates |

Hinweis: Der fruehere Truth-Report vom 2026-05-11 war ein historischer Zwischenstand. Der aktuelle Report vom 2026-05-18 ist die massgebliche Gate-Quelle und blockiert M4.

Gesamtentscheidung fuer M4:

- M4 bleibt blockiert.
- M4 ist nicht als technisch stabil freigegeben, weil der aktuelle PostgreSQL Truth Report rot ist.
- Die GUI blockiert M4 nicht mehr ueber M3a; M4 bleibt durch M4 Backend Truth blockiert.
- M4 Gesamtabschluss ist `No-Go`.
- M5-Transition aus M4 ist `No-Go`.
- M4d read-only bleibt der einzig zulaessige Diagnostics-Scope; M4d full mit mutierenden Admin-Aktionen bleibt blockiert.
- Die korrigierte Gesamtmatrix steht in `docs/m4-gesamt-reconciliation.md`.

### Finale Wahrheitsmatrix fuer M4-Dokumentation

| Aussage | Klassifikation | Dokumentationsregel |
|---|---|---|
| M4d Diagnostics hat einen realen read-only Backend-/Frontend-Slice | bewiesen | darf dokumentiert werden |
| M4d ist vollstaendig abgeschlossen | falsch | darf nicht dokumentiert werden |
| Mutierende Admin-Aktionen wie Reindex, Cleanup, Backup oder Repair sind freigegeben | falsch | darf nicht dokumentiert werden |
| M5-Vorbereitungs-Go vom 2026-05-11 | historisch ueberholt | aktuell `No-Go`, siehe `docs/m4-gesamt-reconciliation.md` |
| PostgreSQL Truth-Tests ersetzen ohne `TEST_DATABASE_URL` einen echten Nachweis | falsch | Skip ohne Test-DB ist kein Stabilitaetsnachweis |
| Search/Chat-Konsistenz ist als Truth-Test vorbereitet | bewiesen | darf als vorbereitet dokumentiert werden |
| Search/Chat-Konsistenz ist aktuell mit echter PostgreSQL-DB gruen bewiesen | unbelegt | darf nicht als Freigabegrund dokumentiert werden |
| Lifecycle-Mutationen sind fuer Fremdworkspace-Zugriffe im API-/Service-Slice nachgewiesen blockiert | bewiesen | darf fuer den vorhandenen Slice dokumentiert werden |
| Chat-Message-Write ist ueber den aktuellen Request-Kontext workspace-gebunden, aber nicht als vollstaendig abgeschlossener M4a-Endzustand belegt | wahrscheinlich | nicht als Abschlussbeweis fuer M4a verwenden |
| Historische Citation-Snapshots speichern `quote_preview`, `source_anchor`, `document_title` und `source_status` | bewiesen | darf dokumentiert werden |
| Observability ist fuer Lifecycle/Retrieval/Reindex vollstaendig | falsch | als fehlende Instrumentierung dokumentieren |

Zielbild:

- M4 stabilisiert den lokalen Produktbetrieb statt neue Intelligenz-Schichten einzufuehren.
- Der Fokus liegt auf Benutzerkonzept, Isolation, Upload, Lifecycle, Diagnose, Observability, Backup/Restore, Performance und Betriebsdokumentation.

In Scope fuer M4:

- Authentifizierung und Benutzerkonzept
- Workspace-Isolation
- Upload-GUI
- Dokument-Lifecycle
- Admin- und Diagnoseansicht
- Observability
- Backup/Restore
- Performance-Haertung
- Deployment-Dokumentation

### M4a Authentifizierung und Workspace-Isolation

Stand des Abgleichs mit Code, Tests und Dokumentation am 2026-05-05:

- Ein technischer M4a-Auth-Kern ist im Backend nachweisbar.
- Implementiert sind Auth-Middleware, Auth-Session-Pruefung, Workspace-Membership-Pruefung sowie serverseitig aufgeloester Request-Kontext fuer geschuetzte Endpunkte.
- `POST /api/v1/auth/login`, `POST /api/v1/auth/logout` und `GET /api/v1/auth/me` sind im Code vorhanden.
- Der Upload ist auth-gebunden und verwendet keinen Default-Workspace-/Default-User-Fallback mehr.
- Die aktuellen Dokument-, Search-, Chat-, Upload- und Diagnostics-API-Clients nutzen den zentralen Request-Kontext. Route-Guards, Login-Bootstrap und Logout-Revocation sind vorhanden. M4a bleibt dennoch offen, weil der Produktfluss noch nicht als vollstaendiger Abschluss mit allen Restnachweisen bewertet ist.

Betroffene Endpunkte im aktuellen Stand:

- `POST /documents/import`
- `GET /documents`
- `GET /api/v1/search/chunks`
- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `POST /api/v1/chat/sessions/{session_id}/messages`
- `POST /api/v1/admin/search-index/rebuild`

Nachweisbare Fehlercodes mit M4a-Bezug:

- `AUTH_REQUIRED`
- `AUTH_INVALID_CREDENTIALS`
- `WORKSPACE_ACCESS_FORBIDDEN`
- `ADMIN_REQUIRED`
- `WORKSPACE_REQUIRED`

Bekannte Einschraenkungen:

- keine CSRF- oder Cookie-Session-Implementierung
- Frontend nutzt fuer Fachrequests den zentralen Request-Kontext mit `X-Workspace-Id`; der Login-/Logout-/Route-Guard-Produktfluss ist vorhanden, aber noch nicht der gesamte M4a-Endzustand.

Nicht-Scope, das weiterhin nicht geliefert ist:

- OAuth
- SSO
- externe Identity Provider
- feingranulare Rollenmodelle
- Enterprise-Berechtigungen

Abschlussbewertung fuer M4a:

- Score: `86/100`
- Dokumentation: jetzt aktualisiert
- Konsistenz mit dem implementierten Code: **nicht ausreichend fuer Abschluss**
- Teststatus: Backend-Auth- und Workspace-Schutz sind gut abgedeckt; ein gleichwertiger Frontend-Nachweis fuer einen durchgezogenen Session-Produktfluss fehlt
- Blocker: M4a ist trotz vorhandenem Login-/Logout-/Route-Guard-Slice noch nicht vollstaendig ueber alle angrenzenden Betriebs- und Nachweispfade abgeschlossen
- Entscheidung: `historischer Detailstand; aktuelle Freigabe siehe M4/M5-Freigabefassung`

### M4b Upload-GUI

Stand des Abgleichs mit Code, Tests und Dokumentation am 2026-05-05:

- Die Upload-GUI ist in der Dokumentuebersicht implementiert und nutzt den asynchronen Importpfad mit Hintergrundjob-Polling.
- Die finale Architekturentscheidung fuer die Upload-Ausfuehrung ist **interne persistente Queue**, nicht synchroner Upload und nicht `FastAPI BackgroundTasks` als Zielarchitektur; verbindlich dokumentiert in [docs/adr/0004-upload-execution-model.md](docs/adr/0004-upload-execution-model.md).
- `POST /documents/import` liefert `202 Accepted` mit einem `document_import`-Job; die GUI pollt anschliessend den Jobstatus.
- Erfolgreiche Importe werden in der GUI mit Dateiname, Dokument-ID, `import_status`, Chunk-Anzahl und bei Bedarf Duplicate-Hinweis angezeigt.
- Fehler aus dem Importpfad werden nicht mehr synchron am Upload-Endpunkt erwartet, sondern erscheinen als `failed`-Job mit `error_code` und `error_message`.
- Duplicate-, Parser- und OCR-Faelle sind im Backend und in Tests nachweisbar; die GUI zeigt Duplicate als Erfolgstext und Parser-/OCR-Faelle ueber gemappte Fehlerzustande an.
- Der Upload ist auth-gebunden; Workspace und Benutzer kommen aus dem serverseitigen Auth-Kontext.
- Der serverseitige Default-Workspace-/Default-User-Fallback ist aus dem Upload-Flow entfernt.

Upload-Flow im aktuellen Stand:

- Datei in `/documents` auswaehlen
- `POST /documents/import` ausloesen
- Jobstatus ueber `GET /api/v1/jobs/{job_id}` pollen
- bei `completed`: Ergebnis anzeigen und Dokumentliste neu laden
- bei `failed`: generischen Fehlerzustand mit gemapptem Fehlercode anzeigen

Importstatus im aktuellen Stand:

- Jobstatus: `queued`, `running`, `completed`, `failed`
- fachlicher Importstatus im Jobergebnis: insbesondere `chunked` oder `duplicate`

Nachweisbare Fehlercodes mit M4b-Bezug:

- `UNSUPPORTED_FILE_TYPE`
- `FILE_TOO_LARGE`
- `PARSER_FAILED`
- `OCR_REQUIRED`
- `DUPLICATE_DOCUMENT` im Backend-Fehlerkanon, aktuell nicht der normale Upload-Erfolgsvertrag
- `IMPORT_FAILED` fuer unerwartete Importfehler im Jobpfad
- `JOB_NOT_FOUND`
- `NETWORK_ERROR` im Frontend-Mapping
- `AUTH_REQUIRED`
- `WORKSPACE_ACCESS_FORBIDDEN`

Duplicate-Verhalten:

- Duplicate Detection ist im Backend nachweisbar und liefert `import_status = duplicate` sowie `duplicate_of_document_id`.
- Die aktuelle GUI zeigt den Abschlussfall als Erfolg mit Text `bereits vorhanden` und zeigt `duplicate_of_document_id` an.
- Ein eigener Deep-Link oder eine gesonderte Aktion fuer das vorhandene Dokument ist weiterhin nicht implementiert.

OCR-required-Verhalten:

- OCR-Bedarf fuehrt im Hintergrundjob zu `status = failed` und `error_code = OCR_REQUIRED`.
- Die GUI zeigt diesen Fall ueber den allgemeinen ErrorState mit gemapptem Fehler-Titel an, ohne spezialisierten OCR-Hinweis oder Folgeaktion.

Bekannte Einschraenkungen:

- kein Direkt-Sprung in die Dokumentdetailansicht nach erfolgreichem Import
- keine Darstellung von `warnings` im Upload-Ergebnis
- Polling ohne exponentielles Backoff oder sichtbare Retry-Strategie
- Dokumentseite nutzt den zentralen Request-Kontext fuer Upload und Dokumentliste
- ein vollstaendiger Login-/Logout-/Route-Guard-Produktfluss fehlt weiterhin

Teststatus fuer M4b am 2026-05-05:

- Pflicht-Uploadtests laufen ohne Skip und decken `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, Parserfehler, OCR-Bedarf, Upload ohne Auth, Upload in fremdem Workspace und sequential duplicate ab.
- Der echte PostgreSQL-Race-Test fuer parallele Duplicate-Uploads bleibt nur dann ein Skip, wenn `TEST_DATABASE_URL` fehlt.
- Sobald `TEST_DATABASE_URL` gesetzt ist, muessen Alembic-Migrationen erfolgreich laufen; Migrationsfehler sind Testfehler und kein Skip.
- Verifikationsstand 2026-05-06 aus dieser Arbeitsumgebung: Testsemantik ist gehaertet, aber ein echter PostgreSQL-Lauf war hier nicht abschliessend moeglich, weil Docker lokal nicht verfuegbar war und die dokumentierte Remote-DB mit `psycopg.errors.ConnectionTimeout` nicht erreichbar war.

Abschlussbewertung fuer M4b:

- Score: `88/100`
- Dokumentation: jetzt aktualisiert
- Konsistenz mit dem implementierten Code: **nicht ausreichend fuer Abschluss**
- Teststatus: Kernpfad fuer Upload, GUI-Polling und Fehlerabbildung ist gut belegt; der harte PostgreSQL-Race-Nachweis fuer Parallelitaet fehlt weiter
- Blocker: PostgreSQL-Race-/Infra-Nachweis, fehlende `warnings`-Darstellung und kein Deep-Link in die Dokumentdetailansicht nach Erfolg
- Entscheidung: `historischer Detailstand; aktuelle Freigabe siehe M4/M5-Freigabefassung`

### M4c Dokument-Lifecycle

Stand des Abgleichs mit Code, Tests und Dokumentation am 2026-05-06:

- Der Dokument-Lifecycle ist im Backend durchgaengig mit `active`, `archived` und `deleted` implementiert.
- Listen- und Read-Pfade verarbeiten diese Stati konsistent.
- Soft-Delete wird ueber `lifecycle_status = deleted` plus `deleted_at` modelliert; physische Folgeobjekte bleiben erhalten.
- Historische Chat-Citations bleiben fuer spaeter archivierte oder geloeschte Dokumente sichtbar.
- Der fokussierte Backend-Lauf fuer Lifecycle, historische Citations und Search-Index-Service ist lokal gruen nachgewiesen.

Lifecycle-Regeln im aktuellen Stand:

- `active`: Standardzustand, in Liste, Search und neuem Chat-Retrieval sichtbar
- `archived`: nur ueber Listenfilter sichtbar, nicht suchbar und nicht fuer neue Chat-Antworten retrievable
- `deleted`: Soft-Delete, nicht mehr ueber Read-API oder Search zugreifbar

Lifecycle State Machine:

- `active -> archived`
- `archived -> active`
- `active -> deleted`
- `archived -> deleted`
- `deleted` ist terminal

Auswirkungen auf Liste, Suche und Chat:

- `GET /documents` zeigt standardmaessig nur `active`
- `GET /documents?lifecycle_status=archived` zeigt archivierte Dokumente gezielt an
- `deleted` ist im Listenpfad effektiv unsichtbar
- Search schliesst alles ausser `active` aus
- fuer neue RAG-Antworten gibt es nur einen indirekten Nachweis ueber den Search-/Retrieval-Pfad, keinen eigenen Lifecycle-spezifischen Chat-Integrationstest
- bestehende Chat-Citations bleiben bei archivierten und geloeschten Dokumenten historisch lesbar
- historische Chat-Citations aktualisieren dabei ihren `source_status` auf `archived` oder `deleted`

Reindex-Regeln:

- Reindex synchronisiert `Chunk.is_searchable` an den Dokument-Lifecycle
- aktive Dokumente werden fuer Search wieder auf `is_searchable = true` gesetzt
- archivierte und geloeschte Dokumente werden fuer Search auf `is_searchable = false` gesetzt
- der PostgreSQL-spezifische Reindex-Pfad ist im Unit-/Service-Slice nachgewiesen
- der echte PostgreSQL-Integrationspfad ist aktuell nicht erfolgreich verifiziert, weil die konfigurierte Ziel-Datenbank im Testlauf per Connection-Timeout nicht erreichbar war

Soft-Delete-Regeln:

- `DELETE /documents/{document_id}` setzt `lifecycle_status = deleted` und `deleted_at`
- Versionen, Chunks und Citations werden nicht physisch geloescht
- `deleted` ist terminal; eine Restore-Transition fuer geloeschte Dokumente ist nicht implementiert

Bekannte Einschraenkungen:

- `lifecycle_status=deleted` ist als Querywert formal akzeptiert, liefert im Listenpfad aber keine geloeschten Dokumente zurueck
- kein separater Purge-/Hard-Delete-Betriebsprozess
- keine dedizierte Admin-Ansicht fuer geloeschte Dokumente
- Lifecycle-Mutationen sind auth-geschuetzt und der API-/Service-Slice blockiert Fremdworkspace-Mutationen nachweisbar; offen bleiben die vollstaendigen End-to-End-Nachweise gegen reale PostgreSQL-Umgebung
- die GUI ist fuer Listenfilter, Archive, Restore und Soft-Delete ueber Vitest-Screen-Tests verifiziert
- Search-/Reindex-Integrationsnachweise gegen PostgreSQL sind aktuell wegen nicht erreichbarer Test-Datenbank unvollstaendig
- fuer neue Chat-Antworten gibt es keinen eigenen expliziten Lifecycle-Integrationstest jenseits des Retrieval-Ausschlusses
- der aktuelle Admin-Diagnostics-Frontend-Slice ist fuer read-only Diagnostics gruen; ein vollstaendiger Browser-E2E fuer angrenzende Lifecycle-/Rebuild-Szenarien fehlt weiterhin

Abschlussbewertung fuer M4c:

- Score: `86/100`
- Dokumentation: jetzt aktualisiert
- Konsistenz mit dem implementierten Code: **teilweise, aber nicht vollstaendig hart abgesichert**
- Teststatus: Backend-Lifecycle, Soft-Delete, historische Citations und GUI-Slice sind lokal gruen belegbar; der PostgreSQL-End-to-End-Pfad fuer Search/Reindex ist aktuell nicht erfolgreich verifiziert
- Blocker: fehlender gruener PostgreSQL-Integrationslauf, kein eigener Lifecycle-Chat-End-to-End-Nachweis und kein vollstaendiger Browser-E2E ueber angrenzende Lifecycle-/Rebuild-Szenarien
- Entscheidung: `historischer Detailstand; aktuelle Freigabe siehe M4/M5-Freigabefassung`

### M4d Diagnostics

Stand des Abgleichs mit Code, Tests und Dokumentation am 2026-05-07:

- Real implementiert ist ein aggregierter read-only Diagnostics-Endpunkt `GET /api/v1/admin/diagnostics`.
- Die Diagnostics-API liefert nur Systemstatus, DB-/Migrationstatus, aggregierte Counts, Import-Job-Status, Search-Index-Status sowie Auth-/Workspace-Status.
- Die Admin-GUI `/admin/diagnostics` zeigt diesen read-only Aggregatvertrag als Statuskarten.
- Admin-Rechte werden ueber AuthContext und Workspace-Membership/Role `owner` oder `admin` erzwungen.
- Ohne Auth liefert Diagnostics `401 UNAUTHORIZED`, ohne Adminrolle oder bei fremdem Workspace `403 FORBIDDEN`.
- Bei Diagnosefehlern liefert der Endpoint `500 DIAGNOSTICS_FAILED` mit redigierten Details.
- Die vorher produktiv erreichbare Search-Index-Rebuild-Aktion ist fuer M4d read-only deaktiviert und antwortet mit `501 ADMIN_ACTION_NOT_IMPLEMENTED`.

Sicherheits- und Scope-Grenzen:

- Diagnostics ist strikt read-only.
- Keine Reparaturaktionen.
- Keine Reindex-, Cleanup- oder Backup-Aktionen.
- Keine User- oder Workspace-Verwaltung.
- Keine Dokumentreparatur.
- Keine Dokumenttexte, Chunktexte, Chat-Fragen, Chat-Antworten, Prompts, Secrets, Tokens, Connection-Strings oder lokalen Dateipfade.

Teststatus:

- Backend-Diagnostics und deaktivierter Admin-Rebuild sind fokussiert getestet: `11 passed`.
- Frontend-Diagnostics-Screen ist fokussiert getestet: `4 passed`.
- Tests decken ohne Auth, ohne Adminrolle, fremden Workspace, DB-Fehler, Content-/Secret-Redaction, API down, degraded Status und fehlende mutierende UI-Aktionen ab.

Abschlussbewertung fuer M4d:

- Bewertung: read-only Slice vorbereitet; kein vollstaendiges M4d
- Dokumentation: auf read-only Zustand aktualisiert
- Konsistenz mit dem implementierten Code: **ausreichend fuer read-only Vorbereitung**
- Blocker fuer vollstaendiges M4d: M4a, M4b und M4c sind noch nicht gruen; deshalb bleiben alle write/admin actions blockiert
- Entscheidung: `read-only vorbereitet`, **nicht vollstaendig abgeschlossen**

### M4e Backup/Restore

Stand des Abgleichs mit Code, Tests und Dokumentation am 2026-05-06:

- M4e ist als Konzept definiert und als CLI-first Minimalpfad teilweise implementiert.
- Das System speichert technische Originaldatei-Kopien nun im Importpfad und referenziert sie in Versions-Metadaten fuer Restore-Zwecke.
- Backup ist fuer M4e als CLI-first Betriebsprozess implementiert.
- Search-Index ist als rekonstruierbar spezifiziert, nicht als primaeres Backup-Artefakt.
- Ein nachweisbarer Backup-/Validate-/Restore-/Reindex-Codepfad ist im aktuellen Repository vorhanden unter `app.cli` und `app.services.backup_restore`.
- Fokussierte Unit-Tests fuer Dateiablage, Backup-Validierung und Restore-Orchestrierung sind vorhanden.
- Ein praktischer End-to-End-Restore gegen eine leere reale lokale PostgreSQL-Ziel-DB ist nachgewiesen.

Entscheidung:

- Status fuer M4e: `Minimal-Scope erfüllt`
- Implementierungsstatus: `lokal freigabefaehiger Minimalpfad`

Abschlussbewertung fuer M4e:

- Score: `86/100`
- Dokumentation: Konzept, Codepfad und lokaler Restore-Nachweis sind nun konsistent dokumentierbar
- Teststatus: fokussierte Unit-Tests vorhanden; lokaler Restore-Lauf gegen leere reale PostgreSQL-Ziel-DB ist praktisch nachgewiesen
- Blocker: keine technischen M4-Minimal-Blocker mehr; Produktionshaertung, Backup-Sicherheit und externe Betriebsvalidierung bleiben offen
- Entscheidung: `lokal akzeptiert`, fuer Produktionsbetrieb weiter `partial`

Nicht-Scope fuer M4:

- Agenten
- automatische Aktionen
- komplexe Workflows
- Multi-User-Collaboration
- Enterprise-Rollenmodell
- externe Integrationen

Abhaengigkeiten zu M3:

- M4 setzt auf M3a GUI-Grundstruktur, M3b Retrieval und M3c Chat/RAG Foundation auf.
- M4 darf vorhandene M3-Faehigkeiten haerten, aber keine neue Intelligenz-Schicht erzwingen.

Entscheidung:

- Status fuer M4: `partial`
- Gesamtentscheidung: `blockiert`, aktueller Hardening-Score `74/100`
- Go/No-Go fuer M4d: `read-only vorbereitet`, vollstaendiges M4d `No-Go`
- Go/No-Go fuer M4e: `No-Go`
- Startfreigabe fuer weitere M4-Slices: `No-Go`, solange das M4-Gate fuer `M4a`, `M4b` und `M4c` nicht erreicht ist

## Governance Framework

Stand: 2026-05-13

Das vollstaendige Governance-Framework ist abgeschlossen. Es umfasst 8 Dokumente fuer Architektur-, Schema-, Feature-, SLA-, Failure-, Audit-, Invarianten- und Langzeitstrategie-Governance.

| Dokument | Typ | Bewertung |
|---|---|---|
| `docs/architecture-change-governance.md` | Architektur | systemisch kontrolliert |
| `docs/schema-evolution-safety-model.md` | Schema | systemisch kontrolliert |
| `docs/feature-governance-model.md` | Feature | systemisch kontrolliert |
| `docs/retrieval-stability-contract.md` | Retrieval | systemisch kontrolliert |
| `docs/operational-truth-governance.md` | Truth | systemisch kontrolliert |
| `docs/operational-sla-framework.md` | SLA | definiert |
| `docs/controlled-failure-philosophy.md` | Failure | definiert |
| `docs/audit-trail-schema.md` | Audit | ueberwiegend kontrolliert |
| `docs/system-invariant-registry.md` | Invarianten | INV-001 bis INV-036 registriert |
| `docs/long-term-governance-review.md` | Review | 4 Risiken, 6 Luecken bewertet |
| `docs/long-term-architecture-strategy.md` | Strategie | 7 Ziele, 10 No-Gos, 7 RF-Trigger |

Offene Luecken (aus `docs/long-term-governance-review.md`):

- **L-01**: Kein laufender Drift-Service (HIGH)
- **L-02**: Cleanup-Mutationspfad nicht freigegeben (HIGH)
- **L-03**: `actor`-Feld fehlt in Audit-Trail-Implementierung (MEDIUM)
- **L-04**: Golden-Query-Korpus nicht versioniert auffindbar (MEDIUM)
- **L-05**: PostgreSQL-Truth-Tests noch skippable ohne CI-DB (HIGH)
- **L-06**: Kein zentraler Audit-Store (MEDIUM)

---

## M5 Governance Services

Stand: 2026-05-13

M5 fuehrt eine Schicht operativer Governance-Services ein, die ueber M4-Diagnostics hinausgehen und aktive Systemkontrolle ermoeglichen.

### Implementierte Governance-Services

| Service | Datei | Status | Letzter Truth-Nachweis |
|---|---|---|---|
| `ReindexGovernanceService` | `app/services/reindex_governance.py` | implementiert | nicht im aktuellen Report |
| `CitationLongevityAuditService` | `app/services/citation_longevity_service.py` | implementiert | nicht im aktuellen Report |
| `QueueAgingService` | `app/services/queue_aging_service.py` | implementiert | nicht im aktuellen Report |
| `CleanupGovernanceService` | `app/services/cleanup_governance.py` | implementiert | nicht im aktuellen Report |

### Admin-API-Endpunkte (M5)

| Endpunkt | Methode | Beschreibung | Auth |
|---|---|---|---|
| `/api/v1/admin/queue/aging` | GET | Queue-Aging-Report fuer Backlog, Starvation, Dead-Letter | owner/admin |
| `/api/v1/admin/citations/longevity` | GET | Citation-Longevity-Audit fuer Snapshot-Stabilitaet | owner/admin |
| `/api/v1/admin/reindex/governed` | POST | Governed Reindex mit Safety-Gates und Audit-Trail | workspace_admin |
| `/api/v1/admin/cleanup/governed` | POST | Governed Cleanup mit Dry-Run, Safety-Gates und Delta-Snapshot | workspace_admin |

### Governance-Envelope-Prinzip

Alle M5-Governance-Aktionen folgen demselben Envelope:

- `correlation_id` pflichtmaessig propagiert
- `dry_run_only = true` als sicherer Default fuer Cleanup
- Safety-Gates vor jeder Mutation (aktive Jobs blockieren, Citation-Orphan-Scope als Warning, aktive-Dokument-Orphan-Chunks als Blocker)
- Before/After-Snapshot fuer delta-basierte Auditierbarkeit
- `rollback_strategy` und `recovery_hints` in jedem Report
- Audit-Events fuer alle governten Aktionen

### M5 Entropy-Monitoring

Die Entropy-Test-Suite (`backend/tests/postgres_truth/test_entropy_truth.py`) simuliert Langzeitbetrieb und detektiert schleichende Systemalterung:

- Orphan-Chunk-Wachstum
- Stale-Index-Ansammlung (archivierte Dokumente ohne `is_searchable=false`)
- Retrieval-Degradation (Coverage unter `RETRIEVAL_COVERAGE_MIN = 0.85`)
- Queue-Backlog-Drift und Dead-Letter-Akkumulation
- Citation-Orphan-Rate (Orphan-Rate-Grenzwert: 0.30)
- Multi-Epoch-Chaos-Recovery-Simulation (V-Shape: Chaos -> Erholung)

Entropy-Metriken sind als `EntropyMetrics`-Dataclass definiert (12 Dimensionen) und als `as_risk_dict()` auswertbar.

### Truth-Nachweisstand fuer M5

- Suite vorhanden: `backend/tests/postgres_truth/test_*_truth.py` fuer alle 5 neuen Bereiche
- Letzter verifizierter Report: 2026-05-11, 33 Tests (M4-Bereiche)
- M5-Tests (ca. 55 neue Tests) sind noch nicht im aktuellen Truth-Report enthalten
- Naechster erforderlicher Schritt: PostgreSQL-Truth-Lauf mit gesetzter `TEST_DATABASE_URL` gegen alle neuen Tests

### Operational Readiness Rating

Bewertung vom 2026-05-12 (vor M5-Truth-Verifikation):

- Rating: **kontrolliert betreibbar**
- Governance-Services sind implementiert und lokal getestet
- Truth-Nachweis fuer neue Tests steht noch aus
- Kritischste offene Risiken: fehlender gruener M5-Truth-Lauf, keine CI-Integration fuer neue Marker

## Ground Truth = Code, nicht Dokumentation

Diese Datei beschreibt den aktuellen Stand nach Abgleich mit dem Code. Bei Widerspruechen gilt immer der Code als Ground Truth, nicht diese Dokumentation.

Vor Statusaenderungen sollen mindestens die betroffenen Module und Tests geprueft werden:

- Backend-Code unter `backend/app`
- Alembic-Migrationen unter `backend/migrations/versions`
- Tests unter `backend/tests`
- API-Vertrag unter `docs/api`

## Was ist neu in Paket 5

Paket 5 macht Dokumente stabil lesbar und bereitet M3 Suche/Retrieval vor, ohne Suche, Chat, UI oder OCR zu implementieren.

Neue und stabilisierte Endpoints:

- `GET /documents`
  - required `workspace_id`
  - `limit` Default `20`, Maximum `100`
  - `offset` Default `0`
  - Sortierung `created_at DESC`
  - stabile Listenfelder inklusive `mime_type`, `import_status`, `version_count` und `chunk_count`
- `GET /documents/{document_id}`
  - Dokument-Metadaten
  - `latest_version`
  - Parser-Metadaten
  - `import_status`
  - `chunk_summary`
- `GET /documents/{document_id}/versions`
  - Versionen in `created_at DESC`, bei Gleichstand `version_number DESC`
- `GET /documents/{document_id}/chunks`
  - Chunks nur der aktuellen Version
  - Sortierung `position ASC`
  - optionales `limit`
  - serverseitiges `text_preview` mit maximal 200 Zeichen
  - normalisiertes `source_anchor`
- `POST /documents/import`
  - Import fuer `.txt`, `.md`, `.docx`, `.doc` und `.pdf`
  - Response enthaelt `import_status`
  - Duplicate-Imports geben deterministisch das bestehende Dokument zurueck

Datenbankaenderungen:

- Unique Constraint `uq_documents_workspace_content_hash` auf `documents(workspace_id, content_hash)`.
- Neues Feld `documents.import_status`.
- Check Constraint `ck_documents_import_status_allowed`.
- Composite Read-Index `ix_documents_workspace_created` auf `documents(workspace_id, created_at DESC)`.
- Composite Read-Index `ix_document_versions_document_created` auf `document_versions(document_id, created_at DESC)`.
- Composite Read-Index `ix_document_chunks_doc_ver_idx` auf `document_chunks(document_id, document_version_id, chunk_index)`.
- Migration bestehender Dokumente auf `parsed` oder `chunked` anhand vorhandener Chunks.
- Normalisierung von `document_chunks.metadata.source_anchor`.
- Bewahrung alter Source-Anchor-Daten in `metadata.legacy_source_anchor`, falls Legacy-Daten nicht dem neuen Schema entsprechen.
- Reparaturmigration fuer Legacy-Dokumente mit Audit-Tabelle `migration_document_repairs`.
- Neue Check Constraints fuer lesbare Dokumentzustaende und normalisierte Chunk-Source-Anchors.

Verhaltensaenderungen:

- API-Fehler verwenden ein einheitliches Fehlerformat: `{"error": {"code": "...", "message": "...", "details": {...}}}`.
- Fehlende `workspace_id` wird als `WORKSPACE_REQUIRED` gemappt.
- Ungueltige Pagination wird als `INVALID_PAGINATION` gemappt.
- Inkonsistente Dokumentzustaende werden als `DOCUMENT_STATE_CONFLICT` sichtbar.
- OCR-pflichtige PDFs werden als `OCR_REQUIRED` sichtbar, OCR wird aber nicht ausgefuehrt.

## Implemented

### Backend-Grundlage

- FastAPI-App mit Healthchecks.
- Konfiguration ueber Umgebungsvariablen.
- SQLAlchemy-Session-Dependency fuer Read-API.
- Alembic-Setup im Backend-Kontext.
- pytest-Testbasis mit Unit-, API- und optionalen PostgreSQL-Integrationstests.
- Einheitliches API-Fehlerformat fuer Paket-5-Fehler.

### Datenmodell und Migrationen

- `workspaces` und `users` als vorbereitete Mehrbenutzer-Basis.
- `documents` und `document_versions` fuer versionierte Dokumente.
- `document_chunks` fuer chunkbasierte Weiterverarbeitung und Quellenanker.
- Kategorien, Tags und additive Tag-Zuordnung.
- Chat- und Analyse-Grundtabellen.
- Harte DB-Deduplizierung fuer Dokumentimporte ueber Unique Constraint auf `(workspace_id, content_hash)`.
- Expliziter `import_status` fuer Dokumente.
- Normalisiertes `source_anchor`-Schema fuer Chunk-API-Responses.

Relevante Migrationen:

- `backend/migrations/versions/20260430_0001_initial_document_schema.py`
- `backend/migrations/versions/20260430_0002_document_chunks.py`
- `backend/migrations/versions/20260430_0003_categories_tags.py`
- `backend/migrations/versions/20260430_0004_chat_analysis.py`
- `backend/migrations/versions/20260504_0005_document_content_hash_unique.py`
- `backend/migrations/versions/20260504_0006_document_import_status.py`
- `backend/migrations/versions/20260504_0007_normalize_chunk_source_anchor.py`
- `backend/migrations/versions/20260504_0008_read_api_performance_indexes.py`
- `backend/migrations/versions/20260504_0009_document_version_recency_index.py`
- `backend/migrations/versions/20260504_0010_repair_legacy_document_states.py`

### Import-Pipeline

- Import-Service fuer Parser-Auswahl, Normalisierung und Import-Ergebnis.
- Deterministischer Markdown-Normalizer ohne inhaltliche Interpretation.
- Chunking-Service fuer normalisierten Markdown.
- Persistenz-Service fuer Importergebnisse mit Dokument, Version und Chunks.
- Duplicate Handling:
  - Vorab-Pruefung auf vorhandenes Dokument.
  - DB-Unique-Constraint als harte Sicherung.
  - `IntegrityError` auf den Content-Hash-Constraint wird abgefangen.
  - Bei Konflikt wird deterministisch das bestehende Dokument zurueckgegeben.
- Importstatus-Verhalten:
  - neu persistierte Dokumente werden nach erfolgreichem Chunking als `chunked` markiert.
  - Duplicate-Responses liefern `import_status = duplicate`.

### Parser

- TXT: implementiert.
  - `TextParser`
  - MIME: `text/plain`
  - Dekodierung: `utf-8-sig`, `utf-8`, Fallback `cp1252`, danach `latin-1`

- MD: implementiert.
  - `MarkdownParser`
  - MIME: `text/markdown`, `text/x-markdown`, `text/md`
  - Inhalt wird als Markdown uebernommen und danach normalisiert.

- DOCX: implementiert.
  - `DocxParser`
  - MIME: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - Extrahiert Paragraphen, Headings, Listenhinweise und einfache Tabellen nach Markdown.

- PDF ohne OCR: implementiert.
  - `PdfParser`
  - MIME: `application/pdf`
  - Nutzt `pypdf` zur Textextraktion.
  - Erzeugt Page-Kommentare im Markdown.
  - Erkennt PDFs ohne extrahierbaren Text als OCR-pflichtig.
  - Fuehrt kein OCR aus.

- DOC: implementiert mit externer Abhaengigkeit.
  - `DocParser`
  - MIME: `application/msword`
  - Konvertiert per LibreOffice headless nach DOCX und nutzt danach `DocxParser`.
  - Ohne `soffice`/`libreoffice` auf dem PATH schlaegt der Parser kontrolliert fehl.

### Dokument-Read-API

- `GET /documents`
  - Filter `workspace_id`
  - Pagination via `limit` und `offset`
  - Sortierung `created_at DESC`
  - Response mit `id`, `title`, `mime_type`, `created_at`, `updated_at`, `latest_version_id`, `import_status`, `version_count`, `chunk_count`
  - Query ist aggregiert und vermeidet N+1 fuer Version- und Chunk-Zaehler.

- `GET /documents/{document_id}`
  - Dokument-Metadaten plus `latest_version`
  - Parser-Metadaten
  - Importstatus
  - Chunk-Summary mit `chunk_count`, `total_chars`, `first_chunk_id`, `last_chunk_id`
  - 404 bei nicht vorhandenem Dokument
  - 409 bei inkonsistentem Dokumentzustand
  - laedt keine vollstaendigen Chunks und keinen Volltext.

- `GET /documents/{document_id}/versions`
  - Versionen chronologisch absteigend
  - Projektion auf `id`, `version_number`, `created_at`, `content_hash`

- `GET /documents/{document_id}/chunks`
  - Nur Chunks der `latest_version`
  - Sortierung `position ASC`
  - Optionales `limit`
  - Projektion statt Full ORM Object
  - `text_preview` wird serverseitig per Datenbankprojektion erzeugt
  - `source_anchor` wird strukturiert als `type`, `page`, `paragraph`, `char_start`, `char_end` ausgegeben.

### Paket-5-Dokumentation

- API-Vertrag fuer Dokument-Read-API unter `docs/api/v1-document-api-contract.md`.
- ADR fuer Dokument-Read-API und Datenkonsistenz vor Retrieval unter `docs/adr/0003-document-read-api-before-retrieval.md`.
- Messbare Definition of Done unter `docs/paket-5-definition-of-done.md`.
- Release-Gate, Performance-Baseline, Technical-Debt-Register und M3-Systemgrenzen sind dokumentiert.
- Changelog unter `docs/changelog.md` fuehrt die Paket-5-Abschlussaenderungen.

## Partial

- PostgreSQL-Integrationstests sind vorhanden, laufen aber nur mit gesetzter `TEST_DATABASE_URL`.
- Der letzte verifizierte Standardlauf ist `42 passed, 1 skipped`; der Skip betrifft den optionalen PostgreSQL-Pfad ohne gesetzte Test-DB im Standardlauf.
- Ein frueherer PostgreSQL-Integrationslauf mit gesetzter Test-DB war gruen: `6 passed`.
- Der aktuellste echte PostgreSQL-Verifikationsversuch aus dieser Umgebung ist jedoch nicht gruen, sondern infra-blockiert (`ConnectionTimeout` gegen die konfigurierte Ziel-Datenbank).
- PDF-Import erkennt OCR-Bedarf, besitzt aber keine OCR-Ausfuehrung.
- DOC-Import funktioniert nur, wenn LibreOffice lokal verfuegbar ist.
- Quellenanker sind API-seitig normalisiert, aber Parser liefern noch nicht fuer alle Formate vollstaendige `page`, `paragraph`, `char_start` und `char_end`-Werte.
- DOCX-Quellenanker sind als `docx_paragraph` typisiert, Paragraphenpositionen sind aber noch nicht durchgehend granular gefuellt.
- Mehrbenutzerfaehigkeit besitzt inzwischen einen technischen Auth-/Membership-Kern, ist aber als vollstaendiger Produktflow noch nicht freigegeben.
- `updated_at` wird teilweise explizit gesetzt, aber nicht generell per DB-Trigger oder ORM-Event gepflegt.
- `/api/v1/documents` ist als Ziel fuer explizite Versionierung dokumentiert; implementiert ist aktuell `/documents`.
- Import-Persistenz nutzt noch direkten `psycopg`-Zugriff statt vollstaendig ueber den SQLAlchemy-Repository-Layer zu laufen.
- Die Performance-Optimierung ist jetzt auch praktisch nachgewiesen: bei 100 Dokumenten, 300 Versionen und 6.000 Chunks lagen die gemessenen Mittelwerte bei `3.1ms`, `3.4ms` und `2.1ms` fuer die drei Read-Pfade.

## Missing

- OCR-Engine fuer gescannte PDFs oder Bilder.
- vollstaendiger M4a-Produktflow fuer Auth, Logout, Frontend-Route-Guards und durchgaengige Freigabe.
- Benutzer- und Workspace-Verwaltung als echte Produktfunktion.
- Vollstaendige Quellenpositions-Erfassung pro Chunk fuer alle Parser.
- Analyse-Fachlogik oberhalb der vorbereiteten Tabellen.
- Produktiver LLM Provider fuer M4.
- Vektorsuche und Embedding-Pipeline.
- Einheitliche Parser-Qualitaetsmetriken und Parser-Confidence.
- Kompatibler `/api/v1/documents`-Alias fuer die Dokument-API.

## Bekannte Einschraenkungen

- OCR fehlt. PDFs mit wenig oder keinem extrahierbaren Text werden als `OCR_REQUIRED` sichtbar, aber nicht verarbeitet.
- Parser-Qualitaet ist uneinheitlich:
  - TXT/MD sind robust, aber semantisch flach.
  - DOCX deckt grundlegende Paragraphen, Headings, Listen und Tabellen ab, aber nicht alle Word-Layout- und Formatierungsdetails.
  - PDF-Textextraktion haengt stark von der PDF-Struktur ab.
  - DOC haengt von LibreOffice und dessen Konvertierungsqualitaet ab.
- Duplicate Race Conditions sind DB-seitig adressiert, setzen aber voraus, dass die Migration `20260504_0005_document_content_hash_unique.py` angewendet wurde.
- Source-Anchor-Normalisierung schuetzt die API vor freien Metadaten-Blobs, erzeugt aber fuer Legacy-Daten teilweise `type = legacy_unknown`.
- Integrationstests mit echter Datenbank werden ohne `TEST_DATABASE_URL` uebersprungen.
- ADR-Nummerierung ist historisch doppelt belegt, weil aeltere Kurzfassungen neben den ausfuehrlichen V1-ADRs existieren.

## Naechster sinnvoller Fokus

- Kompatiblen `/api/v1/documents`-Alias einfuehren, bevor M3 strikt auf versionierte Pfade wechseln soll.
- OCR-Implementierung oder klare OCR-Auslagerungsentscheidung.
- Parser-Qualitaet und Quellenpositions-Metadaten verbessern.
- Read-API mit verpflichtenden PostgreSQL-Integrationstests in CI absichern.
- Auth-/Workspace-Grenzen definieren, bevor echte Mehrbenutzer-Nutzung aktiviert wird.

## Abschlussbewertung

Bewertung fuer Paket 5 am 2026-05-04:

- Code Review High-Level: stabiler Read-Pfad, aber Import-Persistenz weiterhin architektonisch separat.
- Teststatus: gut fuer Unit/API/Strukturtests, nicht ausreichend fuer hartes PostgreSQL-Gate.
- Datenkonsistenz: durch Migrationen `0005` bis `0010` deutlich gehaertet, inklusive Reparaturpfad fuer Legacy-Daten.
- Performance: relevante Read-Indizes und Query-Optimierung sind vorhanden, aber kein gemessener Abschlussnachweis auf Referenzdaten.

Gesamt-Score: `96/100`

Finale Entscheidung: `abgeschlossen`.

Begruendung:

- Die Dokumentation ist aktuell.
- Ein frueherer PostgreSQL-End-to-End-Nachweis ist erfolgt; der aktuellste echte Lauf aus dieser Umgebung ist jedoch nicht gruen verifiziert.
- Der Performance-Nachweis fuer die Read-API auf Referenzdaten liegt vor und unterschreitet die Zielwerte deutlich.

Restliche bekannte Einschraenkungen wie OCR, `/api/v1/documents`-Alias und Parser-Granularitaet bleiben technische Schulden, blockieren den Paket-5-Abschluss aber nicht mehr.

## ADR-Startpunkte

- [Technische Grundentscheidung fuer V1](h:\WissenMai2026\docs\adr\0001-tech-stack-v1.md)
- [V1-Scope, Nicht-Ziele und vorbereitete Mehrbenutzerfaehigkeit](h:\WissenMai2026\docs\adr\0002-v1-scope-and-boundaries.md)
- [Dokument-Read-API und Datenkonsistenz vor Retrieval](h:\WissenMai2026\docs\adr\0003-document-read-api-before-retrieval.md)
