# Frontend Telemetry Governance

Stand: 2026-05-18

Ziel: Frontend-Telemetry macht degradierte GUI-Zustaende, Bootstrap-Probleme, Fachfehler und Concurrency-Verluste messbar, ohne sensitive Inhalte zu erfassen. Telemetry ist kein Ersatz fuer Runtime-State-Machine oder Error-State-Catalog, sondern deren maschinenlesbare Betriebsableitung.

Verbindliche Bezugsdokumente:

- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-cache-governance.md`
- `docs/frontend-concurrency-safety.md`
- `docs/frontend-error-state-catalog.md`
- `docs/m5-observability.md`
- `frontend/src/api/requestCoordinator.js`
- `frontend/src/api/client.js`

## Telemetry-Modell

Frontend-Telemetry besteht aus drei Ebenen:

| Ebene | Zweck | Scope |
|---|---|---|
| Runtime Event | einzelner messbarer Frontend-Vorfall | Request-, Route- oder Bootstrap-Ebene |
| Aggregated Metric | zaehl- oder ratefaehige Metrik | Workspace oder global |
| State Snapshot | aktueller degradierter Frontend-Zustand | Workspace oder global |

Telemetry darf nur aus expliziten GUI-Zustaenden, standardisierten Fehlerklassen, Request-Tickets oder Request-Ausgaengen entstehen. Leere Daten, fehlende Anzeigen oder freie Logtexte sind keine Telemetry-Quelle.

### Event-Schema

Jedes Frontend-Telemetry-Event nutzt dieses Grundschema:

```json
{
  "event_name": "frontend_metric_observed",
  "metric_name": "fe_api_error_rate",
  "event_version": "1",
  "generated_at": "2026-05-18T12:00:00Z",
  "status": "ok",
  "value": 0.0,
  "unit": "ratio",
  "kind": "rate",
  "aggregation_scope": "workspace",
  "workspace_id": "workspace-uuid",
  "route": "/documents",
  "feature": "documents",
  "window": "current",
  "dimensions": {
    "result": "success"
  },
  "correlation_id": "optional-trace-id"
}
```

Pflichtfelder:

- `event_name`
- `metric_name`
- `event_version`
- `generated_at`
- `status`
- `value`
- `unit`
- `kind`
- `aggregation_scope`
- `workspace_id`
- `route`
- `feature`
- `window`
- `dimensions`

Optional:

- `correlation_id`

`correlation_id` ist fuer Tracing erlaubt, aber nicht verpflichtend. Fehlt sie, bleibt das Event gueltig. Sie darf nicht durch fachliche Inhalte ersetzt werden.

### Erlaubte Werte

`status` verwendet nur:

- `ok`
- `watch`
- `degraded`
- `blocked`
- `unknown`

`kind` verwendet nur:

- `counter`
- `rate`
- `gauge`

`aggregation_scope` verwendet nur:

- `workspace`
- `global`

### Erlaubte Dimensionen

- `metric_source`
- `operation`
- `result`
- `error_code`
- `runtime_state`
- `feature`
- `route_group`
- `window`

Dimensionen muessen kontrollierte Enum-Werte oder kleine technische Codes enthalten. Keine Freitext-Payloads.

## Datenschutzregeln

Frontend-Telemetry ist strikt metadatenbasiert.

Nicht erfassen:

- Dokumenttexte
- Chunktexte
- Dokumenttitel
- Dateinamen
- Dateipfade
- Chattexte
- Nutzerfragen
- Assistant-Antworten
- Citation-Previews
- Query-Texte
- Tokens, Secrets, Session-Inhalte
- freie `details`-Objekte aus Backend-Fehlern

Erlaubt sind nur:

- technische Fehlercodes wie `API_UNREACHABLE`, `FORBIDDEN`, `TIMEOUT`, `RETRIEVAL_FAILED`
- Route-Gruppen wie `documents`, `chat`, `auth`, `admin_diagnostics`
- Runtime-States wie `authenticating`, `workspace_loading`, `degraded`, `reconnecting`
- Aggregatwerte wie Counts, Ratios, Window-Buckets
- `workspace_id` fuer workspace-scoped Metriken
- optionale `correlation_id`

### Workspace-Aggregation

- Workspace-Metriken tragen genau eine `workspace_id`.
- Globale Metriken setzen `workspace_id = null`.
- Kein Roh-Event darf mehrere Workspaces in einem Event mischen.
- Cross-Workspace-Auswertungen entstehen nur aus spaeterer Aggregation, nie aus einem Misch-Event.
- Workspace-IDs duerfen nicht mit Dokumenttiteln, Dateinamen, Query-Texten oder Chat-Inhalten kombiniert werden.

### Correlation-Regeln

- `correlation_id` ist optional.
- Wenn vorhanden, kommt sie aus `requestCoordinator.begin()` oder einem bewusst gesetzten externen Trace-Kontext.
- `correlation_id` darf keine Nutzereingaben, Queryteile, Dokumentnamen oder Chatfragmente kodieren.
- Correlation dient nur zur technischen Verkettung von Request, Fehler und Response-Verwerfung.

## Frontend-Metriken

### Pflichtmetriken

| Metrik | Typ | Einheit | Scope | Definition | Warnschwelle | Kritische Schwelle |
|---|---|---|---|---|---|---|
| `fe_api_error_rate` | rate | ratio | workspace | Anteil fehlgeschlagener Fachrequests an allen Fachrequests eines Workspace | > 0.05 im 15m-Fenster | > 0.15 im 15m-Fenster oder 3 Fenster negativ |
| `fe_bootstrap_failures_total` | counter | events | global | fehlgeschlagene Auth-Bootstrap-Laeufe vor validiertem Nutzer-/Workspace-Kontext | > 0 im aktuellen Release-Fenster | persistierend oder letzter Bootstrap blockiert |
| `fe_workspace_bootstrap_failures_total` | counter | events | workspace | fehlgeschlagene Workspace-Validierung nach vorhandenem Token | > 0 pro Workspace | wiederholt oder kombiniert mit `FORBIDDEN`/`WORKSPACE_NOT_CONFIGURED` |
| `fe_search_failures_total` | counter | events | workspace | fehlgeschlagene Search-Requests oder Search-Responses mit Error-State | > 0 im 15m-Fenster | wiederholt oder gekoppelt mit `degraded`/`reconnecting` |
| `fe_upload_failures_total` | counter | events | workspace | fehlgeschlagene Upload-Starts oder Polling-Enden im Fehlerzustand | > 0 im 15m-Fenster | wiederholt, `JOB_TIMEOUT` oder Queue-bezogener Blocker |
| `fe_chat_retrieval_failures_total` | counter | events | workspace | fehlgeschlagene Chat-Retrieval-/Post-Message-Vorgaenge | > 0 im 15m-Fenster | wiederholt oder `RETRIEVAL_FAILED`/`LLM_UNAVAILABLE` im Cluster |
| `fe_stale_response_drops_total` | counter | drops | workspace | Responses, die wegen Ticket-Generations-, Auth- oder Workspace-Mismatch verworfen wurden | > 0 bei einem Flow | sprunghafter Anstieg oder regelmaessig je Route |
| `fe_reconnect_events_total` | counter | events | workspace | Uebergaenge in `reconnecting` nach zuvor validiertem Kontext | > 0 im 15m-Fenster | wiederholt oder gefolgt von `api_unreachable` |

### Quellen pro Metrik

| Metrik | Primaere Quelle | Trigger |
|---|---|---|
| `fe_api_error_rate` | `requestJson()` + standardisierte Fehlerklassifizierung | `ApiClientError`, HTTP-Fehler, Timeout, Netzwerkfehler |
| `fe_bootstrap_failures_total` | `AuthContext` Bootstrap-Flow | `mapBootstrapFailure(error)` oder validierter Bootstrap-Error |
| `fe_workspace_bootstrap_failures_total` | Auth-/Workspace-Validierung | fehlende Membership, ungueltiger aktiver Workspace, `FORBIDDEN` |
| `fe_search_failures_total` | Dokumentsuche | `searchState.status = error` |
| `fe_upload_failures_total` | Upload-Start und Job-Polling | `uploadState.status = error` |
| `fe_chat_retrieval_failures_total` | Chat Message/Post-Retrieval | `detailState.status = error` nach `chat:message` |
| `fe_stale_response_drops_total` | `requestCoordinator.isCurrent(ticket)` | Response wird verworfen statt State zu schreiben |
| `fe_reconnect_events_total` | Runtime-State-Machine | Transition `workspace_ready|degraded -> reconnecting` |

### Degraded Frontend States messbar machen

Die Runtime-State-Machine ist die normative Quelle. Telemetry misst degradierte Frontend-Zustaende ueber Events und Snapshots, nicht ueber implizite UI-Heuristiken.

| Frontend-State | Messsignal | Abgeleitete Metrik |
|---|---|---|
| `degraded` | State-Eintritt, betroffener Feature-Bereich, Dauer bis Aufloesung | `fe_frontend_state_degraded_total`, optional Dauer-Gauge |
| `reconnecting` | jeder Eintritt und Ausgang | `fe_reconnect_events_total` |
| `api_unreachable` | globaler API-Fehlerzustand | Anteil in `fe_api_error_rate`, optional Snapshot |
| `restore_mode` | Eintritt/Austritt in Read-only-Blockzustand | `fe_frontend_state_restore_mode_total` |
| `forbidden` | Bootstrap- oder Fachrequest-Blockierung | Bootstrap- oder Workspace-Failure-Counter |

Pflichtregel: Ein degradierter Frontend-Zustand ist messbar, wenn mindestens ein Runtime-Event und eine aggregierbare Metrik daraus entstehen. Ein sichtbarer Banner ohne Telemetry gilt als unvollstaendige Governance.

## Ableitungsregeln

### API Error Rate

```text
fe_api_error_rate =
  failed_api_requests / total_api_requests
```

Zaehlt nur technische Request-Ausgaenge. Validierte Empty-Responses sind keine Fehler. Abgebrochene Requests zaehlen nur dann als Fehler, wenn sie in einen sichtbaren Error-State fuehren; stale Drops zaehlen separat.

### Bootstrap Failures

Zaehlt:

- `AUTH_BOOTSTRAP_FAILED`
- `AUTH_SESSION_EXPIRED`
- `AUTH_FORBIDDEN`
- `API_UNREACHABLE` und `TIMEOUT` waehrend Auth-Bootstrap

Nicht zaehlen:

- manuelle Logout-Aktionen
- bewusstes Leeren lokaler Session-Daten

### Workspace Bootstrap Failures

Zaehlt nur Fehler nach vorhandenem Token, wenn kein gueltiger `active_workspace_id` hergestellt werden kann.

Beispiele:

- Membership fehlt
- Ziel-Workspace nicht in Memberships
- `WORKSPACE_NOT_CONFIGURED`
- `FORBIDDEN` auf workspace-scoped Fachrequest waehrend Bootstrap/Refresh

### Search Failures

Zaehlt nur Suchfehler mit sichtbarem Search-Error-State.

Nicht zaehlen:

- leere Suchtreffer bei HTTP 200
- verworfene Search-Responses wegen neuerer Suche

### Upload Failures

Zaehlt:

- Fehler beim Start von `POST /documents/import`
- Polling-Ende mit `failed`
- `JOB_TIMEOUT`
- Polling-Abbruch nach zu vielen Netzwerkfehlern

Nicht zaehlen:

- Duplicate-Hinweise als kontrollierter Ausgang
- manueller Formularabbruch ohne Request

### Chat Retrieval Failures

Zaehlt:

- `RETRIEVAL_FAILED`
- `INSUFFICIENT_CONTEXT` nur dann, wenn der GUI-Vertrag es als Fehlerzustand und nicht als kontrollierten No-Answer-Zustand behandelt
- `LLM_UNAVAILABLE`
- API-/Timeout-Fehler im `chat:message`-Pfad

### stale response drops

Zaehlt jedes Ticket, dessen Response wegen mindestens eines dieser Gruende nicht schreiben darf:

- `sequence` nicht mehr aktuell
- `AbortSignal` abgebrochen
- Auth-Snapshot geaendert
- Workspace-Snapshot geaendert
- fachlicher Zielkontext geaendert, z. B. Chat-Session-Wechsel

Diese Metrik ist kein Fehlerindikator fuer den Nutzer, aber ein Pflichtsignal fuer Concurrency-Druck und UI-Stabilitaet.

### reconnect events

Zaehlt jeden Eintritt in `reconnecting`.

Ein reconnect event muss mindestens diese Dimensionen tragen:

- `runtime_state=reconnecting`
- `feature`
- `result=entered|recovered|failed`

## Statuslogik

| Telemetry-Status | Bedeutung |
|---|---|
| `ok` | Metrik berechenbar, keine Schwelle verletzt |
| `watch` | einzelner Vorfall oder fruehe negative Tendenz |
| `degraded` | wiederholte Fehler, negative Folgefenster oder sichtbarer Runtime-Degraded-State |
| `blocked` | Bootstrap dauerhaft blockiert, API systemisch nicht erreichbar oder Privacy-/Aggregation-Regel verletzt |
| `unknown` | Messung fehlt, Eventquelle nicht angeschlossen oder Scope nicht ableitbar |

## Implementierungsanker

- `frontend/src/api/client.js` fuer API-Fehlerklassifizierung und `correlationId`-Weitergabe
- `frontend/src/api/requestCoordinator.js` fuer Ticket-Lebenszyklus und stale response drops
- `frontend/src/auth/AuthContext.jsx` fuer Bootstrap- und Workspace-Bootstrap-Fehler
- `frontend/src/pages/DocumentsPage.jsx` fuer Search-/Upload-Fehler
- `frontend/src/pages/ChatPage.jsx` fuer Chat-Retrieval-Fehler

## Gate-Regeln

Frontend Telemetry Governance gilt nur dann als erfuellt, wenn:

- alle acht Pflichtmetriken definiert sind
- degradierte Frontend-Zustaende maschinenlesbar messbar sind
- keine sensitiven Inhalte in Telemetry-Dimensionen oder Events enthalten sind
- Workspace-Events genau eine `workspace_id` tragen
- globale Events `workspace_id = null` setzen
- `correlation_id` optional bleibt und nicht als Pflichtfeld missbraucht wird
- stale response drops getrennt von echten API-Fehlern ausgewiesen werden
