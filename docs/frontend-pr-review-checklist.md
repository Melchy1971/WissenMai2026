# GUI PR Review Checklist

Stand: 2026-05-18

Ziel: Diese Checkliste ist das operative Review-Minimum fuer GUI-PRs. Sie ersetzt keine Truth- oder Gate-Artefakte, stellt aber sicher, dass neue GUI-Aenderungen dieselben strategischen, betrieblichen und sicherheitsrelevanten Regeln respektieren.

Verbindliche Bezugsdokumente:

- `docs/frontend-strategic-principles.md`
- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-error-state-catalog.md`
- `docs/frontend-cache-governance.md`
- `docs/frontend-concurrency-safety.md`
- `docs/frontend-offline-degraded-strategy.md`
- `docs/operational-truth-governance.md`
- `docs/security.md`

## Review-Checkliste

### 1. Zustandsmodell

- Ist fuer den geaenderten Screen oder Slice ein expliziter Runtime-State erkennbar?
- Vermeidet der PR implizite State-Mischungen aus mehreren booleans oder ad-hoc Flags?
- Sind `loading`, `ready`, `empty`, `error`, `stale` und `degraded` fuer den betroffenen Scope geklaert?
- Verletzt der PR keine verbotene Transition aus `docs/frontend-runtime-state-machine.md`?

### 2. Fehlertransparenz

- Werden technische Fehler als Error-State und nicht als Empty-State dargestellt?
- Bleiben Fehlercode, Ursache und naechste Nutzeraktion sichtbar?
- Nutzt der PR das zentrale Error-Mapping statt eigener Fehlertexte pro Komponente?
- Fuehrt der PR keinen stillen Retry oder dekorativen Pseudo-Erfolg ein?

### 3. Recovery und Degraded

- Sind Retry, Reconnect, Restore, Reindex oder Queue-Degradierung sichtbar geregelt, falls der Slice betroffen ist?
- Bleibt Recovery nachvollziehbar statt als stiller Hintergrundpfad zu laufen?
- Werden stale Daten sichtbar markiert?
- Wird kein `ready` vor erneuter Validierung nach Recovery behauptet?

### 4. Drift und operative Wahrheit

- Macht der PR Drift-, Warning- oder Degraded-Signale sichtbar, wenn der Backend- oder Runtime-Zustand sie hergibt?
- Entsteht kein Fake-Green-Zustand bei unbekannter oder schlechter Evidenz?
- Vermeidet der PR versteckte Fallbacks auf alte Daten oder Default-Werte?
- Widerspricht die UI-Darstellung keinem aktuellen Truth- oder Gate-Artefakt?

### 5. Workspace- und Security-Kontext

- Ist der Slice klar an Auth- und Workspace-Kontext gebunden?
- Werden Workspace-Wechsel, Logout oder 401/403-Faelle korrekt behandelt?
- Umgeht der PR keine zentralen Guards, Rollen- oder Redaction-Regeln?
- Bleiben keine Daten eines alten Workspace im UI sichtbar?

### 6. Frontend-Abstraktionen

- Nutzt der PR den zentralen API-Client statt eigener Fetch-Sonderwege?
- Nutzt der PR Request-Ticketing, Cancellation und Snapshot-Schutz bei async Writes?
- Nutzt der PR ViewModel-/Presenter-Mapping fuer nichttriviale Response-zu-UI-Ableitungen?
- Hält der PR Cache-Governance mit `source_timestamp` oder `source_version` ein, wenn Cache betroffen ist?

### 7. Tests und Nachweise

- Gibt es einen passenden Test oder Report fuer den geaenderten GUI-Slice?
- Wurde kein fokussierter Testlauf als Full-GUI-Nachweis ueberdehnt?
- Wenn der PR produktionsnahe Aussagen trifft: gibt es einen aktuellen `frontend_truth_report.json` oder einen klar begrenzten Scope-Hinweis?
- Widerspricht der PR nicht dem Contract-Report oder einem aktuellen Gate-Report?

## Harte Review-Stopper

Ein GUI-PR darf nicht als freigabefaehig bewertet werden, wenn mindestens eines davon zutrifft:

- technischer Fehler wird als Empty-State gerendert
- degrade-, stale- oder drift-relevante Lage wird als gesund dargestellt
- async Response kann ohne Ticket-/Snapshot-Pruefung aktuellen State ueberschreiben
- Workspace-Isolation ist gebrochen oder nicht nachgewiesen
- Auth-, Forbidden- oder Recovery-Pfad ist unklar oder unsichtbar
- lokaler Testgrünstand wird benutzt, um roten Truth- oder Gate-Status zu relativieren
- der PR fuehrt eine neue lokale Sonderabstraktion ein, obwohl dafuer bereits ein zentraler Mechanismus existiert

## Review-Entscheidung

Ein GUI-PR ist nur dann architekturkonform reviewbar, wenn diese drei Aussagen gleichzeitig zutreffen:

- der Slice bleibt deterministisch und governance-konform
- der Slice fuehrt keine No-Go-Patterns aus `docs/frontend-strategic-principles.md` ein
- der Slice verschlechtert Truth-, Drift-, Recovery-, Contract- oder Security-Nachweis nicht