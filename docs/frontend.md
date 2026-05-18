# Frontend M3a, M3b Retrieval-UI, M3c Chat/RAG-Foundation-UI und M4-Produktisierungsstand

Stand: 2026-05-18

## Status

Die GUI ist als read-only Basis umgesetzt, wurde fuer M3b um Retrieval-Suche erweitert, fuer M3c um eine dokumentgestuetzte Chat-Oberflaeche ergaenzt und in M4 um Upload-, Lifecycle- sowie read-only Admin-Diagnostics-Slices erweitert. Das belegt: GUI vorhanden. Es belegt nicht: GUI stabilisiert. Der aktuelle M3a-Gate-Report `reports/m3a_gate_result.json` steht auf `FAIL` mit Score `57.1`.

Verbindliche Nachweisgrenze: Gruene Aussagen zum Frontend duerfen nur aus aktuellen Reports abgeleitet werden. `reports/frontend_truth_report.json` vom 2026-05-18 weist `80 collected`, `58 passed`, `22 failed`, `0 skipped` aus. Damit ist M3a nicht abgeschlossen.

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

## Aktueller Nachweis

- Screen-Tests fuer Dokumentliste und Dokumentdetail: vorhanden.
- Screen-Tests fuer Suchtreffer, Such-Leerzustand und Such-Fehlerzustand: vorhanden.
- Screen-Tests fuer Chat-Sessionliste, Chat-Nachrichten, Quellenanzeige und Insufficient-Context-Zustand: vorhanden.
- Screen-Tests fuer neue Session, Frage senden, Assistant-Antwort mit Quellen und Chat-Fehlercodes: vorhanden.
- Historische Screen- und Unit-Tests sind vorhanden, ersetzen aber keinen gruenen Frontend Truth Report.
- Frontend Truth Report: `reports/frontend_truth_report.json`, Stand 2026-05-18, `80 collected`, `58 passed`, `22 failed`, `0 skipped`, Browser `chromium`, API `http://127.0.0.1:8000`, echte PostgreSQL-DB nachgewiesen.
- M3a Gate: `reports/m3a_gate_result.json`, `FAIL`, Score `57.1`.

Keine Freigabeaussage:

- Ein lokaler Unit-/Build-Lauf darf die Browser-E2E-Fehler nicht ueberstimmen.
- M3a darf nicht als `abgeschlossen`, `freigegeben` oder `stabilisiert` markiert werden, solange das M3a-Gate nicht gruen ist.

## Aktuelle Luecken vor finaler Freigabe

- 22 fehlgeschlagene Frontend-E2E-Flows im aktuellen Frontend Truth Report.
- gruener `reports/contract_test_report.json`; Contract Tests blockieren M3a aktuell nicht.
- roter `reports/postgres_truth_report.json`.
- M3a Gate `FAIL`.
- Keine separaten Routen fuer Versionen- und Chunk-Ansicht; beides ist aktuell in die Detailseite integriert.
- Keine echten Unit-Tests fuer ViewModel-Mapping und Fehlerabbildung.
- Keine separaten API-Mock-Tests fuer `404`, `409` und Netzwerkfehler auf API-Client-Ebene.
- Kein E2E-Smoke-Test fuer den Kernflow.
- Keine GUI-Pagination fuer umfangreiche Suchtreffermengen.
- Kein Browser-E2E-Test gegen einen laufenden Backend-Prozess; die aktuelle Absicherung erfolgt ueber Vitest/Fetch-Mocks gegen den echten API-Vertrag.
- Kein Direktlink in die Dokumentdetailansicht nach erfolgreichem Upload.
- Keine Darstellung von `warnings` im Upload-Ergebnis.
- Polling nutzt festen 250-ms-Takt ohne Backoff.
- Dokument-, Search- und Chat-API-Clients senden keinen `workspace_id` mehr in Query oder Body, sondern nutzen den zentralen Request-Kontext fuer `X-Workspace-Id`.
- Ein vollstaendiger Frontend-Produktflow fuer Login, Logout, Sessionwiederherstellung und geschuetzte Route-Guards fehlt weiterhin.
- Kein Login-Screen und kein Logout; die GUI konsumiert geschuetzte Endpunkte ueber den Request-Kontext, bietet aber keinen vollstaendigen M4a-Produktfluss.
- Admin-Diagnostik nutzt den zentralen Auth-/Workspace-Kontext; die GUI zeigt keinen manuellen `x-admin-token`-Pfad und keine mutierenden Admin-Aktionen mehr.

## M4a Konsistenzstand im Frontend

Nachweisbar implementiert:

- Fehlerabbildung fuer `AUTH_REQUIRED`, `ADMIN_REQUIRED`, `WORKSPACE_REQUIRED`
- Read-only Admin-Diagnostik mit Membership-/Rollenpruefung aus dem AuthContext
- Workspace-Sichtbarkeit in Dokument- und Chat-Routen

Nicht nachweisbar implementiert:

- Login-Screen
- Logout-Flow
- Sessionwiederherstellung
- geschuetzter Route-Guard aus einem echten Auth-Kontext
- vollstaendige geschuetzte Navigation ohne manuelle Workspace-Kontextannahmen

## Fazit

Der Frontend-Schnitt deckt Dokumente, Suche, Chat sowie erste M4-Produktisierungs-Slices fuer Upload, Lifecycle und read-only Diagnostics ab. Das ist ein vorhandener GUI-Stand, aber kein stabilisierter M3a-Abschluss. Aktuell blockieren der rote Frontend Truth Report und der rote PostgreSQL Truth Report das M3a-Gate; der Contract-Test-Report ist gruen. M4d ist im Frontend nur read-only vorbereitet; Reparatur-, Reindex-, Cleanup- und Backup-Aktionen sind nicht Teil eines freigegebenen UI-Scope.
