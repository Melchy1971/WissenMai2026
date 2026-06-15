from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AnalysisJobStatus = Literal["pending", "running", "completed", "failed", "approved"]
AnalysisSuggestionStatus = AnalysisJobStatus
ApprovalDecision = Literal["approved"]


class AnalysisResult(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    job_id: str
    summary: str
    key_points: list[str]
    suggested_tags: list[str]
    suggested_topics: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime


class AnalysisComparison(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    job_id: str
    compared_document_ids: list[str]
    overlaps: list[dict]
    differences: list[dict]
    suggested_merge: dict | None
    created_at: datetime


class AnalysisSuggestion(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    job_id: str
    suggestion_type: str
    payload: dict
    status: AnalysisSuggestionStatus
    approved_by: str | None
    approved_at: datetime | None


class AnalysisJobListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    workspace_id: str
    source_document_ids: list[str]
    status: AnalysisJobStatus
    analysis_type: str
    prompt: str
    created_by: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None


class AnalysisJobResponse(AnalysisJobListItem):
    result: AnalysisResult | None
    comparison: AnalysisComparison | None
    suggestions: list[AnalysisSuggestion]


class AnalysisJobListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[AnalysisJobListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class CreateAnalysisJobRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source_document_ids: list[str] = Field(min_length=1)
    analysis_type: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1)


class CompareRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    compared_document_ids: list[str] = Field(default_factory=list)
    max_differences: int = Field(default=50, ge=1, le=200)


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    prompt: str | None = Field(default=None, min_length=1)
    max_suggestions: int = Field(default=10, ge=1, le=50)


class ApproveRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    decision: ApprovalDecision = "approved"
