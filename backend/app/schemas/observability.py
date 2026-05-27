from typing import Literal

from pydantic import BaseModel, ConfigDict


ImportEventName = Literal[
    "upload_received",
    "parsing_started",
    "parsing_completed",
    "chunking_started",
    "chunking_completed",
    "indexing_started",
    "indexing_completed",
    "import_failed",
]

ImportEventStatus = Literal["received", "started", "completed", "failed"]


class ImportObservabilityEvent(BaseModel):
    model_config = ConfigDict(strict=True)

    event_name: ImportEventName
    event_type: str
    severity: str
    document_id: str | None
    job_id: str | None
    workspace_id: str | None
    duration_ms: int | None
    parser_type: str
    chunk_count: int
    error_code: str | None
    correlation_id: str | None
    status: ImportEventStatus
