# Runtime Connectivity Report

- Result: `PASS`
- Generated: `2026-06-03T09:35:24.440Z`
- Database: `postgresql+psycopg://Markus:***@85.215.131.200:5432/wissen2026`
- API: `http://127.0.0.1:8001`
- Frontend: `http://127.0.0.1:5174`

## Checks

| Check | Result | Evidence |
|---|---:|---|
| DATABASE_URL gesetzt | `PASS` | postgresql+psycopg://Markus:***@85.215.131.200:5432/wissen2026 |
| Alembic head | `PASS` | current=20260602_0019 |
| Seed erfolgreich | `PASS` | seed_auth.py exit 0 |
| Backend /health | `PASS` | 200 |
| /auth/login | `PASS` | 200 |
| /auth/me | `PASS` | 200 |
| Frontend API erreichbar | `PASS` | 3 API response(s) |
| Workspace Bootstrap erfolgreich | `PASS` | http://127.0.0.1:5174/documents |

## Alembic

- Heads: `20260602_0019`
- Current: `20260602_0019`

## Verbleibende Fehler

- keine
