from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.analysis import AnalysisJob
from app.models.documents import Document, Workspace
from tests.conftest import (
    DEFAULT_USER_ID,
    DEFAULT_WORKSPACE_ID,
    DOCUMENT_ID,
    OLDER_DOCUMENT_ID,
    SESSION_TOKEN,
)

pytestmark = pytest.mark.unit_fast


def _create_job(client: TestClient, *, source_document_ids: list[str] | None = None) -> dict:
    response = client.post(
        "/api/v1/analysis/jobs",
        json={
            "source_document_ids": source_document_ids or [DOCUMENT_ID, OLDER_DOCUMENT_ID],
            "analysis_type": "comparison",
            "prompt": "Check relevant changes",
        },
    )
    assert response.status_code == 201
    return response.json()


def _other_workspace_job(db_session: Session, document_id: str) -> AnalysisJob:
    now = datetime.now(UTC)
    workspace_id = "analysis-other-workspace"
    db_session.add(Workspace(id=workspace_id, name="Other", is_default=False, created_at=now))
    job = AnalysisJob(
        id="analysis-other-job",
        workspace_id=workspace_id,
        status="pending",
        analysis_type="summary",
        prompt="Other workspace",
        created_by=DEFAULT_USER_ID,
        created_at=now,
    )
    job.source_document_ids = [document_id]
    db_session.add(job)
    db_session.commit()
    return job


class TestAnalysisAuth:
    def test_jobs_require_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/analysis/jobs")

        assert response.status_code == 401


class TestAnalysisWorkspaceIsolation:
    def test_list_jobs_is_workspace_scoped(
        self,
        client: TestClient,
        db_session: Session,
        document_fixture: dict[str, str],
    ) -> None:
        _other_workspace_job(db_session, document_fixture["document_id"])

        response = client.get("/api/v1/analysis/jobs")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_get_job_hides_other_workspace(
        self,
        client: TestClient,
        db_session: Session,
        document_fixture: dict[str, str],
    ) -> None:
        job = _other_workspace_job(db_session, document_fixture["document_id"])

        response = client.get(f"/api/v1/analysis/jobs/{job.id}")

        assert response.status_code == 404

    def test_create_rejects_document_from_other_workspace(
        self,
        client: TestClient,
        db_session: Session,
        document_fixture: dict[str, str],
    ) -> None:
        now = datetime.now(UTC)
        workspace_id = "analysis-other-workspace"
        db_session.add(Workspace(id=workspace_id, name="Other", is_default=False, created_at=now))
        db_session.add(
            Document(
                id="analysis-other-document",
                workspace_id=workspace_id,
                owner_user_id=DEFAULT_USER_ID,
                current_version_id=None,
                title="Other doc",
                source_type="upload",
                mime_type="text/plain",
                content_hash="analysis-other-document-hash",
                import_status="pending",
                created_at=now,
                updated_at=now,
            )
        )
        db_session.commit()

        response = client.post(
            "/api/v1/analysis/jobs",
            json={
                "source_document_ids": ["analysis-other-document"],
                "analysis_type": "summary",
                "prompt": "Invalid",
            },
        )

        assert response.status_code == 404


class TestAnalysisLifecycle:
    def test_create_compare_summarize_and_approve_flow(
        self,
        client: TestClient,
        document_fixture: dict[str, str],
    ) -> None:
        job = _create_job(client)
        assert job["status"] == "pending"
        assert job["source_document_ids"] == [DOCUMENT_ID, OLDER_DOCUMENT_ID]
        assert job["result"] is None

        compare = client.post(
            f"/api/v1/analysis/jobs/{job['id']}/compare",
            json={"compared_document_ids": [OLDER_DOCUMENT_ID], "max_differences": 5},
        )
        assert compare.status_code == 202
        compared_job = compare.json()
        assert compared_job["status"] == "completed"
        assert compared_job["comparison"]["job_id"] == job["id"]
        assert compared_job["comparison"]["compared_document_ids"] == [OLDER_DOCUMENT_ID]
        assert compared_job["result"]["key_points"]
        assert all(item["status"] == "pending" for item in compared_job["suggestions"])

        summarize = client.post(
            f"/api/v1/analysis/jobs/{job['id']}/summarize",
            json={"prompt": "privacy", "max_suggestions": 2},
        )
        assert summarize.status_code == 202
        summarized_job = summarize.json()
        assert summarized_job["status"] == "completed"
        assert summarized_job["suggestions"]

        approve = client.post(
            f"/api/v1/analysis/jobs/{job['id']}/approve",
            json={"decision": "approved"},
        )
        assert approve.status_code == 200
        approved_job = approve.json()
        assert approved_job["status"] == "approved"
        assert all(item["status"] == "approved" for item in approved_job["suggestions"])
        assert all(item["approved_by"] == DEFAULT_USER_ID for item in approved_job["suggestions"])


class TestAnalysisApprovalRequired:
    def test_cannot_approve_pending_job(self, client: TestClient, document_fixture: dict[str, str]) -> None:
        job = _create_job(client)

        response = client.post(
            f"/api/v1/analysis/jobs/{job['id']}/approve",
            json={"decision": "approved"},
        )

        assert response.status_code == 409

    def test_result_not_available_before_analysis(
        self,
        client: TestClient,
        document_fixture: dict[str, str],
    ) -> None:
        job = _create_job(client, source_document_ids=[DOCUMENT_ID])

        response = client.get(f"/api/v1/analysis/jobs/{job['id']}/result")

        assert response.status_code == 409

    def test_compare_requires_compared_document(self, client: TestClient, document_fixture: dict[str, str]) -> None:
        job = _create_job(client, source_document_ids=[DOCUMENT_ID])

        response = client.post(
            f"/api/v1/analysis/jobs/{job['id']}/compare",
            json={"max_differences": 1},
        )

        assert response.status_code == 422


class TestAnalysisResult:
    def test_result_retrieval_after_summary(self, client: TestClient, document_fixture: dict[str, str]) -> None:
        job = _create_job(client, source_document_ids=[DOCUMENT_ID])
        client.post(
            f"/api/v1/analysis/jobs/{job['id']}/summarize",
            json={"max_suggestions": 1},
        )

        response = client.get(f"/api/v1/analysis/jobs/{job['id']}/result")

        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == job["id"]
        assert body["summary"]
        assert 0 <= body["confidence"] <= 1
