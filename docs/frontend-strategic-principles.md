# Strategische GUI-Prinzipien

Stand: 2026-05-18

Ziel: Die GUI wird nicht auf maximale Dynamik, maximale Effekte oder maximale Feature-Dichte optimiert. Sie wird auf deterministische Zustandsfuehrung, sichtbare Fehler, nachvollziehbare Recovery und governance-konforme Darstellung optimiert.

Verbindliche Bezugsdokumente:

- `docs/frontend-runtime-state-machine.md`
- `docs/frontend-error-state-catalog.md`
- `docs/frontend-cache-governance.md`
- `docs/frontend-concurrency-safety.md`
- `docs/frontend-offline-degraded-strategy.md`
- `docs/operational-truth-governance.md`
- `docs/security.md`
- `docs/controlled-failure-philosophy.md`

## GUI-Prinzipien

### 1. Deterministische Zustaende

- Jede Route rendert aus genau einem expliziten Runtime-State plus optionalem Detailfehler.
- Zustandswechsel sind Ereignis-getrieben und duerfen nicht aus verstreuten UI-Flags implizit rekonstruiert werden.
- Ein Zustand ohne klaren Besitzer ist unzulaessig.
- Fachdaten duerfen nur in `workspace_ready` als frisch und voll belastbar dargestellt werden.

### 2. Transparente Fehler

- Technische Fehler erscheinen nie als leere Datenlage.
- Fehlercodes bleiben sichtbar oder ableitbar ueber einen standardisierten Error-State.
- Retry, Nicht-Retry und naechste Nutzeraktion muessen pro Fehlerzustand erkennbar sein.
- Backend-, Netzwerk-, Auth- und Validierungsfehler werden nicht in dekorative oder euphemistische UI-Texte uebersetzt.

### 3. Nachvollziehbare Recovery

- Recovery ist explizit, sichtbar und testbar.
- Retry darf nur fuer klar retrybare Faelle angeboten werden.
- Reconnect, Restore, Reindex und Queue-Degradierung muessen einen sichtbaren UI-Zustand erzeugen.
- Eine GUI darf nach Recovery nicht ohne erneute Validierung direkt auf `ready` springen.

### 4. Drift-aware UI

- Die GUI zeigt degradierte, stale oder unklare Betriebszustaende sichtbar an.
- Unbelegte oder unbekannte Zustaende werden konservativ als `warning`, `unknown` oder `not_verified` behandelt.
- Search Drift, Queue degraded, Restore, Reindex, Retrieval Regression, Backup-Staleness und Cleanup Dry Run duerfen nicht hinter gruenen Standardwidgets verschwinden.
- Drift-Sichtbarkeit ist kein Admin-Luxus, sondern Teil der operativen Wahrheit.

### 5. Governance-konforme Darstellung

- Gruene Aussagen duerfen nur aus aktuellen Truth- und Gate-Artefakten abgeleitet werden.
- Ein UI-Slice darf nur so stark beschrieben werden wie der nachgewiesene Scope des Artefakts.
- Dokumentation beschreibt den Status, sie erzeugt ihn nicht.
- Fokussierte Tests, lokale Beobachtung oder Einzelkomponenten ersetzen keinen integrierten GUI-Truth-Nachweis.

### 6. Keine Fake-Green-Zustaende

- Kein degradiertes Feature darf wie gesunder Normalbetrieb aussehen.
- Ein fehlender Nachweis ist `unknown` oder `not_verified`, niemals `ok`.
- Historisch gruene Aussagen werden durch aktuelle rote Reports ueberstimmt.
- Ein Screen darf nicht optisch erfolgreich wirken, wenn Mutationen blockiert oder Daten stale sind.

### 7. Keine versteckten Fallbacks

- Fallbacks sind explizit, sichtbar und begrenzt.
- Stale Cache-Daten muessen als stale markiert werden.
- Fallback auf alte Search- oder Chat-Daten darf nicht als aktuelle Wahrheit erscheinen.
- Client-seitige Defaults duerfen keine verlorenen Backend-Zustaende verstecken.

### 8. Workspace-isolierte States

- Jeder fachliche State ist an Auth- und Workspace-Kontext gebunden.
- Workspace-Wechsel invalidiert workspace-scoped Daten, Requests und abgeleitete ViewModels.
- Kein Screen darf Daten aus einem frueheren Workspace still weiterverwenden.
- Route- und Cache-State muessen den aktiven Workspace explizit respektieren.

## Architekturregeln

### Pflichtabstraktionen

Die folgenden Frontend-Abstraktionen sind fuer neue GUI-Entwicklung verpflichtend:

1. Explizite Runtime-State-Machine fuer App- und Route-Zustaende.
2. Zentrales Error-Catalog-Mapping mit sichtbaren GUI-Klassen statt freier Fehlerbehandlung je Komponente.
3. Zentraler API-Client mit Auth-, Workspace- und optionaler `correlationId`-Propagation.
4. Request-Koordination mit Ticketing, Cancellation und Stale-Write-Schutz.
5. Workspace-scoped Cache-Governance mit `source_timestamp` oder `source_version`.
6. Degraded-/Offline-State-Modell mit sichtbaren Bannern, Badges oder State-Cards.
7. ViewModel- oder Presenter-Schicht fuer API-zu-UI-Mapping in allen nichttrivialen Screens.
8. Maschinenlesbare Frontend-Truth-Reports fuer produktionsnahe Aussagen.

### Architekturregeln fuer neue GUI-Slices

- Neue Screens brauchen vor Implementierung eine definierte State-Matrix fuer `loading`, `empty`, `error`, `stale`, `degraded` und `ready`, soweit fachlich relevant.
- Jeder Schreibpfad braucht explizite Regeln fuer Blocker, Retry, Abort und Erfolgsdarstellung.
- Jeder Screen muss angeben, welche Daten frisch, stale oder unbekannt sind.
- Cross-cutting Regeln fuer Auth, Workspace, Recovery und Drift duerfen nicht lokal pro Screen neu erfunden werden.
- Komponenten duerfen Backend-Responses nicht ungeprueft direkt rendern, wenn Governance-relevante Ableitungen noetig sind.

### Pflicht fuer Sichtbarkeit

- Error-State statt Empty-State bei technischem Fehler.
- Read-only-Stale-State statt implizitem Normalbetrieb bei API down oder Reconnect.
- Warn- oder Critical-Indikator statt normalem Erfolgsbadge bei Drift- oder Betriebsproblemen.
- Sichtbare Ursache statt generischem `es hat nicht funktioniert`.

### Stop-Kriterien fuer GUI-Featureentwicklung

GUI-Featureentwicklung muss gestoppt oder auf Stabilisierung umgestellt werden, wenn mindestens eines davon gilt:

- der aktuelle Frontend-Truth-Report ist rot
- ein Gate-Report fuer den betroffenen GUI-Slice ist `fail`, `blocked` oder `unknown`
- Security-Governance fuer Auth, Workspace oder Rollen wird durch den neuen Slice verletzt oder umgangen
- Contract-Report und GUI-Verhalten widersprechen sich
- der neue Slice fuehrt verdeckte Fallbacks, Fake-Green-Zustaende oder unmarkierte Stale-Daten ein
- Workspace-Isolation ist fuer den Slice nicht nachgewiesen
- Recovery- oder Error-State-Regeln sind fuer den Slice nicht definiert
- Drift-Signale des Slices koennen nicht sichtbar dargestellt werden

Featureentwicklung darf erst weiterlaufen, wenn der Blocker entweder behoben oder explizit als nicht Scope klassifiziert und durch Governance-Dokumente begrenzt wurde.

## No-Go-Patterns

### Verbotene GUI-Patterns

- implizite State-Ableitung aus mehreren booleans ohne kanonischen Runtime-State
- Empty-State bei Netzwerk-, Auth- oder Serverfehlern
- optimism without rollback bei fachlichen Mutationen
- Silent Retry ohne sichtbaren Status und ohne Abbruchgrenze
- Hintergrund-Fallback auf stale Cache ohne Kennzeichnung
- lokales Ueberschreiben frischer Daten durch spaete oder stale Responses
- route-lokale Auth- oder Workspace-Sonderlogik ausserhalb des zentralen Kontexts
- gruenes Statusbadge trotz `degraded`, `restore_mode`, `api_unreachable` oder unbekannter Evidenz
- Ausblenden technischer Fehlercodes zugunsten rein dekorativer Fehlermeldungen
- UI-Entscheidungen auf Basis historischer Dokumentation statt aktueller Reports
- direkte Backend-Response-Renderings ohne ViewModel bei komplexen Zustandsregeln
- Feature-spezifische eigene Retry- oder Error-Modelle, die dem zentralen Katalog widersprechen

### Verbotene Abkuerzungen

- `best effort`-Rendern ohne sichtbaren Hinweis
- Workspace-Wechsel ohne Cache-Reset oder Request-Abbruch
- manuelles `setState` aus async Responses ohne Ticket-/Snapshot-Pruefung
- Admin- oder Betriebszustandsanzeige ohne Redaction- und Rollenregeln
- Recovery als stiller Hintergrundpfad ohne sichtbare UI-Phase

## Entscheidungsregel fuer kuenftige GUI-Arbeit

Ein neues GUI-Feature ist nur dann architekturkonform, wenn alle folgenden Fragen mit `ja` beantwortet werden koennen:

- Hat der Slice einen deterministischen Runtime-State?
- Sind Fehlerklassen und Recovery sichtbar definiert?
- Ist Workspace-Isolation Teil des Designs?
- Gibt es keine Fake-Green- oder Silent-Fallback-Pfade?
- Ist Drift oder Staleness sichtbar, wenn sie fachlich relevant werden?
- Laesst sich der Slice in Truth-, Contract- und Security-Governance einordnen?

Wenn eine dieser Fragen mit `nein` beantwortet wird, ist der Slice nicht freigabefaehig fuer weitere GUI-Ausweitung.