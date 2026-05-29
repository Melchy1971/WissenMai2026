# Runtime Connectivity Root Cause

Stand: 2026-05-20T10:50:00+02:00

## Ergebnis

Root Cause: Das Backend lauscht nicht auf der konfigurierten API Base URL. Das Frontend ist erreichbar, aber der Browser-Request `POST http://127.0.0.1:8000/api/v1/auth/login` endet mit `net::ERR_CONNECTION_REFUSED`.

Betroffene Schicht: Runtime Process Connectivity.

## Pruefung

| Check | Ergebnis | Befund |
|---|---|---|
| Backend laeuft tatsaechlich? | FAIL | Kein Listener auf `127.0.0.1:8000`, `8001` oder `8013`. |
| API_BASE_URL korrekt? | PASS | Frontend-Client defaultet auf `http://127.0.0.1:8000`. |
| VITE_API_BASE_URL korrekt? | DEFAULT_USED | Keine gesetzte `VITE_API_BASE_URL`; Default `http://127.0.0.1:8000` greift. |
| CORS korrekt? | Nicht Root Cause | CORS erlaubt `localhost/127.0.0.1` auf `5173/5174`; Fehler passiert vor CORS. |
| HTTPS/HTTP mismatch? | Nein | Frontend und API Base URL nutzen HTTP. |
| Reverse Proxy korrekt? | Nicht im Pfad | Browser ruft Backend direkt auf. |
| Docker Netzwerk korrekt? | FAIL/Unavailable | Docker API nicht erreichbar; lokale DB-Ports `5432`/`5433` lauschen nicht. |
| `/health` erreichbar? | FAIL | `http://127.0.0.1:8000/health` refused. |
| `/auth/me` erreichbar? | FAIL | `http://127.0.0.1:8000/api/v1/auth/me` refused. |
| Browser Console | Confirmed | `Failed to load resource: net::ERR_CONNECTION_REFUSED`. |
| Network Tab | Confirmed | Request failed: `POST http://127.0.0.1:8000/api/v1/auth/login`, `net::ERR_CONNECTION_REFUSED`. |

## Network-Klassifikation

- DNS: nicht Root Cause
- Timeout: nicht beobachtet
- Refused: beobachtet
- CORS: nicht beobachtet
- 404: nicht beobachtet
- 502: nicht beobachtet
- 503: nicht beobachtet

## Fix

1. Lokale DB starten: `scripts/dev-db.ps1`
2. Backend starten: `scripts/dev-backend.ps1`
3. Frontend mit passender API Base URL starten oder neu starten: `npm --prefix frontend run dev -- --host 127.0.0.1`
4. Falls Backend absichtlich auf anderem Port laeuft: `VITE_API_BASE_URL` vor Vite-Start auf exakt diese HTTP-URL setzen.

Verifikation:

- `GET http://127.0.0.1:8000/health` liefert `200`.
- `GET http://127.0.0.1:8000/health/db` liefert gesunden DB-Status.
- Login-Request liefert JSON statt `ERR_CONNECTION_REFUSED`.
- Browser Network Tab zeigt keine refused Requests gegen `127.0.0.1:8000`.

## Gate-Auswirkung

- M3a: Neue Runtime-/Frontend-Truth-Verifikation waere aktuell nicht moeglich; bestehendes RC-Artefakt wird dadurch nicht rueckwirkend geaendert.
- M4: Blockiert runtime-nahe M4-Validierung, weil Auth, Upload, Lifecycle und Diagnostics API nicht erreichbar sind.
- M5: Keine Implementierungsfreigabe; M5 bleibt durch M4 und Pre-M5 Decision blockiert.
