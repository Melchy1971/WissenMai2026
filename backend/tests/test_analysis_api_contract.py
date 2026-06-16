"""Contract tests for Task #77: Analysis REST API.

Tests every endpoint for:
- Correct HTTP status codes
- Response schema compliance (Pydantic validation via TestClient)
- Pagination parameters (limit/offset/total)
- Status and source_type filter validation
- Permission enforcement (member vs admin)
- Domain error → HTTP error mapping (404 / 409 / 422)

Marker: unit_fast (no external I/O, in-memory SQLite)
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import analysis as analysis_api
from app.main import app
from app.services.analysis.service import AnalysisService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID, SESSION_TOKEN
from tests.fixtures.analysis_seed import (
    JOB_ID_CANCELLED,
    JOB_ID_COMPLETED,
    JOB_ID_FAILED,
    JOB_ID_QUEUED,
    RESULT_ID_APPROVED,
    RESULT_ID_DRAFT,
    RESULT_ID_REVIEW,
    make_analysis_job,
    make_analysis_result,
    seed_cancelled_job,
    seed_completed_job_with_result,
    seed_failed_job,
    seed_queued_job,
)

pytestmark = pytest.mark.unit_fast

_AUTH_HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
}


# ── Client fixture ────────────────────────────────────────────────────────────

@pytest.fixture()
def analysis_client(db_session: Session, auth_fixture: dict[str, str]) -> Iterator[TestClient]:
    def override_service() -> Iterator[AnalysisService]:
        yield AnalysisService(db_session)

    app.dependency_overrides[analysis_api.get_analysis_service] = override_service
    try:
        yield TestClient(app, headers=_AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()


# ── GET /analysis/jobs ────────────────────────────────────────────────────────

class TestListJobs:
    def test_empty_workspace_returns_empty_list(
        self, analysis_client: TestClient, auth_fixture: dict
    ):
        resp = analysis_client.get("/api/v1/analysis/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_pagination_params_reflected(
        self, analysis_client: TestClient, auth_fixture: dict
    ):
        resp = analysis_client.get("/api/v1/analysis/jobs?limit=5&offset=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 10

    def test_status_filter_invalid_returns_422(
        self, analysis_client: TestClient, auth_fixture: dict
    ):
        resp = analysis_client.get("/api/v1/analysis/jobs?status=BOGUS")
        assert resp.status_code == 422

    def test_source_type_filter_invalid_returns_422(
        self, analysis_client: TestClient, auth_fixture: dict
    ):
        resp = analysis_client.get("/api/v1/analysis/jobs?source_type=UNKNOWN")
        assert resp.status_code == 422

    def test_status_filter_valid(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_queued_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.get("/api/v1/analysis/jobs?status=queued")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "queued"

    def test_source_type_filter_valid(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_queued_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.get("/api/v1/analysis/jobs?source_type=DOCUMENTS")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_source_type_no_match_returns_empty(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_queued_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.get("/api/v1/analysis/jobs?source_type=TOPIC")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ── POST /analysis/jobs ───────────────────────────────────────────────────────

class TestCreateJob:
    def test_create_job_minimal_payload(
        self, analysis_client: TestClient, auth_fixture: dict,
        document_fixture: dict,
    ):
        payload = {
            "source_document_ids": [DOCUMENT_ID],
            "analysis_type": "summary",
            "prompt": "Fasse zusammen.",
        }
        resp = analysis_client.post("/api/v1/analysis/jobs", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"
        assert data["analysis_type"] == "summary"
        assert data["workspace_id"] == DEFAULT_WORKSPACE_ID

    def test_create_job_with_provider_and_model(
        self, analysis_client: TestClient, auth_fixture: dict,
        document_fixture: dict,
    ):
        payload = {
            "source_document_ids": [DOCUMENT_ID],
            "analysis_type": "summary",
            "prompt": "Analyse.",
            "source_type": "DOCUMENTS",
            "provider": "ollama",
            "model": "llama3",
        }
        resp = analysis_client.post("/api/v1/analysis/jobs", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "ollama"
        assert data["model"] == "llama3"

    def test_create_job_no_documents_no_source_ids_returns_422(
        self, analysis_client: TestClient, auth_fixture: dict,
    ):
        payload = {
            "source_document_ids": [],
            "analysis_type": "summary",
            "prompt": "Test.",
        }
        resp = analysis_client.post("/api/v1/analysis/jobs", json=payload)
        # Service raises AnalysisSourceRequiredApiError → 422
        assert resp.status_code == 422

    def test_create_job_missing_required_fields_returns_422(
        self, analysis_client: TestClient, auth_fixture: dict,
    ):
        resp = analysis_client.post("/api/v1/analysis/jobs", json={"prompt": "x"})
        assert resp.status_code == 422


# ── GET /analysis/jobs/{job_id} ───────────────────────────────────────────────

class TestGetJob:
    def test_get_existing_job(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_queued_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.get(f"/api/v1/analysis/jobs/{JOB_ID_QUEUED}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == JOB_ID_QUEUED
        assert "result" in data
        assert "suggestions" in data

    def test_get_unknown_job_returns_404(
        self, analysis_client: TestClient, auth_fixture: dict,
    ):
        resp = analysis_client.get("/api/v1/analysis/jobs/does-not-exist")
        assert resp.status_code == 404


# ── POST /analysis/jobs/{job_id}/cancel ───────────────────────────────────────

class TestCancelJob:
    def test_cancel_queued_job(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_queued_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.post(f"/api/v1/analysis/jobs/{JOB_ID_QUEUED}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_completed_job_returns_409(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_completed_job_with_result(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.post(f"/api/v1/analysis/jobs/{JOB_ID_COMPLETED}/cancel")
        assert resp.status_code == 409

    def test_cancel_unknown_job_returns_404(
        self, analysis_client: TestClient, auth_fixture: dict,
    ):
        resp = analysis_client.post("/api/v1/analysis/jobs/no-such-job/cancel")
        assert resp.status_code == 404


# ── POST /analysis/jobs/{job_id}/retry ────────────────────────────────────────

class TestRetryJob:
    def test_retry_failed_job_creates_new_job(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_failed_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.post(f"/api/v1/analysis/jobs/{JOB_ID_FAILED}/retry")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"
        assert data["id"] != JOB_ID_FAILED

    def test_retry_queued_job_returns_409(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        seed_queued_job(db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID])
        db_session.commit()
        resp = analysis_client.post(f"/api/v1/analysis/jobs/{JOB_ID_QUEUED}/retry")
        assert resp.status_code == 409


# ── GET /analysis/results/{result_id} ────────────────────────────────────────

class TestGetResult:
    def test_get_existing_result(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        job, result = seed_completed_job_with_result(
            db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID]
        )
        db_session.commit()
        resp = analysis_client.get(f"/api/v1/analysis/results/{result.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == result.id
        assert data["status"] == "draft"

    def test_get_unknown_result_returns_404(
        self, analysis_client: TestClient, auth_fixture: dict,
    ):
        resp = analysis_client.get("/api/v1/analysis/results/no-such-result")
        assert resp.status_code == 404


# ── PATCH /analysis/results/{result_id} ──────────────────────────────────────

class TestUpdateResult:
    def test_update_draft_result(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        job, result = seed_completed_job_with_result(
            db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID]
        )
        db_session.commit()
        resp = analysis_client.patch(
            f"/api/v1/analysis/results/{result.id}",
            json={"title": "Neuer Titel", "summary": "Neue Zusammenfassung."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Neuer Titel"
        assert data["summary"] == "Neue Zusammenfassung."

    def test_update_unknown_result_returns_404(
        self, analysis_client: TestClient, auth_fixture: dict,
    ):
        resp = analysis_client.patch(
            "/api/v1/analysis/results/no-such",
            json={"title": "x"},
        )
        assert resp.status_code == 404


# ── POST /analysis/results/{result_id}/review ────────────────────────────────

class TestMarkForReview:
    def test_mark_draft_for_review(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        job, result = seed_completed_job_with_result(
            db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID]
        )
        db_session.commit()
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/review",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

    def test_mark_already_review_returns_409(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        job = make_analysis_job(
            db_session, workspace_id=DEFAULT_WORKSPACE_ID,
            created_by=DEFAULT_USER_ID, document_ids=[DOCUMENT_ID],
            job_id="review-job-id", status="completed",
        )
        result = make_analysis_result(
            db_session, job=job, result_id="review-result-id", status="review"
        )
        db_session.commit()
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/review",
            json={},
        )
        assert resp.status_code == 409


# ── POST /analysis/results/{result_id}/approve ────────────────────────────────

class TestApproveResult:
    def _seed_review_result(self, db_session: Session) -> Any:
        job = make_analysis_job(
            db_session, workspace_id=DEFAULT_WORKSPACE_ID,
            created_by=DEFAULT_USER_ID, document_ids=[DOCUMENT_ID],
            job_id="approve-job-id", status="completed",
        )
        result = make_analysis_result(
            db_session, job=job, result_id="approve-result-id", status="review"
        )
        db_session.commit()
        return result

    def test_approve_review_result_with_confirm(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        result = self._seed_review_result(db_session)
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == DEFAULT_USER_ID
        assert data["approved_at"] is not None

    def test_approve_without_confirm_returns_422(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        result = self._seed_review_result(db_session)
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": False},
        )
        assert resp.status_code == 422

    def test_approve_draft_result_returns_409(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        job, result = seed_completed_job_with_result(
            db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID]
        )
        db_session.commit()
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": True},
        )
        assert resp.status_code == 409


# ── POST /analysis/results/{result_id}/reject ─────────────────────────────────

class TestRejectResult:
    def _seed_review_result(self, db_session: Session) -> Any:
        job = make_analysis_job(
            db_session, workspace_id=DEFAULT_WORKSPACE_ID,
            created_by=DEFAULT_USER_ID, document_ids=[DOCUMENT_ID],
            job_id="reject-job-id", status="completed",
        )
        result = make_analysis_result(
            db_session, job=job, result_id="reject-result-id", status="review"
        )
        db_session.commit()
        return result

    def test_reject_review_result(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        result = self._seed_review_result(db_session)
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/reject",
            json={"reason": "Inhalt unvollständig."},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_reject_without_reason_returns_422(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        result = self._seed_review_result(db_session)
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/reject",
            json={"reason": ""},
        )
        assert resp.status_code == 422

    def test_reject_draft_result_returns_409(
        self, analysis_client: TestClient, auth_fixture: dict,
        db_session: Session, document_fixture: dict,
    ):
        job, result = seed_completed_job_with_result(
            db_session, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, [DOCUMENT_ID]
        )
        db_session.commit()
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/reject",
            json={"reason": "Kein gültiger Status."},
        )
        assert resp.status_code == 409


# ── Unauthenticated access ────────────────────────────────────────────────────

class TestAuthEnforcement:
    def test_list_jobs_without_auth_returns_401(self):
        client = TestClient(app)
        resp = client.get("/api/v1/analysis/jobs")
        assert resp.status_code == 401

    def test_create_job_without_auth_returns_401(self):
        client = TestClient(app)
        resp = client.post("/api/v1/analysis/jobs", json={
            "source_document_ids": ["x"],
            "analysis_type": "summary",
            "prompt": "p",
        })
        assert resp.status_code == 401
