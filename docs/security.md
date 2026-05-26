# Security

Stand: 2026-05-07


## Seed-/Auth-Bootstrap & Sicherheitsmodell (Stand 2026-05-26)

### Seed-Flow & Credentials

Alle Seed-Skripte und Bootstrap-Prozesse lesen konsistent:

- `SEED_ADMIN_LOGIN` (Default: `admin@localhost`)
- `SEED_ADMIN_PASSWORD` (Default: `change-me`)
- `SEED_WORKSPACE_NAME` (Default: `Default Workspace`)

> **Warnung (lokale Entwicklung):** `.env` enthält das Klartext-Passwort. Niemals `.env` committen! In produktiver Dokumentation keine Klartext-Credentials angeben.

### Auth Bootstrap Guard

Nach dem Seed prüft `scripts/check_auth_bootstrap.py` Login und Workspace-Isolation. Fehler führen zu Exit != 0 und Report in `reports/auth_bootstrap_guard.json`.

### Auth- und Workspace-Konsistenz

Der dokumentierte Zielzustand für M4a ist ein serverseitig erzwungener Benutzer- und Workspace-Kontext. Im aktuellen Gate-Stand für M4 nachweisbar:

- Einheitliches API-Fehlerformat
- Fehlercodes `AUTH_REQUIRED`, `ADMIN_REQUIRED`, `WORKSPACE_REQUIRED`
- `POST /api/v1/auth/login` und `GET /api/v1/auth/me`
- Auth-Middleware mit Sessionprüfung und Workspace-Membership-Prüfung für geschützte Endpunkte
- Admin-Schutz für `GET /api/v1/admin/diagnostics` über AuthContext + Workspace-Membership/Rolle
- Blockierter Admin-Schutz für `POST /api/v1/admin/search-index/rebuild` (M4d read-only, liefert `501 ADMIN_ACTION_NOT_IMPLEMENTED`)
- Serverseitiger Auth-Kontext für `POST /documents/import`
- Workspace-Filter in Dokument-, Search- und Chat-Verträgen

Nicht nachweisbar implementiert:

- `POST /auth/logout`
- Vollständiger Cookie-Session- oder JWT-Produktflow für das Frontend
- Durchgängiger Login-/Logout-/Route-Guard-Flow im Frontend
- CSRF-Schutz für mutierende Cookie-basierte Requests

### Read-only Diagnostics Scope (M4d)

`GET /api/v1/admin/diagnostics` ist ein read-only Admin-Endpunkt.

Erzwungen:

- AuthContext erforderlich
- Aktiver Workspace erforderlich
- Workspace-Membership mit Rolle `owner` oder `admin` erforderlich
- Fremder Workspace wird abgewiesen

Fehlercodes:

- `401 UNAUTHORIZED` ohne gültige Authentifizierung
- `403 FORBIDDEN` ohne Admin-/Owner-Rolle oder bei fremdem Workspace
- `500 DIAGNOSTICS_FAILED` bei Diagnosefehlern mit redigierten Details

Nicht ausgegeben:

- Dokumenttexte
- Chunktexte
- Dokumenttitel
- Chat-Fragen oder Chat-Antworten
- Prompts
- Secrets
- Tokens
- Header-Werte
- Connection-Strings
- Lokale Dateipfade

Nicht freigegeben:

- Reparaturaktionen
- Reindex-Aktionen
- Cleanup-Aktionen
- Backup-/Restore-Aktionen
- User-Verwaltung
- Workspace-Mutation
- Dokumentreparatur

M4d ist damit nur read-only vorbereitet. Vollständige M4d-Admin-Aktionen bleiben blockiert, bis M4a, M4b und M4c grün sind.

### Workspace-Isolation

- Dokumente, Chat-Sessions und Search arbeiten fachlich mit `workspace_id`.
- Geschützte Backend-Endpunkte prüfen den AuthContext über die Middleware gegen Workspace-Membership.
- Dokument-Read-, Search-, Chat-, Upload-, Jobs- und Diagnostics-Pfade leiten den Workspace serverseitig aus dem AuthContext ab.
- Dokument-Lifecycle-Mutationen sind im aktuellen Wahrheitsstand nicht mehr als offener M4-Gate-Blocker zu dokumentieren; massgeblich ist der gruene Truth- und Transition-Nachweis.
- Offene Produkt- oder Ausbaupunkte ausserhalb des aktuellen M4-Minimalscopes bleiben Weiterentwicklung und aendern den erreichten Freigabestand nicht.

## Betroffene Endpoints

- `GET /documents`
- `POST /documents/import`
- `GET /api/v1/search/chunks`
- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `POST /api/v1/chat/sessions/{session_id}/messages`
- `GET /api/v1/admin/diagnostics`
- `POST /api/v1/admin/search-index/rebuild`

## Fehlercodes

- `AUTH_REQUIRED`: keine gueltige Session oder kein Auth-Kontext
- `ADMIN_REQUIRED`: Session ist vorhanden, aber ohne Adminrolle im aktiven Workspace
- `WORKSPACE_REQUIRED`: Workspace-Parameter fehlt im Fachrequest

## Bekannte Einschraenkungen

- Frontend-API-Clients nutzen den zentralen Request-Kontext; ein vollstaendiger geschuetzter Route-Flow mit Login-/Logout-/Sessionwiederherstellung fehlt weiterhin.
- Lifecycle-Mutationen brauchen noch einen harten workspace-scoped Service-/Testnachweis.
- Es gibt keine Logout- oder Session-Invalidierungslogik fuer regulare Benutzer.

## Nicht-Scope

- OAuth
- SSO
- externe Identity Provider
- Enterprise-Rollenmodell
- feingranulare Berechtigungen

## Abschlussentscheidung fuer M4a

- Dokumentation aktualisiert: ja
- Sicherheitsmodell konsistent mit dem aktuellen M4-Minimalscope: ja
- Entscheidung: M4a ist im aktuellen Gate-Stand freigabefaehig abgeschlossen
