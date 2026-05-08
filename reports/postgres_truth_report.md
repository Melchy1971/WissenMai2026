# PostgreSQL Truth-Test-Report

| Feld | Wert |
|---|---|
| Zeitpunkt | 2026-05-08T09:40:55.356836Z |
| Command | `python.exe -m pytest -m postgres_truth tests/postgres_truth -q` |
| TEST_DATABASE_URL gesetzt | false |
| Alembic head | 20260508_0014 |
| Collected | 25 |
| Passed | 0 |
| Failed | 0 |
| Skipped | 25 |
| Errors | 0 |
| Duration | 1.163s |
| Pytest exit code | 0 |
| Commit | 7109332d3493b3f7b547f35607c4021511ba7e74 |

## Interpretation

- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.
- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.
- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.
