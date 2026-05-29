# M3a Gate Result

| Feld | Wert |
|---|---|
| Gate Result | PASS |
| Score | 100.0 |
| Entscheidung | M3a abgeschlossen |
| Regeln | 9 / 9 |
| Timestamp | `2026-05-19T08:59:27.903906+00:00` |

## Regeln

| Regel | Status | Blocker |
|---|---|---|
| `full_suite_frontend_truth_green` | PASS |  |
| `m3a_backend_minimum_green` | PASS |  |
| `contract_tests_green` | PASS |  |
| `gui_chaos_tests_green` | PASS |  |
| `frontend_truth_passed_equals_collected` | PASS |  |
| `frontend_truth_failed_zero` | PASS |  |
| `frontend_truth_skipped_zero` | PASS |  |
| `no_api_unreachable_in_normalflow` | PASS |  |
| `no_workspace_not_configured_after_valid_login` | PASS |  |

## Blocker

- keine

## Scope-Entscheidung

- M3a Frontend Truth: `frontend_truth_report.json`, `gui_truth/latest.json`, GUI Chaos und Contract Tests sind blockierend.
- M3a Backend-Minimum: echte API erreichbar, echte DB aktiv, Contract Tests gruen und relevante M3a-Endpunktflows im Frontend Truth belegt.
- M4 Backend Truth: `postgres_truth_report.json` bewertet Backend-Hardening und ist keine M3a-Gate-Regel.
- M5 Operational Truth: Entropy-, Queue-Aging-, Drift-, Cleanup- und Longevity-Tests sind keine M3a-Gate-Regeln.

## M4/M5 Referenz

- `postgres_truth_considered_for_m3a`: `false`

| Failure/Error | Gruppe | M4-kritisch | M5-kritisch | M3a-relevant |
|---|---|---|---|---|
| `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_chunk_deletion_increases_citation_orphan_rate` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_citation_orphan_rate_tracks_deletion_scale` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_drift_trend_function_returns_valid_structure` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_entropy_simulation_detects_chaos_and_verifies_recovery` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_repeated_archive_restore_cycles_stay_entropy_neutral` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_chunks_are_detected_by_metric` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_purge_restores_clean_state` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_dead_letter_accumulation_is_detected` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_draining_jobs_reduces_backlog` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_retryable_jobs_accumulate_and_are_detected` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_retrieval_repair_restores_coverage` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_searchability_drift_reduces_coverage` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_restore_cycle_does_not_create_stale_entries` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_cleared_by_repair_pass` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_grows_when_archive_skips_repair` | M5 entropy/drift | no | yes | no |
| `tests/postgres_truth/test_m4_truth_flows.py::test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows` | M4b | yes | no | no |
| `unclassified_setup_error_1` | Setup/Error | yes | yes | no |
| `unclassified_setup_error_2` | Setup/Error | yes | yes | no |
