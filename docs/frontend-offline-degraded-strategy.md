# Frontend Offline-/Degraded-Strategie

Stand: 2026-05-18

Ziel: Nicht jede Stoerung darf wie ein Totalausfall wirken. Das Frontend muss zwischen vollstaendigem API-Ausfall, feature-spezifischer Degradierung und temporaerer Read-only-Nutzung unterscheiden. Jeder Zustand braucht explizite Regeln fuer erlaubte Aktionen, blockierte Aktionen, Retry, UI und Cache-Nutzung.

Verbindliche Bezugsdokumente:

- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-cache-governance.md`
- `docs/frontend-error-state-catalog.md`
- `docs/frontend-concurrency-safety.md`
- `docs/frontend-telemetry-governance.md`

## Degraded-State-Strategie

### Grundprinzipien

- Nicht jeder Fehler ist ein globaler Ausfall. Feature-spezifische Stoerungen bleiben lokal, solange Auth, Workspace und andere Fachpfade intakt sind.
- Ein degradiertes Feature bleibt sichtbar als degradiert, nicht als leer, nicht als gruen.
- Read-only Cache-Nutzung ist erlaubt, wenn Frische und Staleness sichtbar sind.
- Mutationen werden nur dort blockiert, wo der betroffene Zustand die Korrektheit oder Nachvollziehbarkeit gefaehrdet.
- Retry darf nur fuer transiente oder plausibel kurzlebige Stoerungen angeboten werden.
- Reindex und Restore sind keine normalen Benutzeraktionen; sie wirken als Betriebszustand und ziehen sichtbare Frontend-Einschraenkungen nach sich.

### Statusklassen

| Klasse | Bedeutung |
|---|---|
| `offline` | API oder ein Kernpfad ist nicht erreichbar |
| `degraded` | Feature ist eingeschraenkt, aber nicht vollstaendig ausgefallen |
| `maintenance` | System laeuft in einem kontrollierten Betriebsmodus wie Reindex oder Restore |
| `unavailable` | Feature ist temporaer nicht nutzbar, andere Features koennen weiterlaufen |

### Grundregeln fuer alle Zustaende

- Kein Empty-State bei technischem Fehler.
- Kein Mutationserfolg aus stale Cache-Daten.
- Kein automatischer Wechsel von `degraded` zu `ok` ohne frischen technischen Nachweis.
- Kein stilles Verwenden von Search- oder Chat-Caches als frisch, wenn Reindex oder Restore aktiv sind.
- Jede Route zeigt einen sichtbaren Indikator auf Shell-, Seiten- oder Komponentenebene.

## Offline-Regeln

### 1. API komplett down

Normativer Runtime-State: `api_unreachable`

| Aspekt | Regel |
|---|---|
| Erlaubte Aktionen | Navigation, manuelles Retry, read-only Sicht auf klar als stale markierte Cache-Daten |
| Blockierte Aktionen | Login-geschuetzte Fachmutationen, Upload, Chat senden, Lifecycle-Mutationen, Workspace-sensitive Neuabfragen |
| Retry-Regeln | expliziter Retry-Button erlaubt; kein unendlicher Retry-Loop; Backoff fuer automatische Reconnect-Versuche |
| UI-Indikatoren | globaler Error-/Offline-Banner, sichtbarer technischer Zustand `Backend nicht erreichbar`, Stale-Hinweise je betroffene Route |
| Cache-Nutzung erlaubt/verboten | Dokumente, Suche, Chat duerfen read-only als stale sichtbar bleiben; Diagnostics nur stale, nie als aktuell; kein Empty-State aus Fehlern |

Zusatzregel:

- Wenn kein valider Cache existiert, wird ein technischer Fehlerzustand gezeigt, nicht eine leere Liste.

### 2. Search down

Normativer Zustand: feature-spezifisch `degraded`, kein globales `api_unreachable`

| Aspekt | Regel |
|---|---|
| Erlaubte Aktionen | Dokumentlisten lesen, Dokumentdetail lesen, Diagnostics lesen, Chat-Historie read-only lesen |
| Blockierte Aktionen | neue Search Requests als fachlich erfolgreich darstellen, Chat-Retrieval mit frischem Suchkontext, Aktionen, die aktuelle Suchfrische voraussetzen |
| Retry-Regeln | lokaler Retry im Search-Bereich erlaubt; kein globaler App-Retry; bei transientem Fehler begrenzter erneuter Suchversuch |
| UI-Indikatoren | Search-Panel zeigt `Search aktuell nicht verfuegbar` oder `Search eingeschraenkt`; Shell darf zusaetzlich Degraded-Badge zeigen |
| Cache-Nutzung erlaubt/verboten | alte Search Results duerfen nur read-only und sichtbar stale angezeigt werden; stale Search Results duerfen nicht als neue Chat-Retrieval-Basis dienen |

Zusatzregeln:

- Dokumentansichten bleiben verfuegbar.
- Search-Fehler duerfen nicht den Eindruck erwecken, dass es keine Treffer gibt.

### 3. Queue degraded

Normativer Zustand: `degraded`

| Aspekt | Regel |
|---|---|
| Erlaubte Aktionen | Dokumente lesen, Diagnostics lesen, bestehende Chat-Historie lesen, Suche lesen sofern Search selbst gesund ist |
| Blockierte Aktionen | Upload starten, Queue-abhaengige Mutationen als normal verfuegbar zeigen, riskante Hintergrundjob-nahe Aktionen |
| Retry-Regeln | kein aggressiver Auto-Retry fuer Upload; Nutzer darf nach sichtbarer Fehlermeldung manuell erneut versuchen, wenn Queue wieder gesund ist |
| UI-Indikatoren | Upload-Bereich zeigt Queue-Warnhinweis; globaler Degraded-Banner moeglich; Diagnostics zeigt Queue-Indikator sichtbar |
| Cache-Nutzung erlaubt/verboten | Lese-Caches erlaubt; Upload-bezogene Statusanzeigen duerfen nicht aus altem Polling als aktuell erscheinen; Jobstatus-Cache nur mit sichtbarem Stand |

Zusatzregeln:

- Queue-Degradierung ist kein Vollausfall fuer Dokumente, Suche oder historische Chats.

### 4. Reindex laeuft

Normativer Zustand: `maintenance` innerhalb `degraded`

| Aspekt | Regel |
|---|---|
| Erlaubte Aktionen | Dokumentlisten lesen, Dokumentdetail lesen, Diagnostics lesen, Navigation |
| Blockierte Aktionen | Search als frisch ausgeben, Chat-Retrieval starten, neue Treffer als final bestaetigt behandeln |
| Retry-Regeln | kein Retry gegen Reindex selbst aus der Fach-UI; Search-Reload erst nach Abschluss oder auf explizite Nutzeraktion |
| UI-Indikatoren | sichtbarer Banner `Suchindex wird aktualisiert`; Search- und Chat-Retrieval-Flaechen tragen Stale-/Wartehinweis |
| Cache-Nutzung erlaubt/verboten | Dokumentlisten duerfen read-only bleiben; Search Results werden stale markiert; Chat-Citation-/Retrieval-Kontext wird stale markiert; Diagnostics duerfen neu geladen werden |

Zusatzregeln:

- Reindex ist ein kontrollierter Betriebszustand, kein stiller Fehler.
- Search-Result-Caches bleiben sichtbar, aber nicht frisch.

### 5. Restore laeuft

Normativer Runtime-State: `restore_mode`

| Aspekt | Regel |
|---|---|
| Erlaubte Aktionen | minimale read-only Navigation, Sicht auf technische Hinweise, Login-/Session-Neuvalidierung nach Restore-Ende |
| Blockierte Aktionen | Upload, Chat senden, Lifecycle-Mutationen, Search als frisch, Workspace-sensitive Fachmutationen |
| Retry-Regeln | kein fachlicher Retry innerhalb des Restore-Zustands; nur Refresh/Neuladen nach Abschluss; automatischer Uebergang erst nach Cache-Invalidierung und Auth-/Workspace-Refresh |
| UI-Indikatoren | globaler Restore-Banner, klare Read-only-Kennzeichnung, Hinweis auf Neuvalidierung nach Abschluss |
| Cache-Nutzung erlaubt/verboten | bestehende Dokument-, Search- und Chat-Caches nur stale/read-only; Diagnostics werden invalidiert; nach Restore-Ende: alle Fachcaches leeren und neu laden |

Zusatzregeln:

- Restore ist der strengste Read-only-Betriebszustand.
- Kein Fachcache darf nach Restore ohne komplette Neuvalidierung als vertrauenswuerdig gelten.

### 6. Chat temporaer unavailable

Normativer Zustand: feature-spezifisch `unavailable` oder `degraded`

| Aspekt | Regel |
|---|---|
| Erlaubte Aktionen | Chat-Historie lesen, Dokumente lesen, Suche nutzen sofern Search gesund ist, Sessionliste ansehen |
| Blockierte Aktionen | neue Chat-Nachricht senden, neue Assistant-Antwort erwarten, Retrieval-gestuetzte Chat-Mutationen |
| Retry-Regeln | lokaler Retry im Chat-Bereich erlaubt fuer `TIMEOUT`, `API_UNREACHABLE`, `SERVER_ERROR`, `LLM_UNAVAILABLE`; kein Retry-Loop bei `FORBIDDEN`, `AUTH_REQUIRED`, `VALIDATION_ERROR` |
| UI-Indikatoren | Composer deaktiviert mit klarer Ursache `Chat temporaer nicht verfuegbar`; Session-/Verlaufsbereich bleibt sichtbar |
| Cache-Nutzung erlaubt/verboten | Chat-Historie darf read-only aus Cache sichtbar bleiben; keine neue Nachricht aus lokalem Zwischenstand als gesendet darstellen; stale Quellen muessen sichtbar als unbestaetigt markiert sein |

Zusatzregeln:

- Chat-Unverfuegbarkeit darf nicht die Sessionliste oder den bisherigen Verlauf verschwinden lassen.

## UI-Verhalten

### Shell-Verhalten

| Zustand | Shell-Verhalten |
|---|---|
| API komplett down | globaler Offline-Banner mit Retry |
| Search down | Degraded-Badge oder feature-spezifischer Hinweis, kein globaler Totalausfalltext |
| Queue degraded | globaler oder seitenlokaler Warnbanner, Schwerpunkt auf Upload-Blockierung |
| Reindex laeuft | globaler oder suchnaher Maintenance-Hinweis |
| Restore laeuft | globaler Restore-Banner, Read-only-Modus |
| Chat temporaer unavailable | Chat-seitiger Availability-Hinweis, andere Routen bleiben normal |

### Routenverhalten

| Route | API down | Search down | Queue degraded | Reindex laeuft | Restore laeuft | Chat unavailable |
|---|---|---|---|---|---|---|
| Dokumentliste | stale/read-only oder Fehlerzustand | normal nutzbar, Search-Panel degradiert | lesbar, Upload blockiert | lesbar, Search stale | stale/read-only | normal |
| Dokumentdetail | stale/read-only oder Fehlerzustand | normal | normal | normal | stale/read-only | normal |
| Search-Panel | technischer Fehler, kein Empty-State | lokaler Fehlerzustand | normal wenn Search gesund | stale/maintenance | blockiert/stale | normal |
| Chat-Seite | stale/read-only oder Fehlerzustand | nur wenn Chat Search braucht eingeschraenkt | Verlauf lesbar | Retrieval stale | read-only/stale | Composer blockiert, Verlauf sichtbar |
| Diagnostics | stale, nie als aktuell | zeigt Search-Problem sichtbar | zeigt Queue-Degradierung sichtbar | zeigt Reindex sichtbar | zeigt Restore sichtbar | zeigt Chat-Problem sichtbar |

### Retry-Matrix

| Zustand | Automatischer Retry | Manueller Retry | Verboten |
|---|---|---|---|
| API komplett down | ja, mit Backoff ueber Reconnect-Logik | ja | Endlosschleife ohne Backoff |
| Search down | nein global | ja lokal im Search-Bereich | globale Reload-Schleife fuer alle Features |
| Queue degraded | nein fuer Upload-Spam | ja nach sichtbarer Fehlermeldung | blinder Upload-Retry im Polling-Loop |
| Reindex laeuft | nein | ja nach Abschluss fuer Search-Reload | Retry auf Betriebszustand selbst |
| Restore laeuft | nein | nur Refresh nach Abschluss | Fachliche Mutation-Retries waehrend Restore |
| Chat temporaer unavailable | nein global | ja lokal im Chat | Retry-Loop bei nicht retryable Fehlern |

## Cache-Nutzung erlaubt/verboten

### Erlaubte Cache-Nutzung

- `api_unreachable`: bestehende Fachcaches read-only mit sichtbarem stale-Indikator
- `search down`: alte Search Results read-only und stale, aber nie als aktuelle Suchwahrheit
- `queue degraded`: Dokument-, Search- und Chat-Lesecaches normal oder stale je Feature
- `reindex laeuft`: Dokumentlisten weiter nutzbar; Search- und Retrieval-Caches stale
- `restore laeuft`: nur minimale stale/read-only Sicht bis kompletter Reset
- `chat unavailable`: Sessionliste und Verlauf read-only nutzbar

### Verbotene Cache-Nutzung

- stale Search Results als neue Retrieval-Basis verwenden
- stale Diagnostics als aktuellen Betriebszustand ohne Stale-Hinweis rendern
- Chat-Compose-Status aus lokalem Zwischenzustand als erfolgreich zeigen, wenn Chat unavailable ist
- Search-/Chat-/Dokumentcaches nach Restore-Ende ohne komplette Invalidierung weiterverwenden
- einen technischen Fehler durch Cache-Leerstand in einen Empty-State umdeuten

## Entscheidungsregeln

### Wann wirkt eine Stoerung global?

Eine Stoerung ist nur dann global, wenn mindestens eine dieser Bedingungen gilt:

- der zentrale API-Pfad ist nicht erreichbar
- Auth-/Workspace-Validierung ist nicht moeglich
- Restore-Modus blockiert die gesamte Datenbasis

Sonst bleibt die Stoerung feature-spezifisch.

### Wann darf Read-only weiterlaufen?

Read-only darf weiterlaufen, wenn:

- der letzte bekannte Cache workspace-korrekt ist
- `source_timestamp` oder `source_version` vorhanden ist
- der Nutzer sichtbar darauf hingewiesen wird, dass die Daten stale oder eingeschraenkt sind
- keine Mutation aus diesem Cache als frisch oder erfolgreich abgeleitet wird

## Gate-Regeln

Diese Strategie gilt nur dann als erfuellt, wenn:

- jeder der sechs Zustaende eine explizite UI-Regel hat
- erlaubte und blockierte Aktionen getrennt definiert sind
- Retry-Regeln pro Zustand beschrieben sind
- Cache-Nutzung pro Zustand erlaubt oder verboten ist
- kein Degraded-Zustand wie kompletter Ausfall oder leere Datenlage wirkt
