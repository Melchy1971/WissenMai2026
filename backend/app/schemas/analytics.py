"""Pydantic schemas for Analytics / Drift API (PRI-4).

Response DTOs for:
  GET /api/v1/drift/overview
  GET /api/v1/drift/snapshots
  GET /api/v1/drift/snapshots/{id}
  GET /api/v1/drift/snapshots/{id}/metrics
  POST /api/v1/drift/snapshots/recalculate

Design rules:
  - No UUIDs in response output (id field is excluded from widget views).
  - No secrets in payload (enforced upstream at repository layer).
  - Status always one of PASS|WARNING|FAIL|BLOCKED.
  - Missing data represented as None — UI must treat as WARNING.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SnapshotStatus = Literal["PASS", "WARNING", "FAIL", "BLOCKED"]

SnapshotType = Literal[
    "PRODUCT_MATURITY",
    "GOLD_PATH",
    "RELEASE_GATE",
    "TEST_COVERAGE",
    "ID_LEAK_AUDIT",
    "SECURITY_AUDIT",
]


# ---------------------------------------------------------------------------
# Metric response
# ---------------------------------------------------------------------------

class MetricResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    metric_key: str
    metric_label: str
    metric_value: str
    metric_unit: str | None
    threshold_warning: float | None
    threshold_fail: float | None
    status: SnapshotStatus
    created_at: datetime


# ---------------------------------------------------------------------------
# Snapshot responses
# ---------------------------------------------------------------------------

class SnapshotSummary(BaseModel):
    """Used in overview widget and list views. No payload, no internal ID."""
    model_config = ConfigDict(strict=True)

    snapshot_type: SnapshotType
    score: float | None
    status: SnapshotStatus
    created_at: datetime
    created_by: str | None


class SnapshotDetail(BaseModel):
    """Used by DriftDetailPage. Includes payload (no secrets, no UUIDs as primary text)."""
    model_config = ConfigDict(strict=True)

    snapshot_type: SnapshotType
    score: float | None
    status: SnapshotStatus
    payload: dict | None
    created_at: datetime
    created_by: str | None
    # Internal ID included here for /metrics lookup — never rendered as primary UI text
    id: str = Field(..., description="Internal snapshot ID. Not for display in UI.")


class SnapshotListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str = Field(..., description="Internal ID. Not for display.")
    snapshot_type: SnapshotType
    score: float | None
    status: SnapshotStatus
    created_at: datetime
    created_by: str | None


class SnapshotListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[SnapshotListItem]
    total: int
    page: int
    page_size: int


class MetricListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    snapshot_type: SnapshotType
    snapshot_status: SnapshotStatus
    metrics: list[MetricResponse]


# ---------------------------------------------------------------------------
# Overview response
# ---------------------------------------------------------------------------

class OverviewWidget(BaseModel):
    """One widget in the Dashboard overview. None = no data (treat as WARNING in UI)."""
    model_config = ConfigDict(strict=True)

    status: SnapshotStatus
    score: float | None = None
    label: str                           # Human-readable label, no UUID
    last_updated: datetime | None = None
    # For navigation/click-through — passes snapshot_type, not UUID
    snapshot_type: SnapshotType


class DriftOverviewResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    product_maturity: OverviewWidget | None
    gold_path: OverviewWidget | None
    release_gate: OverviewWidget | None
    test_coverage: OverviewWidget | None
    id_leak_audit: OverviewWidget | None
    security_audit: OverviewWidget | None
    last_updated: datetime | None
    global_status: SnapshotStatus


# ---------------------------------------------------------------------------
# Recalculate response
# ---------------------------------------------------------------------------

class RecalculateResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    snapshots_created: int
    snapshots_failed: list[str]
    global_status: SnapshotStatus
    created_at: datetime
    message: str
