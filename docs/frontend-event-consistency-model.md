# Frontend Event-Konsistenzmodell

Stand: 2026-05-18

Ziel: Die GUI reagiert auf viele asynchrone Ereignisse wie Upload-Abschluss, Queue-Retry, Reindex, Restore, Lifecycle-Wechsel und Reconnect. Diese Ereignisse duerfen nur dann UI-State veraendern, wenn Reihenfolge, Scope und Aktualitaet zum aktuellen Auth-, Workspace- und Routen-Kontext passen.

Verbindliche Bezugsdokumente:

- `docs/frontend-concurrency-safety.md`
- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-cache-governance.md`
- `docs/frontend-error-state-catalog.md`
- `docs/frontend-telemetry-governance.md`
- `docs/frontend-truth-surface-model.md`
- `frontend/src/api/requestCoordinator.js`
- `frontend/src/api/client.js`

## Event-Konsistenzmodell

### Grundmodell

Ein Frontend-Event ist jede asynchrone Information, die UI-State veraendern kann.

Dazu gehoeren insbesondere:

- Request-Responses
- Polling-Updates
- Reconnect-Ergebnisse
- Health-/Diagnostics-Signale
- Runtime-State-Uebergaenge
- Lifecycle-Rueckmeldungen
- Job-Statuswechsel wie Upload, Retry oder Reindex

Ein Event darf nur dann angewendet werden, wenn alle folgenden Bedingungen gelten:

- das Event gehoert zum aktuellen fachlichen Zielkontext
- Auth- und Workspace-Snapshot stimmen noch
- das Event ist nicht von einem neueren Event desselben Streams ueberholt
- das Event verschlechtert keine bereits bestaetigte Wahrheit zu einem scheinbar besseren Zustand
- das Event verletzt keine Runtime-State-Regel

## Reihenfolgeregeln

### 1. Stream-lokale Ordnung vor globaler Zeit

- Reihenfolge wird primär pro Event-Stream bewertet, nicht ueber globale Uhrzeit.
- Ein Stream ist z. B. `documents:upload`, `documents:search`, `chat:message`, `chat:detail`, `runtime`, `diagnostics`.
- Innerhalb eines Streams gewinnt nur das aktuellste gueltige Event.

### 2. Monotone Generation pro Stream

- Jeder request-getriebene Stream verwendet eine monotone `sequence` aus `requestCoordinator.begin()`.
- Eine spaetere Generation macht alle frueheren Events desselben Streams stale.
- Polling- und Replay-Events muessen logisch an dieselbe Stream-Generation gebunden sein oder explizit einen neuen Stream erzeugen.

### 3. Runtime-State hat Vorrang vor Detail-Events

- Eintritt in `unauthenticated`, `forbidden`, `workspace_loading`, `api_unreachable`, `reconnecting` oder `restore_mode` invalidiert Events, die noch `workspace_ready` voraussetzen.
- Kein Detail-Event darf eine verbotene Transition der Runtime-State-Machine erzeugen.
- Beispiel: Ein spaetes Upload-`completed` darf waehrend `restore_mode` oder nach Workspace-Wechsel keinen Success-State rendern.

### 4. Workspace-Wechsel ist harter Ordnungsbruch

- Ein Workspace-Wechsel beendet die Konsistenz alter fachlicher Event-Streams.
- Alle workspace-scoped Events aus dem alten Workspace sind nach dem Wechsel stale, auch wenn sie technisch spaeter eintreffen.

### 5. Recovery-Events brauchen Neuvalidierung

- Events nach Reconnect, Restore oder Reindex-Ende gelten nicht automatisch als voll belastbar.
- Der Weg zur Rueckkehr nach `workspace_ready` braucht frische Kontextvalidierung und gegebenenfalls Cache-Reload.

## Event Ordering Regeln pro Problemfall

### Upload fertig

- `queued -> running -> completed|failed|retryable|dead_letter|cancelled` ist die kanonische Reihenfolge.
- Ein Endzustand darf nur aus der Job-Quelle oder einem gleichwertigen Backend-Nachweis abgeleitet werden.
- Ein spaeter eintreffendes `running` nach bereits bestaetigtem `completed` ist stale.

### Reindex laeuft

- `not_active -> running -> finished|failed` ist kanonisch.
- Solange `running` oder `unknown` gilt, bleiben Search- und Retrieval-bezogene Flaechen stale oder maintenance.
- Ein spaeteres altes `not_active` darf ein aktuelles `running` nicht verdecken.

### Queue retry

- `failed|retryable -> retrying -> running|failed|dead_letter|completed` ist kanonisch.
- Retry ist kein Success-Ereignis.
- Ein Replay oder Retry-Zaehler muss sichtbar bleiben und darf nicht als frischer Ersterfolg erscheinen.

### Restore aktiv

- `normal -> restore_mode -> revalidate -> workspace_ready|unauthenticated` ist kanonisch.
- Fach-Events aus dem Vor-Restore-Kontext sind nach Eintritt in `restore_mode` stale.
- Restore-Ende allein reicht nicht fuer Success; erst Revalidierung hebt den Blockzustand auf.

### Lifecycle-Wechsel

- `active -> archived -> restored(active)` oder `active|archived -> deleted` ist kanonisch gemäss Backend-Zustandslogik.
- Ein spaetes altes Detail-Event darf einen neuen Lifecycle-Status nicht ueberschreiben.
- Historische Citations muessen bei spaeter eintreffenden Lifecycle-Ereignissen ihren `source_status` sichtbar korrigieren.

## Stale-Event Strategie

### Stale-Erkennung

Ein Event ist stale, wenn mindestens eine Bedingung gilt:

- seine Stream-`sequence` ist nicht mehr aktuell
- sein `AbortSignal` ist abgebrochen
- `authToken` stimmt nicht mehr mit dem Start-Snapshot ueberein
- `workspaceId` stimmt nicht mehr mit dem Start-Snapshot ueberein
- der Routen- oder Objektkontext stimmt nicht mehr, z. B. andere Chat-Session oder anderes Dokument
- ein neuerer Runtime-State blockiert die Anwendung

### Stale-Behandlung

- Stale-Events werden verworfen, nicht gemerged.
- Das Verwerfen eines stale Events ist kein Fehler, sondern ein kontrollierter Schutzmechanismus.
- Stale-Event-Verwerfungen duerfen Telemetry erzeugen, z. B. `fe_stale_response_drops_total`.

### Sichtbarkeitsregel

- Stale-Verwerfung darf nie zu stiller Success-UI fuehren.
- Wenn durch Verwerfung die letzte bestaetigte Wahrheit unklar bleibt, zeigt die UI `stale`, `unknown` oder den letzten sicheren read-only Zustand.

## Idempotente UI Updates

### Grundregel

- Jedes Event-Update muss idempotent sein: mehrfaches Anwenden desselben fachlich identischen Events darf keinen neuen falschen Zustand erzeugen.

### Pflichtregeln

- Endzustaende wie `completed`, `failed`, `forbidden`, `restore_mode` oder `archived` duerfen mehrfach gesetzt werden, ohne Zusatznebenwirkungen auszulösen.
- UI-Updates duerfen nicht an inkrementelle lokale Annahmen gekoppelt sein, wenn die Quelle einen kompletten Snapshot liefert.
- Merge-Logik muss konservativ sein: Ein Event darf bestaetigte Warn- oder Fehlerzustände nur mit gleichwertiger oder staerkerer Evidenz aufheben.

### Beispiele

- wiederholtes Upload-`completed` zeigt denselben Endzustand, startet aber keinen zweiten Success-Flow
- wiederholtes `restore_mode` oeffnet nicht mehrfach denselben Recovery-Dialog
- wiederholtes `forbidden` fuehrt nicht zu wiederholtem Redirect-Loop

## Workspace-scoped Event Isolation

### Isolationsregeln

- Jedes fachliche Event ist an genau einen Workspace gebunden oder explizit global.
- Events ohne gueltigen Workspace-Kontext duerfen keinen workspace-scoped Fachzustand fortschreiben.
- Ein globales Runtime-Event darf lokale Workspace-Slices blockieren, aber nicht mit Daten aus mehreren Workspaces schreiben.

### Verboten

- Event-Merge ueber zwei Workspaces hinweg
- Fortschreiben alter Listen-, Search-, Upload- oder Chat-States nach Workspace-Wechsel
- Wiederverwendung lokaler optimistic State-Fragmente aus dem alten Workspace

## correlation_id propagation

### Ist-Regel

- `requestCoordinator.begin()` erzeugt eine `correlationId`.
- `requestJson()` propagiert sie als `X-Correlation-Id`.
- Telemetry erlaubt `correlation_id` optional fuer technische Verkettung.

### Verbindliche Regeln

- Jeder request-getriebene Event-Stream soll dieselbe `correlationId` von Request bis Response-Verarbeitung tragen.
- Polling-Events duerfen entweder dieselbe Ursprungs-`correlationId` fortfuehren oder eine klar verknuepfte Folge-ID nutzen; die Beziehung muss technisch nachvollziehbar bleiben.
- `correlation_id` ist niemals Wahrheitsquelle fuer Ordnung, sondern nur Trace-Hilfe.
- `correlation_id` darf keine Nutzerinhalte, Dokumenttitel, Querytexte oder Chatfragmente enthalten.

### Pruefstatus

- Die technische Propagation ist im aktuellen Frontend-Client vorhanden.
- Fuer Browser-Truth und Replay-/Reconnect-Pfade bleibt der Nachweis weiter verifizierbar, nicht bloss dokumentiert.

## Event Replay Handling

### Replay-Regeln

- Ein Replay-Event ist kein neues unabhaengiges Wahrheitsereignis, sondern ein erneuter Zustellversuch fuer denselben fachlichen Strom oder einen explizit neu gestarteten Reparaturstrom.
- Replays muessen idempotent verarbeitet werden.
- Replay darf einen bereits neueren Endzustand nicht ueberschreiben.
- Replay muss sichtbar als Replay, Retry oder erneuter Versuch klassifizierbar bleiben, falls es fachlich relevant ist.

### Verboten

- Replay eines alten Events als frischen Success darstellen
- Replay ohne Sequence-/Snapshot-Pruefung anwenden
- Replay nutzen, um rote oder warnende Zustände still auf gruen zu drehen

## Reconnect Event Recovery

### Reconnect-Regeln

- Eintritt in `reconnecting` friert Mutationen ein und markiert bestaetigte Daten als read-only oder stale.
- Alte Responses aus dem Vor-Reconnect-Kontext duerfen nach Snapshot-Wechsel keinen State schreiben.
- Reconnect-Erfolg fuehrt erst nach Kontextvalidierung zu `workspace_ready`.
- Fehlgeschlagener Reconnect fuehrt deterministisch zu `api_unreachable`, `unauthenticated` oder `forbidden` gemaess Runtime-State-Machine.

### Recovery-Pfad

1. Eintritt in `reconnecting`
2. Mutationen blockieren, laufende kritische Streams einfrieren oder verwerfen
3. Retry/Backoff ausfuehren
4. Auth-/Workspace-Kontext neu pruefen
5. stale Caches nachladen
6. erst dann `workspace_ready`

### UI-Regel

- Während Reconnect bleibt die letzte sichere Ansicht read-only sichtbar.
- Kein automatischer Wechsel auf verdeckten Normalbetrieb ohne frischen Nachweis.

## Degradation-Prinzipien fuer Events

- Out-of-order Events duerfen niemals zu Fake-Green fuehren.
- Wenn Ordering nicht sicher belegbar ist, gewinnt der konservativere Zustand.
- `unknown`, `stale`, `retrying`, `reconnecting` und `maintenance` sind legitime Zwischenzustaende.
- Completion ohne verifizierten Endnachweis ist verboten.

## Verboten

- implizite Annahme, dass spaeter angekommen immer frischer bedeutet
- Event-Anwendung ohne Sequence-, Snapshot- oder Scope-Pruefung
- optimistic completion ohne Backend-Endnachweis
- Merge von Events verschiedener Workspaces
- Route-Wechsel ignorieren und spaete Responses trotzdem rendern
- Reconnect oder Restore als stillen Hintergrundpfad behandeln
- `correlation_id` als Ersatz fuer Sequence- oder Runtime-Regeln missbrauchen