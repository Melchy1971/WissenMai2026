# PostgreSQL Truth-Test-Report

| Feld | Wert |
|---|---|
| Zeitpunkt | 2026-05-08T13:02:01.393633Z |
| Command | `python.exe -m pytest -m postgres_truth tests/postgres_truth -q` |
| TEST_DATABASE_URL gesetzt | true |
| Alembic head | 20260508_0014 |
| Collected | 32 |
| M4a-Gate Tests | 9 |
| M4b-Gate Tests | 5 |
| M4c-Gate Tests | 8 |
| Passed | 26 |
| Failed | 3 |
| Skipped | 0 |
| Errors | 3 |
| Duration | 38.362s |
| Pytest exit code | 1 |
| Commit | 96ca514c53112dcdd153a789493627d40e957685 |
| M4-Gate-Auswirkung | M4-Gate BLOCKED |

## Interpretation

- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.
- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.
- Bei gesetzter `TEST_DATABASE_URL` sind Skips, Migrationfehler, Setup-Errors und Testfehler Gate-blockierend.
- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.

## M4-Gate-Blocker

- 3 Testfehler
- 3 Setup-/Collect-Fehler
