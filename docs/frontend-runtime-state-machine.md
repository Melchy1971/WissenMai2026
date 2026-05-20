# Frontend Runtime State Machine

Stand: 2026-05-18

Ziel: Frontend-Zustaende duerfen nicht implizit aus verstreuten Flags, leeren Daten oder Fehlermeldungen abgeleitet werden. Jede Route muss aus genau einem Runtime-State plus optionalem Detailfehler gerendert werden.

Cache-Folgen der States sind in `docs/frontend-cache-governance.md` verbindlich konkretisiert.
Offline-/Degraded-Verhalten pro Betriebszustand ist in `docs/frontend-offline-degraded-strategy.md` verbindlich konkretisiert.
API_UNREACHABLE-Recovery, Retry-Grenzen und Reconnect-Verhalten sind in `docs/frontend-api-unreachable-recovery.md` verbindlich konkretisiert.

## Runtime States

| State | Bedeutung | UI-Regel | Upload blockiert |
|---|---|---|---|
| `booting` | App startet, lokale Session und Request-Kontext werden gelesen | Nur Shell/Loading, keine Fachrequests | ja |
| `unauthenticated` | kein gueltiger Token vorhanden | Login-Ansicht oder Auth-Hinweis | ja |
| `authenticating` | Login oder Session-Bootstrap laeuft | Auth-Loading, keine Fachrequests ausser `/auth/*` | ja |
| `authenticated` | Token und Benutzer sind bekannt, Workspace ist noch nicht validiert | keine Fachroute als ready rendern | ja |
| `workspace_loading` | Memberships und aktiver Workspace werden geladen oder gewechselt | Workspace-Loading, bestehende Fachdaten nicht als frisch ausgeben | ja |
| `workspace_ready` | Token, Benutzer, Membership und aktiver Workspace sind validiert | Fachrouten duerfen Daten laden und Aktionen anbieten | nein |
| `degraded` | API erreichbar, aber Teilfunktionen oder Health sind eingeschraenkt | Warnbanner plus eingeschraenkte Aktionen | bedingt |
| `reconnecting` | transienter Fehler nach zuvor validiertem Kontext, Retry/Backoff aktiv | letzte sichere Ansicht darf read-only bleiben, Mutationen stoppen | ja |
| `forbidden` | Zugriff fuer Benutzer/Rolle/Workspace verweigert | Fehlerzustand, kein Retry-Loop | ja |
| `api_unreachable` | Backend nicht erreichbar oder CORS/Netzwerk blockiert | Fehlerzustand mit Retry | ja |
| `restore_mode` | System laeuft im Restore-/Recovery-Modus oder ist fuer Mutationen gesperrt | read-only Banner, keine Mutationen | ja |

## State Ownership

| Datenbereich | Besitzer | Muss aus State abgeleitet werden |
|---|---|---|
| `authToken` | Auth Runtime | ja |
| `user` | Auth Runtime | ja |
| `memberships` | Auth Runtime | ja |
| `active_workspace_id` | Workspace Runtime | ja |
| API-Request-Kontext | Runtime State Machine | ja |
| Dokument-/Search-/Chat-Cache | Route Cache | wird durch State invalidiert |
| Fehlerdetails | Error-State Catalog | optionaler Zusatz zum Runtime-State |

## Transition Matrix

| Von | Event | Nach | Side Effects |
|---|---|---|---|
| `booting` | keine gespeicherte Session | `unauthenticated` | API-Kontext leeren; alle Route-Caches leeren; Search/Chat resetten |
| `booting` | gespeicherter Token gefunden | `authenticating` | API-Kontext nur mit Token setzen; Fachrequests blockieren |
| `booting` | Restore-Flag/Restore-Health erkannt | `restore_mode` | Mutationen blockieren; Caches als stale markieren |
| `unauthenticated` | Login submit | `authenticating` | alte Auth-/Workspace-Daten loeschen; Search/Chat resetten |
| `unauthenticated` | Backend nicht erreichbar beim Login | `api_unreachable` | API-Kontext leer lassen; Retry erlauben |
| `authenticating` | Login erfolgreich, User vorhanden | `authenticated` | Token und User persistieren; API-Kontext mit Token setzen |
| `authenticating` | Session abgelaufen oder 401 | `unauthenticated` | Token entfernen; API-Kontext leeren; alle Caches leeren |
| `authenticating` | 403 | `forbidden` | API-Kontext leeren; keine Retry-Schleife |
| `authenticating` | Netzwerk/Timeout | `api_unreachable` | Token nicht als validiert behandeln; Retry erlauben |
| `authenticated` | Memberships/Workspace fehlen noch | `workspace_loading` | Fachrequests weiter blockieren |
| `authenticated` | keine Membership | `forbidden` | API-Kontext ohne Workspace; Upload/Search/Chat blockieren |
| `authenticated` | aktiver Workspace validiert | `workspace_ready` | API-Kontext mit Token und Workspace setzen; Route-Daten laden |
| `workspace_loading` | Workspace validiert | `workspace_ready` | workspace-scoped Caches fuer neuen Workspace laden |
| `workspace_loading` | Workspace fehlt | `forbidden` | API-Kontext Workspace leeren; Route-Caches leeren |
| `workspace_loading` | Backend nicht erreichbar | `api_unreachable` | Fachrequests abbrechen; Retry erlauben |
| `workspace_ready` | Workspace wechseln | `workspace_loading` | alle workspace-scoped Caches invalidieren; Search/Chat resetten; Upload abbrechen |
| `workspace_ready` | Logout | `unauthenticated` | Token entfernen; API-Kontext leeren; alle Caches leeren; Search/Chat resetten |
| `workspace_ready` | 401 aus Fachrequest | `unauthenticated` | Session loeschen; Caches leeren; zur Auth fuehren |
| `workspace_ready` | 403 aus Fachrequest | `forbidden` | betroffene Route blockieren; keine automatische Wiederholung |
| `workspace_ready` | API down/Timeout transient | `reconnecting` | Mutationen stoppen; letzte sichere Daten nur read-only anzeigen |
| `workspace_ready` | Health degraded | `degraded` | Warnbanner setzen; riskante Aktionen je Feature sperren |
| `workspace_ready` | Restore/Recovery aktiv | `restore_mode` | Upload, Lifecycle-Mutationen und Chat-Write blockieren |
| `degraded` | Health wieder ok | `workspace_ready` | Warnbanner entfernen; betroffene Caches nachladen |
| `degraded` | API down/Timeout | `reconnecting` | Mutationen stoppen; Retry/Backoff starten |
| `degraded` | Restore/Recovery aktiv | `restore_mode` | alle Mutationen blockieren |
| `reconnecting` | Retry erfolgreich und Kontext validiert | `workspace_ready` | stale Caches nachladen; Mutationen wieder freigeben |
| `reconnecting` | Retry 401 | `unauthenticated` | Session loeschen; Caches leeren |
| `reconnecting` | Retry 403 | `forbidden` | Retry stoppen; Route blockieren |
| `reconnecting` | Retry weiter Netzwerk/Timeout | `api_unreachable` | globalen API-Fehler zeigen |
| `api_unreachable` | Retry erfolgreich ohne Token | `unauthenticated` | API-Kontext leer; Login anzeigen |
| `api_unreachable` | Retry erfolgreich mit Token | `authenticating` | Auth-Bootstrap neu starten |
| `forbidden` | Logout | `unauthenticated` | API-Kontext leeren; Caches leeren |
| `forbidden` | anderer gueltiger Login | `authenticating` | alte Session leeren; neuen Bootstrap starten |
| `restore_mode` | Restore abgeschlossen, Token vorhanden | `authenticating` | alle Caches invalidieren; Auth/Workspace neu validieren |
| `restore_mode` | Restore abgeschlossen, kein Token | `unauthenticated` | API-Kontext leeren; Login anzeigen |

## Verbotene Transitions

| Von | Nach | Warum |
|---|---|---|
| `booting` | `workspace_ready` | Auth, Membership und Workspace muessen zuerst validiert werden |
| `unauthenticated` | `workspace_ready` | kein Token und kein Workspace-Kontext |
| `unauthenticated` | `workspace_loading` | Workspace darf nicht ohne Auth geladen werden |
| `authenticating` | `workspace_ready` | Workspace-Validierung darf nicht uebersprungen werden |
| `authenticated` | `workspace_ready` ohne Membership-Check | aktiver Workspace muss aus Memberships stammen |
| `api_unreachable` | `workspace_ready` ohne erfolgreichen Auth-/Workspace-Refresh | Netzwerkfehler darf nicht als alter Ready-State maskiert werden |
| `forbidden` | `workspace_ready` durch Retry derselben Session | 403 ist kein transienter Zustand |
| `restore_mode` | `workspace_ready` ohne Cache-Invalidierung | Restore kann Datenbasis und IDs veraendern |
| `degraded` | `workspace_ready` ohne Health-Refresh | Degraded darf nicht nur durch UI-Navigation verschwinden |
| `reconnecting` | `workspace_ready` ohne Kontextvalidierung | alte Daten duerfen nicht als frisch gelten |

## Verbotene Zustandskombinationen

| Kombination | Regel |
|---|---|
| `workspace_ready` ohne `authToken` | ungueltig |
| `workspace_ready` ohne `active_workspace_id` | ungueltig |
| `workspace_ready` mit `active_workspace_id` ausserhalb der Memberships | ungueltig |
| `unauthenticated` mit nicht leerem API-Auth-Kontext | ungueltig |
| `forbidden` mit aktivem Upload | ungueltig |
| `api_unreachable` mit Empty-State fuer Dokumente/Suche/Chat | ungueltig |
| `restore_mode` mit sichtbaren Mutationsbuttons | ungueltig |
| `reconnecting` mit laufender neuer Mutation | ungueltig |
| `degraded` ohne sichtbares Degraded-Signal | ungueltig |

## Cache-Invalidierung

Detailregeln fuer Cache-Keys, `source_timestamp`/`source_version`, Stale-Indikatoren und bereichsspezifische Invalidierung stehen in `docs/frontend-cache-governance.md`.

| State/Transition | Invalidiert Cache |
|---|---|
| `booting -> unauthenticated` | alle Caches |
| `unauthenticated -> authenticating` | alle auth- und workspace-scoped Caches |
| `authenticating -> unauthenticated` | alle Caches |
| `authenticated -> workspace_loading` | keine Fachcache-Freigabe; vorhandene Daten bleiben stale |
| `workspace_ready -> workspace_loading` | Dokumente, Suche, Chat, Jobs, Diagnostics fuer alten Workspace |
| `workspace_ready -> unauthenticated` | alle Caches |
| `workspace_ready -> forbidden` | betroffener Route-Cache |
| `workspace_ready -> reconnecting` | keine sofortige Leerung; alle Daten als stale/read-only markieren |
| `reconnecting -> workspace_ready` | stale Caches nachladen |
| `restore_mode -> authenticating` | alle Caches |

## Search/Chat Reset

| State/Transition | Search reset | Chat reset |
|---|---|---|
| Logout oder 401 zu `unauthenticated` | ja | ja |
| Login-Start aus `unauthenticated` | ja | ja |
| Workspace-Wechsel | ja | ja |
| `workspace_loading -> forbidden` | ja | ja |
| `restore_mode` Eintritt | ja | ja |
| `api_unreachable` | nein, aber read-only/stale; keine Empty-State-Ableitung |
| `reconnecting` | nein, aber read-only/stale |
| `degraded` | nein, ausser Feature-Health meldet Search/Chat ungueltig |

## Upload-Blocker

Upload ist nur in `workspace_ready` erlaubt und nur, wenn kein Feature-spezifischer Degraded-Blocker aktiv ist.

| State | Upload |
|---|---|
| `booting` | blockiert |
| `unauthenticated` | blockiert |
| `authenticating` | blockiert |
| `authenticated` | blockiert |
| `workspace_loading` | blockiert |
| `workspace_ready` | erlaubt |
| `degraded` | blockiert, wenn Upload-, Queue- oder DB-Health betroffen ist |
| `reconnecting` | blockiert |
| `forbidden` | blockiert |
| `api_unreachable` | blockiert |
| `restore_mode` | blockiert |

## Side-Effect-Regeln

- API-Kontext darf nur in `authenticated`, `workspace_loading` und `workspace_ready` gesetzt sein; Fachrequests brauchen `workspace_ready`.
- `Authorization` ohne validierten Workspace darf nur fuer Auth-/Bootstrap-Endpunkte verwendet werden.
- `X-Workspace-Id` darf erst ab validiertem `workspace_ready` an Fachrequests gesendet werden.
- `api_unreachable`, `forbidden` und `restore_mode` duerfen nie als leere Dokument-, Such- oder Chatdaten dargestellt werden.
- Jede Transition zu `unauthenticated`, `forbidden`, `api_unreachable` oder `restore_mode` muss laufende Uploads und Chat-Writes abbrechen oder blockieren.
- Jede Transition aus `restore_mode` muss Auth, Workspace und Caches neu validieren.
