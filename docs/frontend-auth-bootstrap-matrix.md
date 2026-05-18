# Frontend Auth Bootstrap Matrix

Stand: 2026-05-18

Validierter Truth-Stand:

- Kanonischer Nachlauf `python scripts/run_gui_truth.py --filter tests/gui_truth/test_02_auth_bootstrap.spec.js` ist gruen (`22/22`).
- Damit sind die Szenarien No Token, Bootstrap Resolve, Complete Session, Invalid Token, Backend Unreachable, No Membership, Forbidden und Logout browsernah belegt.
- Dieser Nachweis gilt fuer den Auth-Bootstrap-Slice und ersetzt keinen grünen Full-Suite-Frontend-Truth-Lauf.

## E2E-Ablauf

| Schritt | Erwartung |
|---|---|
| Login | `POST /api/v1/auth/login` liefert Token; daraus wird noch kein Default-Workspace abgeleitet. |
| Token speichern | Token wird in API-Kontext und Auth-State uebernommen. |
| Session hydrieren | `GET /api/v1/auth/me` laedt User, Memberships und `active_workspace_id`. |
| Workspace setzen | `active_workspace_id` muss in den Memberships enthalten sein. |
| Dokumentliste laden | `GET /documents` sendet `Authorization` und `X-Workspace-Id`. |
| Suche ausfuehren | `GET /api/v1/search/chunks` sendet denselben Workspace-Kontext. |
| Upload starten | `POST /documents/import` sendet denselben Workspace-Kontext. |

## Fehlerklassifikation

| Zustand | API/Client-Code | UI-Zustand |
|---|---|---|
| Netzwerkfehler, Backend nicht erreichbar | `API_UNREACHABLE` | `Backend nicht erreichbar` |
| CORS blockiert | `CORS_ERROR` | `Auth-Anfrage blockiert` oder API-Fehlerzustand |
| Timeout | `TIMEOUT` | `Auth-Anfrage abgelaufen` oder API-Fehlerzustand |
| Kein oder ungueltiger Token | `AUTH_REQUIRED` / `UNAUTHORIZED` | `Session abgelaufen` im Bootstrap, sonst Auth-Fehler |
| Keine Memberships nach `/auth/me` | `WORKSPACE_NOT_CONFIGURED` | `Keine Workspace-Mitgliedschaft` |
| `active_workspace_id` fehlt | `AUTH_WORKSPACE_MISSING` | `Aktiver Workspace fehlt`; kein Default-Workspace wird gewaehlt |
| `active_workspace_id` nicht in Memberships | `AUTH_WORKSPACE_NOT_ALLOWED` | `Workspace nicht zulaessig` |
| Workspace-Zugriff verweigert | `WORKSPACE_ACCESS_FORBIDDEN` | `Workspace-Zugriff verweigert` |

## UI-Zustandsmatrix

| Auth-State | Protected Route | Dokumente/Search/Upload |
|---|---|---|
| Kein Token | Redirect nach `/login` | Keine geschuetzten API-Calls |
| Token, Bootstrap laeuft | Loading `Authentifizierung wird initialisiert...` | Keine geschuetzten API-Calls vor `/auth/me` |
| Token, `/auth/me` erfolgreich, Workspace gueltig | App sichtbar | Geschuetzte Calls mit `Authorization` und `X-Workspace-Id` |
| Token, keine Membership | Fehler `Keine Workspace-Mitgliedschaft` | Keine Dokumentliste, keine Suche, kein Upload |
| Token, Workspace fehlt | Fehler `Aktiver Workspace fehlt` | Kein impliziter Default-Workspace |
| Erfolgreicher Login | `/auth/me` wird geladen, dann `/documents` | Kein Text `nicht konfiguriert` in Workspace-Anzeige |
