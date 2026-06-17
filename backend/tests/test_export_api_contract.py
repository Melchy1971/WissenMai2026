"""Contract tests for Task #87: Export Center REST API.

Tests every endpoint for:
- Correct HTTP status codes
- Response schema compliance
- Pagination parameters (limit/offset/total)
- Status and format filter validation
- Domain error → HTTP status mapping (404 / 409 / 422)
- Approved-only guard (draft AnalysisResult → 422)

Marker: unit_fast (in-memory SQLite, no external I/O)
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import export as export_api
from app.main import app
from app.models.analysis import AnalysisResult
from app.services.export.service import ExportService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, SESSION_TOKEN
from tests.fixtures.export_seed import (
    JOB_ID_CANCELLED,
    JOB_ID_COMPLETED,
    JOB_ID_FAILED,
    JOB_ID_QUEUED,
    RESULT_ID_APPROVED,
    TEMPLATE_ID_DEFAULT,
    make_approved_result,
    seed_cancelled_job,
    seed_completed_job,
    seed_default_template,
    seed_failed_job,
    seed_queued_job,
)

pytestmark = pytest.mark.unit_fast

_AUTH_HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def export_client(
    db_session: Session,
    auth_fixture: dict,
    tmp_path: Path,
) -> Iterator[TestClient]:
    stub_renderer = MagicMock()
    stub_renderer.render.return_value = b"rendered content"

    def override_service() -> Iterator[ExportService]:
        yield ExportService(db_session, renderer=stub_renderer, export_root=tmp_path)

    app.dependency_overrides[export_api.get_export_service] = override_service
    try:
        yield TestClient(app, headers=_AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /export/jobs
# ---------------------------------------------------------------------------

class TestListExportJobs:
    def test_empty_returns_empty_list(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.get("/api/v1/export/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_pagination_reflected(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.get("/api/v1/export/jobs?limit=5&offset=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 10

    def test_invalid_status_filter_returns_422(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.get("/api/v1/export/jobs?status=INVALID")
        assert resp.status_code == 422

    def test_invalid_format_filter_returns_422(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.get("/api/v1/export/jobs?format=INVALID")
        assert resp.status_code == 422

    def test_valid_status_filter_accepted(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.get("/api/v1/export/jobs?status=QUEUED")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_format_filter_scopes_results(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.get("/api/v1/export/jobs?format=PDF")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /export/jobs
# ---------------------------------------------------------------------------

class TestCreateExportJob:
    def test_creates_queued_job(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        db_session.add(make_approved_result())
        db_session.commit()
        resp = export_client.post("/api/v1/export/jobs", json={
            "source_type": "ANALYSIS_RESULT",
            "source_ids": [RESULT_ID_APPROVED],
            "export_format": "MARKDOWN",
            "file_name": "my_export",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "QUEUED"
        assert data["export_format"] == "MARKDOWN"
        assert data["file_name"] == "my_export.md"
        assert data["file_path"] is None

    def test_draft_analysis_returns_422(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        from datetime import UTC, datetime
        from uuid import uuid4
        draft = AnalysisResult(
            id="draft-result-contract",
            job_id=str(uuid4()),
            summary="draft",
            key_points=[],
            suggested_tags=[],
            suggested_topics=[],
            confidence=0.5,
            status="draft",
            approved_by=None,
            approved_at=None,
            created_at=datetime.now(UTC),
        )
        db_session.add(draft)
        db_session.commit()
        resp = export_client.post("/api/v1/export/jobs", json={
            "source_type": "ANALYSIS_RESULT",
            "source_ids": ["draft-result-contract"],
            "export_format": "PDF",
            "file_name": "blocked_export",
        })
        assert resp.status_code == 422

    def test_missing_source_returns_404(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.post("/api/v1/export/jobs", json={
            "source_type": "ANALYSIS_RESULT",
            "source_ids": ["nonexistent-result"],
            "export_format": "JSON",
            "file_name": "missing",
        })
        assert resp.status_code == 404

    def test_empty_source_ids_returns_422(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.post("/api/v1/export/jobs", json={
            "source_type": "ANALYSIS_RESULT",
            "source_ids": [],
            "export_format": "MARKDOWN",
            "file_name": "bad",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /export/jobs/{job_id}
# ---------------------------------------------------------------------------

class TestGetExportJob:
    def test_returns_job(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.get(f"/api/v1/export/jobs/{JOB_ID_QUEUED}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == JOB_ID_QUEUED
        assert data["status"] == "QUEUED"

    def test_unknown_job_returns_404(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.get("/api/v1/export/jobs/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /export/jobs/{job_id}/start
# ---------------------------------------------------------------------------

class TestStartExportJob:
    def test_starts_queued_job(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.post(f"/api/v1/export/jobs/{JOB_ID_QUEUED}/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["file_path"] is not None

    def test_start_completed_job_returns_409(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict, tmp_path: Path
    ) -> None:
        seed_completed_job(db_session, file_path=str(tmp_path / "f.md"))
        db_session.commit()
        resp = export_client.post(f"/api/v1/export/jobs/{JOB_ID_COMPLETED}/start")
        assert resp.status_code == 409

    def test_start_unknown_job_returns_404(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.post("/api/v1/export/jobs/unknown/start")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /export/jobs/{job_id}/cancel
# ---------------------------------------------------------------------------

class TestCancelExportJob:
    def test_cancels_queued_job(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.post(f"/api/v1/export/jobs/{JOB_ID_QUEUED}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

    def test_cancel_failed_returns_409(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_failed_job(db_session)
        db_session.commit()
        resp = export_client.post(f"/api/v1/export/jobs/{JOB_ID_FAILED}/cancel")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /export/jobs/{job_id}/retry
# ---------------------------------------------------------------------------

class TestRetryExportJob:
    def test_retry_failed_job_creates_new_queued_job(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_failed_job(db_session)
        db_session.commit()
        resp = export_client.post(f"/api/v1/export/jobs/{JOB_ID_FAILED}/retry")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "QUEUED"
        assert data["id"] != JOB_ID_FAILED

    def test_retry_queued_job_returns_409(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.post(f"/api/v1/export/jobs/{JOB_ID_QUEUED}/retry")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /export/jobs/{job_id}/download
# ---------------------------------------------------------------------------

class TestDownloadExportFile:
    def test_download_completed_job(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict, tmp_path: Path
    ) -> None:
        (tmp_path / "some-job-id").mkdir(parents=True, exist_ok=True)
        (tmp_path / "some-job-id" / "export.md").write_bytes(b"# Export Content")
        seed_completed_job(db_session, file_path="some-job-id/export.md")
        db_session.commit()
        resp = export_client.get(f"/api/v1/export/jobs/{JOB_ID_COMPLETED}/download")
        assert resp.status_code == 200
        assert b"Export Content" in resp.content
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_download_queued_job_returns_404(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.get(f"/api/v1/export/jobs/{JOB_ID_QUEUED}/download")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /export/jobs/{job_id}/file
# ---------------------------------------------------------------------------

class TestDeleteExportFile:
    def test_delete_file_returns_204(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_queued_job(db_session)
        db_session.commit()
        resp = export_client.delete(f"/api/v1/export/jobs/{JOB_ID_QUEUED}/file")
        assert resp.status_code == 204

    def test_delete_unknown_job_returns_404(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.delete("/api/v1/export/jobs/nonexistent/file")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /export/templates
# ---------------------------------------------------------------------------

class TestListExportTemplates:
    def test_empty_returns_empty(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.get("/api/v1/export/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_seeded_template(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_default_template(db_session)
        db_session.commit()
        resp = export_client.get("/api/v1/export/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Standard PDF"
        assert data["items"][0]["is_default"] is True


# ---------------------------------------------------------------------------
# POST /export/templates
# ---------------------------------------------------------------------------

class TestCreateExportTemplate:
    def test_creates_template(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.post("/api/v1/export/templates", json={
            "name": "My Template",
            "export_format": "PDF",
            "is_default": False,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Template"
        assert data["export_format"] == "PDF"
        assert data["is_default"] is False


# ---------------------------------------------------------------------------
# PUT /export/templates/{template_id}
# ---------------------------------------------------------------------------

class TestUpdateExportTemplate:
    def test_update_template_name(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_default_template(db_session)
        db_session.commit()
        resp = export_client.put(f"/api/v1/export/templates/{TEMPLATE_ID_DEFAULT}", json={
            "name": "Renamed Template",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Template"

    def test_update_unknown_template_returns_404(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.put("/api/v1/export/templates/nonexistent", json={
            "name": "X",
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /export/templates/{template_id}
# ---------------------------------------------------------------------------

class TestDeleteExportTemplate:
    def test_delete_template(
        self, export_client: TestClient, db_session: Session, auth_fixture: dict
    ) -> None:
        seed_default_template(db_session)
        db_session.commit()
        resp = export_client.delete(f"/api/v1/export/templates/{TEMPLATE_ID_DEFAULT}")
        assert resp.status_code == 204

    def test_delete_unknown_returns_404(
        self, export_client: TestClient, auth_fixture: dict
    ) -> None:
        resp = export_client.delete("/api/v1/export/templates/nonexistent")
        assert resp.status_code == 404
