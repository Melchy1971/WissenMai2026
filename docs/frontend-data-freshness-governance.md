# Frontend Data Freshness Governance

Stand: 2026-05-18

Ziel: Das Frontend muss fuer jede relevante Datenart explizit regeln, wann Daten als frisch, stale, unknown oder nicht mehr verwendbar gelten. Freshness ist Teil der UI-Wahrheit und darf nicht implizit aus erfolgreichem Rendering oder altem Cache abgeleitet werden.

Verbindliche Bezugsdokumente:

- `docs/frontend-cache-governance.md`
- `docs/frontend-truth-surface-model.md`
- `docs/frontend-event-consistency-model.md`
- `docs/frontend-offline-degraded-strategy.md`
- `docs/frontend-runtime-state-machine.md`
- `docs/operational-truth-governance.md`

## Freshness Governance

### Grundregeln

- Jede gecachte Fachansicht braucht einen sichtbaren Freshness-Indikator oder einen expliziten Stale-Hinweis.
- Freshness ist immer workspace-scoped.
- `source_timestamp` oder `source_version` ist Pflicht fuer jede Freshness-Aussage.
- Ein erfolgreicher alter Request macht Daten nicht dauerhaft frisch.
- Reindex, Restore, Lifecycle-Wechsel, API-Ausfall, Reconnect und Queue-Degradierung koennen Freshness vorzeitig entwerten, auch vor Ablauf einer TTL.
- Stale Daten duerfen read-only sichtbar bleiben, aber nie als frische operative Wahrheit.
- Stale Retrieval ist verboten: Search- oder Quellenkontext, der stale oder unknown ist, darf nicht als neue Retrieval-Basis fuer Chat verwendet werden.

### Statusklassen

| Status | Bedeutung |
|---|---|
| `fresh` | aktuelle Evidenz innerhalb der erlaubten Schwelle |
| `stale` | letzte bekannte Evidenz ist noch sichtbar, aber nicht mehr frisch |
| `expired` | Cache darf nicht mehr als Grundlage fuer fachliche Aussagen oder Aktionen dienen |
| `unknown` | keine belastbare Freshness-Evidenz vorhanden |

## UI-Freshness-Regeln pro Datenart

### 1. Dokumentlisten

Freshness indicator:

- `Stand: <source_timestamp>` oder `Zuletzt aktualisiert: <Zeitpunkt>`
- bei stale zusaetzlich `Daten koennen veraltet sein`

Stale threshold:

- `60s` unter normalem `workspace_ready`
- sofort stale bei Workspace-Wechsel, Lifecycle-Mutation desselben Workspace, Restore-Beginn oder API-Unreachable

Auto refresh:

- ja, bei Route-Eintritt in `workspace_ready`
- ja, nach erfolgreichem Upload, Archive, Restore oder Delete im selben Workspace
- nein als dauerndes Polling im Hintergrund

Manual refresh Pflicht:

- ja, sobald die Liste `stale`, `expired`, `unknown` oder durch API-Fehler read-only ist

Cache expiry:

- `5 min` absolute TTL unter stabilem `workspace_ready`
- `0` bei Workspace-Wechsel oder Restore-Abschluss, danach zwingendes Refetch

### 2. Search Ergebnisse

Freshness indicator:

- sichtbarer Treffer-Stand, z. B. `Suchstand: <source_timestamp>`
- bei Reindex, Lifecycle-Aenderung oder Search-Fehler expliziter `stale`-Hinweis

Stale threshold:

- `30s` unter normalem `workspace_ready`
- sofort stale bei Reindex-Beginn, Lifecycle-Wechsel, Search-Error, Workspace-Wechsel oder API-Unreachable

Auto refresh:

- nein fuer alte Trefferlisten ohne neue Nutzeraktion
- ja nur fuer die aktive Suche nach explizitem Search-Submit oder nach Abschluss eines dokumentierten Reindex-Ende-Refreshs

Manual refresh Pflicht:

- ja, wenn Search stale ist und frische Treffer benoetigt werden
- ja nach Reindex-Ende fuer jede neue Suchwahrheit

Cache expiry:

- `2 min` absolute TTL
- `0` bei Reindex-Beginn, Workspace-Wechsel oder Lifecycle-Mutation im Workspace

### 3. Chat Retrieval

Freshness indicator:

- sichtbarer Hinweis auf Quellenfrische oder `Quellenstatus wird neu validiert`
- Retrieval-Kontext zeigt `fresh`, `stale`, `unknown` oder `maintenance`

Stale threshold:

- `0s` fuer neue Retrieval-Aktionen, sobald Search-Kontext stale, unknown, reindexing, restore-aktiv oder drift-degraded ist
- historischer Chat-Verlauf darf sichtbar bleiben, aber nur read-only

Auto refresh:

- nein fuer Retrieval-Basis im Hintergrund
- ja nur als explizites erneutes Retrieval bei neuer Nutzeraktion und gueltigem frischem Kontext

Manual refresh Pflicht:

- ja, bevor neue Chat-Nachrichten gesendet werden duerfen, wenn Retrieval-Kontext stale oder unknown ist

Cache expiry:

- Retrieval-Kontext TTL `30s` unter stabilem Search-Zustand
- sofort `expired` bei Reindex, Restore, Workspace-Wechsel, Lifecycle-Aenderung oder Search down

### 4. Diagnostics

Freshness indicator:

- verpflichtendes `Stand: <source_timestamp>`
- bei stale zusaetzlich `nicht aktuell bestaetigt`

Stale threshold:

- `15s` fuer Diagnostics Health unter normalem Betrieb
- sofort stale bei Reconnect, API-Unreachable, Restore, Reindex, Import-Ende oder Lifecycle-Mutation

Auto refresh:

- ja beim Oeffnen der Diagnostics-Route
- ja bei wieder erreichbarem Backend, sofern Route aktiv bleibt
- kein aggressives Dauerspolling ohne sichtbaren Nutzen

Manual refresh Pflicht:

- ja, sobald die Diagnostics stale oder unknown sind

Cache expiry:

- `60s` absolute TTL
- `0` bei Restore-Beginn/Ende, Reindex-Statuswechsel oder Workspace-Wechsel

### 5. Queue Status

Freshness indicator:

- sichtbarer Queue-Stand oder Warnhinweis `Queue-Status nicht aktuell bestaetigt`
- Queue-Warnung darf nicht ohne Zeitbezug erscheinen

Stale threshold:

- `20s` im Diagnostics-/Upload-Kontext
- sofort stale bei API-Unreachable, Reconnect, Restore oder Workspace-Wechsel

Auto refresh:

- ja, solange ein aktiver Upload- oder Queue-naher Screen sichtbar ist
- nein als globales unsichtbares Polling ueber alle Routen hinweg

Manual refresh Pflicht:

- ja, wenn Queue-Status fuer einen Upload-Start blockierend ist und die letzte Evidenz stale oder unknown ist

Cache expiry:

- `90s` absolute TTL
- `0` bei Restore, Workspace-Wechsel oder Route-Verlassen eines aktiven Upload-Kontexts, wenn kein anderer aktiver Queue-Slice vorhanden ist

### 6. Drift Anzeigen

Freshness indicator:

- sichtbarer Zeitbezug je Drift-Surface, z. B. `Drift-Stand: <source_timestamp>`
- unknown oder not-verified sichtbar markieren

Stale threshold:

- `60s` fuer UI-nahe Drift-Anzeigen aus Diagnostics
- sofort stale, wenn Diagnostics selbst stale oder unknown sind

Auto refresh:

- ja auf aktiven Diagnostics-Screens
- ja bei Rueckkehr aus `api_unreachable` oder `reconnecting`, wenn Drift-Surfaces sichtbar sind

Manual refresh Pflicht:

- ja, wenn Drift-Anzeigen Grundlage fuer operative Entscheidungen oder Admin-Diagnose sind und der Stand stale/unknown ist

Cache expiry:

- `5 min` absolute TTL fuer read-only Drift-Anzeigen
- `0` bei Restore-, Reindex-, Queue- oder Backup-bezogenen Zustandsspruengen, die den Driftzustand fachlich veraendern koennen

## Cache TTL Regeln

| Datenart | Fresh bis | Stale ab | Expired ab | Auto Refresh | Manual Refresh Pflicht |
|---|---|---|---|---|---|
| Dokumentlisten | 60s | > 60s oder invalidierendes Ereignis | 5 min | ja, ereignisgetrieben | ja bei stale/unknown |
| Search Ergebnisse | 30s | > 30s oder Reindex/Lifecycle/Search-Fehler | 2 min | nein, ausser neuer Suchlauf | ja fuer neue Suchwahrheit |
| Chat Retrieval Kontext | nur mit frischem Search-Kontext | sofort bei Search-Stale oder Betriebswechsel | 30s oder sofortiges Invalidierungsereignis | nein | ja vor neuem Senden |
| Diagnostics | 15s | > 15s oder Zustandsaenderung | 60s | ja auf aktiver Route | ja bei stale/unknown |
| Queue Status | 20s | > 20s oder Betriebswechsel | 90s | ja im aktiven Kontext | ja bei blockierender Unknown-Lage |
| Drift Anzeigen | 60s | > 60s oder stale Diagnostics | 5 min | ja auf aktiver Route | ja fuer operative Entscheidungen |

## Stale Data sichtbar markieren

### Pflichtregeln

- Jede stale Fachsurface zeigt einen sichtbaren Text-, Badge- oder Banner-Hinweis.
- Stale-Markierung braucht einen Grund, z. B. `Backend nicht erreichbar`, `Suchindex wird aktualisiert`, `Restore aktiv`, `Workspace gewechselt`.
- Ein bloesser Zeitstempel ohne Bewertung reicht nicht, wenn Aktionen blockiert oder Freshness fachlich relevant ist.
- Bei `expired` oder `unknown` duerfen Mutationen und neue Retrieval-Aktionen nicht auf dieser Datenbasis aufsetzen.

### Verboten

- stale Daten optisch gleich wie frische Daten darstellen
- stale Search oder Diagnostics als aktuell rendern
- stale Queue- oder Drift-Signale ohne Warncharakter darstellen

## Stale Retrieval verhindern

### Pflichtregeln

- Chat darf keine neue Retrieval-Operation starten, wenn Search Results, Index-Kontext oder Quellenstatus `stale`, `expired`, `unknown`, `reindexing` oder `restore_mode` sind.
- Reindex, Restore, Search down, Lifecycle-Wechsel und Workspace-Wechsel invalidieren neuen Retrieval-Kontext sofort.
- Historische Chat-Nachrichten duerfen sichtbar bleiben; nur neuer Retrieval-Write ist blockiert.
- Retrieval darf erst wieder als `fresh` gelten, wenn ein neuer erfolgreicher Search-/Retrieval-Lauf mit aktuellem Workspace-Kontext vorliegt.

### UI-Regeln

- Composer oder Send-Aktion zeigt `Retrieval-Kontext veraltet` oder aequivalent, wenn neue Quellenbasis nicht frisch ist.
- Der Nutzer bekommt eine klare Folgeaktion: `Suche aktualisieren`, `Erneut laden` oder `Nach Reindex erneut versuchen`.

## Degradation-Prinzipien

- Freshness verschlechtert sich konservativ, nicht optimistisch.
- Invalidierende Ereignisse schlagen TTLs: Reindex, Restore, Workspace-Wechsel und Lifecycle-Mutation machen Daten sofort stale oder expired.
- `unknown` ist besser als Fake-Green. Quelle: `reports/current/masterplan_status.json`.
- Kein Auto-Refresh-Mechanismus darf still blockierende Betriebszustaende ueberschreiben.
