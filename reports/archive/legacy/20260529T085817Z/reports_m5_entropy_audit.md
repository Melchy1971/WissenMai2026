# M5 Data Aging & Entropy Audit

Status: `watch`
Audit: `m5-data-aging-entropy-v1`

## Entropie-Matrix

| Kategorie | Risiko | Wachstum ueber Zeit | Erkennung | Cleanup/Repair |
|---|---|---|---|---|
| stale Queue Jobs | low | start=0.0, end=11.0, delta=11.0, per_cycle=0.4074, max=11.0 | Age-bucket queue rows by status and claimed_at/updated_at; alert on running timeout, retryable backlog, dead_letter growth and missing audit transitions. | Move timed-out running jobs to retryable, replay dead_letter with advisory lock, cap retry attempts, and preserve replay audit rows. |
| veraltete Backups | low | successful_restore_cycles=[7, 14, 21, 28], max_backup_age_cycles=7, cycle_count=28 | Track latest successful backup timestamp, verify-backup status, restore dry-run age and checksum drift. | Fail readiness when no fresh verified backup exists; rotate old backups only after a newer restore-verified backup is present. |
| orphan growth | low | start=0.0, end=0.0, delta=0.0, per_cycle=0.0, max=0.0 | Run referential integrity probes for chunks without versions, files without documents, citations without message snapshots and index rows without live chunks. | Dry-run first, delete only provably unreachable rows/files, and require protected counts for historical citations and backup artifacts. |
| stale Indexeintraege | low | start=0.0, end=0.0, delta=0.0, per_cycle=0.0, max=0.0 | Compare search index document/chunk ids against DB lifecycle state after upload, archive, delete, restore and reindex. | Run workspace-scoped reindex, remove archived/deleted stale entries, then verify drift report is empty. |
| historische Citation Drift | low | citation_completeness=1.0, lifecycle_exclusion_violations=0 | Replay golden citation queries and compare stored citation snapshots against current document lifecycle/source_status. | Never rewrite historical quote snapshots; repair missing source_status metadata and keep deleted/archived sources visible as historical citations only. |
| duplicate growth | medium | golden_duplicate_detection=pass, production_duplicate_cardinality=not_measured | Aggregate by workspace_id + content_hash and by normalized title/source metadata; alert when controlled duplicates exceed expected pairs. | Keep content_hash uniqueness enforced; merge accidental duplicates only through an audited repair script preserving citations and versions. |
| Cleanup-Rueckstaende | low | start=0.0, end=0.0, delta=0.0, per_cycle=0.0, max=0.0, blocked_max=0 | Run cleanup dry-runs on a schedule and track candidate_count, protected_count and blocked_count deltas. | Convert recurring dry-run candidates into explicit retention rules; require zero blocked_count before destructive cleanup. |

## Aging-Risiken

- `duplicate growth`: GQ-002 duplicate handling is covered; full DB duplicate cardinality requires a live content_hash aggregation audit.

## Praeventionsmassnahmen

- Schedule entropy audit after every longrun simulation and before M5 readiness promotion.
- Gate M5 on stale_index_growth=0, orphan_growth=0, lifecycle_exclusion_violations=0 and successful restore verification.
- Store audit deltas over time so slow growth is visible before thresholds are breached.
- Add live DB duplicate cardinality audit before treating duplicate growth as fully closed.
