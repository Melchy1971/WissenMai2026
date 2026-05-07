# PostgreSQL Truth Tests

Die PostgreSQL Truth-Test-Suite ist der harte Nachweis fuer kritische M4-Flows gegen echte PostgreSQL-Transaktionen. SQLite-, In-Memory- oder Mock-basierte Tests gelten fuer diese Bereiche nicht als ausreichender Sicherheitsnachweis.

## Scope

Die Suite liegt unter `backend/tests/postgres_truth/` und ist mit `postgres_truth` markiert.

Abgedeckte Bereiche:

- Upload
- Duplicate Handling
- Lifecycle
- Search
- Chat Retrieval
- Search/Chat Retrieval Consistency
- Reindex
- Auth/Workspace Isolation

## Ausfuehrung

```powershell
Set-Location backend
$env:TEST_DATABASE_URL = "postgresql://..."
pytest -m postgres_truth tests/postgres_truth
```

Ohne `TEST_DATABASE_URL` darf die Suite skippen. Jeder andere Fehler ist ein echter Fehler.

## Harte Regeln

- Kein Skip ausser bei fehlender `TEST_DATABASE_URL`.
- Alembic- oder Migrationsfehler sind `FAIL`.
- `IntegrityError` ist `FAIL`.
- Stale State zwischen Tests ist verboten.
- Tests nutzen deterministische IDs und Fixtures.
- Truth-Testdaten werden vor und nach jedem Test entfernt.
- Die Suite darf keine produktiven Admin-Aktionen freischalten.

## Testarchitektur

`backend/tests/postgres_truth/conftest.py` stellt die gemeinsame Architektur bereit:

- `postgres_truth_schema`: setzt `settings.database_url`, verbindet die App mit `TEST_DATABASE_URL` und fuehrt `alembic upgrade head` aus.
- `truth_cleanup`: entfernt deterministische Truth-Testdaten vor und nach jedem Test.
- `truth_connection`: oeffnet pro Test eine PostgreSQL-Connection mit aeusserer Transaktion und fuehrt am Testende Rollback aus.
- `truth_seed`: legt deterministische Workspaces, User, Memberships und Sessions an.
- `truth_client`: ruft die API mit echter Auth-Session und Workspace-Header innerhalb der Testtransaktion auf.
- `assert_no_truth_rows`: beweist, dass kein Truth-Test-Stale-State vorhanden ist.

Die Tests verwenden echte SQLAlchemy-/psycopg-Verbindungen gegen PostgreSQL. Fehler werden nicht in SQLite oder Mock-Fakes reproduziert.

## Reportformat

Jeder Lauf soll als Truth-Test-Report dokumentiert werden:

```text
PostgreSQL Truth-Test-Report
Datum:
Command:
TEST_DATABASE_URL: gesetzt, Wert redigiert
Alembic target: head

Summary:
- Gesamt:
- Passed:
- Failed:
- Skipped:
- Dauer:

Matrix:
| Bereich | Test | Deterministisch | Ergebnis | Hinweis |
| Upload | tests/postgres_truth/test_m4_truth_flows.py::test_upload_and_duplicate_handling_use_real_postgresql_transactions | ja | pass/fail | echte Import-Transaktion |
| Duplicate Handling | tests/postgres_truth/test_m4_truth_flows.py::test_upload_and_duplicate_handling_use_real_postgresql_transactions | ja | pass/fail | gleicher Inhalt, ein Dokument |
| Lifecycle | tests/postgres_truth/test_m4_truth_flows.py::test_lifecycle_and_workspace_isolation_are_truth_checked | ja | pass/fail | archivieren/wiederherstellen, fremder Workspace blockiert |
| Search | tests/postgres_truth/test_m4_truth_flows.py::test_search_chat_retrieval_and_reindex_use_real_postgresql_state | ja | pass/fail | nur aktive Workspace-Chunks |
| Chat Retrieval | tests/postgres_truth/test_m4_truth_flows.py::test_search_chat_retrieval_and_reindex_use_real_postgresql_state | ja | pass/fail | echte Chat-Session, echte Retrieval-Quellen |
| Search/Chat Consistency | tests/postgres_truth/test_m4_truth_flows.py::test_search_and_chat_retrieval_use_identical_active_chunks_and_source_anchors | ja | pass/fail | identischer Bestand, identische Query, gleiche active Chunks und source_anchor |
| Reindex | tests/postgres_truth/test_m4_truth_flows.py::test_search_chat_retrieval_and_reindex_use_real_postgresql_state | ja | pass/fail | Service-Rebuild gegen echte Rows |
| Auth/Workspace Isolation | tests/postgres_truth/test_m4_truth_flows.py::test_auth_workspace_truth_blocks_foreign_workspace_and_non_admin_diagnostics | ja | pass/fail | AuthContext und Workspace-Membership |

Nicht deterministisch:
- Keine bekannten nicht deterministischen Truth-Tests.
- Parallel-Race-Tests werden erst aufgenommen, wenn sie ohne Timing-Abhaengigkeit stabil beweisbar sind.
```

## Aktuelle Erwartung

Die Suite ist absichtlich hart. Wenn M4a/M4b/M4c noch offene Gate-Blocker haben, darf ein PostgreSQL-Truth-Lauf fehlschlagen. Solche Fehler sind keine Testinstabilitaet, sondern Freigabe-Blocker.
