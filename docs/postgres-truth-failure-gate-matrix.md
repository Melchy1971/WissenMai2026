# PostgreSQL Truth Failure-to-Gate Matrix

Stand: 2026-05-19

Quelle: `reports/postgres_truth_report.json` vom 2026-05-18.

## Zusammenfassung

| Gruppe | Anzahl | Gate-kritisch fuer M4 | Gate-kritisch fuer M5 | Relevant fuer M3a |
|---|---:|---|---|---|
| M4a | 0 | ja | nein | nein |
| M4b | 1 | ja | nein | nein |
| M4c | 0 | ja | nein | nein |
| M5 entropy/drift | 15 | nein | ja | nein |
| Setup/Error | 2 | ja | ja | nein |

## Failure-to-Gate Matrix

| Failure/Error | Gruppe | Gate-kritisch M4 | Gate-kritisch M5 | Relevant M3a |
|---|---|---|---|---|
| `tests/postgres_truth/test_m4_truth_flows.py::test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows` | M4b | ja | nein | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_chunk_deletion_increases_citation_orphan_rate` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_citation_orphan_rate_tracks_deletion_scale` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_drift_trend_function_returns_valid_structure` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_entropy_simulation_detects_chaos_and_verifies_recovery` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_repeated_archive_restore_cycles_stay_entropy_neutral` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_chunks_are_detected_by_metric` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_purge_restores_clean_state` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_dead_letter_accumulation_is_detected` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_draining_jobs_reduces_backlog` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_retryable_jobs_accumulate_and_are_detected` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_retrieval_repair_restores_coverage` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_searchability_drift_reduces_coverage` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_restore_cycle_does_not_create_stale_entries` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_cleared_by_repair_pass` | M5 entropy/drift | nein | ja | nein |
| `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_grows_when_archive_skips_repair` | M5 entropy/drift | nein | ja | nein |
| `unclassified_setup_error_1` | Setup/Error | ja | ja | nein |
| `unclassified_setup_error_2` | Setup/Error | ja | ja | nein |

## Bereinigte Blockerlogik

- M3a wird durch keine der 18 `postgres_truth`-Findings blockiert. M3a verwendet nur Frontend Truth, GUI Chaos, Contract Tests und das Backend-Minimum.
- M4 wird durch M4a/M4b/M4c-Failures und Setup-/Collect-Errors blockiert. Entropy-, Queue-Aging- und Drift-Failures blockieren M4 nicht.
- M5 wird durch Entropy-/Drift-Failures sowie Setup-/Collect-Errors blockiert.
- Die zwei historischen Errors sind im aktuellen JSON nicht als Nodeids enthalten. Kuenftige Reports muessen `error_tests` ausweisen; bis zur erneuten Ausfuehrung bleiben sie als Setup/Error gate-kritisch fuer Report-Integritaet.

## Neue Fix-Reihenfolge

1. `postgres_truth` erneut mit Error-Nodeid-Erfassung erzeugen, damit die zwei Setup/Error-Faelle konkret sichtbar sind.
2. M4b-Failure `test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows` beheben.
3. M4-Validator erneut ausfuehren; M4 darf nur noch an M4a/M4b/M4c oder Setup/Error scheitern.
4. Danach die 15 M5-Entropy-/Drift-Failures beheben.
5. Queue-Aging-/Drift-Nachweise erst als M5-Operational-Truth freigeben, wenn die Entropy-Basismetriken stabil sind.
