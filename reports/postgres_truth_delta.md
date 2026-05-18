# PostgreSQL Truth — Delta-Report

## Zusammenfassung

| Feld | Vorheriger Lauf | Aktueller Lauf | Delta |
|---|---|---|---|
| Passed | 83 | 120 | +37 |
| Failed | 29 | 16 | -13 |
| Errors | 0 | 2 | +2 |
| Skipped | 0 | 0 | 0 |
| M4-Gate | 2026-05-13 | M4-Gate BLOCKED | — |

## Läufe

| | Zeitpunkt | Commit |
|---|---|---|
| Vorher | 2026-05-13T08:23:30.535021Z | a21e7016a84b3c058e4ac52e6045b2817961396d |
| Jetzt | 2026-05-18T09:45:45.351580Z | 7bb5cec0b67511ed09325b9abda3a16960c381e0 |

## Gelöste Tests

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

## Regressionserkennung

Keine Regression erkannt.
