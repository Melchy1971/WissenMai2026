# Frontend Cache Governance

Stand: 2026-05-18

Ziel: Stale GUI-States duerfen keine Ghost-Daten erzeugen. Jeder Frontend-Cache ist explizit workspace-scoped, versioniert und durch Runtime-State-Transitions invalidierbar.

## Grundregeln

- Jeder Cache-Key enthaelt `workspace_id`.
- Kein globaler Dokument-, Search-, Chat-, Diagnostics- oder Membership-Cache.
- Kein Cache-Eintrag ohne `source_timestamp` oder `source_version`.
- Cache-Daten duerfen nur in `workspace_ready` als frisch gelten.
- In `reconnecting`, `degraded` und `restore_mode` duerfen vorhandene Daten nur mit sichtbarem Stale-Indikator angezeigt werden.
- Fehlerzustaende duerfen keinen Empty-State aus gecachten alten Daten erzeugen.
- Mutationen muessen betroffene Caches synchron invalidieren oder als stale markieren, bevor die UI Erfolg signalisiert.

## Cache Domains

| Bereich | Scope-Key | Pflicht-Metadaten | Frischequelle | Darf global sein |
|---|---|---|---|---|
| Dokumentlisten | `workspace_id + lifecycle_filter + pagination + sort` | `source_timestamp`, optional `list_version`, `etag` | API-Antwortzeit oder Server-Version | nein |
| Search Results | `workspace_id + query + filters + pagination + index_version` | `source_timestamp`, `index_version` oder `search_snapshot_id` | Search-API/Index-Metadaten | nein |
| Chat Sessions | `workspace_id + session_id? + pagination` | `source_timestamp`, `session_updated_at` oder `message_version` | Chat-Session-/Message-Zeitstempel | nein |
| Diagnostics | `workspace_id + diagnostics_scope` | `source_timestamp`, `system_status_version` oder `migration_revision` | Diagnostics-Antwortzeit und Revisionen | nein |
| Workspace Memberships | `user_id + auth_session_id` | `source_timestamp`, `membership_version` oder `auth_session_updated_at` | `/auth/me` | nein |

## Cache Record Contract

Jeder Cache-Eintrag muss mindestens diese Felder tragen:

```json
{
  "workspace_id": "workspace-id",
  "cache_key": "domain-specific-key",
  "domain": "documents|search|chat|diagnostics|memberships",
  "source_timestamp": "2026-05-18T10:00:00Z",
  "source_version": "etag-or-domain-version",
  "runtime_state": "workspace_ready",
  "stale": false,
  "stale_reason": null
}
```

Erlaubte Ausnahme: Membership-Caches nutzen statt `workspace_id` den Key `user_id + auth_session_id`, muessen aber alle enthaltenen Memberships mit ihren `workspace_id`-Werten speichern. Fachcaches duerfen Membership-Caches nicht ersetzen.

## Invalidierungsregeln

| Ereignis | Dokumentlisten | Search Results | Chat Sessions | Diagnostics | Workspace Memberships |
|---|---|---|---|---|---|
| Workspace-Wechsel | invalidate old workspace | invalidate old workspace | invalidate old workspace | invalidate old workspace | keep only if same user/session, then revalidate |
| Logout | clear all | clear all | clear all | clear all | clear all |
| Restore beginnt | mark stale + block mutations | mark stale | mark stale | invalidate | invalidate |
| Restore abgeschlossen | clear all and refetch | clear all and refetch | clear all and refetch | clear all and refetch | refetch `/auth/me` |
| Reindex beginnt | keep list, mark search stale | mark stale + block stale-as-fresh | mark chat retrieval context stale | mark stale | no change |
| Reindex abgeschlossen | optional refetch counts | invalidate all search results | mark citations/retrieval panels stale | refetch diagnostics | no change |
| Lifecycle archive/restore/delete | invalidate list/detail for document | invalidate search for workspace | mark citations/source-status stale | refetch counts/status | no change |
| Dokumentimport completed | invalidate active list | invalidate search for workspace | no direct reset; mark retrieval context stale | refetch import/counts | no change |
| Duplicate erkannt | no list mutation unless backend returns existing doc update | no change | no change | refetch import counters | no change |
| 401/Auth required | clear all | clear all | clear all | clear all | clear all |
| 403/Forbidden | clear affected route cache | clear affected query cache | clear affected session cache | clear diagnostics cache | revalidate membership |
| API unreachable | keep as stale/read-only | keep as stale/read-only | keep as stale/read-only | mark stale | keep but mark auth freshness unknown |
| Runtime `restore_mode` | mark stale | mark stale | mark stale | invalidate | revalidate after restore |

## Bereichsregeln

### Dokumentlisten

- Dokumentlisten duerfen nie ausserhalb des aktuellen `workspace_id` wiederverwendet werden.
- `active`, `archived` und spaetere Filter sind getrennte Cache-Keys.
- Lifecycle-Mutationen invalidieren immer Dokumentliste, Dokumentdetail und Search Results desselben Workspace.
- Ein Dokumentlisten-Cache ohne `source_timestamp` darf nicht gerendert werden.
- Nach Restore muss der Cache geleert werden, nicht nur stale markiert.

### Search Results

- Search Results sind an `workspace_id`, Query, Filter und Index-Version gebunden.
- Reindex macht alle Search Results des Workspace stale.
- Lifecycle-Aenderungen machen alle Search Results des Workspace stale, weil Treffer-Sichtbarkeit von `active` abhaengt.
- Stale Search Results duerfen read-only angezeigt werden, muessen aber sichtbar als veraltet markiert sein.
- Chat darf stale Search Results nicht als neue Retrieval-Basis verwenden.

### Chat Sessions

- Chat-Session-Listen und Chat-Details sind getrennte Cache-Keys.
- Workspace-Wechsel, Logout und Restore resetten Chat-Auswahl und Chat-Composer.
- Reindex und Lifecycle-Aenderungen markieren Quellen-/Citation-Kontext stale, auch wenn Nachrichten selbst historisch erhalten bleiben.
- Neue Chat-Nachrichten duerfen nur mit frischem `workspace_ready` und nicht-stalem Retrieval-Kontext gesendet werden.
- Stale Chat-Verlauf darf read-only sichtbar bleiben, aber Quellenbloecke muessen `Quellenstatus wird neu validiert` oder aequivalent anzeigen.

### Diagnostics

- Diagnostics haben kurze Gueltigkeit und muessen immer einen sichtbaren `Stand` tragen.
- Diagnostics werden bei Restore, Reindex, Lifecycle-Mutationen, Importabschluss und Degraded-Health invalidiert oder neu geladen.
- In `degraded`, `reconnecting` oder `api_unreachable` duerfen alte Diagnostics nicht als aktueller Systemzustand erscheinen.
- Diagnostics duerfen keine Fachcache-Freigabe ersetzen.

### Workspace Memberships

- Memberships werden aus `/auth/me` geladen und sind an `user_id + auth_session_id` gebunden.
- Workspace-Wechsel ist nur erlaubt, wenn der Ziel-Workspace in den frischen Memberships enthalten ist.
- 403 auf Fachrequests invalidiert die betroffene Workspace-Membership-Annahme und erzwingt Revalidation.
- Logout loescht Memberships vollstaendig.
- Restore-Abschluss erzwingt erneutes `/auth/me`, weil Workspace- und Membership-Zuordnung geaendert sein kann.

## Stale-State-Regeln

| Stale Reason | Sichtbarer Indikator | Erlaubte Aktionen | Verbotene Aktionen |
|---|---|---|---|
| `workspace_switch` | `Workspace gewechselt, Daten werden neu geladen` | Navigation, Reload | Upload, Chat senden, Lifecycle-Mutation |
| `logout` | keiner; Daten werden entfernt | Login | Anzeige alter Fachcache-Daten |
| `restore` | `Restore-Modus: Daten werden neu validiert` | read-only Navigation, Reload nach Abschluss | alle Mutationen |
| `reindex` | `Suchindex wird aktualisiert` | Dokumente lesen, Diagnostics lesen | Suche als frisch ausgeben, Chat-Retrieval starten |
| `lifecycle_change` | `Dokumentstatus geaendert, Treffer werden aktualisiert` | Reload, Dokumentdetail lesen | stale Search/Chat-Quellen als frisch ausgeben |
| `api_unreachable` | `Backend nicht erreichbar, angezeigte Daten koennen veraltet sein` | Retry, read-only Anzeige | Empty-State, Upload, Chat senden |
| `degraded_health` | `System eingeschraenkt, Datenstand pruefen` | read-only je Feature | betroffene Mutationen |

Stale-Indikatoren muessen sichtbar in der betroffenen Route oder im Shell-Banner erscheinen. Nur ein Konsolenlog reicht nicht.

## Keine Ghost-Daten

Verboten:

- Dokumente aus Workspace A nach Wechsel zu Workspace B anzeigen.
- Search Results ohne sichtbaren Stale-Indikator nach Reindex oder Lifecycle-Mutation anzeigen.
- Chat-Citations nach Restore als frisch anzeigen, bevor Quellenstatus neu validiert ist.
- Diagnostics aus einem alten Timestamp als aktuellen Health-Stand rendern.
- Memberships aus einer alten Session zur Autorisierung eines neuen Tokens verwenden.
- Cache-Treffer ohne `source_timestamp` oder `source_version` rendern.
- Empty-State anzeigen, wenn der letzte Fetch mit Fehler, Timeout oder API-Unreachable endete.

## Umsetzungspflicht fuer UI

- Jede gecachte Liste oder Detailansicht zeigt entweder `Stand: <source_timestamp>` oder einen sichtbaren Stale-Hinweis.
- Stale-Daten sind read-only.
- Mutationsbuttons sind disabled oder nicht gerendert, solange die betroffenen Caches stale sind.
- Cache-Invalidierung muss vor optimistic UI-Erfolg erfolgen.
- Bei unklarer Frische gilt: stale markieren, nicht als frisch anzeigen.

## Bezug zur Runtime State Machine

Die Runtime-State-Machine in `docs/frontend-runtime-state-machine.md` ist die uebergeordnete Quelle fuer State-Transitions. Dieses Dokument konkretisiert die Cache-Folgen dieser Transitions. Bei Konflikt gilt die strengere Regel: Daten leeren oder stale markieren statt als frisch rendern.
