# Frontend M3a, M3b Retrieval-UI, M3c Chat/RAG-Foundation-UI und M4-Produktisierungsstand

Stand: 2026-05-19

## Status

Die GUI ist als read-only Basis umgesetzt, wurde fuer M3b um Retrieval-Suche erweitert, fuer M3c um eine dokumentgestuetzte Chat-Oberflaeche ergaenzt und in M4 um Upload-, Lifecycle- sowie read-only Admin-Diagnostics-Slices erweitert. Das belegt: GUI vorhanden. Der aktuelle M3a-Gate-Report `reports/m3a_gate_result.json` steht auf `PASS` mit Score `100.0`; damit ist M3a Frontend Foundation abgeschlossen.

Verbindliche Nachweisgrenze: Gruene Aussagen zum Frontend duerfen nur aus aktuellen Reports abgeleitet werden. Der aktuelle Full-Suite-Frontend-Truth-Lauf liegt in `reports/frontend_truth_report.json` und `reports/gui_truth/latest.json` mit `82 collected`, `82 passed`, `0 failed`, `0 skipped`, echter API, echter PostgreSQL-Testdatenbank und gruenem `/health/db`. `reports/gui_truth/gui_chaos_suite_report.json` ist ebenfalls gruen mit `8/8`. Die Gate-Regel ist in `docs/m3a-gate-policy.md` dokumentiert.

Fehlkopplungsregel: `reports/postgres_truth_report.json` ist fuer M3a Frontend Foundation keine blockierende Quelle. Der rote PostgreSQL-Truth-Gesamtstatus bleibt M4 Backend Truth/M5 Operational Truth und darf M3a nur blockieren, wenn API-Erreichbarkeit, echte DB, Contract Tests oder relevante M3a-Endpunktflows verletzt sind.

Verbindlicher Runtime-Vertrag: Die explizite Frontend-State-Machine steht in `docs/frontend-runtime-state-machine.md`. Fachrouten duerfen nur aus `workspace_ready` heraus frische Daten und Mutationen anbieten; `api_unreachable`, `forbidden`, `restore_mode` und `reconnecting` duerfen nie als Empty-State gerendert werden.

Verbindliche Cache-Governance: `docs/frontend-cache-governance.md` schreibt workspace-scoped Cache-Keys, `source_timestamp`/`source_version`, Invalidierungsereignisse und sichtbare Stale-Indikatoren fuer Dokumentlisten, Search Results, Chat Sessions, Diagnostics und Workspace Memberships vor.

Verbindliches Concurrency-Modell: `docs/frontend-concurrency-safety.md` beschreibt Request-Tickets, Cancellation, Workspace-/Auth-Snapshots, `correlationId`-Propagation und Race-Simulationen fuer Search, Upload, Workspace-Wechsel, Logout und Chat Retrieval.

Verbindlicher Full-Suite-Frontend-Truth-Scope: `docs/frontend-truth-full-suite-scope.md` definiert die 15 Pflichtflows von Login bis Stale Response Handling, die Testfallliste und die Akzeptanzkriterien. Ein fokussierter Auth-/Bootstrap-Lauf zaehlt nicht als Full-Suite.

Verbindliche Telemetry-Governance: `docs/frontend-telemetry-governance.md` definiert das Frontend-Telemetry-Modell, Datenschutzgrenzen, Workspace-Aggregation, optionale `correlation_id` und die Pflichtmetriken fuer API-Fehler, Bootstrap, Search, Upload, Chat-Retrieval, stale response drops und Reconnect-Events.

Verbindliche Offline-/Degraded-Strategie: `docs/frontend-offline-degraded-strategy.md` definiert fuer API down, Search down, Queue degraded, Reindex, Restore und temporaer unverfuegbaren Chat die erlaubten Aktionen, Blocker, Retry-Regeln, UI-Indikatoren und Cache-Nutzung.

Verbindliche strategische GUI-Prinzipien: `docs/frontend-strategic-principles.md` definiert deterministische Zustandsfuehrung, transparente Fehler, nachvollziehbare Recovery, drift-aware Darstellung, workspace-isolierte States, verbotene GUI-Patterns, Pflichtabstraktionen und Stop-Kriterien fuer weitere GUI-Featureentwicklung.

Verbindliche GUI-Review-Checkliste: `docs/frontend-pr-review-checklist.md` konkretisiert die strategischen Prinzipien als operatives Review-Minimum fuer GUI-PRs und benennt harte Review-Stopper fuer Fake-Green-, Drift-, Recovery-, Workspace- und Concurrency-Verstoesse.

Verbindliches Truth-Surface-Modell: `docs/frontend-truth-surface-model.md` definiert fuer Upload, Queue, Search, Retrieval, Drift, Restore, Reindex, Lifecycle, Backup und Diagnostics die echte Datenquelle, erlaubte und verbotene Vereinfachungen, degraded Darstellung, unknown handling und allgemeine UI-Wahrheitsregeln.

Verbindliches Event-Konsistenzmodell: `docs/frontend-event-consistency-model.md` definiert Event Ordering, stale-event Erkennung, idempotente UI-Updates, workspace-scoped Event Isolation, `correlation_id`-Propagation, Replay-Regeln und Reconnect-Recovery fuer asynchrone GUI-Ereignisse.

Verbindliche Freshness-Governance: `docs/frontend-data-freshness-governance.md` definiert fuer Dokumentlisten, Search, Chat Retrieval, Diagnostics, Queue-Status und Drift-Anzeigen Freshness-Indikatoren, stale thresholds, Auto-/Manual-Refresh-Pflichten, Cache-TTLs, sichtbare Stale-Markierung und das Verbot von stale Retrieval.

Verbindliches Recovery-UX-Modell: `docs/frontend-recovery-ux-model.md` definiert fuer Backend/DB-Restart, Restore, Queue-Degradierung, Search-Ausfall, Retrieval-Degradierung, Auth-Expiry und Workspace-Verlust sichtbare Hinweise, erlaubte und blockierte Aktionen, Retry-/Reconnect-Regeln, Recovery-Trigger und UI-Zustandsdiagramme.

Verbindliche Performance-Governance: `docs/frontend-performance-governance.md` definiert deterministische Rendering-Flows, stabile Request-Ketten, kontrollierte Parallelitaet, vorhersehbare Ladezustaende, Request-Sturm-Schutz, governance-konforme Performance-Metriken und verbotene Performance-Anti-Patterns.

Verbindliche Accessibility- und Operational-Clarity-Standards: `docs/frontend-accessibility-operational-clarity-standards.md` definiert klare Error- und degraded States, sichtbare destructive actions, eindeutige Restore-/Reindex-/Queue-/Drift-Warnungen, Keyboard-Navigation, Screenreader-Kompatibilitaet und UI-Warnstandards ohne reine Farbsemantik.

## Umgesetzter Scope

- Route `/documents` fuer die Dokumentliste.
- Route `/documents/:id` fuer Dokumentdetail.
- Anzeige von Metadaten, Importstatus, Versionen und Chunk-Vorschau im Detailscreen.
- Getrennter API-Client fuer die Dokument-Read-Pfade.
- Einfache Suchmaske auf der Dokumentuebersicht.
- Ergebnisliste fuer Chunk-Treffer mit Vorschau, Rank und Quellenanker.
- Link vom Suchtreffer zum Dokumentdetail.
- Route `/chat` und `/chat/:id` fuer Chat-Sessions.
- Upload-Block auf `/documents` mit Hintergrundjob-Polling.
- Read-only Admin-Diagnostics unter `/admin/diagnostics`.
- Lifecycle-Filter, Archive, Restore und Soft-Delete in der Dokument-GUI.
- Sessionliste fuer Chat.
- Formular fuer neue Session.
- Frageformular fuer Chat-Nachrichten.
- Nachrichtenverlauf mit Assistant-Antworten.
- Sichtbarer Quellenblock mit Citations.
- Sichtbarer Insufficient-Context-Zustand.
- Fehlerzustaende fuer `CHAT_SESSION_NOT_FOUND`, `CHAT_MESSAGE_INVALID`, `INSUFFICIENT_CONTEXT`, `RETRIEVAL_FAILED` und `LLM_UNAVAILABLE`.
- POST-Message-Request im aktuellen Frontend mit `question` und `retrieval_limit`; Workspace und User kommen aus dem zentralen Request-Kontext.
- POST-Message-Response wird als Assistant-Message mit Citations und Confidence gemappt.
- Lade-, Leer- und Fehlerzustaende.
- Sichtbare Fehlercodes im UI.
- Normalisierte Jobstatuslabels fuer Upload.

## M4d Read-only Diagnostics-GUI im aktuellen Stand

Nachweisbar implementiert:

- Route `/admin/diagnostics`
- API-Client `GET /api/v1/admin/diagnostics`
- Statuskarten fuer Systemstatus, DB Status, Migration Status, Dokument-/Version-/Chunk-Zahlen, Import Job Status, Search Index Status und Auth/Workspace Status
- Zugriff nur fuer AuthContext-Memberships mit Rolle `owner` oder `admin`
- sichtbarer Fehlerzustand fuer API down und API-Fehler wie `DIAGNOSTICS_FAILED`
- sichtbarer degraded Status

Bewusst nicht gerendert:

- keine Reindex-Buttons
- keine Cleanup-Buttons
- keine Backup-Buttons
- keine Admin-Token-Eingabe
- keine Roh-JSON-Anzeige mit unbekannten Zusatzfeldern
- keine Dokumenttexte, Chunktexte, Chat-Fragen, Chat-Antworten oder Secrets

Teststatus:

- Fokussierter Screen-Test: `AdminDiagnosticsPage.test.jsx`, `4 passed`.
- Tests decken Nicht-Admin-Zugriff, API down, degraded Status und Redaction gegen sensible Zusatzfelder ab.

Freigabegrenze:

- M4d ist damit nur als read-only vorbereitet.
- Vollstaendige M4d-Admin-Aktionen bleiben blockiert, bis M4a/M4b/M4c gruen sind.

## M4b Upload-GUI im aktuellen Stand

Nachweisbar implementiert:

- Dateiauswahl fuer `.txt`, `.md`, `.docx`, `.doc` und `.pdf`
- Upload-Start direkt in der Dokumentansicht
- Blockierung eines zweiten Uploads waehrend `loading` oder `polling`
- Polling des generischen Jobstatus-Endpunkts
- Erfolgsanzeige mit Dateiname, Dokument-ID, `import_status` und Chunk-Anzahl
- Duplicate-Hinweis `bereits vorhanden` inklusive Anzeige der vorhandenen Dokument-ID
- generische Fehleranzeige ueber gemappte Fehlercodes wie `OCR_REQUIRED` und `PARSER_FAILED`
- Fehleranzeige fuer `FILE_TOO_LARGE`
- Neuladen der Dokumentliste nach erfolgreichem Abschluss
- Upload-Anfragen nutzen den zentralen Request-Kontext mit `Authorization` und `X-Workspace-Id`

Upload-Flow in der GUI:

- Benutzer waehlt Datei aus
- Frontend sendet `POST /documents/import`
- GUI zeigt `queued`/`running` ueber normalisierte Joblabels
- GUI pollt `GET /api/v1/jobs/{job_id}` alle 250 ms
- bei `completed` wird das Ergebnisfeld angezeigt
- bei `failed` wird `ErrorState` mit gemapptem Fehlercode angezeigt

Importstatus im UI:

- Jobstatuslabels: `In Warteschlange`, `Wird verarbeitet`, `Abgeschlossen`, `Fehlgeschlagen`
- fachliche Importstatuswerte wie `chunked` oder `duplicate` werden im Ergebnistext sichtbar angezeigt

Duplicate-Verhalten:

- Der Backend-Fall ist nachweisbar und die GUI zeigt `Dokument bereits vorhanden` als Erfolgshinweis.
- Es gibt weiterhin keine spezifische Aktion `Vorhandenes Dokument oeffnen`.

OCR-required-Verhalten:

- `OCR_REQUIRED` wird im allgemeinen Fehlerzustand angezeigt.
- Es gibt keinen spezialisierten OCR-Hinweis mit erklaerter Nicht-Scope-Folgeaktion.

## M4c Lifecycle-GUI im aktuellen Stand

Nachweisbar implementiert:

- Dokumentliste filtert zwischen `active` und `archived`.
- `deleted` wird in der GUI nicht als eigener Filter angeboten.
- Dokumentdetail zeigt Lifecycle-Badge und Lifecycle-Hinweis.
- aktive Dokumente koennen archiviert werden.
- archivierte Dokumente koennen wiederhergestellt werden.
- Dokumente koennen per GUI soft-geloescht werden.
- nach Archive und Restore wird der Detailzustand neu geladen.
- nach Soft-Delete navigiert die GUI zur Dokumentliste zurueck.

Nachweisbar nicht umgesetzt:

- keine GUI fuer geloeschte Dokumente
- keine Admin-Restore- oder Purge-Funktion fuer `deleted`
- kein eigener Frontend-Flow fuer historische Citations ueber den bereits angezeigten Chatverlauf hinaus

Bekannte Einschraenkungen im Lifecycle-Slice:

- Die GUI dokumentiert, dass archivierte Dokumente nicht in Suche oder Chat erscheinen, stützt sich dafuer aber auf Backend-Verhalten statt auf eigenen Browser-E2E-Nachweis.
- Der Lifecycle-Slice ist ueber Screen-Tests verifiziert, nicht ueber Browser-E2E gegen ein laufendes Gesamtsystem.
- Der aktuelle fokussierte Diagnostics-Frontend-Lauf ist fuer den read-only Screen gruen; ein Browser-E2E gegen ein laufendes Gesamtsystem fehlt weiterhin.

## Bewusst nicht umgesetzt

- Mutation.
- Rollen und Rechte fuer regulare Fachendpunkte.
- OCR-UI.
- Embeddings.
- Query-Vorschlaege, Facetten und gespeicherte Suchen.
- Streaming.
- Agentenaktionen.
- Bearbeiten von Antworten.
- Dokument-Upload aus dem Chat.

## Aktuelle Struktur

- `frontend/src/api/`: API-Client, Dokument-Requests und Chat-Requests.
- `frontend/src/app/`: App-Rahmen und Routing.
- `frontend/src/components/`: Dokument-, Chat- und Statuskomponenten.
- `frontend/src/pages/`: Dokumentliste, Dokumentdetail und Chat-Seite.
- `frontend/src/view-models/`: Mapping und UI-nahe Ableitungen.
- `frontend/src/tests/pages/`: bisherige Screen-Tests.
- `docs/frontend-runtime-state-machine.md`: verbindliche Runtime States, Transition Matrix, verbotene Transitions und Cache-/Upload-Regeln.
- `docs/frontend-cache-governance.md`: verbindliche Cache-Governance, Invalidierungsregeln und Stale-State-Regeln.
- `docs/frontend-concurrency-safety.md`: verbindliches Request-Management und Race-Sicherheitsmodell.
- `docs/frontend-truth-full-suite-scope.md`: verbindlicher Full-Suite-Frontend-Truth-Scope mit Pflichtflows und Akzeptanzkriterien.
- `docs/m3a-gate-policy.md`: verbindliche Trennung zwischen M3a Frontend Truth, M4 Backend Truth und M5 Operational Truth.

## Aktueller Nachweis

- Screen-Tests fuer Dokumentliste und Dokumentdetail: vorhanden.
- Screen-Tests fuer Suchtreffer, Such-Leerzustand und Such-Fehlerzustand: vorhanden.
- Screen-Tests fuer Chat-Sessionliste, Chat-Nachrichten, Quellenanzeige und Insufficient-Context-Zustand: vorhanden.
- Screen-Tests fuer neue Session, Frage senden, Assistant-Antwort mit Quellen und Chat-Fehlercodes: vorhanden.
- Historische Screen- und Unit-Tests sind vorhanden, ersetzen aber keinen gruenen Frontend Truth Report.
- Full-Suite-Frontend-Truth: `reports/frontend_truth_report.json` und `reports/gui_truth/latest.json`, Stand 2026-05-19, `82 collected`, `82 passed`, `0 failed`, `0 skipped`, Browser `chromium`, API `http://127.0.0.1:8000`, echte PostgreSQL-DB nachgewiesen.
- GUI Chaos Truth: `reports/gui_truth/gui_chaos_suite_report.json`, `8 collected`, `8 passed`, `0 failed`.
- M3a Gate: `reports/m3a_gate_result.json`, `PASS`, Score `100.0`.
- Finales M3a Gate: `reports/m3a_final_gate_report.json`, `PASS`, Score `100.0`, M3a abgeschlossen.

Keine Freigabeaussage:

- Ein lokaler Unit-/Build-Lauf darf die Browser-E2E-Fehler nicht ueberstimmen.
- M3a darf als `abgeschlossen` dokumentiert werden, solange der aktuelle M3a-Gate-Report gruen bleibt und keine neuere rote M3a-Quelle existiert.

## Restpunkte ausserhalb des finalen M3a-Gates

- Roter `reports/postgres_truth_report.json` bleibt M4/M5-Blocker, nicht M3a-Blocker.
- Keine separaten Routen fuer Versionen- und Chunk-Ansicht; beides ist aktuell in die Detailseite integriert.
- ViewModel-Mapping, Fehlerabbildung und zentrale API-Client-Fehler sind getestet, bleiben aber als Pflegebereich fuer neue Codes relevant.
- Keine GUI-Pagination fuer umfangreiche Suchtreffermengen.
- Kein Direktlink in die Dokumentdetailansicht nach erfolgreichem Upload.
- Keine Darstellung von `warnings` im Upload-Ergebnis.
- Polling nutzt festen 250-ms-Takt ohne Backoff.
- Dokument-, Search- und Chat-API-Clients senden keinen `workspace_id` mehr in Query oder Body, sondern nutzen den zentralen Request-Kontext fuer `X-Workspace-Id`.
- Erweiterte M4a-Produktfragen wie Cookie-Session-Standard, CSRF und Enterprise-Rollenmodell bleiben ausserhalb des M3a-Gates.
- Admin-Diagnostik nutzt den zentralen Auth-/Workspace-Kontext; die GUI zeigt keinen manuellen `x-admin-token`-Pfad und keine mutierenden Admin-Aktionen mehr.

## M4a Konsistenzstand im Frontend

Nachweisbar implementiert:

- Fehlerabbildung fuer `AUTH_REQUIRED`, `ADMIN_REQUIRED`, `WORKSPACE_REQUIRED`
- Read-only Admin-Diagnostik mit Membership-/Rollenpruefung aus dem AuthContext
- Workspace-Sichtbarkeit in Dokument- und Chat-Routen

Nicht als M3a-Blocker bewertet:

- Cookie-Session-Produktstandard
- CSRF-Nachweis
- Enterprise-Rollenmodell
- vollstaendige M4a-Backend-Hardening-Freigabe

## Fazit

Der Frontend-Schnitt deckt Dokumente, Suche, Chat sowie erste M4-Produktisierungs-Slices fuer Upload, Lifecycle und read-only Diagnostics ab. M3a Frontend Foundation ist durch `reports/m3a_gate_result.json` abgeschlossen. Der rote PostgreSQL Truth Report blockiert weiterhin M4/M5, aber nicht M3a. M4d ist im Frontend nur read-only vorbereitet; Reparatur-, Reindex-, Cleanup- und Backup-Aktionen sind nicht Teil eines freigegebenen UI-Scope.
