from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.data_quality import DataQualityRun
from app.main import app
from app.models.documents import BackgroundJob, Document, Workspace
from app.models.drift import DriftRun
from app.services.dashboard_service import DashboardSummaryService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID

pytestmark = pytest.mark.unit_fast


def test_dashboard_summary_empty_workspace_returns_zero_and_null_values(
    db_session: Session,
    auth_fixture: dict[str, str],
) -> None:
    summary = DashboardSummaryService(db_session).get_summary(workspace_id=DEFAULT_WORKSPACE_ID)

    assert summary.document_count == 0
    assert summary.active_document_count == 0
    assert summary.archived_document_count == 0
    assert summary.new_imports_count == 0
    assert summary.open_analysis_count == 0
    assert summary.topic_count == 0
    assert summary.quality_score is None
    assert summary.drift_status is None


def test_dashboard_summary_aggregates_workspace_data(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            Document(
                id="dashboard-archived-doc",
                workspace_id=DEFAULT_WORKSPACE_ID,
                owner_user_id=DEFAULT_USER_ID,
                current_version_id=None,
                title="Archived",
                source_type="upload",
                mime_type="text/plain",
                content_hash="dashboard-archived-hash",
                import_status="parsed",
                lifecycle_status="archived",
                created_at=now,
                updated_at=now,
            ),
            Document(
                id="dashboard-pending-import",
                workspace_id=DEFAULT_WORKSPACE_ID,
                owner_user_id=DEFAULT_USER_ID,
                current_version_id=None,
                title="Pending Import",
                source_type="upload",
                mime_type="text/plain",
                content_hash="dashboard-pending-hash",
                import_status="pending",
                lifecycle_status="active",
                created_at=now,
                updated_at=now,
            ),
            Document(
                id="dashboard-deleted-pending-import",
                workspace_id=DEFAULT_WORKSPACE_ID,
                owner_user_id=DEFAULT_USER_ID,
                current_version_id=None,
                title="Deleted Pending Import",
                source_type="upload",
                mime_type="text/plain",
                content_hash="dashboard-deleted-pending-hash",
                import_status="pending",
                lifecycle_status="deleted",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    _add_analysis_job(
        db_session,
        job_id="dashboard-open-analysis",
        status="running",
        topics=None,
        created_at=now,
    )
    _add_analysis_job(
        db_session,
        job_id="dashboard-completed-analysis",
        status="completed",
        topics=["contracts", "privacy", "contracts"],
        created_at=now,
    )
    db_session.add_all(
        [
            DataQualityRun(
                id="dashboard-quality-old",
                workspace_id=DEFAULT_WORKSPACE_ID,
                status="completed",
                started_at=now - timedelta(days=1),
                finished_at=now - timedelta(days=1),
                total_findings=3,
                quality_score=74.0,
                created_by=DEFAULT_USER_ID,
            ),
            DataQualityRun(
                id="dashboard-quality-latest",
                workspace_id=DEFAULT_WORKSPACE_ID,
                status="completed",
                started_at=now,
                finished_at=now,
                total_findings=1,
                quality_score=91.5,
                created_by=DEFAULT_USER_ID,
            ),
            DriftRun(
                id="dashboard-drift-old",
                workspace_id=DEFAULT_WORKSPACE_ID,
                status="completed",
                triggered_by=DEFAULT_USER_ID,
                detector_names=[],
                started_at=now - timedelta(hours=1),
                completed_at=now - timedelta(hours=1),
                total_findings=0,
                error_message=None,
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(hours=1),
            ),
            DriftRun(
                id="dashboard-drift-latest",
                workspace_id=DEFAULT_WORKSPACE_ID,
                status="failed",
                triggered_by=DEFAULT_USER_ID,
                detector_names=[],
                started_at=now,
                completed_at=None,
                total_findings=None,
                error_message="failed",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    summary = DashboardSummaryService(db_session).get_summary(workspace_id=DEFAULT_WORKSPACE_ID)

    assert summary.document_count == 5
    assert summary.active_document_count == 3
    assert summary.archived_document_count == 1
    assert summary.new_imports_count == 1
    assert summary.open_analysis_count == 1
    assert summary.topic_count == 2
    assert summary.quality_score == 91.5
    assert summary.drift_status == "failed"


def test_dashboard_summary_is_workspace_scoped(
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    other_workspace_id = "dashboard-other-workspace"
    db_session.add(Workspace(id=other_workspace_id, name="Other", is_default=False, created_at=now))
    db_session.add(
        Document(
            id="dashboard-other-doc",
            workspace_id=other_workspace_id,
            owner_user_id=DEFAULT_USER_ID,
            current_version_id=None,
            title="Other",
            source_type="upload",
            mime_type="text/plain",
            content_hash="dashboard-other-hash",
            import_status="pending",
            lifecycle_status="active",
            created_at=now,
            updated_at=now,
        )
    )
    _add_analysis_job(
        db_session,
        job_id="dashboard-other-analysis",
        workspace_id=other_workspace_id,
        status="running",
        topics=["other"],
        created_at=now,
    )
    db_session.add(
        DataQualityRun(
            id="dashboard-other-quality",
            workspace_id=other_workspace_id,
            status="completed",
            started_at=now,
            finished_at=now,
            total_findings=0,
            quality_score=12.0,
            created_by=DEFAULT_USER_ID,
        )
    )
    db_session.commit()

    summary = DashboardSummaryService(db_session).get_summary(workspace_id=DEFAULT_WORKSPACE_ID)

    assert summary.document_count == 2
    assert summary.new_imports_count == 0
    assert summary.open_analysis_count == 0
    assert summary.topic_count == 0
    assert summary.quality_score is None


def test_dashboard_summary_endpoint_uses_service(
    client: TestClient,
    document_fixture: dict[str, str],
) -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["document_count"] == 2
    assert body["active_document_count"] == 2
    assert body["archived_document_count"] == 0
    assert body["new_imports_count"] == 0
    assert body["quality_score"] is None
    assert body["drift_status"] is None


def test_dashboard_endpoints_require_authentication() -> None:
    unauthenticated = TestClient(app, raise_server_exceptions=False)

    for path in (
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/activity",
        "/api/v1/dashboard/imports",
        "/api/v1/dashboard/analysis",
        "/api/v1/dashboard/quality",
        "/api/v1/dashboard/topics",
    ):
        response = unauthenticated.get(path)
        assert response.status_code == 401


def test_dashboard_list_endpoints_return_workspace_scoped_safe_shapes(
    client: TestClient,
    db_session: Session,
    document_fixture: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    db_session.add(
        BackgroundJob(
            id="dashboard-import-job",
            job_type="document_import",
            status="running",
            workspace_id=DEFAULT_WORKSPACE_ID,
            requested_by_user_id=DEFAULT_USER_ID,
            payload_={
                "filename": "contract.pdf",
                "mime_type": "application/pdf",
                "temp_file_path": "C:/secret/internal/path/contract.pdf",
                "debug": "not-for-dashboard",
            },
            result_=None,
            progress_current=0,
            progress_total=1,
            progress_message=None,
            error_code=None,
            error_message=None,
            attempt_count=0,
            locked_at=None,
            locked_by=None,
            created_at=now,
            started_at=now,
            finished_at=None,
        )
    )
    _add_analysis_job(
        db_session,
        job_id="dashboard-api-analysis",
        status="completed",
        topics=["contracts", "privacy", "contracts"],
        created_at=now,
    )
    db_session.add(
        DataQualityRun(
            id="dashboard-api-quality",
            workspace_id=DEFAULT_WORKSPACE_ID,
            status="completed",
            started_at=now,
            finished_at=now,
            total_findings=2,
            quality_score=88.0,
            created_by=DEFAULT_USER_ID,
        )
    )
    db_session.add(
        DriftRun(
            id="dashboard-api-drift",
            workspace_id=DEFAULT_WORKSPACE_ID,
            status="completed",
            triggered_by=DEFAULT_USER_ID,
            detector_names=["metadata"],
            started_at=now,
            completed_at=now,
            total_findings=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    imports = client.get("/api/v1/dashboard/imports").json()
    assert imports["total"] == 1
    assert imports["items"][0] == {
        "id": "dashboard-import-job",
        "status": "running",
        "filename": "contract.pdf",
        "mime_type": "application/pdf",
        "created_at": now.replace(tzinfo=None).isoformat(),
        "started_at": now.replace(tzinfo=None).isoformat(),
        "finished_at": None,
    }
    assert "temp_file_path" not in str(imports)
    assert "debug" not in str(imports)

    analysis = client.get("/api/v1/dashboard/analysis").json()
    assert analysis["total"] == 1
    assert analysis["items"][0]["id"] == "dashboard-api-analysis"
    assert set(analysis["items"][0]) == {"id", "status", "analysis_type", "created_at", "started_at", "finished_at"}

    quality = client.get("/api/v1/dashboard/quality").json()
    assert quality["total"] == 1
    assert quality["items"][0]["quality_score"] == 88.0
    assert set(quality["items"][0]) == {"id", "status", "quality_score", "total_findings", "started_at", "finished_at"}

    topics = client.get("/api/v1/dashboard/topics").json()
    assert topics["total"] == 2
    assert topics["items"][0] == {"name": "contracts", "count": 2, "latest_job_id": "dashboard-api-analysis"}
    assert topics["items"][1] == {"name": "privacy", "count": 1, "latest_job_id": "dashboard-api-analysis"}

    activity = client.get("/api/v1/dashboard/activity").json()
    assert activity["total"] >= 4
    assert {item["item_type"] for item in activity["items"]} >= {"document", "import", "analysis", "quality", "drift"}
    assert "gate" not in str(activity).lower()
    assert "debug" not in str(activity).lower()


def test_dashboard_list_endpoints_are_empty_for_empty_workspace(
    client: TestClient,
    auth_fixture: dict[str, str],
) -> None:
    for path in (
        "/api/v1/dashboard/activity",
        "/api/v1/dashboard/imports",
        "/api/v1/dashboard/analysis",
        "/api/v1/dashboard/quality",
        "/api/v1/dashboard/topics",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0}


def _add_analysis_job(
    db_session: Session,
    *,
    job_id: str,
    status: str,
    topics: list[str] | None,
    created_at: datetime,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> AnalysisJob:
    job = AnalysisJob(
        id=job_id,
        workspace_id=workspace_id,
        status=status,
        analysis_type="summary",
        prompt="Summarize",
        created_by=DEFAULT_USER_ID,
        created_at=created_at,
        started_at=created_at if status in {"running", "completed", "approved"} else None,
        finished_at=created_at if status in {"completed", "approved", "failed"} else None,
    )
    job.source_document_ids = [DOCUMENT_ID]
    if topics is not None:
        job.result = AnalysisResult(
            id=f"{job_id}-result",
            job_id=job.id,
            summary="Summary",
            key_points=[],
            suggested_tags=[],
            suggested_topics=topics,
            confidence=0.9,
            created_at=created_at,
        )
    db_session.add(job)
    return job
