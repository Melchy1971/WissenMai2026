"""Pydantic schemas for the Drift Detection read-only API.

Read-only. No repair, no cleanup, no mutation endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class DriftRunSummary(BaseModel):
    """Compact run entry for list responses."""
    model_config = ConfigDict(strict=True)

    run_id: str
    workspace_id: str
    status: str
    triggered_by: str | None
    detector_names: list[str] | None
    started_at: datetime
    completed_at: datetime | None
    total_findings: int | None
    error_message: str | None
    created_at: datetime


class DriftRunDetail(DriftRunSummary):
    """Full run entry including per-type and per-severity finding counts."""
    model_config = ConfigDict(strict=True)

    findings_by_type: dict[str, int] = Field(default_factory=dict)
    findings_by_severity: dict[str, int] = Field(default_factory=dict)


class DriftRunListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[DriftRunSummary]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class DriftFindingItem(BaseModel):
    model_config = ConfigDict(strict=True)

    finding_id: str
    run_id: str
    workspace_id: str
    finding_type: str
    severity: str
    entity_type: str | None
    entity_id: str | None
    detail: dict[str, Any] | None
    created_at: datetime


class DriftFindingListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[DriftFindingItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class DriftSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace_id: str
    latest_run_id: str | None
    latest_run_status: str | None
    latest_run_completed_at: datetime | None
    total_runs: int
    total_findings: int
    findings_by_type: dict[str, int]
    findings_by_severity: dict[str, int]
    critical_count: int
    error_count: int
