from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Status literals
# ---------------------------------------------------------------------------

# v2 preferred; legacy values remain in the union for backward compat
AnalysisJobStatus = Literal[
    "queued", "running", "completed", "failed", "cancelled",
    "pending", "approved",  # legacy
]
AnalysisJobSourceType = Literal["DOCUMENTS", "TOPIC", "SEARCH_RESULT"]
AnalysisResultStatus = Literal["draft", "review", "approved", "rejected"]
AnalysisSuggestionStatus = Literal["pending", "running", "completed", "failed", "approved"]
ApprovalDecision = Literal["approved"]


# ---------------------------------------------------------------------------
# Source reference (used inside sources JSON list)
# ---------------------------------------------------------------------------

class AnalysisSourceRef(BaseModel):
    model_config = ConfigDict(strict=True)

    kind: Literal["document", "topic", "chunk"]
    id: str
    title: str | None = None
    excerpt: str | None = None


# ---------------------------------------------------------------------------
# AnalysisResult schema (v2 — extended)
# ---------------------------------------------------------------------------

class AnalysisResult(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    job_id: str
    # v1 fields
    summary: str
    key_points: list[str]
    suggested_tags: list[str]
    suggested_topics: list[str]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime
    # v2 fields
    title: str | None = None
    content_markdown: str | None = None
    sources: list[AnalysisSourceRef] | None = None
    status: AnalysisResultStatus = "draft"
    approved_at: datetime | None = None
    approved_by: str | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# AnalysisComparison / AnalysisSuggestion (unchanged from v1)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Job schemas (v2 — extended)
# ---------------------------------------------------------------------------

class AnalysisJobListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    workspace_id: str | None
    status: AnalysisJobStatus
    analysis_type: str
    # v2
    source_type: AnalysisJobSourceType | None = None
    source_ids: list[str] | None = None
    source_document_ids: list[str]
    prompt: str
    provider: str | None = None
    model: str | None = None
    result_id: str | None = None
    created_by: str | None
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


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateAnalysisJobRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    # v1 (backward compat)
    source_document_ids: list[str] = Field(default_factory=list)
    analysis_type: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1)
    # v2
    source_type: AnalysisJobSourceType | None = None
    source_ids: list[str] | None = None
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)


class UpdateAnalysisResultRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, min_length=1)
    content_markdown: str | None = None
    sources: list[AnalysisSourceRef] | None = None


class MarkForReviewRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    note: str | None = Field(default=None, max_length=1024)


class ApproveResultRequest(BaseModel):
    """Approval requires an explicit confirm payload — no silent auto-approve."""
    model_config = ConfigDict(strict=True, extra="forbid")

    confirm: Annotated[bool, Field(description="Must be true to confirm the approval action")]
    reviewer_note: str | None = Field(default=None, max_length=1024)


class RejectResultRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=1024)


# ---------------------------------------------------------------------------
# Legacy request schemas (kept for existing service layer compatibility)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Import schemas
# ---------------------------------------------------------------------------

class ImportAnalysisResultResponse(BaseModel):
    """Returned by POST /analysis/results/{result_id}/import."""

    result_id: str
    tags_created: int
    tags_found: int
    document_tags_applied: int
    topics_created: int
    topics_found: int
    topic_docs_attached: int
    topic_tags_applied: int
    source_document_count: int
