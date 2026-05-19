# Frontend Truth Full-Suite Scope

Stand: 2026-05-19

## Entscheidung

Ein `frontend_truth_report.json` gilt nur dann als Full-Suite-Frontend-Truth, wenn er alle unten definierten Pflichtflows explizit ausweist. Ein Auth-/Bootstrap-Slice, ein fokussierter Spec-Run oder ein Mock-only Lauf darf keinen Full-Suite-Pass begruenden.

Pflichtregeln fuer jeden Full-Suite-Report:

- `real_api = true`
- `mock_only = false`
- `test_database_url_set = true`
- `api_database_health.ok = true`
- `passed = collected`
- `failed = 0`
- `skipped = 0`
- `playwright_exit_code = 0`
- Browser-E2E gegen laufende echte API
- API gegen echte PostgreSQL-Testdatenbank

## Pflichtflows

| Flow ID | Pflichtflow | Primaere Spec | Mindestnachweis |
|---|---|---|---|
| FT-01 | Login | `test_01_login.spec.js` | Login-Formular, Redirect unauthenticated, invalid credentials, erfolgreicher Login |
| FT-02 | Auth Bootstrap | `test_02_auth_bootstrap.spec.js` | No token, valid bootstrap, complete session, invalid token, backend unreachable, no membership, forbidden, logout |
| FT-03 | Workspace Bootstrap | `test_10_workspace_bootstrap.spec.js` | Membership-Auswahl, Single-/Multi-Workspace, Switcher, invalid switch rejection, no-membership |
| FT-04 | Dokumentliste | `test_04_documents.spec.js` | Heading, Empty/List-State, Lifecycle-Filter, Upload- und Search-Controls ohne Error |
| FT-05 | Dokumentdetail | `test_04_documents.spec.js` oder eigene Detail-Spec | Navigation zu `/documents/:id`, Metadaten, Versionen, Chunk-Vorschau, Fehlerzustand bei unbekanntem Dokument |
| FT-06 | Upload Job Flow | `test_05_upload.spec.js` | Dateiauswahl, Validierung ohne Datei, Upload, Job-Polling, Completion, Ergebnisanzeige |
| FT-07 | Search Flow | `test_06_search.spec.js` | Search-Form, Empty-Query-Verhalten, echte Search-Anfrage, Ergebnis- oder Empty-State ohne Fehler |
| FT-08 | Chat Flow | `test_07_chat.spec.js` | Chat-Route, Sessionliste oder Empty-State, Composer, Workspace-Kontext, Navigation |
| FT-09 | Lifecycle Flow | `test_08_lifecycle.spec.js` | Active/Archived-Filter, API-Request bei Wechsel, Rueckwechsel, sichtbarer Lifecycle-Hinweis |
| FT-10 | Diagnostics read-only | `test_09_diagnostics.spec.js` | Admin-Route, System-/DB-/Migration-Status, kein mutierender Admin-Button |
| FT-11 | Error-State Flow | `test_11_state_invariants.spec.js` | technische Fehler werden als Error-State gerendert, nicht als Empty-State; Forbidden ohne Retry |
| FT-12 | Workspace-Wechsel | `test_10_workspace_bootstrap.spec.js` | Workspace-Switch aktualisiert Header, laedt Dokumente neu, resetet Search/Upload/Chat-Kontext |
| FT-13 | Logout/Login Recovery | `test_02_auth_bootstrap.spec.js` und `test_01_login.spec.js` | Logout loescht Session; geschuetzte Route fuehrt zu Login; erneuter Login stellt Workspace-Kontext her |
| FT-14 | API reconnect | `test_02_auth_bootstrap.spec.js` oder eigene Recovery-Spec | API_UNREACHABLE mit Retry; Retry fuehrt nach wieder erreichbarer API zu stabilem Auth-/Workspace-State |
| FT-15 | Stale Response Handling | `test_12_concurrency.spec.js` | parallele Search Requests und Workspace-Wechsel waehrend Request duerfen State nicht mit stale Response ueberschreiben |

## Testfallliste

| Testfall ID | Flow | Testfall | Akzeptanzkriterium |
|---|---|---|---|
| FT-01.1 | Login | Loginformular sichtbar | Nutzer sieht Login-Felder und Submit-Aktion |
| FT-01.2 | Login | Unauthenticated Redirect | geschuetzte Route ohne Session landet auf `/login` |
| FT-01.3 | Login | Invalid Credentials | Fehlermeldung sichtbar, keine Fachroute |
| FT-01.4 | Login | Erfolgreicher Login | Redirect zu `/documents`, Workspace-Kontext gesetzt |
| FT-02.1 | Auth Bootstrap | No Token | kein `/auth/me`, Redirect zu Login |
| FT-02.2 | Auth Bootstrap | Valid Bootstrap | genau ein `/auth/me`, Dokumentroute stabil |
| FT-02.3 | Auth Bootstrap | Complete Session | kein unnoetiger Bootstrap-Call |
| FT-02.4 | Auth Bootstrap | Invalid Token | Session-expired Error, kein stiller Redirect |
| FT-02.5 | Auth Bootstrap | Backend unreachable | `API_UNREACHABLE`, Retry sichtbar |
| FT-02.6 | Auth Bootstrap | No Membership | `WORKSPACE_NOT_CONFIGURED`, kein Auth-Expiry-Falschsignal |
| FT-02.7 | Auth Bootstrap | Forbidden | `FORBIDDEN`, kein Retry-Button |
| FT-02.8 | Auth Bootstrap | Logout | Session und LocalStorage geleert |
| FT-03.1 | Workspace Bootstrap | Membership Workspace | aktiver Workspace stammt aus Membership |
| FT-03.2 | Workspace Bootstrap | Single Workspace | kein Switcher |
| FT-03.3 | Workspace Bootstrap | Multi Workspace | Switcher zeigt beide Workspaces |
| FT-03.4 | Workspace Bootstrap | Invalid Switch | ungültiger Workspace wird abgelehnt |
| FT-04.1 | Dokumentliste | Dokumentroute | Heading und Controls sichtbar |
| FT-04.2 | Dokumentliste | Empty/List-State | Empty-State nur bei erfolgreicher leerer API-Antwort |
| FT-05.1 | Dokumentdetail | Detailnavigation | ein reales Dokument kann geoeffnet werden |
| FT-05.2 | Dokumentdetail | Detailinhalt | Metadaten, Versionen und Chunk-Vorschau sichtbar |
| FT-05.3 | Dokumentdetail | Not Found | unbekanntes Dokument wird als Error-State gerendert |
| FT-06.1 | Upload Job Flow | Ohne Datei | Validierungsfehler ohne API-Mutation |
| FT-06.2 | Upload Job Flow | Erfolgreicher Upload | Job laeuft bis Completion, Ergebnis sichtbar |
| FT-06.3 | Upload Job Flow | Duplicate/OCR/Parser | kontrollierter Ergebnis- oder Error-State, kein generischer Erfolg |
| FT-07.1 | Search Flow | Empty Query | kein technischer Error |
| FT-07.2 | Search Flow | Echte Suche | Request geht an echte API mit Workspace-Kontext |
| FT-07.3 | Search Flow | Ergebnis/Empty | Treffer oder fachlicher Empty-State, kein Fake-Green bei API-Fehler |
| FT-08.1 | Chat Flow | Chatroute | Workspace-Kontext sichtbar |
| FT-08.2 | Chat Flow | Sessionliste/Empty | Chat zeigt stabilen Startzustand |
| FT-08.3 | Chat Flow | Composer | Eingabe ist nur bei validem Workspace nutzbar |
| FT-09.1 | Lifecycle Flow | Filterwechsel | archived/active Wechsel triggert echte API |
| FT-09.2 | Lifecycle Flow | Rueckwechsel | Dokumentliste bleibt konsistent |
| FT-10.1 | Diagnostics | Read-only Route | Diagnostics erreichbar fuer berechtigte Session |
| FT-10.2 | Diagnostics | Statuskarten | System, DB und Migration sichtbar |
| FT-10.3 | Diagnostics | Keine Mutation | keine Reindex-/Cleanup-/Backup-Aktionen im freigegebenen Scope |
| FT-11.1 | Error-State | API down != Empty | `API_UNREACHABLE` ersetzt nicht die leere Dokumentliste |
| FT-11.2 | Error-State | Forbidden ohne Retry | `FORBIDDEN` erzeugt keinen Retry-Loop |
| FT-11.3 | Error-State | Workspace invalid | Fachcontrols werden ohne validierten Workspace nicht gerendert |
| FT-12.1 | Workspace-Wechsel | Header-Wechsel | aktive Workspace-Anzeige aktualisiert sich |
| FT-12.2 | Workspace-Wechsel | Reload | Dokumentliste wird fuer neuen Workspace neu geladen |
| FT-12.3 | Workspace-Wechsel | Reset | Search, Upload und Chat-Zielkontext werden resetet |
| FT-13.1 | Logout/Login Recovery | Logout | Session geloescht, `/documents` fuehrt zu Login |
| FT-13.2 | Logout/Login Recovery | Re-Login | erneuter Login stellt Fachnavigation wieder her |
| FT-14.1 | API reconnect | Retry nach API down | Retry fuehrt bei wieder erreichbarer API zu stabiler Ansicht |
| FT-14.2 | API reconnect | kein Retry-Loop | nicht retryable Fehler bleiben ohne Retry-Aktion |
| FT-15.1 | Stale Response | Parallele Search | spaete alte Search-Response ueberschreibt neuen Zustand nicht |
| FT-15.2 | Stale Response | Workspace-Wechsel in-flight | alte Workspace-Response erscheint nach Switch nicht erneut |

## Aktueller Abdeckungsstatus

Der Report vom 2026-05-19 (`82/82`) ist gruen und laeuft gegen echte API/PostgreSQL. Fuer die finale Scope-Definition gelten aber diese Klarstellungen:

| Flow | Aktueller Status im Report | Scope-Entscheidung |
|---|---|---|
| Login | explizit enthalten | Pflicht bleibt |
| Auth Bootstrap | explizit enthalten | Pflicht bleibt |
| Workspace Bootstrap | explizit enthalten | Pflicht bleibt |
| Dokumentliste | explizit enthalten | Pflicht bleibt |
| Dokumentdetail | nicht explizit im Reportnamen ausgewiesen | muss als eigener Full-Suite-Test explizit erscheinen |
| Upload Job Flow | explizit enthalten, Basisfall | Duplicate/OCR/Parser-Faelle als Full-Suite-Erweiterung festhalten |
| Search Flow | explizit enthalten | Pflicht bleibt |
| Chat Flow | explizit enthalten, Basisroute | Message-/Retrieval-Folge kann eigener spaeterer Full-Suite-Ausbau sein |
| Lifecycle Flow | explizit enthalten | Pflicht bleibt |
| Diagnostics read-only | explizit enthalten | Pflicht bleibt |
| Error-State Flow | explizit enthalten | Pflicht bleibt |
| Workspace-Wechsel | explizit enthalten | Pflicht bleibt |
| Logout/Login Recovery | Logout enthalten, Re-Login nicht eigenstaendig ausgewiesen | Re-Login als expliziten Recovery-Test ergaenzen |
| API reconnect | API_UNREACHABLE und Retry-Button enthalten | erfolgreicher Retry nach wieder erreichbarer API explizit ergaenzen |
| Stale Response Handling | Search und Workspace in-flight enthalten | Pflicht bleibt, spaeter um Upload/Chat erweiterbar |

## Akzeptanzkriterien

Ein Full-Suite-Frontend-Truth-Report ist akzeptiert, wenn:

1. alle 15 Pflichtflows mindestens einen expliziten Testfall im Report haben,
2. alle Muss-Felder des Reports gesetzt sind,
3. `collected > 0`,
4. `passed == collected`,
5. `failed = 0`,
6. `skipped = 0`,
7. `errors = []` oder `errors = 0`,
8. `real_api = true`,
9. `mock_only = false`,
10. `test_database_url_set = true`,
11. `/health/db` der API gruen ist,
12. keine technische Fehlersituation als Empty-State erscheint,
13. kein nicht retryable Fehler einen Retry-Loop anbietet,
14. Workspace-, Auth- und Request-Generation-Wechsel stale Responses verwerfen,
15. der Report in `reports/frontend_truth_report.json` und `reports/gui_truth/latest.json` identisch referenziert wird.

Wenn einer dieser Punkte fehlt, ist der Lauf maximal ein fokussierter Slice-Report, nicht Full-Suite-Frontend-Truth.
