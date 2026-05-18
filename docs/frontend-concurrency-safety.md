# Frontend Concurrency Safety

Stand: 2026-05-18

Ziel: Parallele Requests, Kontextwechsel und langsame Responses duerfen keine stale GUI-Zustaende ueberschreiben.

## Sicherheitsmodell

Jeder fachliche Request erhaelt ein Request-Ticket:

- `key`: Request-Familie, z. B. `documents:search` oder `chat:message`
- `sequence`: monotone Generation pro Request-Familie
- `authToken`: Auth-Snapshot beim Start
- `workspaceId`: Workspace-Snapshot beim Start
- `signal`: AbortSignal fuer Cancellation
- `correlationId`: optional propagierte Trace-ID

Eine Response darf State nur schreiben, wenn:

- das Ticket noch die aktuelle Generation fuer seinen `key` ist
- das AbortSignal nicht abgebrochen ist
- Auth-Token und Workspace-ID noch dem Start-Snapshot entsprechen
- die Route noch denselben fachlichen Zielkontext hat, z. B. dieselbe Chat-Session

## Request-Management

Quelle im Code: `frontend/src/api/requestCoordinator.js`.

| Bereich | Request-Key | Verhalten |
|---|---|---|
| Dokumentlisten | `documents:list` | neuer Listenrequest bricht vorherigen Listenrequest ab |
| Search Results | `documents:search` | neue Suche bricht alte Suche ab; alte Response darf State nicht ueberschreiben |
| Upload Start + Job Polling | `documents:upload` | paralleler Upload wird blockiert; Workspace-Wechsel/Unmount bricht Ticket ab |
| Chat Session List | `chat:sessions` | neue Sessionliste bricht alte Sessionliste ab |
| Chat Detail | `chat:detail` | Sessionwechsel bricht altes Detail ab |
| Chat Message/Retrieval | `chat:message` | paralleles Senden wird blockiert; Reconnect/Workspace-Wechsel macht alte Response stale |

## Gepruefte Problemfaelle

| Problemfall | Schutz |
|---|---|
| parallele Search Requests | Abort des alten `documents:search`-Tickets plus Generation-Check |
| parallele Upload Requests | `uploadInFlightRef` plus `documents:upload`-Ticket |
| Workspace-Wechsel waehrend Requests | `cancelAll()` und Workspace-Snapshot-Check |
| Logout waehrend laufender Requests | Auth-Snapshot-Check verhindert stale Writes |
| Reconnect waehrend Chat Retrieval | `chat:message`-Ticket verhindert stale Chat-Append nach Kontextwechsel |
| langsame/stale Responses | `isCurrent(ticket)` vor jedem State-Write |

## Correlation IDs

- `requestCoordinator.begin()` erzeugt automatisch eine `correlationId`.
- API-Wrapper reichen `correlationId` an `requestJson()` weiter.
- `requestJson()` propagiert sie als `X-Correlation-Id`.
- Manuelle IDs sind fuer Tests und externe Traces erlaubt.

## Optimistic UI

- Search und Listen nutzen keine optimistic UI.
- Upload zeigt `loading`/`polling` nur fuer das aktuelle Upload-Ticket.
- Chat schreibt neue User-/Assistant-Nachrichten erst nach erfolgreicher Backend-Response.
- Optimistische Mutationen sind nur erlaubt, wenn ein Rollback-Pfad und ein aktuelles Request-Ticket existieren.

## Tests

| Test | Ebene | Nachweis |
|---|---|---|
| `frontend/src/tests/api/RequestCoordinator.test.js` | Unit | Abort, Workspace-/Logout-Stale-Check, `cancelAll`, `correlationId` |
| `frontend/src/tests/pages/DocumentsPage.test.jsx` | Component Race Simulation | langsame parallele Search-Response ueberschreibt schnelle aktuelle Response nicht |
| `frontend/tests/gui_truth/test_12_concurrency.spec.js` | Browser gegen echte API | parallele Search Requests mit `route.continue()` und kuenstlichem Delay; Workspace-Wechsel waehrend realem Request |

Die Playwright-Tests nutzen echte API-Antworten. Delays werden nur vor `route.continue()` eingefuegt; Responses werden nicht gemockt.

## Offene Erweiterungen

- Chat-Retrieval-Reconnect als eigener Browser-E2E-Fall gegen echte API.
- Upload-Doppelklick-Race als eigener Browser-E2E-Fall gegen echte API.
- Stale-Indikatoren aus `docs/frontend-cache-governance.md` visuell in allen betroffenen Routen nachziehen.
