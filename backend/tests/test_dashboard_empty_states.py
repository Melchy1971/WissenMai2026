from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisJob, AnalysisResult
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID

pytestmark = pytest.mark.unit_fast


def test_workspace_without_documents_returns_valid_empty_dashboard(
    client: TestClient,
    auth_fixture: dict[str, str],
) -> None:
    summary = client.get("/api/v1/dashboard/summary")
    activity = client.get("/api/v1/dashboard/activity")

    assert summary.status_code == 200
    assert activity.status_code == 200
    assert summary.json() == {
        "document_count": 0,
        "active_document_count": 0,
        "archived_document_count": 0,
        "new_imports_count": 0,
        "open_analysis_count": 0,
        "topic_count": 0,
        "quality_score": None,
        "drift_status": None,
    }
    assert activity.json() == {"items": [], "total": 0}


def test_workspace_without_imports_returns_empty_import_list(
    client: TestClient,
    document_fixture: dict[str, str],
) -> None:
    summary = client.get("/api/v1/dashboard/summary")
    imports = client.get("/api/v1/dashboard/imports")

    assert summary.status_code == 200
    assert imports.status_code == 200
    assert summary.json()["new_imports_count"] == 0
    assert imports.json() == {"items": [], "total": 0}


def test_workspace_without_analysis_jobs_returns_empty_analysis_list(
    client: TestClient,
    document_fixture: dict[str, str],
) -> None:
    summary = client.get("/api/v1/dashboard/summary")
    analysis = client.get("/api/v1/dashboard/analysis")

    assert summary.status_code == 200
    assert analysis.status_code == 200
    assert summary.json()["open_analysis_count"] == 0
    assert analysis.json() == {"items": [], "total": 0}


def test_workspace_without_topics_returns_empty_topics_list(
    client: TestClient,
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    job = AnalysisJob(
        id="dashboard-empty-topic-job",
        workspace_id=DEFAULT_WORKSPACE_ID,
        status="completed",
        analysis_type="summary",
        prompt="Summarize",
        created_by=DEFAULT_USER_ID,
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    job.source_document_ids = [DOCUMENT_ID]
    job.result = AnalysisResult(
        id="dashboard-empty-topic-result",
        job_id=job.id,
        summary="Summary",
        key_points=[],
        suggested_tags=[],
        suggested_topics=[],
        confidence=0.8,
        created_at=now,
    )
    db_session.add(job)
    db_session.commit()

    summary = client.get("/api/v1/dashboard/summary")
    topics = client.get("/api/v1/dashboard/topics")

    assert summary.status_code == 200
    assert topics.status_code == 200
    assert summary.json()["topic_count"] == 0
    assert topics.json() == {"items": [], "total": 0}


def test_workspace_without_data_quality_run_returns_null_quality_score(
    client: TestClient,
    document_fixture: dict[str, str],
) -> None:
    summary = client.get("/api/v1/dashboard/summary")
    quality = client.get("/api/v1/dashboard/quality")

    assert summary.status_code == 200
    assert quality.status_code == 200
    assert summary.json()["quality_score"] is None
    assert quality.json() == {"items": [], "total": 0}
