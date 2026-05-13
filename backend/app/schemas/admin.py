from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SearchIndexRebuildResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str | None
    reindexed_chunk_count: int
    reindexed_document_count: int
    index_name: str
    index_action: str
    status: str


class SearchIndexInconsistencyBucket(BaseModel):
    model_config = ConfigDict(strict=True)

    count: int
    status: str
    sample_chunk_ids: list[str]
    sample_document_ids: list[str]
    note: str | None = None


class SearchIndexDriftBucket(BaseModel):
    model_config = ConfigDict(strict=True)

    count: int
    status: str
    severity: str
    repair_recommendation: str
    sample_chunk_ids: list[str]
    sample_document_ids: list[str]
    note: str | None = None


class SearchIndexDriftReportResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str | None
    checked_at: datetime
    index_name: str
    status: str
    severity: str
    drift_score: int
    repair_recommendation: str
    searchable_chunk_count: int
    chunks_without_index: SearchIndexDriftBucket
    index_without_chunk: SearchIndexDriftBucket
    deleted_documents_in_index: SearchIndexDriftBucket
    archived_documents_in_active_index: SearchIndexDriftBucket
    duplicate_index_entries: SearchIndexDriftBucket
    invalid_lifecycle_status: SearchIndexDriftBucket


class SearchIndexInconsistencyReportResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str | None
    checked_at: datetime
    index_name: str
    status: str
    searchable_chunk_count: int
    missing_index_entries: SearchIndexInconsistencyBucket
    orphan_index_entries: SearchIndexInconsistencyBucket
    deleted_documents_in_index: SearchIndexInconsistencyBucket
    archived_documents_in_active_index: SearchIndexInconsistencyBucket


class DiagnosticsSystemResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: Literal["ok", "degraded", "error"]
    version: str
    environment: Literal["local", "test", "production"]


class DiagnosticsDatabaseResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    reachable: bool
    migration_head: str | None
    current_revision: str | None
    is_current: bool


class DiagnosticsCountsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    documents: int
    versions: int
    chunks: int
    chat_sessions: int
    chat_messages: int


class DiagnosticsImportsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    running_jobs: int
    failed_jobs_last_24h: int
    last_error_code: str | None


class DiagnosticsSearchResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    index_available: bool
    indexed_chunks: int
    stale_index_entries: int


class DiagnosticsAuthResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    auth_enabled: bool
    workspace_isolation_enabled: bool


class DiagnosticsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    system: DiagnosticsSystemResponse
    database: DiagnosticsDatabaseResponse
    counts: DiagnosticsCountsResponse
    imports: DiagnosticsImportsResponse
    search: DiagnosticsSearchResponse
    auth: DiagnosticsAuthResponse


class QueueAgingThresholds(BaseModel):
    model_config = ConfigDict(strict=True)

    stalled_pending_seconds: int
    stuck_running_seconds: int
    dead_letter_warning: int
    dead_letter_critical: int
    max_attempts: int
    backlog_warning: int
    backlog_critical: int
    retry_rate_warning_per_hour: float
    dead_letter_growth_window_hours: int


class WorkspaceQueueDistribution(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str
    pending: int
    running: int
    retryable: int
    dead_letter: int
    backlog: int
    backlog_share: float


class QueueAgingReport(BaseModel):
    model_config = ConfigDict(strict=True)

    checked_at: datetime
    workspace_id: str

    # truth metrics
    queue_backlog_count: int
    queue_age_p95_seconds: float | None
    backlog_growth_24h: int

    # pending jobs
    pending_count: int
    pending_age_p95_seconds: float | None
    oldest_pending_age_seconds: float | None
    stalled_pending_count: int

    # retry loops
    retryable_count: int
    max_retry_attempt_count: int
    high_retry_count: int
    retry_rate_per_hour: float

    # dead letters
    dead_letter_count: int
    dead_letter_oldest_age_seconds: float | None
    dead_letter_growth_24h: int

    # stuck running
    running_count: int
    stuck_running_count: int
    oldest_running_age_seconds: float | None

    # starvation
    starvation_detected: bool
    starvation_notes: list[str]
    workspace_queue_distribution: list[WorkspaceQueueDistribution]

    # verdict
    severity: Literal["ok", "warning", "critical"]
    alerts: list[str]
    thresholds: QueueAgingThresholds


class CitationLongevityReport(BaseModel):
    model_config = ConfigDict(strict=True)

    checked_at: datetime
    workspace_id: str
    audit_name: str
    audit_scope: list[str]
    time_horizon: str
    simulated_cycles: list[str]
    total_citations: int

    orphaned_anchor_count: int
    anchor_unverifiable_count: int
    status_drift_count: int
    preview_stale_count: int
    deleted_not_marked_count: int
    restored_not_marked_count: int
    restore_reference_risk_count: int
    rechunk_reference_risk_count: int

    severity: Literal["ok", "warning", "critical"]
    alerts: list[str]
    risk_summary: list[str]
    persistence_risks: list[str]
    hardening_recommendations: list[str]


class ReindexGovernanceRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    reindex_type: Literal["full", "workspace", "document"]
    workspace_id: str | None = None
    document_id: str | None = None
    reason: str
    correlation_id: str | None = None


class ReindexGovernanceReport(BaseModel):
    model_config = ConfigDict(strict=True)

    correlation_id: str
    reindex_type: Literal["full", "workspace", "document"]
    workspace_id: str | None
    document_id: str | None
    reason: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    audit_event_names: list[str]
    audit_event_count: int

    drift_score_before: int
    drift_score_after: int
    drift_delta: int
    drift_severity_before: str
    drift_severity_after: str
    drift_status_before: str
    drift_status_after: str
    drift_snapshot_before_taken: bool
    drift_snapshot_after_taken: bool

    lifecycle_ok: bool
    lifecycle_inconsistency_count: int

    reindexed_chunk_count: int
    reindexed_document_count: int
    index_action: str
    regression_check_required: bool
    retrieval_regression_trigger: Literal["reindex"]
    post_reindex_checks: dict[str, Literal["executed", "required"]]
    status: Literal["completed", "failed"]


class CleanupSnapshot(BaseModel):
    model_config = ConfigDict(strict=True)

    active_document_count: int
    active_chunk_count: int
    citation_count: int
    active_job_count: int
    active_auth_session_count: int


class CleanupSafetyGateReport(BaseModel):
    model_config = ConfigDict(strict=True)

    passed: bool
    active_doc_refs_in_orphan_scope: int
    citation_refs_in_orphan_scope: int
    active_job_refs_in_scope: int
    blocked_reason: str | None


class CleanupDelta(BaseModel):
    model_config = ConfigDict(strict=True)

    active_document_delta: int
    active_chunk_delta: int
    citation_delta: int
    active_job_delta: int
    active_auth_session_delta: int
    citation_loss_detected: bool


class CleanupSafetyConstraints(BaseModel):
    model_config = ConfigDict(strict=True)

    active_documents_preserved: bool
    citations_preserved: bool
    queue_consistency_preserved: bool
    blocking_gate_passed: bool


class CleanupGovernanceRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    dry_run_only: bool = True
    retention_days: int = 7
    workspace_id: str | None = None
    correlation_id: str | None = None


class CleanupGovernanceReport(BaseModel):
    model_config = ConfigDict(strict=True)

    correlation_id: str
    mode: Literal["dry_run", "execute", "blocked"]
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    governance_rules: list[str]
    audit_event_names: list[str]
    audit_event_count: int
    retention_days: int
    workspace_id: str | None
    dry_run_only: bool
    dry_run_executed: bool

    safety_gates: CleanupSafetyGateReport
    snapshot_before: CleanupSnapshot
    snapshot_after: CleanupSnapshot
    delta: CleanupDelta
    drift_delta: CleanupDelta
    safety_constraints: CleanupSafetyConstraints

    dry_run_candidate_count: int
    execute_applied_count: int | None

    severity: Literal["ok", "warning", "critical"]
    alerts: list[str]
    recovery_hints: list[str]
    recovery_required: bool
    rollback_strategy: str


class BackupVerificationRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    input_dir: str


class BackupVerificationIssueResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str
    path: str
    detail: str


class BackupVerificationCheckResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: str
    path: str | None = None
    missing_paths: list[str] | None = None
    mismatches: list[str] | None = None
    invalid_entries: list[str] | None = None
    details: str | None = None
    declared_file_count: int | None = None
    actual_file_count: int | None = None
    missing_fields: list[str] | None = None


class BackupIntegrityReportResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    checks: dict[str, BackupVerificationCheckResponse]
    issue_count: int
    issues: list[BackupVerificationIssueResponse]


class BackupVerificationResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: str
    backup_dir: str
    checked_at: datetime
    integrity_report: BackupIntegrityReportResponse
    error_classes: list[str]
    mismatch_count: int
    mismatches: list[str]
    manifest: dict[str, object]
