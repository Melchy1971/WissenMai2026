# PostgreSQL Truth Tests

Die PostgreSQL Truth-Test-Suite ist der harte Nachweis fuer kritische M4-Flows gegen echte PostgreSQL-Transaktionen. SQLite-, In-Memory- oder Mock-basierte Tests gelten fuer diese Bereiche nicht als ausreichender Sicherheitsnachweis.

Die uebergeordnete Governance fuer Truth-Quellen und Gate-Policies steht in [docs/operational-truth-governance.md](H:/WissenMai2026/docs/operational-truth-governance.md).

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
- Queue Aging Detection (`queue_aging`)
- Reindex Governance (`reindex_governance`)
- Citation Longevity (`citation_longevity`)
- Cleanup Governance (`cleanup_governance`)
- M5 Cleanup Processes (`m5_cleanup`)
- Entropy / Langzeitbetrieb (`entropy`)

## M5 Truth-Test-Erweiterung

M5 darf nicht als rein dokumentarische Phase gelten. Sobald M5 startet, wird `postgres_truth` um echte PostgreSQL-Nachweise fuer die neuen Systemreife-Bloecke erweitert.

Verpflichtende M5-Erweiterungen:

- `data_quality`
	- prueft die dokumentierten M5-Dateninvarianten gegen echte PostgreSQL-Bestaende
	- umfasst insbesondere Dokument/Version/Chunk-Konsistenz, `source_anchor`, Orphans, `content_hash`-Eindeutigkeit und Citation-Sonderfaelle
- `drift_detection`
	- prueft Drift-Arten gegen echte DB-/Index-/Lifecycle-/Queue-Zustaende
	- umfasst mindestens DB-vs-Index, Lifecycle-vs-Searchbarkeit, Citation-Snapshot-vs-Live-Status und Backup-Manifest-Abgleich
- `cleanup_dry_run`
	- prueft, dass Dry-Run-Berichte fuer Cleanup-Klassen erzeugbar, schluessig und nicht mutierend sind
	- beweist insbesondere Schutzregeln fuer Chat-Citations und referenzierte Originaldateien
- `health_score`
	- prueft, dass der M5-Health-Score aus echten Messgrundlagen berechnet werden kann
	- bewertet Formel, Teilkomponenten, konservativen Umgang mit fehlender Evidenz und Statusklassifikation
- `backup_freshness`
	- prueft Backup-Frische und Verifikationslage gegen echte Backup-Artefakte und Reports
	- umfasst mindestens gueltigen Verify-Status, Backup-Alter und Restore-Nachweisbezug

Ziel der Erweiterung:

- M5-Systemreife wird ueber dieselbe Wahrheitslogik abgesichert wie M4-Kernbereiche.
- Reine Dokumentaussagen ohne echten PostgreSQL-Nachweis zaehlen nicht als M5-Freigabegrund.

## Implementierte M5 Truth-Test-Dateien

Stand 2026-05-12:

| Datei | Marker | Tests | Beschreibung |
|---|---|---|---|
| `test_m4_truth_flows.py` | `postgres_truth`, `m4b_gate`, `m4c_gate` | Kern-M4-Flows | Upload, Lifecycle, Reindex, Citations |
| `test_m4a_auth_workspace_truth.py` | `postgres_truth`, `m4a_gate` | Auth/Workspace | Isolation, Membership, Session |
| `test_m4_crash_recovery_truth.py` | `postgres_truth` | Crash-Recovery | Import/Reindex-Absturz-Szenarien |
| `test_rc3_chaos_truth.py` | `postgres_truth` | RC-3 Chaos | Advisory-Lock, Race Conditions |
| `test_queue_aging_truth.py` | `postgres_truth`, `queue_aging` | Queue Aging | Backlog, Starvation, Dead-Letter-Akkumulation |
| `test_reindex_governance_truth.py` | `postgres_truth`, `reindex_governance` | Reindex Governance | Safety-Gates, Audit-Trail, Rollback |
| `test_citation_longevity_truth.py` | `postgres_truth`, `citation_longevity` | Citation Longevity | Snapshot-Stabilitaet, Orphan-Rate |
| `test_cleanup_governance_truth.py` | `postgres_truth`, `cleanup_governance` | Cleanup Governance | Dry-Run, Delta, Safety-Gates |
| `test_m5_cleanup_truth.py` | `postgres_truth`, `m5_cleanup` | Cleanup Processes | Orphan, stale index, temp files, old reports, expired sessions |
| `test_entropy_truth.py` | `postgres_truth`, `entropy` | Entropy / Langzeitbetrieb | Orphan-Wachstum, Stale-Index, Retrieval-Degradation |

Hilfsmodule:

| Datei | Beschreibung |
|---|---|
| `conftest.py` | Gemeinsame Fixtures: `truth_session`, `truth_connection`, `truth_seed`, `truth_client` |
| `support.py` | Gemeinsame Hilfsfunktionen |
| `crash_matrix.py` | Crash-Szenario-Matrix fuer Recovery-Tests |
| `crash_import_worker.py` | Import-Crash-Simulation |
| `crash_reindex_worker.py` | Reindex-Crash-Simulation |
| `entropy_helpers.py` | `EntropyMetrics`, `collect_metrics`, `seed_batch`, Drift-Injection-Funktionen |

Alle neuen Marker sind in `backend/pyproject.toml` registriert:

```toml
"queue_aging: Queue Aging and Starvation Detection truth tests"
"reindex_governance: Reindex Governance safety constraints and audit trail truth tests"
"citation_longevity: Citation Longevity Audit — long-term snapshot stability truth tests"
"cleanup_governance: Cleanup Governance safety constraints and audit trail truth tests"
"m5_cleanup: M5 Cleanup process truth tests"
"entropy: Long-term entropy and system aging detection truth tests"
```

Truth-Nachweisstand:

- Letzter verifizierter Lauf: 2026-05-11, 33 Tests (nur M4-Bereiche, commit b07798e)
- Neue M5-Tests sind noch nicht im letzten Report enthalten
- Naechster Schritt: `TEST_DATABASE_URL` setzen und vollstaendigen Lauf ausfuehren

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
- M5-Truth-Tests zaehlen nur mit echter PostgreSQL-Datenbank und aktueller `TEST_DATABASE_URL`.
- SQLite, In-Memory oder Mock-Fakes duerfen fuer M5 nur als Fast-Feedback dienen, nie als Gate-Quelle.
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

Fuer M5 gilt dieselbe Regel:

- M5-Truth- und Freigabeaussagen duerfen nur aus einem aktuellen JSON-Report mit echter PostgreSQL-Testdatenbank abgeleitet werden.
- Fast-Feedback-Laeufe auf SQLite duerfen dokumentiert werden, aber nicht als Gate-Pass markiert werden.

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

Fuer M5 gilt zusaetzlich:

- Data Quality, Drift Detection, Cleanup Dry Run, Health Score und Backup Freshness muessen in derselben Truth-Logik verankert werden.
- Ein gruener SQLite- oder Mock-Lauf ist fuer M5 nur ein Entwicklerhinweis, kein Betriebs- oder Freigabenachweis.
