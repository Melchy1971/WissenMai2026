# Frontend Performance Governance

Stand: 2026-05-18

Ziel: Frontend-Performance wird nicht ueber isolierte Benchmark-Scores optimiert, sondern ueber deterministische Rendering-Flows, stabile Request-Ketten, kontrollierte Parallelitaet, vorhersehbare Ladezustaende und das Verhindern von Request-Stuermen. Performance darf Truth, Freshness, Recovery oder Workspace-Isolation nicht opfern.

Verbindliche Bezugsdokumente:

- `docs/frontend-telemetry-governance.md`
- `docs/frontend-concurrency-safety.md`
- `docs/frontend-event-consistency-model.md`
- `docs/frontend-data-freshness-governance.md`
- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-strategic-principles.md`
- `docs/operational-truth-governance.md`
- `docs/operational-sla-framework.md`

## Performance Governance

### Leitprinzipien

- Performance ist nur dann gut, wenn der UI-Zustand trotzdem deterministisch, wahr und nachvollziehbar bleibt.
- Weniger Requests sind nicht automatisch besser, wenn dadurch stale oder unknown Daten als frisch erscheinen.
- Schnellere Oberflaechen duerfen keine zentralen Schutzmechanismen wie Ticketing, Cancellation, Revalidation oder sichtbare Stale-Hinweise umgehen.
- Aggressive Caching ist nur erlaubt, wenn Freshness-, Workspace- und Truth-Governance weiter eingehalten werden.
- Ein kurzer Spinner ist besser als ein falscher Success-Zustand.

### Optimierungsziele

Optimiert werden:

1. deterministische Rendering-Flows
2. stabile Request-Ketten
3. kontrollierte Parallelitaet
4. vorhersehbare Ladezustaende
5. keine Request-Stuerme

Nicht optimiert werden:

- Benchmark-Scores allein
- lokale Renderzeiten ohne Zusammenhang zur End-to-End-Wahrheit
- Cache-Treffer auf Kosten von Freshness oder Workspace-Isolation
- vermeintliche Responsiveness durch optimistic completion ohne Nachweis

## Architekturregeln

### 1. Deterministische Rendering-Flows

- Jeder Screen rendert aus expliziten Runtime- und Datenzustaenden, nicht aus konkurrierenden Booleans.
- Ein Render-Flow darf kein Success-Screen zeigen, bevor die benoetigte Request-Kette erfolgreich validiert ist.
- Loading, stale, degraded, reconnecting und blocked sind legitime Performance-Zustaende; sie duerfen nicht aus kosmetischen Gruenden ausgeblendet werden.

### 2. Stabile Request-Ketten

- Jede relevante Request-Kette muss ticket-basiert, abbrechbar und snapshot-sicher sein.
- Teilketten wie Bootstrap -> Workspace-Validation -> Initial Data Load sind nur erfolgreich, wenn jeder Schritt noch im aktuellen Kontext gueltig ist.
- Nach Reconnect, Restore oder Workspace-Wechsel muessen alte Ketten verworfen statt weiterverwendet werden.

### 3. Kontrollierte Parallelitaet

- Parallelitaet ist nur erlaubt, wenn sie zu keinem stale overwrite, keinem Scope-Mix und keinem Request-Sturm fuehrt.
- Search, Chat-Retrieval und Upload-nahe Flows bleiben sequenzkontrolliert; neue Generationen verdrängen alte.
- Parallele Reads duerfen den UI-Zustand nur dann gemeinsam fortschreiben, wenn Scope und Frische kompatibel sind.

### 4. Vorhersehbare Ladezustaende

- Jeder Performance-kritische Flow braucht einen sichtbaren Ladezustand oder einen klaren read-only/stale Zustand.
- Kein endloser Spinner ohne Timeout-, Retry- oder Fehlerpfad.
- Kein abruptes Flackern zwischen `loading`, `ready` und `error` durch konkurrierende Requests.

### 5. Keine Request-Stuerme

- Auto-Refresh, Polling, Retry und Benutzeraktionen muessen gedrosselt, begrenzt und scope-kontrolliert sein.
- Es darf keinen globalen Reload-Loop fuer lokale Feature-Probleme geben.
- Reconnect- oder Queue-Recovery darf nicht zu ungebremstem Wiederanlaufen aller Requests fuehren.

## Metriken

Diese Metriken sind governance-relevant. Sie messen nicht nur Geschwindigkeit, sondern Stabilitaet und Kontrollverlust.

### Pflichtmetriken

| Metrik | Typ | Einheit | Scope | Definition | Warnschwelle | Kritische Schwelle |
|---|---|---|---|---|---|---|
| `fe_bootstrap_duration_ms` | gauge | ms | global | Dauer von App-Start/Session-Erkennung bis stabiler Entscheidung `workspace_ready`, `unauthenticated` oder `forbidden` | p95 > 2_000 ms im 15m-Fenster | p95 > 5_000 ms oder haeufige Blockierung |
| `fe_workspace_switch_duration_ms` | gauge | ms | workspace | Dauer vom Workspace-Wechsel bis neuer stabiler `workspace_ready`-Ansicht | p95 > 1_500 ms | p95 > 4_000 ms oder stale Daten bleiben sichtbar ohne Hinweis |
| `fe_search_latency_ms` | gauge | ms | workspace | Dauer vom Search-Submit bis sichtbarem Endzustand `results|empty|error|degraded` | p95 > 1_000 ms | p95 > 3_000 ms oder Request-Sturm |
| `fe_chat_retrieval_latency_ms` | gauge | ms | workspace | Dauer vom Chat-Senden bis sichtbarer Assistant-/Error-/Degraded-Antwort | p95 > 2_500 ms | p95 > 6_000 ms oder wiederholte Blockierung |
| `fe_stale_response_rate` | rate | ratio | workspace | Anteil verworfener stale Responses an allen Responses eines Flows oder Fensters | > 0.05 im 15m-Fenster | > 0.15 oder stetiger Anstieg |
| `fe_request_cancellation_rate` | rate | ratio | workspace | Anteil bewusst abgebrochener Requests an allen gestarteten Requests | > 0.10 in Search-/Switch-lastigen Flows beobachten | > 0.30 ausserhalb erwarteter Search-/Switch-Muster |

### Ableitungsregeln

- `fe_bootstrap_duration_ms` startet bei App-Start oder Session-Reentry und endet erst bei stabilem Runtime-Endzustand.
- `fe_workspace_switch_duration_ms` startet bei Nutzer- oder Systemwechsel des Workspace und endet erst nach erfolgreicher Kontextvalidierung plus erstem stabilen Route-Render.
- `fe_search_latency_ms` misst End-to-End fuer Search-Submit bis finalem sichtbaren Search-Outcome, nicht nur Netzwerkzeit.
- `fe_chat_retrieval_latency_ms` misst End-to-End fuer Message-Senden bis sichtbarer Antwort, Degradierung oder Fehler.
- `fe_stale_response_rate` nutzt stale drops aus dem Request-Ticketing als Zaehlerbasis.
- `fe_request_cancellation_rate` zaehlt nur kontrollierte Abbrueche, nicht Netzwerkfehler oder Timeouts.

### Datenschutz und Scope

- Keine Metrik darf Querytexte, Dokumenttitel, Chattexte oder andere Fachinhalte enthalten.
- Workspace-spezifische Performance-Metriken tragen genau eine `workspace_id`.
- Globale Metriken wie Bootstrap koennen `workspace_id = null` verwenden.

## UI-Freshness- und Truth-Schutz bei Performance

### Performance darf Truth nicht opfern

- Kein schnellerer Render-Pfad darf stale oder unknown Daten als fresh erscheinen lassen.
- Kein Preloading oder Cache-Reuse darf Workspace-Isolation unterlaufen.
- Kein Render-Shortcut darf `restore_mode`, `reconnecting`, `degraded` oder `forbidden` ueberspringen.

### Aggressive Caching nur governance-konform

- Aggressive Caching ist nur erlaubt, wenn TTL, Invalidierung, sichtbare Freshness-Indikatoren und read-only-Regeln bestehen bleiben.
- Search- und Retrieval-Kontext duerfen nicht aggressiv gecacht werden, wenn Reindex-, Lifecycle-, Restore- oder Drift-Signale aktiv sind.
- Diagnostics-Daten duerfen fuer Performance nie ohne `Stand`-Hinweis oder stale Markierung gehalten werden.

## Request-Sturm-Verhinderung

### Pflichtregeln

- Retry braucht Backoff und Abbruchbedingung.
- Polling braucht Zweckbindung, Sichtbarkeit und Exit-Kriterium.
- Search startet pro Nutzerinteraktion genau eine aktuelle Request-Generation.
- Workspace-Wechsel darf keine alten Requests nachlaufen lassen.
- Reconnect darf Requests nur kontrolliert wiederaufbauen, nicht alle unkoordiniert gleichzeitig.

### Verboten

- globale Reload-Schleifen bei lokalem Feature-Fehler
- Polling ohne maximale Lebensdauer oder ohne sichtbaren Zustand
- Retry-Loop bei `AUTH_REQUIRED`, `FORBIDDEN` oder `WORKSPACE_NOT_CONFIGURED`
- parallele Search-Requests ohne Cancellation
- Upload-Polling plus manuelle Reload-Schleifen ohne Koordination

## Anti-Pattern-Liste

### Verbotene Performance-Anti-Patterns

- Benchmark-Optimierung ohne Bezug zu Truth, Recovery oder Nutzerfluss
- Aggressives Vorladen, das stale oder falsche Workspace-Daten zuerst anzeigt
- Cache-first Rendering ohne sichtbare Freshness-Aussage
- Spinner-Vermeidung durch optimistische Erfolgsdarstellung
- Debounce/Throttle als Ersatz fuer Request-Ticketing und Snapshot-Pruefung
- Parallelisierung, die stale response drops oder cancellation rates stark erhoeht
- Request-Ketten ohne klaren Start- und Endzustand
- unsichtbare Hintergrund-Refresh-Loops, die die API oder Search unnoetig belasten
- Performance-Metriken ohne Unterscheidung zwischen `success`, `error`, `degraded` und `cancelled`
- Diagnose `schnell`, obwohl Nutzerpfad nur wegen unterdrueckter Fehler oder fehlender Hinweise kurz wirkt

### Warn-Anti-Patterns

- zu kurzes TTL-Tuning, das unnoetige Refetch-Stuerme erzeugt
- zu langes TTL-Tuning, das Freshness- und Drift-Regeln verletzt
- Workspace-Wechsel mit parallelem Prefetch alter und neuer Daten
- Hintergrund-Refresh waehrend `restore_mode`, `forbidden` oder `unauthenticated`

## Review- und Gate-Regeln

- Eine Performance-Verbesserung ist nur gueltig, wenn sie keinen Truth-, Freshness-, Recovery-, Contract- oder Security-Verstoss einfuehrt.
- Ein PR darf Performance nicht als Erfolg deklarieren, wenn stale response rate oder cancellation rate dadurch entgleisen.
- Performance-Aenderungen an Search, Chat, Upload, Bootstrap oder Workspace-Wechsel brauchen passende Telemetry- oder Truth-Nachweise fuer den betroffenen Slice.
- Lokale Benchmark-Ergebnisse ohne produktionsnahen Flow-Nachweis begruenden keinen Governance-Pass.
