# PostgreSQL Truth-Test-Report

| Feld | Wert |
|---|---|
| Zeitpunkt | 2026-05-11T08:14:50.371402Z |
| Command | `python.exe -m pytest -m postgres_truth tests/postgres_truth -q` |
| TEST_DATABASE_URL gesetzt | true |
| Alembic head | 20260508_0014 |
| Collected | 33 |
| M4a-Gate Tests | 10 |
| M4b-Gate Tests | 5 |
| M4c-Gate Tests | 8 |
| Passed | 33 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | 40.795s |
| Pytest exit code | 0 |
| Commit | b07798e2a9b9300aee15edfe48de82f160c3a3b3 |
| M4-Gate-Auswirkung | M4-Gate PASS |

## Interpretation

- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.
- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.
- Bei gesetzter `TEST_DATABASE_URL` sind Skips, Migrationfehler, Setup-Errors und Testfehler Gate-blockierend.
- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.
