# M5b Drift Architecture

Stand: 2026-06-08

Status: `DRAFT` (Planungsartefakt; keine `PREPARED`-Freigabe, kein `GO`, keine Implementierung, siehe `reports/current/m5b_start_gate.json`).

Scope: architecture phase only. No implementation, no migration, no API endpoint, no repair action.

This draft is allowed independently of the M5b start gate because it is planning-only. It does not authorize detector implementation, schema changes, background jobs, API routes, dashboard work, reindexing, cleanup, repair, or any mutating operation. While the M5a parent gate is not `PASS`, every M5b planning artifact remains `DRAFT`.

## Gate Status Model

- `DRAFT`: Architekturplanung ist erlaubt und unabhaengig vom Start-Gate.
- `PREPARED`: M5b darf nur dann vorbereitet sein, wenn `reports/current/m5b_start_gate.json` dies meldet und das M5a Parent-Gate `PASS` ist.
- M5b Start-Gate darf erst `PREPARED` werden, wenn M5a Gesamt-`PASS` ist. M5a Gesamt-`PASS` setzt das Parent-Gate `m5a` nach `docs/gate_hierarchy.json` und `reports/current/m5a_data_quality_gate.json` voraus.
- Ein M5a Slice-`PASS` reicht nicht fuer M5b `PREPARED`.
- Solange M5a Parent-Gate nicht `PASS` ist: `DRAFT`, kein `PREPARED`, kein `GO`, keine Implementierung.
- Diese Architektur enthaelt keine globale Prozent- oder Vollstaendigkeitsfreigabe.

M5b defines drift as a time-based divergence between expected system state and observed system state. It is different from M5a Data Quality: M5a checks the current state of data quality findings; M5b checks whether previously valid document, metadata, lifecycle, source-status, or retrieval state has degraded over time.

All M5b drift checks are read-only, workspace-scoped, report-driven, and non-mutating. Repair remains out of scope unless a later governed repair release explicitly enables it.

## Common Model

Drift runs produce one report per workspace. A report contains a run id, timestamp, workspace id, status, counters by drift type, counters by severity, and read-only findings. Findings must reference the observed object and explain the expected state, observed state, detection method, severity, and escalation.

Allowed severity values:

| Severity | Meaning |
| --- | --- |
| `info` | Observable divergence with no immediate operational risk. Track trend only. |
| `warning` | Divergence can degrade quality or operator trust if it grows. Review required. |
| `error` | Divergence violates data, lifecycle, source, or retrieval correctness. Blocks M5b gate if unresolved. |
| `critical` | Divergence can expose deleted data, hide active data, cross workspace boundaries, or invalidate recovery. Freeze mutating operations and escalate immediately. |

Common reporting fields:

| Field | Meaning |
| --- | --- |
| `drift_id` | Stable finding id for the run. |
| `drift_type` | One of `document`, `chunk`, `metadata`, `lifecycle`, `source_status`, `retrieval`. |
| `drift_subtype` | Specific rule id within the drift type. |
| `workspace_id` | Workspace scope for the finding. |
| `severity` | `info`, `warning`, `error`, or `critical`. |
| `entity` | Object references such as document, version, chunk, citation, query, or index ids. |
| `expected_state` | Machine-readable expected state. |
| `observed_state` | Machine-readable observed state. |
| `detection_strategy` | Rule or query family that produced the finding. |
| `remediation_hint` | Human-readable next step. Must not imply automatic repair. |
| `escalation` | Operational action required by severity and threshold. |

## 1. Document Drift

### Definition

Document Drift exists when a document's structural state no longer matches the canonical document model over time. The document row, current version, version sequence, content hash, and chunk set must describe the same logical document. Drift indicates that this relationship changed or decayed without a valid import, versioning, or lifecycle event.

Document Drift is not duplicate detection. Duplicate detection compares documents with each other. Document Drift compares one document against its own expected structural state.

### Trigger

- `documents.current_version_id` references a missing `document_versions.id`.
- A document has no current version although its import state implies parsed or completed content.
- A current version exists but has no chunks while the document is active and import-completed.
- Version numbers are missing, duplicated, or not monotonic for one document.
- Stored document hash and current version hash no longer match the expected hash contract.
- `updated_at` changed after current version creation without a new version or approved lifecycle event.

### Detection Strategy

Use read-only workspace-scoped joins across `documents`, `document_versions`, and `document_chunks`. Detection is rule-based and does not inspect raw file content. The detector compares document-level pointers, version cardinality, current-version consistency, chunk cardinality, and timestamp/hash invariants.

The detection strategy must produce bounded result sets and stable counts. Large workspaces should support pagination or capped finding samples while still reporting full counters.

### Severity

| Condition | Severity |
| --- | --- |
| Current version reference is broken | `error` |
| Active completed document has no current version | `error` |
| Active completed document has no chunks | `error` |
| Version sequence has duplicate or missing numbers | `warning` |
| Hash contract mismatch without content loss evidence | `warning` |
| Timestamp drift without structural breakage | `info` |

### Reporting

Finding type: `DOCUMENT_DRIFT`

Required report details:

- `document_id`
- `version_id` when known
- `drift_subtype`
- `expected_state`
- `observed_state`
- `severity`
- `remediation_hint`

Allowed subtypes:

- `missing_current_version`
- `broken_version_reference`
- `active_document_without_chunks`
- `version_sequence_gap`
- `version_sequence_duplicate`
- `hash_contract_mismatch`
- `timestamp_without_version_event`

### Escalation

Any `error` finding requires technical review before M5b gate approval. Any `critical` variant, if later introduced for cross-workspace or data exposure cases, freezes mutating document operations for the affected workspace until a governed recovery plan exists.

Document Drift rate above 5 percent of active documents is a gate blocker. Warnings below that threshold remain review-required but not automatically blocking.

## 2. Chunk Drift

### Definition

Chunk Drift exists when stored chunk state no longer matches the expected chunk set for the current document version over time. Chunks are retrieval units, so their document id, version id, content hash, normalized text hash, ordering, lifecycle visibility, and index eligibility must remain aligned with the canonical document version.

Chunk Drift is not duplicate detection. Duplicate detection compares equivalent content across documents or versions. Chunk Drift compares the current chunk set to the expected chunk set for the same document version and workspace.

### Trigger

- A current active version has missing chunks compared with its previous approved chunk count or chunk hash baseline.
- A document has chunks that reference an older version while `documents.current_version_id` points elsewhere.
- Chunk order has gaps, duplicates, or non-monotonic positions for a version.
- Chunk content hash or normalized text hash changed without a versioning, parsing, or restore event.
- Chunk workspace id, document id, or version id no longer matches the owning document.
- Chunk searchability diverges from document lifecycle or source-status expectations.

### Detection Strategy

Use read-only workspace-scoped joins across `documents`, `document_versions`, and `document_chunks`. The draft detector compares current-version chunk membership, positional sequence, hash stability, ownership consistency, and lifecycle-derived searchability.

The strategy must not reparse documents, regenerate chunks, mutate indexes, or infer missing chunks through retrieval. When no approved historical chunk baseline exists, the check reports baseline absence as `info` or skips baseline-only rules.

### Severity

| Condition | Severity |
| --- | --- |
| Chunk references a missing document or version | `error` |
| Chunk belongs to a different workspace than its document | `critical` |
| Active current version has missing chunks versus approved baseline | `error` |
| Chunk order contains gaps or duplicates | `warning` |
| Chunk hash changed without a version or parser event | `warning` |
| Searchability is inconsistent with lifecycle state | `error` |
| Historical baseline is unavailable | `info` |

### Reporting

Finding type: `CHUNK_DRIFT`

Required report details:

- `chunk_id`
- `document_id`
- `version_id`
- `workspace_id`
- `drift_subtype`
- `expected_state`
- `observed_state`
- `severity`
- `remediation_hint`

Allowed subtypes:

- `chunk_missing_from_current_version`
- `chunk_wrong_version_reference`
- `chunk_position_gap`
- `chunk_position_duplicate`
- `chunk_hash_changed_without_event`
- `chunk_workspace_mismatch`
- `chunk_searchability_mismatch`
- `chunk_baseline_missing`

### Escalation

Any `critical` Chunk Drift blocks M5b planning promotion and requires workspace-isolation review according to `docs/gate_hierarchy.json` and `reports/current/m5b_start_gate.json`. `error` findings require technical review before retrieval completeness or lifecycle visibility can be declared green. This draft does not authorize automatic rechunking, reindexing, deletion, merge, or repair.

Chunk Drift error rate above 2 percent of eligible active chunks is a planned gate blocker. Warning-level drift remains report-visible and review-required.

## 3. Metadata Drift

### Definition

Metadata Drift exists when document or version metadata regresses over time without a valid versioning or import event. It covers loss, type changes, schema-shape changes, or semantic decay of metadata that was previously present and valid.

Metadata Drift is different from M5a Metadata Findings. M5a detects missing or incomplete metadata now. M5b detects regression from an earlier valid state to a later degraded state.

### Trigger

- A metadata key such as `tags`, `category`, `doc_type`, or `summary` was present in a prior version and is missing or empty in the current version.
- A metadata value changes type unexpectedly, for example `tags` changes from array to string.
- Required metadata keys disappear from `document_versions.metadata`.
- Metadata timestamp fields move backwards or no longer align with version creation time.
- Document-level title/source metadata diverges from the current version's metadata without a version event.

### Detection Strategy

Compare historical versions of the same document in version order. The detector builds an expected metadata baseline from the latest valid earlier version and compares the current version against that baseline. It also validates JSON shape and known metadata field types.

The strategy is read-only and workspace-scoped. It must not infer missing metadata through AI, external services, or raw document parsing. Missing baseline data should produce `info` or no finding, not a fabricated error.

### Severity

| Condition | Severity |
| --- | --- |
| Required metadata key regressed from populated to missing | `warning` |
| Metadata type changed to an invalid shape | `warning` |
| Metadata timestamp moved backwards | `info` |
| Metadata loss affects retrieval filters or source classification | `error` |
| Cross-workspace metadata reference appears | `critical` |

### Reporting

Finding type: `METADATA_DRIFT`

Required report details:

- `document_id`
- `version_id`
- `previous_version_id` when known
- `affected_fields`
- `drift_subtype`
- `expected_state`
- `observed_state`
- `severity`
- `remediation_hint`

Allowed subtypes:

- `metadata_key_regression`
- `metadata_type_regression`
- `metadata_timestamp_drift`
- `document_version_metadata_mismatch`
- `retrieval_filter_metadata_loss`
- `cross_workspace_metadata_reference`

### Escalation

Metadata Drift does not automatically authorize metadata repair. `error` findings require review before metadata-dependent retrieval, filtering, or dashboards are declared green according to `docs/gate_hierarchy.json` and `reports/current/m5b_start_gate.json`. `critical` findings freeze affected workspace reporting because they can indicate isolation failure.

Metadata Drift becomes a gate blocker when metadata-drift errors affect more than 2 percent of active documents or any cross-workspace reference appears.

## 4. Lifecycle Drift

### Definition

Lifecycle Drift exists when the stored lifecycle state of a document and the behavior of dependent systems diverge over time. A document's lifecycle state must be consistent with import state, chunk searchability, citations, retrieval visibility, timestamps, and audit evidence.

M5a Lifecycle Integrity checks current consistency. M5b Lifecycle Drift focuses on temporal divergence after valid lifecycle transitions, restore, reindex, or recovery operations.

### Trigger

- Deleted or archived documents appear in search or retrieval results.
- Active documents are not searchable although their import and chunk state are valid.
- `lifecycle_status` changes without corresponding lifecycle timestamp or audit evidence.
- `archived_at` or `deleted_at` conflicts with `lifecycle_status`.
- Chunk `is_searchable` flags no longer match document lifecycle.
- Restore or reindex changes retrieval visibility without matching lifecycle state.

### Detection Strategy

Combine read-only database checks with search/retrieval visibility checks. Database checks validate allowed lifecycle values, timestamp consistency, and chunk searchability. Retrieval checks run controlled workspace-scoped probes to confirm archived and deleted content is excluded while active content remains discoverable.

The detector must separate direct DB inconsistencies from index or retrieval inconsistencies. It must not perform reindex, status repair, citation updates, or lifecycle mutation.

### Severity

| Condition | Severity |
| --- | --- |
| Deleted document is searchable or retrievable | `critical` |
| Archived document appears in default active search | `error` |
| Active document with valid chunks is not searchable | `error` |
| Lifecycle status and timestamp conflict | `warning` |
| Lifecycle audit evidence missing for non-active document | `warning` |
| Pending document visibility is ambiguous but not exposed | `info` |

### Reporting

Finding type: `LIFECYCLE_DRIFT`

Required report details:

- `document_id`
- `lifecycle_status`
- `import_status`
- `chunk_id` when applicable
- `drift_subtype`
- `expected_state`
- `observed_state`
- `severity`
- `remediation_hint`

Allowed subtypes:

- `deleted_document_searchable`
- `archived_document_searchable`
- `active_document_not_searchable`
- `lifecycle_timestamp_mismatch`
- `chunk_searchability_mismatch`
- `missing_lifecycle_audit_evidence`
- `restore_lifecycle_visibility_mismatch`

### Escalation

Any `critical` Lifecycle Drift freezes mutating document, reindex, and cleanup operations for the affected workspace until an operator reviews the evidence. Any `error` Lifecycle Drift blocks M5b gate approval.

Lifecycle Drift error rate above 2 percent of active documents blocks the gate even when individual findings are not critical.

## 5. Source Status Drift

### Definition

Source Status Drift exists when citation source status no longer reflects the current lifecycle state or existence of the cited source. Citations are trust artifacts: they must preserve historical context while also exposing whether the source is still active, archived, deleted, or missing.

This is not automatic citation rewriting. M5b only detects stale or inconsistent source status.

### Trigger

- Citation has `source_status=active` while the referenced document is archived or deleted.
- Citation has `source_status=archived` while the referenced document is deleted.
- Citation references a missing document but is not marked `missing`.
- Citation is marked `missing` while a document with the same id exists in the same workspace.
- Citation document id, chunk id, or workspace context no longer agrees with current source ownership.

### Detection Strategy

Use read-only joins across citations, messages/sessions, documents, and chunks where available. Compare `chat_citations.source_status` to `documents.lifecycle_status` and validate that citation workspace scope is derived through the owning chat/session context.

The strategy must preserve historical quote snapshots. It must not rewrite citation text, regenerate quotes, or update source status.

### Severity

| Condition | Severity |
| --- | --- |
| Citation says active but document is deleted | `error` |
| Citation says active but document is archived | `warning` |
| Citation says archived but document is deleted | `warning` |
| Citation references missing document but status is not missing | `error` |
| Citation crosses workspace boundary | `critical` |
| Citation says missing but document exists again | `info` |

### Reporting

Finding type: `SOURCE_STATUS_DRIFT`

Required report details:

- `citation_id`
- `message_id` when available
- `document_id`
- `chunk_id` when available
- `current_source_status`
- `current_lifecycle_status`
- `drift_subtype`
- `expected_state`
- `observed_state`
- `severity`
- `remediation_hint`

Allowed subtypes:

- `source_status_stale`
- `active_citation_deleted_source`
- `active_citation_archived_source`
- `missing_document_not_flagged`
- `missing_status_but_document_exists`
- `cross_workspace_citation_source`

### Escalation

`critical` Source Status Drift blocks M5b and requires workspace-isolation review according to `docs/gate_hierarchy.json` and `reports/current/m5b_start_gate.json`. `error` findings require review before citation-dependent UX or reports are declared green. Warning-level drift is visible in reports but does not authorize mutation.

A source-status error rate above 10 percent of non-missing citations triggers escalation to technical review.

## 6. Retrieval Drift

### Definition

Retrieval Drift exists when retrieval behavior diverges from the expected searchable corpus or retrieval-quality baseline. It includes structural index drift and quality regression. Structural drift compares indexed objects to database source of truth. Quality drift compares current retrieval results to a stored baseline.

Retrieval Drift is distinct from lifecycle drift: lifecycle drift asks whether lifecycle rules are respected; retrieval drift asks whether retrieval remains complete, fresh, and accurate for eligible content.

### Trigger

- Search index contains chunk ids that no longer exist in `document_chunks`.
- Active searchable chunks are missing from the index.
- Archived or deleted chunks appear in default retrieval.
- Index counts diverge from eligible DB chunk counts beyond threshold.
- Golden-query metrics degrade from baseline beyond threshold.
- Restore, reindex, import recovery, or parser changes occur.

### Detection Strategy

Use two independent checks.

Structural check: compare eligible DB chunks to indexed chunks for the workspace. Eligible means active document, completed import, valid current version, and searchable chunk. Report stale index entries, missing index entries, lifecycle-excluded index entries, and count discrepancy.

Quality check: run a fixed golden-query benchmark against the retrieval pipeline and compare metrics such as precision at k, recall at k, MRR, and lifecycle-exclusion violations against the latest approved baseline.

Both checks are read-only. The detector must not trigger reindex or modify retrieval settings.

### Severity

| Condition | Severity |
| --- | --- |
| Deleted content appears in retrieval | `critical` |
| Archived content appears in default retrieval | `error` |
| Active eligible chunks are missing from index | `error` |
| Stale index entries exist but are not retrievable | `warning` |
| Count discrepancy exceeds 5 percent | `warning` |
| Golden-query regression exceeds 10 percent | `warning` |
| Golden-query regression exceeds 25 percent or lifecycle exclusion fails | `error` |

### Reporting

Finding type: `RETRIEVAL_DRIFT`

Required report details:

- `chunk_id` when known
- `document_id` when known
- `query_id` for quality findings
- `drift_subtype`
- `expected_state`
- `observed_state`
- `index_count`
- `db_count`
- `baseline_score`
- `current_score`
- `severity`
- `remediation_hint`

Allowed subtypes:

- `stale_index_entry`
- `missing_index_entry`
- `lifecycle_excluded_content_retrievable`
- `index_count_discrepancy`
- `golden_query_quality_regression`
- `retrieval_lifecycle_exclusion_failure`

### Escalation

Any critical Retrieval Drift freezes retrieval-affecting mutations and blocks M5b. Any lifecycle-exclusion failure blocks M5b regardless of count. Missing index entries block the gate when count is greater than zero for active eligible chunks unless an approved maintenance window report explains the gap.

Quality regression above 25 percent on more than one golden query blocks M5b. Warning-level regressions require trend tracking and review before a baseline is updated.

## Report Artifacts

Planned report name: `m5b_drift_report.json`

Planned schema file: `schemas/drift_schema.json`

The report must be generated by `gate_validator` or a later explicitly approved drift reporter. Manual status statements do not override report fields.

Required report summary:

- `total_findings`
- `findings_by_drift_type`
- `findings_by_severity`
- `drift_rate_percent`
- `critical_findings`
- `error_findings`
- `quality_score`
- `decision.go_no_go`

## Non-Scope

- No detector implementation in this phase.
- No database migration in this phase.
- No API endpoint in this phase.
- No dashboard implementation in this phase.
- No automatic repair.
- No automatic reindex.
- No citation mutation.
- No metadata enrichment.
- No cross-workspace aggregation.
