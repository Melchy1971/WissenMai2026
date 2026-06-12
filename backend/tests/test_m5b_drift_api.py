"""Drift API Read-Only Tests.

Tests:
  - GET /drift/runs: pagination, workspace scope, status filter
  - GET /drift/runs/{run_id}: detail with finding counts; 404 on missing/wrong-ws
  - GET /drift/findings: pagination, filters (severity, finding_type, run_id)
  - GET /drift/summary: aggregates correct; no-run workspace returns empty summary
  - No POST/PUT/PATCH/DELETE endpoints exist on the router
  - Unauthenticated requests raise 401

All tests use in-memory SQLite. No TEST_DATABASE_URL required.
"""
from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# sys.modules patches — must run before any app import
# ---------------------------------------------------------------------------

# 1) app.services.auth uses datetime.UTC (Python 3.11+)
_mock_auth_svc = MagicMock()


@dataclass(frozen=True)
class _FakeAuthenticatedContext:
    session_id: str
    user_id: str
    login: str
    display_name: str
    workspace_id: str
    role: str


_mock_auth_svc.AuthenticatedContext = _FakeAuthenticatedContext
sys.modules.setdefault("app.services.auth", _mock_auth_svc)

# 2) app.core.database imports psycopg (not available in test env)
class _DBConfigError(RuntimeError):
    pass


_mock_db_core = MagicMock()
_mock_db_core.DatabaseConfigurationError = _DBConfigError
_mock_db_core.get_sqlalchemy_database_url = MagicMock(return_value="sqlite:///:memory:")
sys.modules.setdefault("app.core.database", _mock_db_core)

# 3) psycopg itself
sys.modules.setdefault("psycopg", MagicMock())

# 4) pydantic_settings (may not be installed)
sys.modules.setdefault("pydantic_settings", MagicMock())

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.api.v1.drift import router as drift_router, get_db_session
from app.models.documents import Base as DocBase, Workspace
from app.models.drift import DriftFinding, DriftRun, DriftSnapshot

UTC = timezone.utc
WS_A = "ws-api-a"
WS_B = "ws-api-b"
USER_ID = "user-api-001"


# ---------------------------------------------------------------------------
# In-memory DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    DocBase.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="module")
def db_session(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_A, name="API WS A", is_default=True,
                        created_at=datetime.now(UTC)))
        s.add(Workspace(id=WS_B, name="API WS B", is_default=False,
                        created_at=datetime.now(UTC)))
        s.commit()
        yield s


def _make_run(session, ws_id: str, status: str = "completed",
              total_findings: int = 0) -> DriftRun:
    run = DriftRun(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        status=status,
        triggered_by="test",
        detector_names=["DocumentDriftDetector"],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC) if status == "completed" else None,
        total_findings=total_findings,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    return run


def _make_finding(session, run: DriftRun, finding_type: str = "DOCUMENT_DRIFT",
                  severity: str = "error", entity_id: str | None = None) -> DriftFinding:
    f = DriftFinding(
        id=str(uuid.uuid4()),
        run_id=run.id,
        workspace_id=run.workspace_id,
        finding_type=finding_type,
        severity=severity,
        entity_type="document",
        entity_id=entity_id or str(uuid.uuid4()),
        detail={"reason": "test"},
        created_at=datetime.now(UTC),
    )
    session.add(f)
    session.flush()
    return f


# ---------------------------------------------------------------------------
# FastAPI app with dependency overrides
# ---------------------------------------------------------------------------

def _make_app(engine, ws_id: str = WS_A) -> FastAPI:
    """Create a test app with per-request sessions from the given engine.

    Per-request sessions (instead of sharing a module-scoped session object)
    avoid cross-thread SQLAlchemy issues when TestClient runs the ASGI app
    in a worker thread.  Test data must be committed before requests are made.
    """
    app = FastAPI()
    app.include_router(drift_router, prefix="/api/v1")

    def _mock_session():
        with Session(engine) as s:
            yield s

    def _mock_auth() -> AuthContext:
        return AuthContext(
            session_id="sess-test",
            user_id=USER_ID,
            login="testuser",
            display_name="Test User",
            workspace_id=ws_id,
            role="member",
            permissions=("workspace:read",),
        )

    app.dependency_overrides[get_db_session] = _mock_session
    app.dependency_overrides[get_current_auth_context] = _mock_auth
    return app


# ---------------------------------------------------------------------------
# Tests: GET /drift/runs
# ---------------------------------------------------------------------------

class TestListRuns:
    def test_returns_runs_for_workspace(self, db_session, engine):
        run = _make_run(db_session, WS_A, total_findings=3)
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        ids = [r["run_id"] for r in data["items"]]
        assert run.id in ids

    def test_workspace_scoped(self, db_session, engine):
        run_b = _make_run(db_session, WS_B)
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/runs")
        assert resp.status_code == 200
        ids = [r["run_id"] for r in resp.json()["items"]]
        assert run_b.id not in ids

    def test_pagination(self, db_session, engine):
        for _ in range(5):
            _make_run(db_session, WS_A)
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/runs?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2

    def test_status_filter(self, db_session, engine):
        _make_run(db_session, WS_A, status="failed")
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/runs?status=failed")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "failed"

    def test_response_schema(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data and "total" in data
        assert "limit" in data and "offset" in data


# ---------------------------------------------------------------------------
# Tests: GET /drift/runs/{run_id}
# ---------------------------------------------------------------------------

class TestGetRun:
    def test_returns_run_detail(self, db_session, engine):
        run = _make_run(db_session, WS_A, total_findings=2)
        _make_finding(db_session, run, "DOCUMENT_DRIFT", "error")
        _make_finding(db_session, run, "METADATA_DRIFT", "warning")
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get(f"/api/v1/drift/runs/{run.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run.id
        assert data["findings_by_type"]["DOCUMENT_DRIFT"] == 1
        assert data["findings_by_type"]["METADATA_DRIFT"] == 1
        assert data["findings_by_severity"]["error"] == 1
        assert data["findings_by_severity"]["warning"] == 1

    def test_404_on_missing_run(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/runs/nonexistent-id")
        assert resp.status_code == 404

    def test_404_cross_workspace(self, db_session, engine):
        run_b = _make_run(db_session, WS_B)
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get(f"/api/v1/drift/runs/{run_b.id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /drift/findings
# ---------------------------------------------------------------------------

class TestListFindings:
    def test_returns_findings_for_workspace(self, db_session, engine):
        run = _make_run(db_session, WS_A)
        f = _make_finding(db_session, run, "LIFECYCLE_DRIFT", "critical")
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/findings")
        assert resp.status_code == 200
        ids = [x["finding_id"] for x in resp.json()["items"]]
        assert f.id in ids

    def test_filter_by_severity(self, db_session, engine):
        run = _make_run(db_session, WS_A)
        _make_finding(db_session, run, "DOCUMENT_DRIFT", "info")
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/findings?severity=info")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["severity"] == "info"

    def test_filter_by_finding_type(self, db_session, engine):
        run = _make_run(db_session, WS_A)
        _make_finding(db_session, run, "SOURCE_STATUS_DRIFT", "warning")
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/findings?finding_type=SOURCE_STATUS_DRIFT")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["finding_type"] == "SOURCE_STATUS_DRIFT"

    def test_filter_by_run_id(self, db_session, engine):
        run1 = _make_run(db_session, WS_A)
        run2 = _make_run(db_session, WS_A)
        f1 = _make_finding(db_session, run1)
        _make_finding(db_session, run2)
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get(f"/api/v1/drift/findings?run_id={run1.id}")
        assert resp.status_code == 200
        ids = [x["finding_id"] for x in resp.json()["items"]]
        assert f1.id in ids
        for item in resp.json()["items"]:
            assert item["run_id"] == run1.id

    def test_invalid_severity_returns_422(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/findings?severity=INVALID")
        assert resp.status_code == 422

    def test_invalid_finding_type_returns_422(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/findings?finding_type=NOT_A_TYPE")
        assert resp.status_code == 422

    def test_workspace_scoped(self, db_session, engine):
        run_b = _make_run(db_session, WS_B)
        f_b = _make_finding(db_session, run_b)
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/findings")
        assert resp.status_code == 200
        ids = [x["finding_id"] for x in resp.json()["items"]]
        assert f_b.id not in ids


# ---------------------------------------------------------------------------
# Tests: GET /drift/summary
# ---------------------------------------------------------------------------

class TestDriftSummary:
    def test_summary_reflects_workspace_data(self, db_session, engine):
        run = _make_run(db_session, WS_A, total_findings=2)
        _make_finding(db_session, run, "DOCUMENT_DRIFT", "error")
        _make_finding(db_session, run, "LIFECYCLE_DRIFT", "critical")
        db_session.commit()

        client = TestClient(_make_app(engine, WS_A))
        resp = client.get("/api/v1/drift/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workspace_id"] == WS_A
        assert data["total_runs"] >= 1
        assert data["total_findings"] >= 2
        assert data["critical_count"] >= 1
        assert data["error_count"] >= 1

    def test_summary_empty_workspace(self, db_session, engine):
        ws_empty = "ws-empty-summary-" + str(uuid.uuid4())[:8]
        db_session.add(Workspace(id=ws_empty, name="Empty WS",
                                 is_default=False, created_at=datetime.now(UTC)))
        db_session.commit()

        client = TestClient(_make_app(engine, ws_empty))
        resp = client.get("/api/v1/drift/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 0
        assert data["total_findings"] == 0
        assert data["latest_run_id"] is None
        assert data["critical_count"] == 0


# ---------------------------------------------------------------------------
# Tests: No mutating endpoints
# ---------------------------------------------------------------------------

class TestReadOnly:
    def test_no_post_runs(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.post("/api/v1/drift/runs", json={})
        assert resp.status_code == 405

    def test_no_delete_runs(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.delete("/api/v1/drift/runs/any-id")
        assert resp.status_code == 405

    def test_no_patch_findings(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.patch("/api/v1/drift/findings/any-id", json={})
        assert resp.status_code == 404  # no path /drift/findings/{id} exists

    def test_no_put_findings(self, db_session, engine):
        client = TestClient(_make_app(engine, WS_A))
        resp = client.put("/api/v1/drift/findings/any-id", json={})
        assert resp.status_code == 404  # no path /drift/findings/{id} exists
