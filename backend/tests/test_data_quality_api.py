"""Tests for Data Quality Read-Only API V1.

Uses the standard db_session + auth_fixture + TestClient pattern.
All endpoints are GET-only; no mutation is tested or expected.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import data_quality as dq_api
from app.main import app
from app.models.data_quality import DataQualityFinding, DataQualityRun

# Reuse constants from conftest
from tests.conftest import DEFAULT_WORKSPACE_ID, SESSION_TOKEN

pytestmark = pytest.mark.m3a_truth


# ---------------------------------------------------------------------------
# Client fixture for DQ API
# ---------------------------------------------------------------------------

@pytest.fixture()
def dq_client(db_session: Session, auth_fixture: dict[str, str]) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[dq_api.get_db_session] = override_session
    try:
        yield TestClient(
            app,
            headers={
                "Authorization": f"Bearer {SESSION_TOKEN}",
                "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
            },
            raise_server_exceptions=True,
        )
    finally:
        app.dependency_overrides.pop(dq_api.get_db_session, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(
    session: Session,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    *,
    status: str = "completed",
    total_findings: int = 0,
    quality_score: float = 100.0,
) -> DataQualityRun:
    run = DataQualityRun(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        status=status,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC) if status != "running" else None,
        total_findings=total_findings,
        quality_score=quality_score,
    )
    session.add(run)
    session.flush()
    return run


def _finding(
    session: Session,
    run: DataQualityRun,
    *,
    finding_type: str = "DUPLICATE_DOCUMENT",
    severity: str = "warning",
    document_id: str | None = None,
) -> DataQualityFinding:
    f = DataQualityFinding(
        id=str(uuid.uuid4()),
        run_id=run.id,
        workspace_id=run.workspace_id,
        finding_type=finding_type,
        severity=severity,
        document_id=document_id,
        version_id=None,
        chunk_id=None,
        title="Test Finding",
        description="desc",
        remediation="review manually",
        created_at=datetime.now(UTC),
    )
    session.add(f)
    session.flush()
    return f


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthRequired:
    def test_runs_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/data-quality/runs")
        assert r.status_code in (401, 403)

    def test_findings_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/data-quality/findings")
        assert r.status_code in (401, 403)

    def test_summary_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/data-quality/summary")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /data-quality/runs
# ---------------------------------------------------------------------------

class TestListRuns:
    def test_empty_workspace(self, dq_client, db_session, auth_fixture):
        r = dq_client.get("/api/v1/data-quality/runs")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_returns_own_runs(self, dq_client, db_session, auth_fixture):
        _run(db_session)
        _run(db_session)
        db_session.commit()
        r = dq_client.get("/api/v1/data-quality/runs")
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_does_not_return_other_workspace_runs(self, dq_client, db_session, auth_fixture):
        other_wid = str(uuid.uuid4())
        _run(db_session, workspace_id=other_wid)
        db_session.commit()
        r = dq_client.get("/api/v1/data-quality/runs")
        assert r.json()["total"] == 0

    def test_pagination_limit(self, dq_client, db_session, auth_fixture):
        for _ in range(5):
            _run(db_session)
        db_session.commit()
        r = dq_client.get("/api/v1/data-quality/runs?limit=2")
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

    def test_pagination_offset(self, dq_client, db_session, auth_fixture):
        for _ in range(3):
            _run(db_session)
        db_session.commit()
        r = dq_client.get("/api/v1/data-quality/runs?limit=2&offset=2")
        assert len(r.json()["items"]) == 1

    def test_run_item_has_required_fields(self, dq_client, db_session, auth_fixture):
        _run(db_session)
        db_session.commit()
        item = dq_client.get("/api/v1/data-quality/runs").json()["items"][0]
        for field in ("run_id", "workspace_id", "status", "started_at", "total_findings", "quality_score"):
            assert field in item


# ---------------------------------------------------------------------------
# GET /data-quality/runs/{run_id}
# ---------------------------------------------------------------------------

class TestGetRun:
    def test_returns_run(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        db_session.commit()
        r = dq_client.get(f"/api/v1/data-quality/runs/{run.id}")
        assert r.status_code == 200
        assert r.json()["run_id"] == run.id

    def test_404_missing_run(self, dq_client, auth_fixture):
        r = dq_client.get("/api/v1/data-quality/runs/nonexistent-id")
        assert r.status_code == 404

    def test_404_other_workspace_run(self, dq_client, db_session, auth_fixture):
        run = _run(db_session, workspace_id=str(uuid.uuid4()))
        db_session.commit()
        r = dq_client.get(f"/api/v1/data-quality/runs/{run.id}")
        assert r.status_code == 404

    def test_includes_finding_counts(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run, finding_type="DUPLICATE_DOCUMENT")
        _finding(db_session, run, finding_type="INVALID_LIFECYCLE")
        db_session.commit()
        body = dq_client.get(f"/api/v1/data-quality/runs/{run.id}").json()
        assert body["finding_counts"]["DUPLICATE_DOCUMENT"] == 1
        assert body["finding_counts"]["INVALID_LIFECYCLE"] == 1


# ---------------------------------------------------------------------------
# GET /data-quality/findings
# ---------------------------------------------------------------------------

class TestListFindings:
    def test_empty(self, dq_client, db_session, auth_fixture):
        r = dq_client.get("/api/v1/data-quality/findings")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_returns_findings(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run)
        _finding(db_session, run)
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/findings").json()
        assert body["total"] == 2

    def test_workspace_isolation(self, dq_client, db_session, auth_fixture):
        other_wid = str(uuid.uuid4())
        other_run = _run(db_session, workspace_id=other_wid)
        _finding(db_session, other_run)
        db_session.commit()
        assert dq_client.get("/api/v1/data-quality/findings").json()["total"] == 0

    def test_filter_severity(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run, severity="error")
        _finding(db_session, run, severity="warning")
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/findings?severity=error").json()
        assert body["total"] == 1
        assert body["items"][0]["severity"] == "error"

    def test_filter_finding_type(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run, finding_type="DUPLICATE_DOCUMENT")
        _finding(db_session, run, finding_type="INVALID_LIFECYCLE")
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/findings?finding_type=DUPLICATE_DOCUMENT").json()
        assert body["total"] == 1
        assert body["items"][0]["finding_type"] == "DUPLICATE_DOCUMENT"

    def test_filter_document_id(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        doc_id = str(uuid.uuid4())
        _finding(db_session, run, document_id=doc_id)
        _finding(db_session, run, document_id=str(uuid.uuid4()))
        db_session.commit()
        body = dq_client.get(f"/api/v1/data-quality/findings?document_id={doc_id}").json()
        assert body["total"] == 1
        assert body["items"][0]["document_id"] == doc_id

    def test_filter_run_id(self, dq_client, db_session, auth_fixture):
        run_a = _run(db_session)
        run_b = _run(db_session)
        _finding(db_session, run_a)
        _finding(db_session, run_b)
        db_session.commit()
        body = dq_client.get(f"/api/v1/data-quality/findings?run_id={run_a.id}").json()
        assert body["total"] == 1
        assert body["items"][0]["run_id"] == run_a.id

    def test_pagination(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        for _ in range(5):
            _finding(db_session, run)
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/findings?limit=2&offset=0").json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["offset"] == 0

    def test_invalid_severity_filter_rejected(self, dq_client, auth_fixture):
        r = dq_client.get("/api/v1/data-quality/findings?severity=CRITICAL")
        assert r.status_code == 422

    def test_finding_item_has_required_fields(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run)
        db_session.commit()
        item = dq_client.get("/api/v1/data-quality/findings").json()["items"][0]
        for field in (
            "finding_id", "run_id", "workspace_id", "finding_type",
            "severity", "title", "description", "remediation", "created_at",
        ):
            assert field in item


# ---------------------------------------------------------------------------
# GET /data-quality/summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_empty_workspace(self, dq_client, db_session, auth_fixture):
        r = dq_client.get("/api/v1/data-quality/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["workspace_id"] == DEFAULT_WORKSPACE_ID
        assert body["total_runs"] == 0
        assert body["total_findings"] == 0
        assert body["latest_run_id"] is None

    def test_reflects_latest_run(self, dq_client, db_session, auth_fixture):
        run = _run(db_session, quality_score=72.5)
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/summary").json()
        assert body["latest_run_id"] == run.id
        assert body["latest_quality_score"] == 72.5
        assert body["total_runs"] == 1

    def test_findings_by_severity(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run, severity="error")
        _finding(db_session, run, severity="error")
        _finding(db_session, run, severity="warning")
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/summary").json()
        assert body["findings_by_severity"]["error"] == 2
        assert body["findings_by_severity"]["warning"] == 1

    def test_findings_by_type(self, dq_client, db_session, auth_fixture):
        run = _run(db_session)
        _finding(db_session, run, finding_type="DUPLICATE_DOCUMENT")
        _finding(db_session, run, finding_type="DUPLICATE_DOCUMENT")
        _finding(db_session, run, finding_type="INVALID_LIFECYCLE")
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/summary").json()
        assert body["findings_by_type"]["DUPLICATE_DOCUMENT"] == 2
        assert body["findings_by_type"]["INVALID_LIFECYCLE"] == 1

    def test_workspace_isolation(self, dq_client, db_session, auth_fixture):
        other_wid = str(uuid.uuid4())
        other_run = _run(db_session, workspace_id=other_wid)
        _finding(db_session, other_run)
        db_session.commit()
        body = dq_client.get("/api/v1/data-quality/summary").json()
        assert body["total_runs"] == 0
        assert body["total_findings"] == 0


# ---------------------------------------------------------------------------
# Read-only: no POST/PUT/DELETE
# ---------------------------------------------------------------------------

class TestReadOnly:
    def test_no_post_on_runs(self, dq_client):
        r = dq_client.post("/api/v1/data-quality/runs", json={})
        assert r.status_code == 405

    def test_no_delete_on_findings(self, dq_client):
        r = dq_client.delete("/api/v1/data-quality/findings/some-id")
        assert r.status_code == 405
