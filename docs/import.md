# Import

Stand: 2026-05-06

## M4b Upload-Flow

Der aktuelle Uploadpfad ist asynchron. Die GUI importiert keine Datei mehr synchron ueber einen direkten Fachresponse, sondern ueber einen persistierten Hintergrundjob.

Sicherheitsgrenzen:

- Der Upload ist auth-gebunden.
- Workspace und Benutzer kommen aus dem serverseitigen Auth-Kontext.
- Ein Default-Workspace-/Default-User-Fallback ist im Upload-Flow nicht aktiv.
- Upload ohne Auth endet mit `401 AUTH_REQUIRED`.
- Upload in fremdem Workspace endet mit `403 WORKSPACE_ACCESS_FORBIDDEN`.

Flow:

1. Benutzer waehlt in der Dokumentansicht genau eine Datei aus.
2. Das Frontend sendet `POST /documents/import` mit `multipart/form-data` und Feld `file`.
3. Der Backend-Endpoint legt einen `document_import`-Job an und antwortet mit `202 Accepted`.
4. Das Frontend pollt `GET /api/v1/jobs/{job_id}`.
5. Der Job endet in `completed` oder `failed`.
6. Bei `completed` enthaelt `result` das fachliche Importergebnis.
7. Bei `failed` bleiben fachliche Fehler in `error_code` und `error_message`.

## Importstatus

Jobstatus:

- `queued`
- `running`
- `completed`
- `failed`

Fachlicher Importstatus im Resultat:

- `chunked`: Dokument neu importiert und gechunkt
- `duplicate`: vorhandenes Dokument wiederverwendet

Weitere Datenpunkte im Resultat:

- `document_id`
- `version_id`
- `duplicate_of_document_id`
- `chunk_count`
- `parser_type`
- `warnings`

## Fehlercodes

Direkt am Upload-Endpoint:

- `FILE_TOO_LARGE`
- `UNSUPPORTED_FILE_TYPE`
- `AUTH_REQUIRED`
- `WORKSPACE_ACCESS_FORBIDDEN`

Im Jobstatus:

- `PARSER_FAILED`
- `OCR_REQUIRED`
- `IMPORT_FAILED`

Im Backend-Fehlerkanon:

- `DUPLICATE_DOCUMENT` ist vorhanden, ist aber nicht der normale Erfolgsvertrag fuer Duplicate-Uploads.

Bei Statusabfrage:

- `JOB_NOT_FOUND`

Im Frontend-Mapping:

- `NETWORK_ERROR`

## Duplicate-Verhalten

- Duplicate Detection ist serverseitig implementiert.
- Ein Duplicate fuehrt nicht zu einem fehlgeschlagenen Job, sondern zu einem erfolgreichen Abschluss mit `result.import_status = duplicate`.
- `result.duplicate_of_document_id` verweist auf das bestehende Dokument.
- Das aktuelle Frontend zeigt diesen Fall als Erfolg mit dem Hinweis `bereits vorhanden` und zeigt die bestehende Dokument-ID an.

## OCR-required-Verhalten

- PDF-Dateien mit zu wenig extrahierbarem Text werden als OCR-beduerftig erkannt.
- Da OCR nicht im Scope ist, endet der Job mit `status = failed` und `error_code = OCR_REQUIRED`.
- Das Frontend zeigt diesen Fall im allgemeinen Fehlerzustand an.

## Bekannte Einschraenkungen

- keine Mehrfachupload-UI
- kein Drag-and-drop
- kein Byte-Fortschritt, nur Jobstatus
- kein Direkt-Sprung in die Dokumentdetailansicht nach Erfolg
- keine Darstellung von `warnings` im Upload-Ergebnis
- Dokumentansicht und aktuelle API-Clients nutzen den zentralen Request-Kontext; ein vollstaendiger Login-/Logout-/Route-Guard-Produktfluss fehlt weiterhin

## Teststatus

Pflicht-Tests:

- `unsupported file type`
- `broken parser`
- `OCR required`
- `file too large`
- `upload without auth`
- `upload foreign workspace`
- `duplicate upload sequential`

Status:

- Die Pflicht-Uploadtests laufen ohne Skip im API-Testlauf.
- Der echte PostgreSQL-Race-Test fuer parallele Duplicate-Uploads bleibt nur ohne `TEST_DATABASE_URL` ein Skip.
- Sobald `TEST_DATABASE_URL` gesetzt ist, muessen Alembic-Migrationen gruen sein; Migrationsfehler sind ein harter Testfehler.
- Verifikation 2026-05-06: Der Test sammelt lokal sauber und skippt nur noch bei fehlender `TEST_DATABASE_URL`; ein echter PostgreSQL-Lauf war in dieser Umgebung wegen nicht verfuegbarem Docker und Remote-Connection-Timeout nicht erfolgreich ausfuehrbar.

Nachweisgrenze:

- Duplicate-Verhalten ist im Backend und im sequentiellen API-Pfad gut belegt.
- Ein gruener echter PostgreSQL-Nachweis fuer paralleles Duplicate-Handling liegt aktuell nicht vor.

## Abschlussentscheidung fuer M4b

- Dokumentation aktualisiert: ja
- Upload-Flow im Code nachweisbar: ja
- Vollstaendige M4b-Produktreife gemaess Zielbild: nein
- Entscheidung: M4b ist im aktuellen Repository nicht abgeschlossen
