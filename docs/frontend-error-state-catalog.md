# Frontend Error-State Catalog

Stand: 2026-05-18  
Quelle fuer UI-Mapping: `frontend/src/view-models/errorCatalog.js`

Ziel: Technische Fehler duerfen nie als leere Datenlage erscheinen. Empty-States sind nur fuer erfolgreiche API-Antworten mit leerer Ergebnisliste erlaubt.

| Zustand | UI-Text | Technischer Code | Erlaubte Aktion | Retry | Logging |
|---|---|---|---|---|---|
| Backend nicht erreichbar | Backend nicht erreichbar. Das Backend ist nicht erreichbar. Es wurden keine Daten geladen. | `API_UNREACHABLE` | Erneut versuchen | ja | `warn gui_api_unreachable` |
| Login erforderlich | Login erforderlich. Die Sitzung ist abgelaufen oder es fehlt eine Anmeldung. | `AUTH_REQUIRED` | Zur Anmeldung wechseln | nein | `info gui_auth_required` |
| Zugriff verboten | Zugriff verboten. Der aktuelle Benutzer darf diese Aktion oder Ansicht nicht ausfuehren. | `FORBIDDEN` | Berechtigung pruefen | nein | `warn gui_forbidden` |
| Workspace fehlt | Workspace fehlt. Es ist kein validierter Workspace fuer diese Sitzung konfiguriert. | `WORKSPACE_NOT_CONFIGURED` | Workspace-Konfiguration pruefen | nein | `warn gui_workspace_missing` |
| Zeitueberschreitung | Zeitueberschreitung. Die Anfrage hat zu lange gedauert. Es wurden keine Daten geladen. | `TIMEOUT` | Erneut versuchen | ja | `warn gui_api_timeout` |
| Validierungsfehler | Validierungsfehler. Die Eingabe ist ungueltig oder unvollstaendig. | `VALIDATION_ERROR` | Eingabe korrigieren | nein | `info gui_validation_error` |
| Serverfehler | Serverfehler. Die Anfrage ist serverseitig fehlgeschlagen. Es wurden keine Daten geladen. | `SERVER_ERROR` | Spaeter erneut versuchen | ja | `error gui_server_error` |
| Import fehlgeschlagen | Import fehlgeschlagen. Der Import konnte nicht abgeschlossen werden. | `IMPORT_FAILED` | Datei pruefen und erneut importieren | nein | `error gui_import_failed` |
| OCR erforderlich | OCR erforderlich. Dieses Dokument benoetigt OCR, aber OCR ist nicht verfuegbar. | `OCR_REQUIRED` | OCR konfigurieren oder Textdatei importieren | nein | `warn gui_ocr_required` |
| Duplicate erkannt | Duplicate erkannt. Dieses Dokument ist bereits im Workspace vorhanden. | `DUPLICATE_DOCUMENT` | Vorhandenes Dokument oeffnen | nein | `info gui_duplicate_detected` |

## Regeln

- Fehlerzustand gewinnt immer gegen Empty-State.
- Direkte Retry-Aktionen sind fuer `API_UNREACHABLE`, `TIMEOUT` und manuelle `SERVER_ERROR`-Wiederholungen erlaubt.
- `FORBIDDEN`, `AUTH_REQUIRED`, `WORKSPACE_NOT_CONFIGURED`, `VALIDATION_ERROR`, `IMPORT_FAILED`, `OCR_REQUIRED` und `DUPLICATE_DOCUMENT` erzeugen keinen Retry-Loop.
- Backend-Domain-Codes duerfen sichtbar bleiben, muessen aber auf eine dieser technischen GUI-Klassen abgebildet werden.
- Backend-Meldungen werden als technische Details gehalten und duerfen den standardisierten UI-Text nicht ersetzen.
- Duplicate ist kein technischer Fehler, aber ein kontrollierter Import-Ausgang und darf nicht als generischer Erfolg ohne Hinweis erscheinen.

## UI-Mapping

| Quelle | Beispielcode | GUI-Zustand | Technischer Code | UI-Verhalten |
|---|---|---|---|---|
| Fetch-/Netzwerkfehler | `TypeError: Failed to fetch` | Backend nicht erreichbar | `API_UNREACHABLE` | Error-State statt leerer Liste, Retry erlaubt |
| Client-/Abort-Timeout | `AbortError`, `JOB_TIMEOUT` | Zeitueberschreitung | `TIMEOUT` | Error-State statt leerer Liste, Retry erlaubt |
| HTTP 401 / Auth-Bootstrap | `UNAUTHORIZED`, `AUTH_SESSION_EXPIRED` | Login erforderlich | `AUTH_REQUIRED` | Error-State, kein Retry-Loop |
| HTTP 403 | `FORBIDDEN`, `AUTH_FORBIDDEN`, `ADMIN_REQUIRED` | Zugriff verboten | `FORBIDDEN` | Error-State, Berechtigung pruefen |
| Workspace-Guards | `WORKSPACE_REQUIRED`, `AUTH_WORKSPACE_MISSING`, `AUTH_WORKSPACE_NOT_ALLOWED` | Workspace fehlt | `WORKSPACE_NOT_CONFIGURED` | Error-State, Workspace-Konfiguration pruefen |
| Validierung | `INVALID_QUERY`, `FILE_REQUIRED`, `FILE_TOO_LARGE` | Validierungsfehler | `VALIDATION_ERROR` | Error-State nahe der Aktion, Eingabe korrigieren |
| HTTP 5xx / Dienste | `SERVICE_UNAVAILABLE`, `LLM_UNAVAILABLE`, `DIAGNOSTICS_FAILED` | Serverfehler | `SERVER_ERROR` | Error-State statt leerer Liste, Retry erlaubt wenn transient |
| Import-Job fehlgeschlagen | `IMPORT_FAILED`, `PARSER_FAILED` | Import fehlgeschlagen | `IMPORT_FAILED` | Import-Error-State, Datei pruefen |
| OCR-Guard | `OCR_REQUIRED` | OCR erforderlich | `OCR_REQUIRED` | Import-Error-State, OCR konfigurieren |
| Duplicate-Import | `DUPLICATE_DOCUMENT`, `DUPLICATE_DETECTED` | Duplicate erkannt | `DUPLICATE_DOCUMENT` | Kontrollierter Hinweis mit vorhandenem Dokument |

## Tests

- `frontend/src/tests/view-models/ErrorCatalog.test.js` prueft Pflichtzustände, Aliase, Retry-Flags, Logging und stabile UI-Texte.
- `frontend/src/tests/components/ErrorState.test.jsx` prueft Darstellung von Fehlercode, technischem Code, Retry-Metadaten und Logging-Event.
- `frontend/src/tests/api/ClientErrors.test.js` prueft Netzwerk-, Timeout-, Auth-, Workspace-, Validierungs- und Serverklassifizierung.
- `frontend/src/tests/pages/DocumentsPage.test.jsx` prueft, dass Dokumentliste, Suche und Import Fehler nicht als Empty-State darstellen.
- `frontend/src/tests/auth/AuthBootstrap.test.jsx` prueft Auth-/Workspace-Bootstrap-Fehler als standardisierte GUI-Fehlerzustände.
