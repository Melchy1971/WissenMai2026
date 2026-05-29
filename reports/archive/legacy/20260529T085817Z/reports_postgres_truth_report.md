# PostgreSQL Truth-Test-Report

| Feld | Wert |
|---|---|
| Zeitpunkt | 2026-05-21T11:10:33.297876Z |
| Command | `python.exe -m pytest -m postgres_truth tests/postgres_truth -q` |
| TEST_DATABASE_URL gesetzt | true |
| Alembic head | 20260508_0014 |
| Collected | 138 |
| M4-Gate Tests | 1 |
| M4a-Gate Tests | 32 |
| M4b-Gate Tests | 11 |
| M4c-Gate Tests | 9 |
| M4e-Gate Tests | 0 |
| M5 Tests | 37 |
| Governance Tests | 39 |
| Chaos Tests | 9 |
| Passed | 129 |
| Failed | 8 |
| Skipped | 0 |
| Errors | 1 |
| Duration | 279.36s |
| Pytest exit code | 1 |
| Commit | 9b0e5e38a43478ab7dee42f2c365f1574da8c8c6 |
| M4-Gate-Auswirkung | M4-Gate PASS |

## Gate Scores

| Gate | Score | Schwelle | Status |
|---|---|---|---|
| M4 | 100.0% | >= 90% | PASS |
| M4a | 96.9% | >= 95% | PASS |
| M4b | 100.0% | >= 90% | PASS |
| M4c | 100.0% | >= 90% | PASS |
| M4e | n/a (keine Tests) | >= 90% | n/a |
| M5 | 78.4% | n/a fuer M4 | n/a |
| Governance | 100.0% | n/a fuer M4 | n/a |
| Chaos | 100.0% | n/a fuer M4 | n/a |

## RC-Blocker

Keine offenen RC-Blocker.

## Interpretation

- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.
- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.
- Bei gesetzter `TEST_DATABASE_URL` sind Skips, Migrationfehler, Setup-Errors und Testfehler Gate-blockierend.
- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.
