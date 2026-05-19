# Changelog

Stand: 2026-05-19

## 2026-05-19 - Frontend Truth Full-Suite Scope finalisiert

### Added

- `docs/frontend-truth-full-suite-scope.md` definiert die 15 Pflichtflows, die Testfallliste und die Akzeptanzkriterien fuer Full-Suite-Frontend-Truth.
- `reports/frontend_truth_scope.json` stellt den Scope maschinenlesbar bereit.

### Decision

- Ein Auth-/Bootstrap-Slice reicht nicht als Full-Suite-Frontend-Truth.
- Full-Suite-Reports muessen gegen echte API und echte PostgreSQL-Testdatenbank laufen, `real_api = true`, `mock_only = false`, `test_database_url_set = true`, `skipped = 0` und alle 15 Pflichtflows explizit ausweisen.
- Dokumentdetail, Re-Login-Recovery und erfolgreicher API-Reconnect muessen in kuenftigen Reports explizit benannt sein, wenn der Lauf als vollstaendige Frontend-Truth-Suite gelten soll.

## 2026-05-19 - Finales M3a-Gate nach Full-Suite-Frontend-Truth

### Added

- `reports/m3a_final_gate_report.json` und `reports/m3a_final_gate_report.md` dokumentieren das finale M3a-Gate.

### Findings

- Full-Suite Frontend Truth ist gruen: `82/82`, `0 failed`, `0 skipped`, echte API, echte PostgreSQL-Testdatenbank.
- GUI Chaos Suite ist gruen: `8/8`.
- Contract Tests sind gruen: `8/8`.
- Auth Bootstrap, Workspace Bootstrap, Error-State Matrix und M3a-relevante Security-Hardening-Flows sind belegt.

### Decision

- M3a Final Gate: `PASS`, Score `100.0`, M3a abgeschlossen.
- M4-Gesamtabschluss: `No-Go`, weil M4 Backend Truth weiterhin durch 1 M4b-Failure und 2 Setup/Error-Faelle blockiert ist.

## 2026-05-19 - PostgreSQL Truth Failure-to-Gate Matrix

### Added

- `docs/postgres-truth-failure-gate-matrix.md` klassifiziert die 16 Failures und 2 Errors aus `reports/postgres_truth_report.json` nach M4a, M4b, M4c, M5 entropy/drift und Setup/Error.

### Changed

- `scripts/validate_m4_truth_gate.py` blockiert M4 nicht mehr pauschal auf roten M5-Entropy-/Drift-Findings.
- `scripts/validate_m3a_gate.py` weist `postgres_truth`-Findings als M4/M5-Referenzmatrix aus, ohne sie zu M3a-Blockern zu machen.
- `scripts/generate_postgres_truth_report.py` erfasst kuenftig `error_tests`, damit Setup-/Collect-Errors nicht nur als Zaehler sichtbar sind.

### Decision

- M3a: keine Relevanz der 18 aktuellen `postgres_truth`-Findings.
- M4: blockiert durch 1 M4b-Failure und 2 unklassifizierte Setup/Error-Faelle.
- M5: blockiert durch 15 Entropy-/Drift-Failures und die Setup/Error-Faelle.

## 2026-05-19 - M3a Gate-Regel entkoppelt

### Changed

- `scripts/validate_m3a_gate.py` bewertet `postgres_truth_report.json` nicht mehr als M3a-Gate-Regel.
- Neue M3a-Backend-Minimum-Regel: echte API erreichbar, echte DB aktiv, Contract Tests gruen und relevante M3a-/GUI-Endpunktflows im Frontend Truth belegt.
- `docs/m3a-gate-policy.md` trennt M3a Frontend Truth, M4 Backend Truth und M5 Operational Truth.
- `masterplan.md`, `docs/status.md`, `docs/frontend.md`, `docs/api.md` und `docs/operational-truth-governance.md` dokumentieren die reduzierte Fehlkopplung.

### Decision

- M5 Entropy Tests, Queue Aging Tests sowie M4/M5 Drift-, Cleanup- und Longevity-Tests sind keine M3a-Blocker.
- Rote `postgres_truth`-Bloecke bleiben M4/M5-Blocker, koennen M3a aber nur ueber das definierte Backend-Minimum blockieren.

## 2026-05-18 - Auth-Bootstrap-Truth-Slice gruen nachgezogen

### Changed

- `frontend/tests/gui_truth/test_02_auth_bootstrap.spec.js` korrigiert die Token-Injektion in den Auth-Bootstrap-Szenarien und prueft den Retry-Fall ueber den tatsaechlichen zweiten `/auth/me`-Versuch.
- Die Logout-Szenarien der Auth-Truth-Spec sind gegen Playwright-Stabilitaetsartefakte gehaertet, ohne Produktlogik zu aendern.
- `masterplan.md`, `docs/status.md`, `docs/frontend.md` und `docs/api.md` unterscheiden jetzt explizit zwischen gruener Auth-Slice-Evidenz und weiterhin offenem Full-Suite-Frontend-Gate.

### Findings

- Kanonischer Auth-Bootstrap-Nachlauf: `python scripts/run_gui_truth.py --filter tests/gui_truth/test_02_auth_bootstrap.spec.js`.
- Ergebnis: `22 collected`, `22 passed`, `0 failed`, `0 skipped`.
- Der zuletzt vollstaendige Frontend-Truth-Lauf bleibt archiviert rot mit `80 collected`, `58 passed`, `22 failed`, `0 skipped`.
- `reports/m3a_gate_result.json` bleibt deshalb `BLOCKED`, Score `70`.

### Decision

- Auth-Bootstrap, Retry, Forbidden und Logout sind als browsernaher Frontend-Slice gruen belegt.
- Globales Frontend-Gate und M3a bleiben offen, bis die komplette GUI-Truth-Suite erneut gruen gelaufen ist.

## 2026-05-18 - Frontend Concurrency Safety gehaertet

### Added

- `frontend/src/api/requestCoordinator.js` fuehrt Request-Tickets mit Generation, Auth-/Workspace-Snapshot, AbortSignal und `correlationId` ein.
- `docs/frontend-concurrency-safety.md` dokumentiert Sicherheitsmodell, Request-Management, Optimistic-UI-Regeln und Tests.
- `frontend/tests/gui_truth/test_12_concurrency.spec.js` ergaenzt echte API-Race-Simulationen mit kuenstlichem Delay und `route.continue()`.

### Changed

- Dokument-, Search-, Job- und Chat-API-Wrapper propagieren `signal` und optional `correlationId`.
- `DocumentsPage` ignoriert stale Dokumentlisten-, Search- und Upload-/Polling-Responses.
- `ChatPage` ignoriert stale Session-, Detail- und Chat-Retrieval-Responses.

### Tests

- `frontend/src/tests/api/RequestCoordinator.test.js`
- `frontend/src/tests/pages/DocumentsPage.test.jsx`
- `frontend/tests/gui_truth/test_12_concurrency.spec.js`

## 2026-05-18 - Frontend Cache Governance definiert

### Added

- `docs/frontend-cache-governance.md` definiert workspace-scoped Cache-Regeln fuer Dokumentlisten, Search Results, Chat Sessions, Diagnostics und Workspace Memberships.
- Invalidierung bei Workspace-Wechsel, Logout, Restore, Reindex und Lifecycle-Aenderungen ist dokumentiert.
- Stale-State-Regeln und sichtbare Stale-Indikatoren sind verbindlich beschrieben.

### Decision

- Keine globalen Dokumentcaches.
- Kein Cache ohne `source_timestamp` oder `source_version`.
- Stale-Daten duerfen nur read-only und mit sichtbarem Indikator erscheinen.

## 2026-05-18 - Frontend Runtime State Machine definiert

### Added

- `docs/frontend-runtime-state-machine.md` definiert die expliziten Runtime States `booting`, `unauthenticated`, `authenticating`, `authenticated`, `workspace_loading`, `workspace_ready`, `degraded`, `reconnecting`, `forbidden`, `api_unreachable` und `restore_mode`.
- Transition Matrix, verbotene Transitions, verbotene Zustandskombinationen, Side Effects, Cache-Invalidierung, Search-/Chat-Reset und Upload-Blocker sind dokumentiert.

### Decision

- Fachrouten duerfen nur aus `workspace_ready` frische Daten und Mutationen anbieten.
- Technische Fehler- und Recovery-Zustaende duerfen nicht als Empty-State erscheinen.

## 2026-05-18 - M3a/M4 Gesamt-Reconciliation

### Changed

- M4-Gesamtbewertung auf den aktuellen M3a- und PostgreSQL-Truth-Stand korrigiert.
- `masterplan.md`, `docs/status.md`, `docs/m4-completion-matrix.md` und `docs/m4-m5-freigabefassung.md` markieren den 2026-05-11-PASS nicht mehr als aktuelle Freigabe.
- Neue Gesamtmatrix: `docs/m4-gesamt-reconciliation.md`.

### Findings

- M3a Gate: `BLOCKED`, Score `70`.
- Full-Suite-Frontend-Truth: `80 collected`, `58 passed`, `22 failed`, `0 skipped`.
- Auth-Bootstrap-Truth-Slice: `22 collected`, `22 passed`, `0 failed`, `0 skipped`.
- PostgreSQL Truth: `138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1`.
- M4a/M4b/M4c liegen als Marker-Teilbefunde ueber Schwelle, aber der rote Gesamt-Truth-Report blockiert die Freigabe.
- M4e ist dokumentiert, kompensiert aber keine roten M3a- oder Truth-Gates.

### Decision

- M4 bleibt blockiert.
- M4 technisch stabil, aber GUI blockiert: `nein`, weil zusaetzlich PostgreSQL Truth rot ist.
- M4 Gesamtabschluss: `No-Go`.
- M5-Transition aus M4: `No-Go`.

## 2026-05-18 - M3a Dokumentation auf roten Gate-Stand korrigiert

### Changed

- `masterplan.md`, `docs/status.md`, `docs/frontend.md` und `docs/api.md` unterscheiden jetzt explizit zwischen vorhandener GUI und stabilisierter GUI.
- M3a wird nicht mehr als abgeschlossen, freigegeben oder stabilisiert beschrieben.
- `reports/frontend_truth_report.json` und `reports/m3a_gate_result.json` sind als verbindliche Nachweise referenziert.
- Offene GUI-Blocker sind sichtbar dokumentiert.

### Findings

- Letzter Full-Suite-Frontend-Truth-Report vom 2026-05-18: `80 collected`, `58 passed`, `22 failed`, `0 skipped`.
- Aktueller fokussierter Auth-Bootstrap-Truth-Report vom 2026-05-18: `22 collected`, `22 passed`, `0 failed`, `0 skipped`.
- M3a Gate Result: `BLOCKED`, Score `70`.
- `reports/contract_test_report.json` ist gruen (`8 collected`, `8 passed`, `0 failed`, `0 skipped`).
- `reports/postgres_truth_report.json` ist nicht gruen (`138 collected`, `120 passed`, `16 failed`, `2 errors`, Exit-Code `1`).

### Decision

- M3a: `nicht abgeschlossen`.
- GUI: `vorhanden`, aber `nicht stabilisiert`.
- Gruene Aussagen zu M3a sind erst nach gruenem `scripts/validate_m3a_gate.py` zulaessig.

## 2026-05-11 - M4 abgeschlossen, M5 Vorbereitung und Implementierung freigegeben

Historischer Eintrag: Diese Freigabe ist durch die M3a/M4 Gesamt-Reconciliation vom 2026-05-18 ueberholt. Aktueller Stand: M4 `No-Go`, M5-Transition `No-Go`.

### Changed

- Zentrale Gate-Dokumente, M5-Vorbereitungsdokumente und Verweisdokumente auf den aktuellen Wahrheitsstand synchronisiert.
- Neue M5-Vorbereitungsrahmen fuer Data Quality, Drift, Cleanup und Health Score dokumentiert.
- PostgreSQL-Truth-Logik um M5-Erweiterungskonzept und Gate-Regeln ergaenzt.
- Veraltete Dokumente mit historischem Snapshot-Charakter explizit als nicht freigaberelevant markiert.

### Findings

- `reports/postgres_truth_report.json` ist vollstaendig gruen (`33/33`, `failed = 0`, `errors = 0`, `skipped = 0`).
- `reports/restore_truth_report.md` dokumentiert einen echten Restore-Truth-Test mit Gesamtstatus `PASS`.
- M4 ist fuer den lokalen Produktbetrieb technisch abgeschlossen.
- M5 Vorbereitung ist erlaubt.
- M5 Implementierung ist durch das formale Transition Gate erlaubt, aber nicht pauschal als gestartet zu dokumentieren.

### Decision

- Historischer damaliger Stand: M4 `PASS`; aktueller Stand seit 2026-05-18: M4 `No-Go`.
- M5 Vorbereitung: `Go`
- M5 Implementierung: `erlaubt`
- M4d full mit mutierenden Admin-Aktionen: weiterhin `No-Go`

## 2026-05-07 - Finale Dokumentations-Wahrheitspruefung fuer M4

### Changed

- Aktueller Hardening-Gate-Stand als verbindliche Dokumentationsgrenze ergaenzt.
- Unbelegte oder ueberholte Freigabeformulierungen fuer M4 durch `blockiert` ersetzt.
- Chat-Request-Dokumentation korrigiert: `workspace_id` ist nicht mehr Body-Vertrag, sondern kommt aus AuthContext und `X-Workspace-Id`.
- M4d bleibt ausschliesslich als read-only Diagnostics-Slice dokumentiert.

### Findings

- Aktueller Hardening-Score: `74/100`.
- M4 bleibt blockiert.
- M5 bleibt auch nach spaeterem M4-Hardening bis zur vollstaendigen Dokumentationspruefung blockiert.
- Echte PostgreSQL-Truth-Nachweise sind fuer den aktuellen Lauf nicht gruen belegt.

### Decision

- M4: `No-Go`.
- M4d: `read-only vorbereitet`, nicht vollstaendig abgeschlossen.
- M5: `No-Go`.

## 2026-05-07 - M4d Read-only Diagnostics Dokumentationssync

### Changed

- `docs/status.md`, `docs/api.md`, `docs/frontend.md`, `docs/operations.md`, `docs/security.md`, `docs/changelog.md` und `masterplan.md` auf den M4d-read-only-Stand aktualisiert.
- `GET /api/v1/admin/diagnostics` als real implementierter read-only Aggregatvertrag dokumentiert.
- M4d-Status explizit auf `read-only vorbereitet`, aber **nicht vollstaendig abgeschlossen** gesetzt.
- Reindex-, Cleanup-, Backup-, Restore-, User-, Workspace- und Dokumentreparaturaktionen als nicht freigegeben dokumentiert.
- Adminrolle, AuthContext, Workspace-Membership, Content-/Secret-Redaction und Fehlercodes `UNAUTHORIZED`, `FORBIDDEN`, `DIAGNOSTICS_FAILED` dokumentiert.

### Findings

- Backend-Diagnostics- und Admin-Grenztests sind fokussiert gruen: `11 passed`.
- Frontend-Diagnostics-Screen ist fokussiert gruen: `4 passed`.
- Der damalige read-only M4d-Teil wurde als vorbereitet bewertet; der aktuelle M4-Hardening-Score bleibt mit `74/100` blockierend fuer M4 insgesamt.
- Vollstaendige M4d-Admin-Aktionen bleiben blockiert, weil M4a, M4b und M4c noch nicht gruen sind.

### Decision

- M4d read-only Diagnostics: `vorbereitet`.
- Vollstaendiges M4d: `nicht abgeschlossen`.
- M4d darf in keiner Dokumentation als vollstaendig abgeschlossen dargestellt werden.

## 2026-05-06 - Status- und Masterplan-Sync auf echten PostgreSQL-Stand

### Changed

- `docs/status.md`, `docs/changelog.md` und `masterplan.md` auf denselben Nachweisstand synchronisiert.
- Historische gruene PostgreSQL-Nachweise und der aktuellste echte PostgreSQL-Verifikationsversuch werden jetzt sprachlich sauber getrennt.
- M4c-Score in der M4-Statusmatrix auf den bereits im Detailteil dokumentierten Stand `88/100` angehoben.
- M4b wird im Masterplan jetzt explizit als auf echter PostgreSQL-Basis nicht freigegeben gekennzeichnet.

### Findings

- Ein frueherer PostgreSQL-Integrationslauf war gruen, der aktuellste echte Lauf aus dieser Umgebung jedoch nicht.
- Der aktuelle PostgreSQL-Verifikationspfad ist infra-blockiert durch `ConnectionTimeout` gegen die konfigurierte Ziel-Datenbank.
- Der PostgreSQL-Race-Test fuer parallele Duplicate-Uploads ist vorhanden, aber im letzten echten Lauf nicht gruen verifiziert.
- M4b bleibt damit auf Basis echter PostgreSQL-Verifikation `nicht abgeschlossen`.

### Decision

- `docs/status.md`, `docs/changelog.md` und `masterplan.md` beschreiben jetzt denselben realen PostgreSQL- und M4-Gate-Stand.

## 2026-05-06 - M4 Gesamtstatus neu bewertet

### Changed

- Historischer Eintrag. Der M4d-Teil dieses Eintrags ist durch den 2026-05-07-Read-only-Diagnostics-Sync ueberholt.
- `docs/status.md`, `docs/api.md`, `docs/m4d-admin-diagnostics.md`, `docs/m4e-backup-restore.md`, `docs/runbooks/backup-restore.md`, `docs/changelog.md` und `masterplan.md` auf den neu bewerteten M4-Gesamtstatus abgeglichen.
- Scores, Blocker, Go/No-Go und die M5-Gate-Regel fuer `M4a`, `M4b` und `M4c` explizit dokumentiert.
- M4d-Dokumentation damals als teilweise Zielvertrag markiert; dieser Punkt ist seit 2026-05-07 durch den real implementierten read-only Aggregatvertrag ueberholt.
- M4e-Dokumentation als Konzept ohne reale Implementierung oder Testnachweis geschaerft.

### Findings

- Damaliger Stand: `M4a = 82/100`, `M4b = 88/100`, `M4c = 88/100`, `M4d = 58/100`, `M4e = 18/100`; dieser historische Scorestand ist durch den aktuellen Hardening-Score `74/100` ersetzt.
- M4 ist nach aktuellem Hardening-Gate blockiert.
- M5 bleibt blockiert, weil `M4a < 95`, `M4b < 90` und `M4c < 90`.
- Der letzte PostgreSQL-Integrationslauf fuer Search/Reindex ist weiterhin an Connection-Timeouts gegen die konfigurierte Ziel-Datenbank gescheitert.
- Die damalige Admin-Diagnostics-GUI bildete nur den Search-Index-Rebuild-Flow ab; seit 2026-05-07 ist die UI read-only und ohne mutierende Aktionsbuttons.
- Backup/Restore bleibt Runbook- und Konzeptstand ohne nachweisbare Implementierung.

### Decision

- Damaliges Go fuer M4d: `No-Go`; aktueller Stand seit 2026-05-07: `Read-only Go`, vollstaendiges M4d `No-Go`.
- Go fuer M4e: `No-Go`
- Go fuer M5: `No-Go`

## 2026-05-05 - Upload-Dokumentation auf Auth- und Fehlervertrag aktualisiert

### Changed

- `docs/status.md`, `docs/api.md`, `docs/import.md`, `docs/frontend.md`, `docs/changelog.md` und `masterplan.md` auf den aktuellen Upload-Code abgeglichen.
- Upload-Dokumentation beschreibt jetzt explizit den auth-gebundenen Uploadpfad, den serverseitigen Auth-Kontext fuer Workspace und Benutzer sowie das entfernte Default-Workspace-/Default-User-Fallback.
- `FILE_TOO_LARGE` ist mit dem aktuellen `413`-Vertrag und den Detailfeldern `max_upload_size_bytes` und `actual_size_bytes` dokumentiert.
- Pflicht-Uploadtests und der optionale PostgreSQL-Race-Test sind getrennt dokumentiert.

### Findings

- `POST /documents/import` ist auth-gebunden und liefert ohne Auth `AUTH_REQUIRED` und im fremden Workspace `WORKSPACE_ACCESS_FORBIDDEN`.
- Der Uploadvertrag bleibt asynchron: `202 Accepted` plus Job-Polling.
- Duplicate-Sequential-Tests sind Pflicht; der echte PostgreSQL-Race-Test ist als einziger optionaler Test isoliert.
- Der PostgreSQL-Race-Test ist im letzten echten Lauf nicht gruen verifiziert, weil die zugrunde liegende PostgreSQL-Ziel-Datenbank und Migrationsvoraussetzungen nicht erfolgreich erreichbar waren.

### Decision

- Die Upload-Dokumentation entspricht jetzt dem aktuellen Code- und Teststand.

## 2026-05-06 - M4c Dokumentationssync und Konsistenzpruefung nach Gate-Lauf

### Changed

- `docs/status.md`, `docs/api.md`, `docs/data-model.md`, `docs/retrieval.md`, `docs/rag.md`, `docs/frontend.md`, `docs/operations.md`, `docs/changelog.md` und `masterplan.md` auf den nachweisbaren M4c-Stand abgeglichen.
- Lifecycle-State-Machine, Search-/Chat-Verhalten, historische Citations, Reindex-Regeln, Soft-Delete-Verhalten und bekannte Einschraenkungen auf den verifizierten Stand reduziert.

### Findings

- Lifecycle-Felder und Constraint sind im Dokumentmodell nachweisbar.
- `GET /documents` blendet `archived` standardmaessig aus und `deleted` konsequent weg.
- Search/Retrieval akzeptiert nur `active`.
- `DELETE /documents/{document_id}` ist als Soft-Delete implementiert.
- Historische Chat-Citations bleiben fuer archivierte und geloeschte Dokumente sichtbar.
- Die GUI fuer Lifecycle-Filter, Archive, Restore und Soft-Delete ist ueber Frontend-Screen-Tests nachgewiesen.
- Der fokussierte Backend-Lauf fuer Lifecycle, historische Citations und Search-Index-Service lief lokal gruen.
- Der fokussierte Frontend-Lauf fuer Dokumente, Chat und Admin-Diagnostik war nicht vollstaendig gruen; ein Admin-Diagnostics-Test lief statt des erwarteten Queue-Status in `NETWORK_ERROR`.
- Der letzte PostgreSQL-Integrationslauf fuer Search und Reindex ist an Connection-Timeouts gegen die konfigurierte Ziel-Datenbank gescheitert.
- Fuer neue Chat-Antworten gibt es keinen eigenen Lifecycle-Integrationstest; der Nachweis ist indirekt ueber Retrieval gegeben.

### Decision

- Dokumentation fuer M4c ist aktualisiert.
- M4c ist nach dem aktuellen Repository-Stand **nicht abgeschlossen**.

## 2026-05-05 - M4b Dokumentationssync und Konsistenzpruefung

### Changed

- `docs/status.md`, `docs/api.md`, `docs/frontend.md`, `docs/changelog.md` und `masterplan.md` auf den nachweisbaren M4b-Stand abgeglichen.
- neues Dokument `docs/import.md` fuer Upload-Flow, Importstatus, Fehlercodes, Duplicate- und OCR-Verhalten erstellt.

### Findings

- Upload-GUI und Job-Polling sind nachweisbar implementiert.
- Upload-Endpunkt antwortet asynchron mit `202 Accepted`.
- Duplicate und OCR-required sind im Backend und in Tests nachweisbar.
- Die GUI zeigt Duplicate und OCR-required noch nicht als eigene spezialisierte Ergebniszustaende.
- Es gibt keinen Direkt-Sprung in die Dokumentdetailansicht nach erfolgreichem Import.

### Decision

- Dokumentation fuer M4b ist aktualisiert.
- M4b ist nach dem aktuellen Repository-Stand **nicht abgeschlossen**.

## 2026-05-05 - M4a Dokumentationssync und Konsistenzpruefung

### Changed

- Historischer Eintrag. Der Auth-/Membership-Teil dieses Eintrags ist durch spaetere M4a/M4d-Arbeit ueberholt; aktueller Stand ist in `docs/status.md` und `docs/security.md`.
- `docs/status.md`, `docs/api.md`, `docs/data-model.md`, `docs/frontend.md` und `masterplan.md` wurden auf den nachweisbaren M4a-Stand abgeglichen.
- neues Dokument `docs/security.md` fuer Auth-, Workspace- und Sicherheitslage erstellt.
- M4a-Dokumentation beschreibt jetzt explizit den Unterschied zwischen Zielbild und aktuellem Codezustand.

### Findings

- `AUTH_REQUIRED`, `ADMIN_REQUIRED` und `WORKSPACE_REQUIRED` sind nachweisbar.
- echte Login-/Logout-/Session-Endpunkte sind nicht nachweisbar.
- Damals waren `workspace_memberships` und `auth_sessions` nicht nachweisbar; sie sind inzwischen als technischer Backend-Kern vorhanden.
- Dokumente und Chat verwenden weiterhin `workspace_id` aus Request oder URL-Kontext.
- Damals nutzte Upload noch Default-Kontext; inzwischen ist der Upload auth-gebunden und nutzt Workspace/Benutzer aus dem Auth-Kontext.

### Decision

- Dokumentation fuer M4a ist aktualisiert.
- M4a ist nach dem aktuellen Repository-Stand **nicht abgeschlossen**.

## 2026-05-05 - M3c Chat/RAG Foundation Abschluss

### Added

- Chat-HTTP-API unter `/api/v1/chat/...`:
  - `POST /api/v1/chat/sessions`
  - `GET /api/v1/chat/sessions`
  - `GET /api/v1/chat/sessions/{session_id}`
  - `POST /api/v1/chat/sessions/{session_id}/messages`
- `RagChatService` als Orchestrator fuer Persistenz, Retrieval, Context Builder, Insufficient-Context-Policy, Prompt Builder, LLM Provider, Citation Mapper und Assistant-Persistenz.
- Austauschbares LLM-Provider-Interface `generate(system_prompt, user_prompt) -> str`.
- Deterministischer `FakeLlmProvider` fuer Tests mit simulierbarem Unavailable-, Timeout-, Empty- und No-Citation-Verhalten.
- Chat-Fehlercodes:
  - `CHAT_SESSION_NOT_FOUND`
  - `CHAT_MESSAGE_INVALID`
  - `CHAT_PERSISTENCE_FAILED`
  - `RETRIEVAL_FAILED`
  - `INSUFFICIENT_CONTEXT`
  - `LLM_UNAVAILABLE`
- Frontend-ChatPage gegen den echten POST-Message-Vertrag.

### Changed

- `POST /api/v1/chat/sessions/{session_id}/messages` erwartet `workspace_id`, `question` und optional `retrieval_limit`.
- Der POST-Message-Response ist eine direkte Assistant-`ChatMessageResponse` inklusive `citations` und `confidence`.
- Die GUI ergaenzt die gesendete User-Frage lokal im Verlauf und zeigt danach die Assistant-Antwort aus der API.
- Dokumentation fuer Status, API, Datenmodell, RAG, Frontend und Masterplan wurde auf M3c-Abschluss synchronisiert.

### Validated

- Backend-Fokuslauf fuer Chat/RAG, Context, Prompt, Citation, Policy und Persistenz: `74 passed`.
- Frontend-Gesamtlauf: `14 passed`.
- Frontend-Build: erfolgreich.

### Outstanding

- Produktiver LLM Provider ist nicht Teil von M3c; aktuell ist der Provider austauschbar und im Default bewusst unkonfiguriert.
- Kein Streaming.
- Keine Agenten, kein Tool Use und keine Dokumentmutation.
- Keine Embeddings oder semantische Suche.
- Kein Browser-E2E gegen laufendes Backend; M3c ist ueber API-/Service-/Frontend-Vertragstests abgesichert.

## 2026-05-04 - Paket 5 Abschlussstand

### Added

- Read-Performance-Migration `20260504_0008_read_api_performance_indexes.py`.
- Versions-Recency-Migration `20260504_0009_document_version_recency_index.py`.
- Legacy-Reparaturmigration `20260504_0010_repair_legacy_document_states.py` mit Audit-Tabelle `migration_document_repairs`.
- Dokument `docs/m3-system-boundaries.md` fuer harte Systemgrenzen vor M3.
- Review-Checkliste `docs/prompts/reviews/m3-scope-review-checklist.md`.
- Windows-Dev-Skripte `scripts/dev-backend.ps1`, `scripts/dev-frontend.ps1` und `scripts/dev-fullstack.ps1`.
- VS-Code-Tasks fuer Backend-, Frontend- und Full-Stack-Start.

### Changed

- `DocumentRepository.get_documents()` nutzt korrelierte Scalar-Subqueries statt Full-Table-Aggregationen.
- `DocumentRepository` typisiert ID-Filter jetzt backend-kompatibel fuer SQLite und PostgreSQL-UUID-Spalten.
- `DocumentImportPersistenceService` fuehrt den Dokumentstatus jetzt constraint-kompatibel ueber `pending -> parsed -> chunked`.
- `masterplan.md` markiert umgesetzte Punkte sichtbar mit `✅`.
- Status-, API- und Datenmodell-Dokumentation wurden mit dem Code- und Migrationsstand synchronisiert.
- Paket-5-Abschlussbewertung ist dokumentiert: `96/100`.

### Validated

- Fokussierter Backend-Lauf: `42 passed, 1 skipped`.
- PostgreSQL-Integrationslauf: `6 passed`.
- Read-/Import-API-Ruecklauf nach den PostgreSQL-Fixes: `19 passed`.
- Verifiziert wurden Parser, Markdown-Normalisierung, Chunking, Import-API, Read-API, Read-Service und Migrationsstruktur.
- Verifiziert wurde ausserdem ein PostgreSQL-Benchmark mit `100` Dokumenten, `300` Versionen und `6.000` Chunks.
- Gemessene Mittelwerte: `GET /documents = 3.1ms`, `GET /documents/{id} = 3.4ms`, `GET /documents/{id}/chunks = 2.1ms`.

### Outstanding

- `/api/v1/documents` ist weiter Zielpfad, aber noch kein implementierter Alias.
- OCR und feinere Source-Anchor-Granularitaet bleiben offene Folgethemen.

## 2026-05-04 - M3a GUI Foundation Prototyp

### Added

- Minimaler read-only Frontend-Prototyp fuer M3a auf React/Vite.
- Routing fuer `/documents` und `/documents/:id`.
- Getrennter API-Client fuer die Dokument-Read-Endpunkte.
- Statuskomponenten fuer Loading, Empty und Error.
- Dokumentliste, Dokumentdetail, Versionen-Anzeige und Chunk-Vorschau.
- Frontend-Dokumente `docs/frontend.md`, `docs/api.md`, `docs/m3a-viewmodels.md`, `docs/m3a-implementation-plan.md`, `docs/m3a-test-strategy.md`.

### Changed

- `frontend/src/app/App.jsx` verwendet jetzt Routing statt Platzhalterseite.
- `frontend/src/pages/DocumentsPage.jsx` rendert Dokumentliste ueber `GET /documents`.
- `frontend/src/pages/DocumentDetailPage.jsx` rendert Detail, Versionen und Chunk-Vorschau ueber die bestehenden Paket-5-Endpunkte.
- `masterplan.md` und `docs/status.md` spiegeln den M3a-Zwischenstand wider.

### Validated

- Historischer Zwischenstand: Frontend-Testlauf `5 passed`.
- Historischer Zwischenstand: Frontend-Build `vite build` erfolgreich.
- Diese historischen Nachweise begruenden keine aktuelle M3a-Freigabe; verbindlich ist der aktuelle Gate-Stand vom 2026-05-18.

### Outstanding

- Keine separaten Unit-Tests fuer ViewModel-Mapping und Fehlerabbildung.
- Keine eigenstaendigen API-Mock-Tests fuer `404`, `409` und API down.
- Kein E2E-Smoke-Test.
- Versionen und Chunks haben noch keine eigenen Routen, sondern leben aktuell im Detailscreen.

## 2026-05-04 - M3b Retrieval Foundation

### Added

- Search API `GET /api/v1/search/chunks`.
- `SearchService`, `SearchRepository` und Search-Response-Schema.
- Migration `20260504_0011_chunk_search_vector.py` fuer PostgreSQL `search_vector` und `GIN`-Index.
- Frontend-Suchmaske auf der Dokumentuebersicht.
- Suchergebnisliste mit Vorschau, Rank und Quellenanker.
- Dokument `docs/m3b-retrieval-foundation.md`.
- Dokument `docs/m3b-retrieval-evaluation-dataset.md`.
- Dokument `docs/retrieval.md` als Retrieval-Einstiegspunkt.

### Changed

- `docs/api.md`, `docs/frontend.md`, `docs/data-model.md`, `docs/status.md` und `masterplan.md` wurden auf den aktuellen Retrieval-Stand abgeglichen.
- GUI zeigt jetzt Such-Lade-, Leer- und Fehlerzustaende auf `/documents`.
- API-Fehlermapping kennt jetzt `INVALID_QUERY` fuer Suchanfragen.

### Validated

- Backend-Retrieval-Nachweis: `14 passed` fuer Search-Service, Search-API und Migrationspfad.
- Frontend-Such- und Screen-Nachweis: `8 passed`.
- Frontend-Build: `vite build` erfolgreich.

### Superseded

- Dieser Zwischenstand wurde durch spaetere PostgreSQL- und Ranking-Tests ueberholt.
- M3c wurde am 2026-05-05 auf dem stabilisierten Retrieval-Vertrag abgeschlossen.

## 2026-05-04 - M3c Chat/RAG Foundation

### Added

- `ContextBuilder` fuer deterministische Kontextpakete.
- `PromptBuilder` fuer dokumentgestuetzte Prompts.
- `CitationMapper` fuer maschinenlesbare Citations.
- `InsufficientContextPolicy` mit festen Schwellenwerten und No-Answer-Verhalten.
- Chat-Persistenzmodelle, Migration und Service fuer Sessions, Messages und Citations.
- Frontend-Chatseite mit Sessionliste, neuer Session, Nachrichtenverlauf, Quellenanzeige und Insufficient-Context-Zustand.
- Dokumente `docs/chat-rag-api-contract.md`, `docs/rag-dataflow.md` und `docs/rag.md`.

### Changed

- `docs/status.md`, `docs/api.md`, `docs/data-model.md`, `docs/frontend.md`, `docs/retrieval.md` und `masterplan.md` wurden auf den realen M3c-Stand abgeglichen.
- `chat_messages.source_metadata` wurde fuer den Zielvertrag auf `metadata` ausgerichtet.

### Validated

- Backend-Fokustests fuer Context Builder, Prompt Builder, Citation Mapper, Insufficient-Context-Policy und Chat-Persistenz: `37 passed`.
- Frontend-Tests inklusive ChatPage: `11 passed`.
- Frontend-Build: `vite build` erfolgreich.

### Superseded

- Dieser Zwischenstand wurde durch den Abschluss vom 2026-05-05 ueberholt.
- Chat-HTTP-API, end-to-end RAG-Pfad und API-Tests sind inzwischen implementiert und verifiziert.

## 2026-05-04 - M4 Integrierter Wissensbasis-Chat

### Status

- Noch nicht implementiert.
- Start ist seit dem M3c-Abschluss vom 2026-05-05 freigegeben.

### Open

- stabile Chat-HTTP-API im Backend
- integrierter Antwortpfad ueber Retrieval, Prompting, Policy, LLM und Citations
- API- und Integrationsnachweise fuer diesen produktiven Pfad
