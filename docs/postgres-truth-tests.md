# PostgreSQL Truth Tests

Die PostgreSQL Truth-Test-Suite ist der harte Nachweis fuer kritische M4-Flows gegen echte PostgreSQL-Transaktionen. SQLite-, In-Memory- oder Mock-basierte Tests gelten fuer diese Bereiche nicht als ausreichender Sicherheitsnachweis.

## Scope

Die Suite liegt unter `backend/tests/postgres_truth/` und ist mit `postgres_truth` markiert.

Aktueller Code-Stand:

- Die Suite liegt unter `backend/tests/postgres_truth/test_*.py`.
- Collection- und Laufzahlen fuer M4-Gates muessen aus `reports/postgres_truth_report.json` kommen.
- Ob die Suite gruen ist, darf nur aus einem aktuellen JSON-Testreport mit gesetzter `TEST_DATABASE_URL` behauptet werden.
- `reports/postgres_truth_report.md` ist nur eine menschenlesbare Begleitansicht und keine M4-Gate-Quelle.

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
Set-Location H:\WissenMai2026
$env:TEST_DATABASE_URL = "postgresql://..."
.\scripts\run-postgres-truth.ps1
.\scripts\validate-m4-truth-gate.ps1
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
- Keine statischen Aussagen wie `18/18 gruen`, `24/24 gruen` oder aehnliche Zaehler ohne beigefuegten aktuellen Report.
- Dokumentationsstatus fuer `postgres_truth` darf nur diese Formen verwenden, wenn kein aktueller Report beiliegt:
	- Suite vorhanden
	- letzter Lauf nur mit `TEST_DATABASE_URL` beweisbar
	- Ergebnis muss aus aktuellem Testreport kommen

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

Jeder Lauf schreibt zwei Artefakte:

- `reports/postgres_truth_report.json`
- `reports/postgres_truth_report.md`

Die einzige automatisierbare und freigaberelevante M4-Gate-Quelle ist:

- `reports/postgres_truth_report.json`

Pflichtfelder:

- `generated_at`
- `test_database_url_set`
- `alembic_heads`
- `collected`
- `passed`
- `failed`
- `skipped`
- `duration_seconds`
- `commit_hash` optional

Die Markdown-Datei ist nur die menschenlesbare Sicht auf denselben Lauf. Massgeblich fuer Automatisierung und Freigabe bleibt die JSON-Datei.

## M4 Truth Gate Validator

Der Validator liegt unter `scripts/validate_m4_truth_gate.py` und wird lokal ueber `scripts/validate-m4-truth-gate.ps1` ausgefuehrt.

`M4 Truth Gate = PASS` gilt nur, wenn alle Bedingungen aus `reports/postgres_truth_report.json` erfuellt sind:

- `test_database_url_set = true`
- `skipped = 0`
- `failed = 0`
- `passed > 0`
- `pytest_exit_code = 0`

Wenn eine Bedingung verletzt ist, gibt der Validator `M4 Truth Gate = FAIL` aus und beendet sich mit Exit-Code `1`.

## Aktuelle Erwartung

Die Suite ist absichtlich hart. Wenn M4a/M4b/M4c noch offene Gate-Blocker haben, darf ein PostgreSQL-Truth-Lauf fehlschlagen. Solche Fehler sind keine Testinstabilitaet, sondern Freigabe-Blocker.
