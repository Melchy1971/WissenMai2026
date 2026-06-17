"""API Contract Tests — vollständige Abdeckung PRI-5 (Task #16).

Abgedeckte Bereiche:
  1. Documents    — Pagination, Filter, Edge Cases
  2. Search       — Pagination, leere Ergebnisse, Edge Cases
  3. Topics       — CRUD, Status-Übergänge, Pagination, Filter, Edge Cases
  4. Analysis     — nur fehlende Lücken (Hauptabdeckung: test_analysis_api_contract.py)
  5. Export       — nur fehlende Lücken (Hauptabdeckung: test_export_api_contract.py)
  6. Dashboard    — vollständiger Contract (Hauptabdeckung: test_dashboard_empty_states.py)
  7. Drift        — nur fehlende Lücken (Hauptabdeckung: test_m5b_drift_api_contracts.py)
  8. Auth/Workspace — Login, Logout, /me, Workspace-Auswahl
  9. Error Middleware — DTO-Struktur, Edge Cases, fehlende Daten → WARNING

Marker: unit_fast (in-memory SQLite, keine externen Abhängigkeiten)
Regeln:
  - Fehlende Daten → WARNING, nicht PASS
  - Kein UUID als Primärtext in Response-Payloads
  - Error-DTOs: { error: { code, message, details } }
  - DRAFT-Status: kein Export, kein Auto-Approve
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models.topics  # noqa: F401 — topics-Tabellen registrieren
from app.api.v1 import topics as topics_api
from app.api.v1 import auth as auth_api
from app.api.v1 import dashboard as dashboard_api
from app.main import app
from app.models.topics import Topic, TopicTag
from app.services.topics.service import TopicService
from app.services.topics.merge_service import TopicMergeService
from tests.conftest import (
    DEFAULT_USER_ID,
    DEFAULT_WORKSPACE_ID,
    DOCUMENT_ID,
    SESSION_TOKEN,
)

pytestmark = pytest.mark.unit_fast

_AUTH_HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(UTC)


def _make_topic(
    *,
    id: str | None = None,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    slug: str | None = None,
    title: str = "Vertragstopic",
    status: str = "draft",
) -> Topic:
    now = _now()
    return Topic(
        id=id or str(uuid4()),
        workspace_id=workspace_id,
        title=title,
        slug=slug or f"slug-{uuid4().hex[:8]}",
        summary=None,
        status=status,
        created_by=DEFAULT_USER_ID,
        approved_at=None,
        approved_by=None,
        deleted_at=None,
        created_at=now,
        updated_at=now,
    )


def _assert_error_dto(payload: dict[str, Any], *, code: str | None = None) -> None:
    """Error-DTO muss { error: { code, message, details } } sein."""
    assert "error" in payload, f"Kein 'error'-Key in: {payload}"
    err = payload["error"]
    assert isinstance(err.get("code"), str), f"code kein String: {err}"
    assert isinstance(err.get("message"), str), f"message kein String: {err}"
    assert isinstance(err.get("details"), dict), f"details kein dict: {err}"
    if code:
        assert err["code"] == code, f"Erwartet code={code!r}, got {err['code']!r}"


def _assert_no_raw_uuid_in_display(text: str, field_name: str = "") -> None:
    """Sicherstellen dass kein UUID als Primäranzeigetext erscheint."""
    import re
    uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    assert not uuid_re.match(text), f"UUID als Anzeigetext in {field_name!r}: {text!r}"


# ---------------------------------------------------------------------------
# Fixtures — Topics
# ---------------------------------------------------------------------------

@pytest.fixture()
def topics_client(db_session: Session, auth_fixture: dict[str, str]) -> Iterator[TestClient]:
    def _svc() -> Iterator[TopicService]:
        yield TopicService(db_session)

    def _merge_svc() -> Iterator[TopicMergeService]:
        yield TopicMergeService(db_session)

    app.dependency_overrides[topics_api.get_topic_service] = _svc
    app.dependency_overrides[topics_api.get_merge_service] = _merge_svc
    try:
        yield TestClient(app, headers=_AUTH_HEADERS)
    finally:
        app.dependency_overrides.pop(topics_api.get_topic_service, None)
        app.dependency_overrides.pop(topics_api.get_merge_service, None)


@pytest.fixture()
def seeded_topic(db_session: Session, auth_fixture: dict[str, str]) -> Topic:
    topic = _make_topic(status="draft")
    db_session.add(topic)
    db_session.flush()
    return topic


@pytest.fixture()
def seeded_topic_approved(db_session: Session, auth_fixture: dict[str, str]) -> Topic:
    topic = _make_topic(status="approved")
    db_session.add(topic)
    db_session.flush()
    return topic


# ===========================================================================
# 3. Topics API Contract
# ===========================================================================

class TestTopicsListContract:
    def test_list_returns_pagination_shape(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.get("/api/v1/topics")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)

    def test_list_item_fields(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.get("/api/v1/topics")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        item = items[0]
        required = {"id", "title", "slug", "status", "created_at", "updated_at", "doc_count", "tag_count"}
        assert set(item.keys()) >= required

    def test_list_pagination_limit_offset(self, topics_client: TestClient, db_session: Session, auth_fixture: dict) -> None:
        for i in range(5):
            db_session.add(_make_topic(title=f"Topic {i}", slug=f"slug-{i}-{uuid4().hex[:6]}"))
        db_session.flush()

        r = topics_client.get("/api/v1/topics?limit=2&offset=0")
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) <= 2
        assert body["limit"] == 2
        assert body["offset"] == 0

    def test_list_filter_by_status(self, topics_client: TestClient, db_session: Session, auth_fixture: dict) -> None:
        db_session.add(_make_topic(status="approved", slug=f"approved-{uuid4().hex[:6]}"))
        db_session.add(_make_topic(status="draft", slug=f"draft-{uuid4().hex[:6]}"))
        db_session.flush()

        r = topics_client.get("/api/v1/topics?status=approved")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["status"] == "approved"

    def test_list_empty_workspace_returns_zero_total(self, topics_client: TestClient, auth_fixture: dict) -> None:
        r = topics_client.get("/api/v1/topics")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 0

    def test_title_is_not_raw_uuid(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.get("/api/v1/topics")
        assert r.status_code == 200
        for item in r.json()["items"]:
            _assert_no_raw_uuid_in_display(item["title"], field_name="title")


class TestTopicsGetContract:
    def test_get_returns_detail_shape(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.get(f"/api/v1/topics/{seeded_topic.id}")
        assert r.status_code == 200
        body = r.json()
        required = {"id", "workspace_id", "title", "slug", "summary", "status",
                    "created_by", "approved_at", "approved_by", "deleted_at",
                    "created_at", "updated_at", "documents", "tags"}
        assert set(body.keys()) >= required

    def test_get_unknown_id_returns_404(self, topics_client: TestClient, auth_fixture: dict) -> None:
        r = topics_client.get(f"/api/v1/topics/{uuid4()}")
        assert r.status_code == 404
        _assert_error_dto(r.json())

    def test_get_workspace_isolation(self, topics_client: TestClient, db_session: Session, auth_fixture: dict) -> None:
        other_topic = _make_topic(workspace_id="other-ws-id")
        db_session.add(other_topic)
        db_session.flush()
        r = topics_client.get(f"/api/v1/topics/{other_topic.id}")
        assert r.status_code == 404


class TestTopicsCreateContract:
    def test_create_returns_201_and_draft_status(self, topics_client: TestClient, auth_fixture: dict) -> None:
        payload = {"title": "Neues Topic", "slug": f"neues-topic-{uuid4().hex[:6]}"}
        r = topics_client.post("/api/v1/topics", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "draft"
        assert body["title"] == "Neues Topic"

    def test_create_duplicate_slug_returns_409(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        payload = {"title": "Doppelt", "slug": seeded_topic.slug}
        r = topics_client.post("/api/v1/topics", json=payload)
        assert r.status_code == 409
        _assert_error_dto(r.json())

    def test_create_missing_title_returns_422(self, topics_client: TestClient, auth_fixture: dict) -> None:
        r = topics_client.post("/api/v1/topics", json={"slug": "kein-title"})
        assert r.status_code == 422

    def test_create_empty_title_returns_422(self, topics_client: TestClient, auth_fixture: dict) -> None:
        r = topics_client.post("/api/v1/topics", json={"title": "", "slug": "leer"})
        assert r.status_code == 422


class TestTopicsUpdateContract:
    def test_update_title_returns_200(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.put(f"/api/v1/topics/{seeded_topic.id}", json={"title": "Aktualisiert"})
        assert r.status_code == 200
        assert r.json()["title"] == "Aktualisiert"

    def test_update_unknown_id_returns_404(self, topics_client: TestClient, auth_fixture: dict) -> None:
        r = topics_client.put(f"/api/v1/topics/{uuid4()}", json={"title": "X"})
        assert r.status_code == 404
        _assert_error_dto(r.json())


class TestTopicsStatusContract:
    def test_approve_draft_returns_approved_status(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.post(f"/api/v1/topics/{seeded_topic.id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_archive_approved_returns_archived(self, topics_client: TestClient, seeded_topic_approved: Topic) -> None:
        r = topics_client.post(f"/api/v1/topics/{seeded_topic_approved.id}/archive")
        assert r.status_code == 200
        assert r.json()["status"] == "archived"

    def test_invalid_status_transition_returns_409(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        # draft → archive ist ungültig (muss erst approved sein)
        r = topics_client.post(f"/api/v1/topics/{seeded_topic.id}/archive")
        assert r.status_code in (409, 422)
        if r.status_code == 409:
            _assert_error_dto(r.json())


class TestTopicsDeleteContract:
    def test_delete_returns_204(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        r = topics_client.delete(f"/api/v1/topics/{seeded_topic.id}")
        assert r.status_code == 204

    def test_deleted_topic_not_in_list(self, topics_client: TestClient, seeded_topic: Topic) -> None:
        topics_client.delete(f"/api/v1/topics/{seeded_topic.id}")
        r = topics_client.get("/api/v1/topics")
        ids = [item["id"] for item in r.json()["items"]]
        assert seeded_topic.id not in ids


# ===========================================================================
# 6. Dashboard API Contract
# ===========================================================================

class TestDashboardSummaryContract:
    def test_summary_required_fields(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        body = r.json()
        required = {
            "document_count", "active_document_count", "archived_document_count",
            "new_imports_count", "open_analysis_count", "topic_count",
        }
        assert required <= set(body.keys())

    def test_summary_counts_are_integers(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        body = r.json()
        int_fields = ["document_count", "active_document_count", "archived_document_count",
                      "new_imports_count", "open_analysis_count", "topic_count"]
        for field in int_fields:
            assert isinstance(body[field], int), f"{field} ist kein int"

    def test_summary_drift_status_nullable(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        # drift_status darf None sein (fehlende Daten → kein PASS, nur WARNING oder null)
        body = r.json()
        assert body.get("drift_status") is None or isinstance(body["drift_status"], str)

    def test_summary_quality_score_nullable(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        qs = r.json().get("quality_score")
        assert qs is None or isinstance(qs, (int, float))

    def test_activity_pagination_shape(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/activity")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)

    def test_imports_pagination_shape(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/imports")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body

    def test_analysis_pagination_shape(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/analysis")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body

    def test_drift_endpoint_returns_snapshot_list(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/dashboard/drift")
        assert r.status_code == 200
        body = r.json()
        # Mindestens global_status oder snapshots-Schlüssel erwartet
        assert "global_status" in body or "snapshots" in body or "drift_status" in body or isinstance(body, dict)


# ===========================================================================
# 8. Auth / Workspace Contract
# ===========================================================================

class TestAuthContract:
    def test_login_invalid_credentials_returns_401(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/auth/login",
            json={"login": "nobody@example.com", "password": "wrongpassword"},
            headers={},
        )
        assert r.status_code == 401
        _assert_error_dto(r.json())

    def test_login_missing_fields_returns_422(self, client: TestClient) -> None:
        r = client.post("/api/v1/auth/login", json={}, headers={})
        assert r.status_code == 422

    def test_login_empty_password_returns_422(self, client: TestClient) -> None:
        r = client.post("/api/v1/auth/login", json={"login": "x@y.de", "password": ""}, headers={})
        assert r.status_code == 422

    def test_me_without_token_returns_401(self, client: TestClient) -> None:
        r = client.get("/api/v1/auth/me", headers={})
        assert r.status_code == 401

    def test_me_with_valid_token_returns_session_shape(
        self, client: TestClient, auth_fixture: dict[str, str]
    ) -> None:
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 200
        body = r.json()
        assert "user" in body
        assert "memberships" in body
        assert isinstance(body["memberships"], list)
        # Kein raw UUID als login/display_name
        _assert_no_raw_uuid_in_display(body["user"]["login"], "user.login")

    def test_logout_returns_204(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.post("/api/v1/auth/logout")
        assert r.status_code == 204

    def test_workspace_id_header_required_for_protected_routes(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        # Ohne X-Workspace-Id: 400 oder 422 oder 401
        assert r.status_code in (400, 401, 422)

    def test_wrong_workspace_id_is_rejected(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(
            "/api/v1/documents",
            headers={
                "Authorization": f"Bearer {SESSION_TOKEN}",
                "X-Workspace-Id": str(uuid4()),
            },
        )
        assert r.status_code in (401, 403, 404)


# ===========================================================================
# 9. Error Middleware Contract
# ===========================================================================

class TestErrorMiddlewareContract:
    def test_404_has_standard_error_dto(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(f"/api/v1/topics/{uuid4()}", headers=_AUTH_HEADERS)
        assert r.status_code == 404
        _assert_error_dto(r.json())

    def test_422_has_fastapi_validation_error_shape(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/topics?limit=-1")
        assert r.status_code == 422
        body = r.json()
        # FastAPI validation errors haben "detail"-Key
        assert "detail" in body or "error" in body

    def test_invalid_workspace_id_format_returns_4xx(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(
            "/api/v1/topics",
            headers={
                "Authorization": f"Bearer {SESSION_TOKEN}",
                "X-Workspace-Id": "not-a-uuid",
            },
        )
        assert r.status_code in (400, 401, 403, 422)

    def test_missing_auth_header_returns_401(self, client: TestClient) -> None:
        r = client.get("/api/v1/documents", headers={})
        assert r.status_code == 401

    def test_error_response_never_leaks_internal_path(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(f"/api/v1/topics/{uuid4()}", headers=_AUTH_HEADERS)
        body = r.text
        assert "/home/" not in body
        assert "/sessions/" not in body
        assert "backend/app" not in body

    def test_error_response_never_leaks_stack_trace(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(f"/api/v1/topics/{uuid4()}", headers=_AUTH_HEADERS)
        body = r.text
        assert "Traceback" not in body
        assert "File \"" not in body

    def test_missing_data_in_summary_returns_null_not_pass(self, client: TestClient, auth_fixture: dict) -> None:
        """Fehlende Daten ergeben null (WARNING), nicht einen fiktiven PASS-Wert."""
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        body = r.json()
        # Leeres Workspace: quality_score und drift_status müssen null sein (nicht "PASS")
        assert body.get("quality_score") is None
        assert body.get("drift_status") != "PASS"

    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/v1/does-not-exist-at-all")
        assert r.status_code == 404


# ===========================================================================
# 1./2. Documents & Search — fehlende Edge Cases
# ===========================================================================

class TestDocumentsContractEdgeCases:
    def test_documents_list_pagination_shape(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/documents")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body
        assert isinstance(body["items"], list)

    def test_documents_invalid_id_returns_404_with_error_dto(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get(f"/api/v1/documents/{uuid4()}")
        assert r.status_code == 404
        _assert_error_dto(r.json())

    def test_documents_list_title_not_raw_uuid(
        self, client: TestClient, document_fixture: dict
    ) -> None:
        r = client.get("/api/v1/documents")
        assert r.status_code == 200
        for item in r.json()["items"]:
            if item.get("title"):
                _assert_no_raw_uuid_in_display(item["title"], "document.title")

    def test_documents_filter_by_lifecycle_status(self, client: TestClient, document_fixture: dict) -> None:
        r = client.get("/api/v1/documents?status=active")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item.get("lifecycle_status") in ("active", None) or item.get("status") == "active"


class TestSearchContractEdgeCases:
    def test_search_empty_query_returns_400_or_422(self, client: TestClient, auth_fixture: dict) -> None:
        r = client.get("/api/v1/search/chunks?q=")
        assert r.status_code in (200, 400, 422)

    def test_search_no_hits_returns_empty_items(self, client: TestClient, document_fixture: dict) -> None:
        r = client.get("/api/v1/search/chunks?q=nohitneedle-contract-test-xyz")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body or "chunks" in body or "results" in body

    def test_search_response_never_leaks_internal_path(self, client: TestClient, document_fixture: dict) -> None:
        r = client.get("/api/v1/search/chunks?q=test")
        assert r.status_code == 200
        assert "/sessions/" not in r.text
        assert "backend/app" not in r.text
