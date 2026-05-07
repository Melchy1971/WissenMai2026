# Security

Stand: 2026-05-07

## M4a Auth- und Workspace-Konsistenz

Der dokumentierte Zielzustand fuer M4a ist ein serverseitig erzwungener Benutzer- und Workspace-Kontext. Dieser Zielzustand ist im aktuellen Code nur teilweise umgesetzt.

Nachweisbar implementiert:

- einheitliches API-Fehlerformat
- Fehlercodes `AUTH_REQUIRED`, `ADMIN_REQUIRED`, `WORKSPACE_REQUIRED`
- `POST /api/v1/auth/login` und `GET /api/v1/auth/me`
- Auth-Middleware mit Sessionpruefung und Workspace-Membership-Pruefung fuer geschuetzte Endpunkte
- Admin-Schutz fuer `GET /api/v1/admin/diagnostics` ueber AuthContext + Workspace-Membership/Rolle
- blockierter Admin-Schutz fuer `POST /api/v1/admin/search-index/rebuild`, der fuer M4d read-only `501 ADMIN_ACTION_NOT_IMPLEMENTED` liefert
- serverseitiger Auth-Kontext fuer `POST /documents/import`
- Workspace-Filter in Dokument-, Search- und Chat-Vertraegen

Nicht nachweisbar implementiert:

- `POST /auth/logout`
- vollstaendiger Cookie-Session- oder JWT-Produktflow fuer das Frontend
- durchgaengiger Login-/Logout-/Route-Guard-Flow im Frontend
- CSRF-Schutz fuer mutierende Cookie-basierte Requests

## Auth-Modell im aktuellen Stand

- Regulare Benutzer-Authentifizierung und Workspace-Memberships sind fuer Fachendpunkte im Code nachweisbar.
- Read-only Diagnostics nutzt denselben serverseitigen Auth-Kontext und verlangt eine Workspace-Rolle `owner` oder `admin`.
- Der Admin-Rebuild ist fuer M4d read-only nicht freigegeben.
- Ein gesendeter `x-admin-token`-Header ist kein Autorisierungsmechanismus mehr und gilt nur noch als Legacy-Eingabe ohne Rechtewirkung.

## M4d Read-only Diagnostics Sicherheitsgrenzen

`GET /api/v1/admin/diagnostics` ist ein read-only Admin-Endpunkt.

Erzwungen:

- AuthContext erforderlich
- aktiver Workspace erforderlich
- Workspace-Membership mit Rolle `owner` oder `admin` erforderlich
- fremder Workspace wird abgewiesen

Fehlercodes:

- `401 UNAUTHORIZED` ohne gueltige Authentifizierung
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
- lokale Dateipfade

Nicht freigegeben:

- Reparaturaktionen
- Reindex-Aktionen
- Cleanup-Aktionen
- Backup-/Restore-Aktionen
- User-Verwaltung
- Workspace-Mutation
- Dokumentreparatur

M4d ist damit nur read-only vorbereitet. Vollstaendige M4d-Admin-Aktionen bleiben blockiert, bis M4a, M4b und M4c gruen sind.

## Workspace-Isolation im aktuellen Stand

- Dokumente, Chat-Sessions und Search arbeiten fachlich mit `workspace_id`.
- Geschuetzte Backend-Endpunkte pruefen den AuthContext ueber die Middleware gegen Workspace-Membership.
- Dokument-Read-, Search-, Chat-, Upload-, Jobs- und Diagnostics-Pfade leiten den Workspace serverseitig aus dem AuthContext ab.
- Dokument-Lifecycle-Mutationen (`archive`, `restore`, `delete`) sind auth-geschuetzt, uebergeben den Workspace aber aktuell nicht an den Lifecycle-Service; das ist ein Gate-Blocker fuer M4a/M4c.
- M4a bleibt dennoch offen, weil der Frontend-Produktfluss und einzelne Vertragsstellen noch nicht als durchgaengiges Sicherheitsmodell freigegeben sind.

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
- Sicherheitsmodell konsistent mit einem abgeschlossenen M4a: nein
- Entscheidung: M4a ist im vorliegenden Repository nicht abgeschlossen
