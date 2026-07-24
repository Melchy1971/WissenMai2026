# Evidenz — Truth-Neulauf (Der Rat, Empfehlung Schritt 1)

Stand: 2026-07-24. Umgebung: Cowork-Sandbox, lokales **PostgreSQL 16.2** (pgserver),
Python 3.10 mit `datetime.UTC`-Shim. Gegen die echte Test-DB (85.215.131.200) konnte
hier nicht getestet werden — ausgehendes Netz gesperrt. Diese Belege stammen aus einem
lokalen Postgres, sind aber DB-echt (kein SQLite-Mock).

## Bewiesen (reproduzierbar)

| Gegenstand | Ergebnis | Nachweis |
|---|---|---|
| Alembic-Kette komplett | **rc=0 bis Head `20260618_0026`**, 38 Public-Tabellen | `alembic -c backend/alembic.ini upgrade head` (vom Repo-Root) |
| GA-PERF-01 GIN-Index | **vorhanden** `ix_document_chunks_search_vector_gin` | `pg_indexes` auf `document_chunks` |
| Migrations-Integrationstests | **4 passed** | `pytest tests/integration/test_migrations.py` |
| GA-SEC-01 CSP | Code verdrahtet (`SecurityHeadersMiddleware` in `main.py`) | Codelesung; laut PRI-8-Plan 18/18 Tests grün |

## Zwei konkrete Funde

### Fund 1 — Redundanter GIN-Index (Tech Debt, bestätigt deinen PRI-8-Befund)
Auf `document_chunks.search_vector` liegen **zwei** GIN-Indizes:
- `ix_document_chunks_search_vector` (alt, aus `0011/0012`, nicht-partiell)
- `ix_document_chunks_search_vector_gin` (neu, aus `0026`, partiell `WHERE search_vector IS NOT NULL`)

Doppelte Schreiblast und Speicher ohne Lesevorteil. Entscheidung: einen droppen
(Folge-Migration). Wahrscheinlich den alten nicht-partiellen, falls der partielle die
Query-Prädikate abdeckt.

### Fund 2 — Backup/Restore-Truth-Gate ist unabhängig von SCGB-01 gebrochen
`tests/postgres_truth/test_m4e_backup_restore_truth.py` (Zeile ~6):

```python
from app.services.backup_restore import create_backup, validate_backup, restore_backup
```

Diese freien Funktionen existieren **nicht mehr**. `app/services/backup_restore.py`
exportiert heute eine klassenbasierte API:

```
class BackupRestoreService, class BackupSummary, class BackupRestoreError, ...
```

Folge: Die Datei bricht schon beim **Import** (Collection-Error). Der Marker
`m4e_backup_restore_truth` steht in `FINAL_TRUTH_MARKERS` **und** `M4_BLOCKING_MARKERS`
(tests/conftest.py). Damit kann der Backup/Restore-Truth-Gate **nicht** grün werden —
selbst mit erreichbarer Test-DB. Das ist ein echter Blocker, den der Maschinenstatus
nicht ausweist. Fix: die Testdatei auf `BackupRestoreService` umschreiben, bevor SCGB-01
überhaupt etwas nützt.

## Was hier NICHT verlässlich lief
Die vollständigen Truth-Marker-Suiten (`m4a/b/c`, `m5`, `governance`) liefen im Sandbox
nicht sauber durch: Zusammenspiel aus (a) dem projekteigenen Truth-Marker-Collection-Gate,
(b) der gebrochenen m4e-Datei (Fund 2) und (c) sporadischem `/tmp`-Reset der Sandbox.
Diese Suiten gehören auf deine echte DB via `run_truth_against_real_db.ps1` — mit dem
m4e-Fix zuerst.

## Reproduktion (lokal, echtes Postgres)
```bash
# vom Repo-Root, mit erreichbarer DB in DATABASE_URL/TEST_DATABASE_URL
python -m alembic -c backend/alembic.ini upgrade head
cd backend
python -m pytest tests/integration/test_migrations.py -q      # -> 4 passed
```
