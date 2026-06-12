"""Drift API Contract Tests.

Validates the API contracts defined in drift_api_contract_registry.json.
Tests that actual API responses conform to declared required fields,
enum constraints, pagination structure, and error codes.
"""
from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

_mock_auth_svc = MagicMock()

@dataclass(frozen=True)
class _FakeAuthContext:
    session_id: str
    user_id: str
    login: str
    display_name: str
    workspace_id: str
    role: str

_mock_auth_svc.AuthenticatedContext = _FakeAuthContext
sys.modules.setdefault("app.services.auth", _mock_auth_svc)
_mock_db = MagicMock()
_mock_db.DatabaseConfigurationError = RuntimeError
sys.modules.setdefault("app.core.database", _mock_db)
sys.modules.setdefault("psycopg", MagicMock())
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
from app.models.drift import DriftFinding, DriftRun

UTC = timezone.utc
WS_ID = "ws-contract-001"
USER_ID = "user-contract-001"

REGISTRY_PATH = Path(__file__).parent.parent.parent / "reports" / "current" / "drift_api_contract_registry.json"


@pytest.fixture(scope="module")
def registry():
    with open(REGISTRY_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(eng, "connect")
    def _fk(conn, _): conn.execute("PRAGMA foreign_keys=ON")
    DocBase.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="module")
def seeded_db(engine):
    with Session(engine) as s:
        s.add(Workspace(id=WS_ID, name="Contract WS", is_default=True, created_at=datetime.now(UTC)))
        run = DriftRun(
            id=str(uuid.uuid4()), workspace_id=WS_ID, status="completed",
            triggered_by="test", detector_names=["DocumentDriftDetector"],
            started_at=datetime.now(UTC), completed_at=datetime.now(UTC),
            total_findings=2, created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        s.add(run)
        s.flush()
        s.add(DriftFinding(
            id=str(uuid.uuid4()), run_id=run.id, workspace_id=WS_ID,
            finding_type="DOCUMENT_DRIFT", severity="error",
            entity_type="document", entity_id=str(uuid.uuid4()),
            detail={"reason": "orphaned"}, created_at=datetime.now(UTC),
        ))
        s.add(DriftFinding(
            id=str(uuid.uuid4()), run_id=run.id, workspace_id=WS_ID,
            finding_type="METADATA_DRIFT", severity="warning",
            entity_type="document", entity_id=str(uuid.uuid4()),
            detail={"missing_field": "title"}, created_at=datetime.now(UTC),
        ))
        s.commit()
        yield s, run.id


def _make_client(engine) -> TestClient:
    app = FastAPI()
    app.include_router(drift_router, prefix="/api/v1")
    def _sess():
        with Session(engine) as s: yield s
    def _auth():
        return AuthContext(
            session_id="sess", user_id=USER_ID, login="u", display_name="U",
            workspace_id=WS_ID, role="member", permissions=("workspace:read",),
        )
    app.dependency_overrides[get_db_session] = _sess
    app.dependency_overrides[get_current_auth_context] = _auth
    return TestClient(app)


# ---------------------------------------------------------------------------
# C-01: DriftRunListResponse
# ---------------------------------------------------------------------------

class TestContractRunList:
    def test_required_fields_present(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs")
        assert resp.status_code == 200
        data = resp.json()
        required = registry["contracts"]["DriftRunListResponse"]["response_schema"]["required_fields"]
        for field in required:
            assert field in data, f"Missing required field: {field}"

    def test_items_required_fields(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs")
        data = resp.json()
        assert len(data["items"]) > 0
        item_required = registry["contracts"]["DriftRunListResponse"]["response_schema"]["items_schema"]["required_fields"]
        for item in data["items"]:
            for field in item_required:
                assert field in item, f"Item missing required field: {field}"

    def test_pagination_fields(self, seeded_db, engine):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs?limit=5&offset=0")
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert isinstance(data["total"], int)

    def test_limit_max_422(self, seeded_db, engine):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs?limit=999")
        assert resp.status_code == 422

    def test_status_filter_valid(self, seeded_db, engine):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs?status=completed")
        assert resp.status_code == 200

    def test_no_repair_fields_in_response(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs")
        body = resp.text.lower()
        forbidden = registry["contracts"]["DriftRunListResponse"]["forbidden_response_fields"]
        for f in forbidden:
            assert f not in body, f"Forbidden field \"{f}\" in response"


# ---------------------------------------------------------------------------
# C-02: DriftRunDetailResponse
# ---------------------------------------------------------------------------

class TestContractRunDetail:
    def test_required_fields_present(self, seeded_db, engine, registry):
        _, run_id = seeded_db
        client = _make_client(engine)
        resp = client.get(f"/api/v1/drift/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        required = registry["contracts"]["DriftRunDetailResponse"]["response_schema"]["required_fields"]
        for field in required:
            assert field in data, f"Missing required field: {field}"

    def test_findings_by_type_is_dict(self, seeded_db, engine):
        _, run_id = seeded_db
        client = _make_client(engine)
        data = client.get(f"/api/v1/drift/runs/{run_id}").json()
        assert isinstance(data["findings_by_type"], dict)
        assert isinstance(data["findings_by_severity"], dict)

    def test_404_wrong_id(self, seeded_db, engine):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs/no-such-run")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# C-03: DriftFindingListResponse
# ---------------------------------------------------------------------------

class TestContractFindingList:
    def test_required_fields_present(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/findings")
        assert resp.status_code == 200
        data = resp.json()
        required = registry["contracts"]["DriftFindingListResponse"]["response_schema"]["required_fields"]
        for field in required:
            assert field in data

    def test_items_required_fields(self, seeded_db, engine, registry):
        client = _make_client(engine)
        data = client.get("/api/v1/drift/findings").json()
        assert len(data["items"]) > 0
        item_required = registry["contracts"]["DriftFindingListResponse"]["response_schema"]["items_schema"]["required_fields"]
        for item in data["items"]:
            for field in item_required:
                assert field in item

    def test_invalid_severity_422(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/findings?severity=INVALID")
        expected_code = registry["contracts"]["DriftFindingListResponse"]["query_params"]["severity"]["error_code"]
        assert resp.status_code == expected_code

    def test_invalid_finding_type_422(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/findings?finding_type=NOT_A_TYPE")
        expected_code = registry["contracts"]["DriftFindingListResponse"]["query_params"]["finding_type"]["error_code"]
        assert resp.status_code == expected_code

    def test_severity_enum_values(self, seeded_db, engine, registry):
        client = _make_client(engine)
        valid_severities = registry["enum_registry"]["severity"]
        for sev in valid_severities:
            resp = client.get(f"/api/v1/drift/findings?severity={sev}")
            assert resp.status_code == 200, f"Valid severity {sev!r} rejected"


# ---------------------------------------------------------------------------
# C-04: DriftSummaryResponse
# ---------------------------------------------------------------------------

class TestContractSummary:
    def test_required_fields_present(self, seeded_db, engine, registry):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/summary")
        assert resp.status_code == 200
        data = resp.json()
        required = registry["contracts"]["DriftSummaryResponse"]["response_schema"]["required_fields"]
        for field in required:
            assert field in data

    def test_counts_are_integers(self, seeded_db, engine):
        client = _make_client(engine)
        data = client.get("/api/v1/drift/summary").json()
        assert isinstance(data["total_runs"], int)
        assert isinstance(data["total_findings"], int)
        assert isinstance(data["critical_count"], int)
        assert isinstance(data["error_count"], int)

    def test_empty_workspace_nulls(self, engine, registry):
        ws_empty = "ws-contract-empty-" + str(uuid.uuid4())[:8]
        with Session(engine) as s:
            s.add(Workspace(id=ws_empty, name="Empty", is_default=False, created_at=datetime.now(UTC)))
            s.commit()
        app = FastAPI()
        app.include_router(drift_router, prefix="/api/v1")
        def _sess():
            with Session(engine) as s: yield s
        def _auth():
            return AuthContext(
                session_id="s", user_id="u", login="u", display_name="u",
                workspace_id=ws_empty, role="member", permissions=("workspace:read",),
            )
        app.dependency_overrides[get_db_session] = _sess
        app.dependency_overrides[get_current_auth_context] = _auth
        data = TestClient(app).get("/api/v1/drift/summary").json()
        null_fields = registry["contracts"]["DriftSummaryResponse"]["response_schema"]["null_when_no_runs"]
        for field in null_fields:
            assert data[field] is None, f"{field} should be null when no runs"


# ---------------------------------------------------------------------------
# C-05: DriftErrorResponse + Method Constraints
# ---------------------------------------------------------------------------

class TestContractErrorResponse:
    def test_405_on_post_runs(self, seeded_db, engine):
        client = _make_client(engine)
        assert client.post("/api/v1/drift/runs", json={}).status_code == 405

    def test_405_on_delete_run(self, seeded_db, engine):
        client = _make_client(engine)
        assert client.delete("/api/v1/drift/runs/any").status_code == 405

    def test_404_on_patch_finding(self, seeded_db, engine):
        client = _make_client(engine)
        assert client.patch("/api/v1/drift/findings/any", json={}).status_code == 404

    def test_detail_field_in_error(self, seeded_db, engine):
        client = _make_client(engine)
        resp = client.get("/api/v1/drift/runs/nonexistent-run-id")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
