# PostgreSQL Truth — Delta-Report

## Zusammenfassung

| Feld | Vorheriger Lauf | Aktueller Lauf | Delta |
|---|---|---|---|
| Passed | 33 | 83 | +50 |
| Failed | 0 | 29 | +29 |
| Errors | 0 | 0 | 0 |
| Skipped | 0 | 0 | 0 |
| M4-Gate | 2026-05-11 | M4-Gate BLOCKED | REGRESSION |

## Läufe

| | Zeitpunkt | Commit |
|---|---|---|
| Vorher | 2026-05-11T08:14:50.371402Z | b07798e2a9b9300aee15edfe48de82f160c3a3b3 |
| Jetzt | 2026-05-13T08:23:30.535021Z | a21e7016a84b3c058e4ac52e6045b2817961396d |

## Neue Fehlschläge

- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_archive_syncs_citation_status`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_delete_syncs_citation_status`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_deleted_not_marked`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_orphaned_anchor_after_rechunk`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_preview_staleness`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_restored_not_marked`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_status_drift`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_restore_syncs_citation_back_to_active`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_workspace_isolation`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceDryRun::test_dry_run_candidate_count_correct_with_expired_sessions`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceDryRun::test_dry_run_does_not_modify_db`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceSafetyGates::test_running_jobs_block_execution`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceSnapshots::test_snapshot_delta_on_execute_reflects_session_deletion`
- `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_chunk_deletion_increases_citation_orphan_rate`
- `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_citation_orphan_rate_tracks_deletion_scale`
- `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_drift_trend_function_returns_valid_structure`
- `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_entropy_simulation_detects_chaos_and_verifies_recovery`
- `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_repeated_archive_restore_cycles_stay_entropy_neutral`
- `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_chunks_are_detected_by_metric`
- `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_purge_restores_clean_state`
- `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_dead_letter_accumulation_is_detected`
- `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_draining_jobs_reduces_backlog`
- `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_retryable_jobs_accumulate_and_are_detected`
- `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_retrieval_repair_restores_coverage`
- `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_searchability_drift_reduces_coverage`
- `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_restore_cycle_does_not_create_stale_entries`
- `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_cleared_by_repair_pass`
- `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_grows_when_archive_skips_repair`
- `tests/postgres_truth/test_m4_truth_flows.py::test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows`

## Regressionserkennung

**REGRESSION DETECTED** — dieser Lauf hat neue Testfehler oder blockiert das M4-Gate.

Erstmals fehlschlagende Tests:
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_archive_syncs_citation_status`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_delete_syncs_citation_status`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_deleted_not_marked`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_orphaned_anchor_after_rechunk`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_preview_staleness`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_restored_not_marked`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_detects_status_drift`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_restore_syncs_citation_back_to_active`
- `tests/postgres_truth/test_citation_longevity_truth.py::test_longevity_workspace_isolation`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceDryRun::test_dry_run_candidate_count_correct_with_expired_sessions`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceDryRun::test_dry_run_does_not_modify_db`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceSafetyGates::test_running_jobs_block_execution`
- `tests/postgres_truth/test_cleanup_governance_truth.py::TestCleanupGovernanceSnapshots::test_snapshot_delta_on_execute_reflects_session_deletion`
- `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_chunk_deletion_increases_citation_orphan_rate`
- `tests/postgres_truth/test_entropy_truth.py::TestCitationDegradation::test_citation_orphan_rate_tracks_deletion_scale`
- `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_drift_trend_function_returns_valid_structure`
- `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_entropy_simulation_detects_chaos_and_verifies_recovery`
- `tests/postgres_truth/test_entropy_truth.py::TestMultiEpochEntropySimulation::test_repeated_archive_restore_cycles_stay_entropy_neutral`
- `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_chunks_are_detected_by_metric`
- `tests/postgres_truth/test_entropy_truth.py::TestOrphanGrowthDetection::test_orphan_purge_restores_clean_state`
- `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_dead_letter_accumulation_is_detected`
- `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_draining_jobs_reduces_backlog`
- `tests/postgres_truth/test_entropy_truth.py::TestQueueBacklogDrift::test_retryable_jobs_accumulate_and_are_detected`
- `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_retrieval_repair_restores_coverage`
- `tests/postgres_truth/test_entropy_truth.py::TestRetrievalDegradation::test_searchability_drift_reduces_coverage`
- `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_restore_cycle_does_not_create_stale_entries`
- `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_cleared_by_repair_pass`
- `tests/postgres_truth/test_entropy_truth.py::TestStaleIndexDetection::test_stale_index_grows_when_archive_skips_repair`
- `tests/postgres_truth/test_m4_truth_flows.py::test_postgres_truth_recover_stale_import_job_retries_without_duplicate_rows`
