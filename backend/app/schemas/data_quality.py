"""Pydantic schemas for the Data Quality read-only API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class DataQualityRunSummary(BaseModel):
    """Compact run entry for list responses."""
    model_config = ConfigDict(strict=True)

    run_id: str
    workspace_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    total_findings: int | None
    quality_score: float | None
    created_by: str | None


class DataQualityRunDetail(DataQualityRunSummary):
    """Full run entry including per-type finding counts."""
    model_config = ConfigDict(strict=True)

    finding_counts: dict[str, int] = Field(default_factory=dict)


class DataQualityRunListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[DataQualityRunSummary]
    total: int


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class DataQualityFindingItem(BaseModel):
    model_config = ConfigDict(strict=True)

    finding_id: str
    run_id: str
    workspace_id: str
    finding_type: str
    severity: str
    document_id: str | None
    version_id: str | None
    chunk_id: str | None
    title: str
    description: str
    remediation: str
    created_at: datetime


class DataQualityFindingListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[DataQualityFindingItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class DataQualitySummary(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str
    latest_run_id: str | None
    latest_run_status: str | None
    latest_run_at: datetime | None
    latest_quality_score: float | None
    total_runs: int
    total_findings: int
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_type: dict[str, int] = Field(default_factory=dict)
