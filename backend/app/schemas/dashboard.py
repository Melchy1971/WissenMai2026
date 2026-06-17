from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    document_count: int = 0
    active_document_count: int = 0
    archived_document_count: int = 0
    new_imports_count: int = 0
    open_analysis_count: int = 0
    topic_count: int = 0
    quality_score: float | None = None
    drift_status: str | None = None


class DashboardActivityItem(BaseModel):
    id: str
    item_type: Literal["document", "import", "analysis", "quality", "drift"]
    title: str
    status: str
    created_at: datetime


class DashboardImportItem(BaseModel):
    id: str
    status: str
    filename: str | None
    mime_type: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class DashboardAnalysisItem(BaseModel):
    id: str
    status: str
    analysis_type: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class DashboardQualityItem(BaseModel):
    id: str
    status: str
    quality_score: float | None
    total_findings: int | None
    started_at: datetime
    finished_at: datetime | None


class DashboardTopicItem(BaseModel):
    name: str
    count: int
    latest_job_id: str | None


class DashboardListResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
    total: int = 0


class DashboardActivityResponse(BaseModel):
    items: list[DashboardActivityItem] = Field(default_factory=list)
    total: int = 0


class DashboardImportsResponse(BaseModel):
    items: list[DashboardImportItem] = Field(default_factory=list)
    total: int = 0


class DashboardAnalysisResponse(BaseModel):
    items: list[DashboardAnalysisItem] = Field(default_factory=list)
    total: int = 0


class DashboardQualityResponse(BaseModel):
    items: list[DashboardQualityItem] = Field(default_factory=list)
    total: int = 0


class DashboardTopicsResponse(BaseModel):
    items: list[DashboardTopicItem] = Field(default_factory=list)
    total: int = 0


# -- Topics widget data --------------------------------------------------------

class TopicsDayCount(BaseModel):
    date: str   # ISO date "YYYY-MM-DD"
    count: int


class TopicTagCount(BaseModel):
    name: str
    count: int


class TopicsWidgetData(BaseModel):
    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    new_last_7_days: int = 0
    new_per_day: list[TopicsDayCount] = Field(default_factory=list)
    unreviewed: int = 0
    top_tags: list[TopicTagCount] = Field(default_factory=list)


# -- Drift Analytics widgets (PRI-4) ------------------------------------------

class DriftWidget(BaseModel):
    """One drift analytics widget in the Dashboard.

    status: PASS|WARNING|FAIL|BLOCKED. None means no snapshot data yet.
    score: numeric value where applicable (0-100), else None.
    label: human-readable, no UUIDs, no internal keys.
    snapshot_type: machine key for click-through navigation to DriftDetailPage.
    last_updated: timestamp of the underlying snapshot, None if no data.
    """
    snapshot_type: str
    label: str
    status: str | None = None          # None = no data → UI shows WARNING
    score: float | None = None
    last_updated: datetime | None = None


class DashboardDriftResponse(BaseModel):
    """6 drift widgets + global_status for Dashboard overview row.

    missing_data: list of snapshot_type values where no snapshot exists yet.
    global_status: highest-priority status across all present widgets.
    No technical IDs, no UUIDs, no internal file paths in this response.
    """
    product_maturity: DriftWidget
    gold_path: DriftWidget
    release_gate: DriftWidget
    test_coverage: DriftWidget
    id_leak_audit: DriftWidget
    security_audit: DriftWidget
    global_status: str                  # PASS|WARNING|FAIL|BLOCKED
    missing_data: list[str] = Field(default_factory=list)
    last_updated: datetime | None = None
