from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Literal


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
