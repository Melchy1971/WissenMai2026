# Frontend Recovery UX Modell

Stand: 2026-05-18

Ziel: Recovery fuer degradierte Zustaende muss im Frontend transparent, nachvollziehbar und deterministisch sein. Der Nutzer muss sehen, warum ein Zustand eingeschraenkt ist, welche Aktionen noch erlaubt sind, was blockiert bleibt, wie Retry funktioniert und wodurch Recovery wieder in einen belastbaren Zustand uebergeht.

Verbindliche Bezugsdokumente:

- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-offline-degraded-strategy.md`
- `docs/frontend-error-state-catalog.md`
- `docs/frontend-event-consistency-model.md`
- `docs/frontend-cache-governance.md`
- `docs/controlled-failure-philosophy.md`

## Recovery UX Modell

### Grundprinzipien

- Recovery ist ein sichtbarer UI-Zustand, kein stiller Hintergrundpfad.
- Jede Recovery-Situation braucht einen sichtbaren Hinweis, erlaubte und blockierte Aktionen, eine Retry-Strategie und einen expliziten Recovery-Trigger.
- Der Weg zur Rueckkehr in `workspace_ready` oder einen gesunden Feature-Zustand braucht frische Validierung.
- Recovery darf keine Fake-Green-Phasen erzeugen.
- Die letzte sichere Ansicht darf read-only sichtbar bleiben, wenn sie klar als stale oder eingeschraenkt markiert ist.

### Statusklassen

| Klasse | Bedeutung |
|---|---|
| `recovering` | Frontend versucht einen transienten oder erwarteten Fehler kontrolliert zu ueberwinden |
| `blocked` | Nutzeraktion ist bis zu einem externen oder technischen Trigger blockiert |
| `maintenance` | System befindet sich in einem kontrollierten Betriebsmodus |
| `reauth_required` | Recovery braucht neue Authentifizierung |
| `workspace_revalidate` | Recovery braucht neue Workspace-Validierung |

## Szenarien

### 1. Backend Restart

Normativer Runtime-State: `reconnecting` oder `api_unreachable`

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | globaler Banner `Backend wird neu verbunden` oder `Backend nicht erreichbar`; letzte sichere Daten als stale/read-only markiert |
| Erlaubte Aktionen | Navigation, manueller Retry, read-only Sicht auf vorhandene stale Daten |
| Blockierte Aktionen | Upload, Chat senden, Lifecycle-Mutationen, neue fachliche Mutationen |
| Retry Strategie | automatischer Retry mit Backoff plus manueller Retry-Button |
| Recovery Trigger | erfolgreicher API-Health-/Bootstrap-Check mit gueltigem Auth-/Workspace-Kontext |

Recovery UX Regel:

- Wechsel zur gesunden Ansicht erst nach erfolgreicher Kontextvalidierung, nicht nach bloesser Netzwerkverbindung.

### 2. DB Restart

Normativer Zustand: global `degraded` oder `api_unreachable`, je Fehlerbild

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | technischer Banner `Datenbank voruebergehend nicht verfuegbar` oder `Datenstand wird wieder verbunden` |
| Erlaubte Aktionen | Navigation, read-only auf bereits bestaetigte stale Daten, manueller Retry |
| Blockierte Aktionen | Upload, Search als frisch, Chat senden, Lifecycle-Mutationen, Diagnostics als aktuell behaupten |
| Retry Strategie | automatischer Reconnect fuer transienten DB-Ausfall, manueller Retry fuer betroffene Route |
| Recovery Trigger | erfolgreicher Fachrequest oder Diagnostics-/Health-Nachweis nach DB-Erholung |

Recovery UX Regel:

- DB-Rueckkehr setzt betroffene stale Caches nicht automatisch auf fresh; ein neuer erfolgreicher Read ist erforderlich.

### 3. Restore laeuft

Normativer Runtime-State: `restore_mode`

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | globaler Restore-Banner `System wird wiederhergestellt`; Read-only-Modus klar sichtbar |
| Erlaubte Aktionen | minimale read-only Navigation, Sicht auf Hinweise, Refresh nach Abschluss |
| Blockierte Aktionen | Upload, Search als frisch, Chat senden, Lifecycle-Mutationen, Workspace-sensitive Fachmutationen |
| Retry Strategie | kein fachlicher Retry waehrend Restore; nur Refresh/Neuladen nach Abschluss |
| Recovery Trigger | Restore-Ende plus Auth-/Workspace-Neuvalidierung plus Cache-Invalidierung |

Recovery UX Regel:

- Restore-Ende allein beendet die UX-Recovery nicht; erst Revalidierung fuehrt aus `restore_mode` heraus.

### 4. Queue degraded

Normativer Zustand: `degraded`

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | Queue-Warnhinweis im Upload-Bereich plus optionaler globaler Warnbanner |
| Erlaubte Aktionen | Dokumente lesen, Search lesen sofern gesund, Chat-Verlauf lesen, Diagnostics lesen |
| Blockierte Aktionen | Upload starten, queue-abhaengige Mutationen, implizite Erfolgsaussagen fuer laufende Jobs |
| Retry Strategie | kein Auto-Retry-Spam; manueller Retry nach sichtbarer Fehlermeldung und erneuter Queue-Bestaetigung |
| Recovery Trigger | frischer Queue-Health-/Diagnostics-Nachweis ohne blockierende Degradierung |

Recovery UX Regel:

- Retry ist nur zulaessig, wenn die Queue-Surface nicht mehr stale oder unknown ist.

### 5. Search unavailable

Normativer Zustand: feature-spezifisch `degraded` oder `unavailable`

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | lokaler Search-Error-State `Search aktuell nicht verfuegbar` oder `Search eingeschraenkt` |
| Erlaubte Aktionen | Dokumentlisten lesen, Dokumentdetail lesen, Chat-Historie read-only lesen |
| Blockierte Aktionen | neue Search-Erfolge behaupten, frisches Retrieval auf stale Search-Basis, Search-basierte Mutationen |
| Retry Strategie | lokaler manueller Retry; kein globaler Retry-Loop |
| Recovery Trigger | erfolgreicher Search-Request mit aktuellem Workspace-Kontext |

Recovery UX Regel:

- Leere Trefferliste ist niemals Recovery-Indikator nach technischem Search-Fehler.

### 6. Chat Retrieval degraded

Normativer Zustand: feature-spezifisch `degraded`

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | Hinweis im Chat `Quellenbasis eingeschraenkt` oder `Retrieval aktuell degradiert` |
| Erlaubte Aktionen | Chat-Verlauf lesen, Sessionliste lesen, Dokumente lesen, Suche nutzen sofern gesund |
| Blockierte Aktionen | neue Chat-Nachricht mit retrieval-gestuetzter Antwort, wenn Retrieval-Kontext stale, unknown oder degraded ist |
| Retry Strategie | lokaler Retry fuer `TIMEOUT`, `SERVER_ERROR`, `API_UNREACHABLE`, `LLM_UNAVAILABLE`; kein Retry bei nicht retryable Fehlern |
| Recovery Trigger | neuer erfolgreicher Retrieval-/Search-Lauf mit frischem Kontext und ohne Degradierung |

Recovery UX Regel:

- Historische Nachrichten bleiben sichtbar; nur neuer retrieval-gestuetzter Write bleibt blockiert.

### 7. Auth expired

Normativer Runtime-State: `unauthenticated`

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | Error-State `Login erforderlich. Die Sitzung ist abgelaufen` |
| Erlaubte Aktionen | Zur Anmeldung wechseln, Login neu starten |
| Blockierte Aktionen | alle geschuetzten Fachmutationen und neue Fachrequests |
| Retry Strategie | kein Retry-Loop; explizite Re-Authentifizierung erforderlich |
| Recovery Trigger | erfolgreicher Login plus erneuter Auth-/Workspace-Bootstrap |

Recovery UX Regel:

- Alte Fachdaten werden nicht als weiterhin belastbar dargestellt; Sessionverlust ist kein transienter Retry-Fall.

### 8. Workspace verloren

Normativer Runtime-State: `forbidden` oder `workspace_loading` mit Fehlschlag

| Aspekt | Regel |
|---|---|
| Sichtbarer Hinweis | Fehlerzustand `Workspace fehlt` oder `Zugriff auf Workspace verloren` |
| Erlaubte Aktionen | Workspace-Kontext pruefen, falls moeglich anderen gueltigen Workspace waehlen, neu anmelden |
| Blockierte Aktionen | alle workspace-scoped Fachaktionen fuer den verlorenen Workspace |
| Retry Strategie | kein automatischer Retry-Loop; Revalidation oder neuer Workspace-Kontext erforderlich |
| Recovery Trigger | erfolgreicher `/auth/me`- oder Workspace-Validierungs-Check mit gueltigem Ziel-Workspace |

Recovery UX Regel:

- Daten des verlorenen Workspace duerfen nicht weiter als aktive Fachbasis angezeigt werden.

## Retry-/Reconnect-Regeln

### Retry-Regeln

- Retry ist nur erlaubt fuer transiente technische Fehler oder kontrollierte Feature-Recovery.
- Retry braucht sichtbare Ursache und klaren Zielpfad.
- Retry ist verboten bei `AUTH_REQUIRED`, `FORBIDDEN`, `WORKSPACE_NOT_CONFIGURED`, `VALIDATION_ERROR` und waehrend `restore_mode`.
- Ein Retry darf keine verbotene Runtime-Transition erzwingen.

### Reconnect-Regeln

- `reconnecting` friert Mutationen ein.
- letzte sichere Ansicht bleibt read-only sichtbar
- stale oder alte Responses aus dem Vor-Kontext duerfen keinen frischen State schreiben
- Rueckkehr zu `workspace_ready` erst nach Auth-/Workspace-Kontextvalidierung und Nachladen betroffener stale Caches
- Fehlschlag fuehrt deterministisch zu `api_unreachable`, `unauthenticated` oder `forbidden`

### Retry-Matrix

| Zustand | Automatischer Retry | Manueller Retry | Verboten |
|---|---|---|---|
| Backend Restart | ja, mit Backoff | ja | Endlosschleife ohne Backoff |
| DB Restart | ja, begrenzt | ja | lokaler Success ohne frischen Read |
| Restore laeuft | nein | nur Refresh nach Abschluss | fachlicher Retry waehrend Restore |
| Queue degraded | nein fuer Upload-Spam | ja nach neuer Queue-Bestaetigung | blinder Job-Retry |
| Search unavailable | nein global | ja lokal | globale Reload-Schleife |
| Chat Retrieval degraded | nein global | ja lokal fuer retryable Fehler | Retry bei stale Retrieval-Basis |
| Auth expired | nein | nein, stattdessen Re-Login | automatischer Auth-Retry-Loop |
| Workspace verloren | nein | nein, stattdessen Revalidation | 403-Schleife auf gleichem Kontext |

## UI-Zustandsdiagramme

### 1. Technische Reconnect-Recovery

```text
workspace_ready
  -> reconnecting
  -> api_unreachable | workspace_ready | unauthenticated | forbidden
```

### 2. Restore-Recovery

```text
workspace_ready | degraded
  -> restore_mode
  -> authenticating
  -> workspace_loading
  -> workspace_ready | unauthenticated | forbidden
```

### 3. Search-/Retrieval-Recovery

```text
workspace_ready
  -> degraded(search_unavailable | retrieval_degraded)
  -> local_retry
  -> workspace_ready | degraded
```

### 4. Auth-/Workspace-Recovery

```text
workspace_ready
  -> unauthenticated | forbidden
  -> authenticating
  -> workspace_loading
  -> workspace_ready | unauthenticated | forbidden
```

## Degradation-Prinzipien

- Recovery muss transparent und nachvollziehbar sein.
- Kein degradiertes Feature darf waehrend Recovery wie Normalbetrieb aussehen.
- Kein Recovery ohne sichtbaren Recovery-Trigger.
- Kein Recovery ohne klar erkennbare Folgeaktion fuer den Nutzer.
- Kein Recovery-Ende ohne frischen technischen Nachweis.
