from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Status / format literals
# ---------------------------------------------------------------------------

ExportJobStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
ExportSourceType = Literal["SEARCH_RESULT", "ANALYSIS_RESULT", "TOPIC", "DOCUMENT_COLLECTION"]
ExportFormat = Literal["MARKDOWN", "JSON", "PDF"]


# ---------------------------------------------------------------------------
# ExportJob schemas
# ---------------------------------------------------------------------------

class ExportJobResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    workspace_id: str | None
    status: ExportJobStatus
    source_type: ExportSourceType
    source_ids: list[str] | None
    export_format: ExportFormat
    file_name: str
    file_path: str | None
    error_message: str | None
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ExportJobListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[ExportJobResponse]
    total: int
    limit: int
    offset: int


class CreateExportJobRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    source_type: ExportSourceType
    source_ids: Annotated[list[str], Field(min_length=1)]
    export_format: ExportFormat
    file_name: Annotated[str, Field(min_length=1, max_length=200)]


# ---------------------------------------------------------------------------
# ExportTemplate schemas
# ---------------------------------------------------------------------------

class ExportTemplateResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    name: str
    export_format: ExportFormat
    layout_config: dict | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ExportTemplateListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[ExportTemplateResponse]
    total: int


class CreateExportTemplateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    name: Annotated[str, Field(min_length=1, max_length=128)]
    export_format: ExportFormat
    layout_config: dict | None = None
    is_default: bool = False


class UpdateExportTemplateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    name: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    export_format: ExportFormat | None = None
    layout_config: dict | None = None
    is_default: bool | None = None
