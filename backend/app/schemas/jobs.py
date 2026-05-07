from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


JobType = Literal["document_import", "search_index_rebuild"]
JobStatus = Literal["pending", "running", "completed", "failed", "retryable", "dead_letter", "cancelled"]


class ImportJobResult(BaseModel):
    model_config = ConfigDict(strict=True)

    document_id: str
    version_id: str | None
    import_status: str
    duplicate_of_document_id: str | None
    chunk_count: int
    parser_type: str
    warnings: list[dict[str, Any]]


class SearchIndexRebuildJobResult(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str | None
    reindexed_chunk_count: int
    reindexed_document_count: int
    index_name: str
    index_action: str
    status: str


class JobResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    job_type: JobType
    status: JobStatus
    workspace_id: str
    requested_by_user_id: str | None
    filename: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress_current: int
    progress_total: int
    progress_message: str | None
    error_code: str | None
    error_message: str | None
    result: ImportJobResult | SearchIndexRebuildJobResult | None = None