# PostgreSQL Truth-Test-Report

| Feld | Wert |
|---|---|
| Zeitpunkt | 2026-05-13T08:23:30.535021Z |
| Command | `python.exe -m pytest -m postgres_truth tests/postgres_truth -q` |
| TEST_DATABASE_URL gesetzt | true |
| Alembic head | 20260508_0014 |
| Collected | 112 |
| M4a-Gate Tests | 13 |
| M4b-Gate Tests | 12 |
| M4c-Gate Tests | 11 |
| M4d-Gate Tests | 0 |
| Passed | 83 |
| Failed | 29 |
| Skipped | 0 |
| Errors | 0 |
| Duration | 85.976s |
| Pytest exit code | 1 |
| Commit | a21e7016a84b3c058e4ac52e6045b2817961396d |
| M4-Gate-Auswirkung | M4-Gate BLOCKED |

## Gate Scores

| Gate | Score | Schwelle | Status |
|---|---|---|---|
| M4a | 100.0% | >= 95% | PASS |
| M4b | 91.7% | >= 90% | PASS |
| M4c | 100.0% | >= 90% | PASS |
| M4d | n/a (keine Tests) | >= 85% | n/a |

## RC-Blocker

Keine offenen RC-Blocker.

## Interpretation

- Freigabeaussagen fuer `postgres_truth` duerfen nur aus diesem Report oder dem JSON-Pendant abgeleitet werden.
- `TEST_DATABASE_URL gesetzt = false` bedeutet: kein echter PostgreSQL-Nachweis; ein gruenes M4-Gate darf daraus nicht abgeleitet werden.
- Bei gesetzter `TEST_DATABASE_URL` sind Skips, Migrationfehler, Setup-Errors und Testfehler Gate-blockierend.
- Mehrere Alembic-Heads sind ein Befund des Repositories und werden hier unverdeckt ausgewiesen.

## M4-Gate-Blocker

- 29 Testfehler
