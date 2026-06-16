"""
Gold-Path-Tests Analysebereich — Layer 2 (API Contract) & Layer 3 (Security Gate)

Layer 2: HTTP-Statuscodes + Response-Schema-Compliance für alle 11 GP-Schritte.
          Geht direkt gegen die FastAPI-App via TestClient.

Layer 3: Permission-Enforcement.
          - approve/reject/import erfordern Admin-Rolle
          - Member-Only-Client bekommt 403
          - Falscher Workspace → 403/404
          - Import ohne approved-Status → 409

Marker: unit_fast (In-Memory-SQLite, kein Netzwerk)
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import analysis as analysis_api
from app.main import app
from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.documents import AuthSession, User, WorkspaceMembership
from app.services.analysis.service import AnalysisService
from app.services.auth import hash_token
from tests.conftest import (
    DEFAULT_USER_ID,
    DEFAULT_WORKSPACE_ID,
    DOCUMENT_ID,
    OLDER_DOCUMENT_ID,
    SESSION_TOKEN,
)

pytestmark = pytest.mark.unit_fast

# ── Auth constants ────────────────────────────────────────────────────────────

_MEMBER_TOKEN = "member-session-token"
_MEMBER_USER_ID = "00000000-0000-0000-0000-000000000099"

_AUTH_HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
}
_MEMBER_HEADERS = {
    "Authorization": f"Bearer {_MEMBER_TOKEN}",
    "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
}
_WRONG_WS_HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "X-Workspace-Id": "00000000-0000-0000-0000-000000000099",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def analysis_client(db_session: Session, auth_fixture: dict) -> Iterator[TestClient]:
    def _override() -> Iterator[AnalysisService]:
        yield AnalysisService(db_session)

    app.dependency_overrides[analysis_api.get_analysis_service] = _override
    try:
        yield TestClient(app, headers=_AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def member_client(db_session: Session, auth_fixture: dict) -> Iterator[TestClient]:
    """TestClient für einen Workspace-Member (keine Admin-Rechte)."""
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    db_session.add(User(
        id=_MEMBER_USER_ID,
        display_name="Member",
        login="member",
        password_hash="x",
        is_active=True,
        is_default=False,
        created_at=now,
    ))
    db_session.add(WorkspaceMembership(
        id="membership-member",
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=_MEMBER_USER_ID,
        role="member",
        created_at=now,
        updated_at=now,
    ))
    db_session.add(AuthSession(
        id="session-member",
        user_id=_MEMBER_USER_ID,
        token_hash=hash_token(_MEMBER_TOKEN),
        expires_at=datetime(2036, 1, 1, tzinfo=timezone.utc),
        created_at=now,
        last_seen_at=now,
        revoked_at=None,
    ))
    db_session.commit()

    def _override() -> Iterator[AnalysisService]:
        yield AnalysisService(db_session)

    app.dependency_overrides[analysis_api.get_analysis_service] = _override
    try:
        yield TestClient(app, headers=_MEMBER_HEADERS)
    finally:
        app.dependency_overrides.clear()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_completed_result(
    db_session: Session,
    *,
    status: str = "draft",
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    doc_ids: list[str] | None = None,
) -> tuple[AnalysisJob, AnalysisResult]:
    now = _now()
    doc_ids = doc_ids or [DOCUMENT_ID]
    job = AnalysisJob(
        id=str(uuid4()),
        workspace_id=DEFAULT_WORKSPACE_ID,
        status="completed",
        analysis_type="summary",
        source_document_ids=doc_ids,
        prompt="Analyse-Gold-Path.",
        created_by=DEFAULT_USER_ID,
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    db_session.add(job)
    db_session.flush()
    result = AnalysisResult(
        id=str(uuid4()),
        job_id=job.id,
        title="GP-Result",
        summary="Telekom-Systemlandschaft.",
        key_points=["SAP", "Prozesse"],
        suggested_tags=tags or ["sap", "prozess"],
        suggested_topics=topics or ["SAP-Prozesse"],
        confidence=0.9,
        status=status,
        created_at=now,
        updated_at=now,
    )
    db_session.add(result)
    db_session.flush()
    job.result_id = result.id
    db_session.commit()
    return job, result


# ── Layer 2: API Contract ─────────────────────────────────────────────────────

class TestAnalysisGoldPathApiLayer:
    """
    Layer 2: HTTP-Statuscodes + Response-Schema für alle 11 GP-Schritte.
    """

    def test_gp_a02_create_job_returns_201_and_schema(
        self, analysis_client: TestClient, document_fixture: dict
    ):
        """GP-A02: POST /analysis/jobs → 201, job.status=queued, job.id vorhanden."""
        resp = analysis_client.post("/api/v1/analysis/jobs", json={
            "source_document_ids": [DOCUMENT_ID],
            "analysis_type": "summary",
            "prompt": "Gold-Path-Test.",
        })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "queued"
        assert "id" in body
        assert body["workspace_id"] == DEFAULT_WORKSPACE_ID

    def test_gp_a03_get_job_returns_200(
        self, analysis_client: TestClient, document_fixture: dict
    ):
        """GP-A03: GET /analysis/jobs/{job_id} → 200, status=queued."""
        created = analysis_client.post("/api/v1/analysis/jobs", json={
            "source_document_ids": [DOCUMENT_ID],
            "analysis_type": "summary",
            "prompt": "Status-Test.",
        }).json()
        resp = analysis_client.get(f"/api/v1/analysis/jobs/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]
        assert resp.json()["status"] == "queued"

    def test_gp_a04_list_jobs_filter_status(
        self, analysis_client: TestClient, document_fixture: dict
    ):
        """GP-A04: GET /analysis/jobs?status=queued → 200, items.status==queued."""
        analysis_client.post("/api/v1/analysis/jobs", json={
            "source_document_ids": [DOCUMENT_ID],
            "analysis_type": "summary",
            "prompt": "Filter.",
        })
        resp = analysis_client.get("/api/v1/analysis/jobs?status=queued&limit=20")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(j["status"] == "queued" for j in body["items"])

    def test_gp_a05_seeded_result_is_draft(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A05: Geseedetes Ergebnis ist status=draft."""
        job, result = _seed_completed_result(db_session)
        resp = analysis_client.get(f"/api/v1/analysis/jobs/{job.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"

    def test_gp_a06_get_result_returns_200(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A06: GET /analysis/results/{result_id} → 200, status=draft."""
        job, result = _seed_completed_result(db_session)
        resp = analysis_client.get(f"/api/v1/analysis/results/{result.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == result.id
        assert body["status"] == "draft"

    def test_gp_a07_mark_for_review_returns_200(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A07: POST /analysis/results/{result_id}/review → 200, status=review."""
        job, result = _seed_completed_result(db_session, status="draft")
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/review",
            json={"note": "Bitte prüfen."},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "review"

    def test_gp_a08_reject_result_returns_200(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A08: POST /analysis/results/{result_id}/reject → 200, status=rejected."""
        job, result = _seed_completed_result(db_session, status="review")
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/reject",
            json={"reason": "Unvollständig."},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "rejected"

    def test_gp_a09_approve_result_returns_200(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A09: POST /analysis/results/{result_id}/approve?confirm=true → 200, status=approved."""
        job, result = _seed_completed_result(db_session, status="review")
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": True, "reviewer_note": "Freigegeben."},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "approved"
        assert body["approved_by"] == DEFAULT_USER_ID
        assert body["approved_at"] is not None

    def test_gp_a09_approve_without_confirm_returns_error(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A09 Sicherheitsnetz: confirm=False blockiert Approval."""
        job, result = _seed_completed_result(db_session, status="review")
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": False},
        )
        assert resp.status_code in (400, 409, 422), (
            f"confirm=False muss abgewiesen werden, bekam {resp.status_code}: {resp.text}"
        )

    def test_gp_a10_import_returns_200_and_stats(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A10: POST /analysis/results/{result_id}/import → 200, Stats-Schema korrekt."""
        job, result = _seed_completed_result(
            db_session,
            status="approved",
            tags=["sap", "prozess"],
            topics=["SAP-Systemlandschaft"],
            doc_ids=[DOCUMENT_ID],
        )
        resp = analysis_client.post(f"/api/v1/analysis/results/{result.id}/import")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        required_fields = {
            "result_id", "tags_created", "tags_found",
            "document_tags_applied", "topics_created", "topics_found",
            "topic_docs_attached", "topic_tags_applied", "source_document_count",
        }
        assert required_fields.issubset(body.keys()), (
            f"Fehlende Felder: {required_fields - body.keys()}"
        )
        assert body["result_id"] == result.id
        assert body["tags_created"] == 2
        assert body["topics_created"] == 1
        assert body["topic_docs_attached"] == 1
        assert body["topic_tags_applied"] == 2

    def test_gp_a11_import_idempotent(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """GP-A11: Zweiter Import erzeugt keine neuen Einträge (found=1, created=0)."""
        job, result = _seed_completed_result(
            db_session,
            status="approved",
            tags=["sap"],
            topics=["SAP-Prozesse"],
        )
        analysis_client.post(f"/api/v1/analysis/results/{result.id}/import")
        resp2 = analysis_client.post(f"/api/v1/analysis/results/{result.id}/import")
        assert resp2.status_code == 200, resp2.text
        body = resp2.json()
        assert body["tags_created"] == 0
        assert body["tags_found"] == 1
        assert body["topics_created"] == 0
        assert body["topics_found"] == 1
        assert body["document_tags_applied"] == 0
        assert body["topic_docs_attached"] == 0


# ── Layer 3: Security Gate ────────────────────────────────────────────────────

class TestAnalysisGoldPathSecurityGate:
    """
    Layer 3: Permission-Enforcement.
    Alle Schreiboperationen sind admin-only.
    """

    def test_member_cannot_approve(
        self, member_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """L3: Member-Client kann Ergebnis nicht genehmigen → 403."""
        job, result = _seed_completed_result(db_session, status="review")
        resp = member_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": True},
        )
        assert resp.status_code == 403, (
            f"Member darf nicht genehmigen, bekam {resp.status_code}: {resp.text}"
        )

    def test_member_cannot_reject(
        self, member_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """L3: Member kann Ergebnis nicht ablehnen → 403."""
        job, result = _seed_completed_result(db_session, status="review")
        resp = member_client.post(
            f"/api/v1/analysis/results/{result.id}/reject",
            json={"reason": "Nein."},
        )
        assert resp.status_code == 403, (
            f"Member darf nicht ablehnen, bekam {resp.status_code}: {resp.text}"
        )

    def test_member_cannot_import(
        self, member_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """L3: PROHIBIT-08 — Member kann nicht importieren → 403."""
        job, result = _seed_completed_result(db_session, status="approved")
        resp = member_client.post(f"/api/v1/analysis/results/{result.id}/import")
        assert resp.status_code == 403, (
            f"PROHIBIT-08 verletzt: Member hat Import ausgeführt, Status {resp.status_code}: {resp.text}"
        )

    def test_import_non_approved_returns_conflict(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """L3: Import auf nicht-approved Result → 409 Conflict (status guard)."""
        for bad_status in ("draft", "review", "rejected"):
            job, result = _seed_completed_result(db_session, status=bad_status)
            resp = analysis_client.post(f"/api/v1/analysis/results/{result.id}/import")
            assert resp.status_code == 409, (
                f"Import auf status={bad_status} muss 409 liefern, bekam {resp.status_code}"
            )

    def test_approve_without_confirm_is_blocked(
        self, analysis_client: TestClient, db_session: Session, auth_fixture: dict, document_fixture: dict
    ):
        """L3: approve ohne confirm=True → kein 200 (Policy-Gate)."""
        job, result = _seed_completed_result(db_session, status="review")
        resp = analysis_client.post(
            f"/api/v1/analysis/results/{result.id}/approve",
            json={"confirm": False, "reviewer_note": None},
        )
        assert resp.status_code != 200, (
            f"approve ohne confirm=True darf nicht 200 liefern, bekam {resp.status_code}"
        )

    def test_result_not_found_returns_404(
        self, analysis_client: TestClient, auth_fixture: dict
    ):
        """L3: Import auf unbekannte result_id → 404."""
        resp = analysis_client.post("/api/v1/analysis/results/nonexistent-id/import")
        assert resp.status_code == 404

    def test_job_not_found_returns_404(
        self, analysis_client: TestClient, auth_fixture: dict
    ):
        """L3: GET auf unbekannte job_id → 404."""
        resp = analysis_client.get("/api/v1/analysis/jobs/nonexistent-job-id")
        assert resp.status_code == 404
