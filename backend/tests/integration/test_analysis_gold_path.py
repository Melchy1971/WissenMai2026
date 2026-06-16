"""
Gold-Path-Tests Analysebereich — Layer 1 & 4 (Service-Layer E2E + KB-Verifikation)

11 Schritte des Analyse-Gold-Paths, ausgeführt direkt gegen die Service-Schicht:

  GP-A01  Dokument im Workspace vorhanden
  GP-A02  Analyse-Job anlegen
  GP-A03  Job-Status abrufen (queued)
  GP-A04  Job-Liste filtern (status=queued)
  GP-A05  KI-Ergebnis einbuchen (completed + Result)
  GP-A06  Ergebnis abrufen (draft)
  GP-A07  Zur Prüfung einreichen (draft → review)
  GP-A08  Ergebnis ablehnen (review → rejected)
  GP-A09  Erneut zur Prüfung + Genehmigen (draft→review→approved)
  GP-A10  In Wissensbasis importieren
  GP-A11  Wissensbasis-Verifikation: Tags, Topics, DocumentTags in DB

Marker: unit_fast  (In-Memory-SQLite, kein Netzwerk)

Layer 1 = sequentieller State-Machine-Test (kompletter Flow in einem Test)
Layer 4 = KB-Verifikation in eigener Klasse
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import AnalysisResultInvalidStateApiError
from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.topics import Topic, TopicDocument, TopicTag
from app.schemas.analysis import (
    ApproveResultRequest,
    CreateAnalysisJobRequest,
    MarkForReviewRequest,
    RejectResultRequest,
)
from app.services.analysis.import_service import AnalysisResultImportService
from app.services.analysis.service import AnalysisService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID, OLDER_DOCUMENT_ID
from tests.fixtures.analysis_seed import make_analysis_job, make_analysis_result

pytestmark = pytest.mark.unit_fast


# ── shared helpers ────────────────────────────────────────────────────────────

def _svc(db_session: Session) -> AnalysisService:
    return AnalysisService(db_session)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_completed_result(
    db_session: Session,
    *,
    job_id: str | None = None,
    doc_ids: list[str] | None = None,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    status: str = "draft",
) -> tuple[AnalysisJob, AnalysisResult]:
    """Seed a completed job + result directly, bypassing the KI provider."""
    now = _now()
    doc_ids = doc_ids or [DOCUMENT_ID]
    job = AnalysisJob(
        id=job_id or str(uuid4()),
        workspace_id=DEFAULT_WORKSPACE_ID,
        status="completed",
        analysis_type="summary",
        source_document_ids=doc_ids,
        prompt="Fasse zusammen.",
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
        title="Analyseergebnis",
        summary="Telekom-Systemlandschaft analysiert.",
        key_points=["SAP-Systeme detektiert", "Prozesslücken identifiziert"],
        suggested_tags=tags or ["sap", "prozess"],
        suggested_topics=topics or ["SAP-Systemlandschaft"],
        confidence=0.88,
        status=status,
        created_at=now,
        updated_at=now,
    )
    db_session.add(result)
    db_session.flush()
    job.result_id = result.id
    db_session.flush()
    return job, result


# ── Layer 1: vollständiger sequentieller Gold-Path ────────────────────────────

class TestAnalysisGoldPathServiceLayer:
    """
    Kompletter Analyse-Gold-Path als sequentieller State-Machine-Test.
    Ein Test, 11 Steps, kein externer I/O.
    """

    def test_gp_a01_dokument_vorhanden(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A01: Dokument im Workspace vorhanden — Voraussetzung für Job-Erstellung."""
        from app.models.documents import Document
        from sqlalchemy import select
        doc = db_session.execute(
            select(Document).where(
                Document.id == DOCUMENT_ID,
                Document.workspace_id == DEFAULT_WORKSPACE_ID,
            )
        ).scalar_one_or_none()
        assert doc is not None, "GP-A01 FAIL: Dokument nicht im Workspace"
        assert doc.lifecycle_status != "deleted"

    def test_gp_a02_job_anlegen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A02: Analyse-Job anlegen."""
        svc = _svc(db_session)
        request = CreateAnalysisJobRequest(
            source_document_ids=[DOCUMENT_ID],
            analysis_type="summary",
            prompt="Fasse die Dokumente zusammen.",
        )
        job = svc.create_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            request=request,
        )
        assert job.id is not None
        assert job.status == "queued"
        assert job.workspace_id == DEFAULT_WORKSPACE_ID
        assert DOCUMENT_ID in job.source_document_ids

    def test_gp_a03_job_status_abrufen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A03: Job-Status über get_job abrufen."""
        svc = _svc(db_session)
        request = CreateAnalysisJobRequest(
            source_document_ids=[DOCUMENT_ID],
            analysis_type="summary",
            prompt="Status-Test.",
        )
        created = svc.create_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            request=request,
        )
        fetched = svc.get_job(workspace_id=DEFAULT_WORKSPACE_ID, job_id=created.id)
        assert fetched.id == created.id
        assert fetched.status == "queued"
        assert fetched.result is None

    def test_gp_a04_job_liste_filtern(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A04: Job-Liste mit status-Filter abrufen."""
        svc = _svc(db_session)
        for _ in range(2):
            svc.create_job(
                workspace_id=DEFAULT_WORKSPACE_ID,
                user_id=DEFAULT_USER_ID,
                request=CreateAnalysisJobRequest(
                    source_document_ids=[DOCUMENT_ID],
                    analysis_type="summary",
                    prompt="Filter-Test.",
                ),
            )
        listing = svc.list_jobs(
            workspace_id=DEFAULT_WORKSPACE_ID,
            limit=20,
            offset=0,
            status="queued",
        )
        assert listing.total >= 2
        assert all(j.status == "queued" for j in listing.items)

    def test_gp_a05_ki_ergebnis_einbuchen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A05: KI-Ergebnis einbuchen (simuliert — kein Provider-Aufruf)."""
        job, result = _make_completed_result(db_session, doc_ids=[DOCUMENT_ID])
        db_session.commit()
        assert job.status == "completed"
        assert result.status == "draft"
        assert result.job_id == job.id

    def test_gp_a06_ergebnis_abrufen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A06: Ergebnis über Service abrufen (status=draft)."""
        job, result = _make_completed_result(db_session, doc_ids=[DOCUMENT_ID])
        db_session.commit()

        svc = _svc(db_session)
        fetched = svc.get_result_by_id(workspace_id=DEFAULT_WORKSPACE_ID, result_id=result.id)
        assert fetched.id == result.id
        assert fetched.status == "draft"
        assert fetched.summary == "Telekom-Systemlandschaft analysiert."

    def test_gp_a07_zur_pruefung_einreichen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A07: draft → review über mark_result_for_review."""
        job, result = _make_completed_result(db_session, doc_ids=[DOCUMENT_ID])
        db_session.commit()

        svc = _svc(db_session)
        reviewed = svc.mark_result_for_review(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
            request=MarkForReviewRequest(note="Bitte prüfen."),
        )
        assert reviewed.status == "review"

    def test_gp_a08_ablehnen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A08: review → rejected über reject_result."""
        job, result = _make_completed_result(db_session, status="review", doc_ids=[DOCUMENT_ID])
        db_session.commit()

        svc = _svc(db_session)
        rejected = svc.reject_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            actor_role="admin",
            result_id=result.id,
            request=RejectResultRequest(reason="Zusammenfassung unvollständig."),
        )
        assert rejected.status == "rejected"

    def test_gp_a09_genehmigen(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A09: review → approved über approve_result (mit confirm=True)."""
        job, result = _make_completed_result(db_session, status="review", doc_ids=[DOCUMENT_ID])
        db_session.commit()

        svc = _svc(db_session)
        approved = svc.approve_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            actor_role="admin",
            result_id=result.id,
            request=ApproveResultRequest(confirm=True, reviewer_note="Freigegeben."),
        )
        assert approved.status == "approved"
        assert approved.approved_by == DEFAULT_USER_ID
        assert approved.approved_at is not None

    def test_gp_a10_importieren(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A10: approved → In Wissensbasis importieren."""
        job, result = _make_completed_result(
            db_session,
            status="approved",
            doc_ids=[DOCUMENT_ID],
            tags=["sap", "prozess"],
            topics=["SAP-Systemlandschaft"],
        )
        db_session.commit()

        svc = AnalysisResultImportService(db_session)
        stats = svc.import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )
        assert stats.tags_created == 2
        assert stats.topics_created == 1
        assert stats.topic_docs_attached == 1
        assert stats.topic_tags_applied == 2
        assert stats.source_document_count == 1

    def test_gp_a11_wissensbasis_verifikation(self, db_session: Session, auth_fixture, document_fixture):
        """GP-A11: Nach Import — Tags, Topics, DocumentTags in DB nachweisbar."""
        job, result = _make_completed_result(
            db_session,
            status="approved",
            doc_ids=[DOCUMENT_ID, OLDER_DOCUMENT_ID],
            tags=["telekom", "sap"],
            topics=["Telekom-Systeme"],
        )
        db_session.commit()

        AnalysisResultImportService(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        # Tags in DB
        tag_count = db_session.execute(
            text("SELECT COUNT(*) FROM tags WHERE workspace_id = :ws"),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).scalar_one()
        assert tag_count == 2, f"GP-A11: erwartet 2 Tags, gefunden {tag_count}"

        # DocumentTags — 2 Tags × 2 Docs = 4
        doc_tag_count = db_session.execute(
            text(
                "SELECT COUNT(*) FROM document_tags "
                "WHERE document_id IN (:d1, :d2) AND source = 'ki'"
            ),
            {"d1": DOCUMENT_ID, "d2": OLDER_DOCUMENT_ID},
        ).scalar_one()
        assert doc_tag_count == 4, f"GP-A11: erwartet 4 document_tags, gefunden {doc_tag_count}"

        # Topic in DB
        topic = db_session.execute(
            text("SELECT slug FROM topics WHERE workspace_id = :ws LIMIT 1"),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).one()
        assert topic.slug == "telekom-systeme", f"GP-A11: falscher Slug '{topic.slug}'"

        # TopicDocument — 2 Docs
        td_count = db_session.execute(
            text(
                "SELECT COUNT(*) FROM topic_documents td "
                "JOIN topics t ON td.topic_id = t.id "
                "WHERE t.workspace_id = :ws"
            ),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).scalar_one()
        assert td_count == 2, f"GP-A11: erwartet 2 topic_documents, gefunden {td_count}"

        # TopicTag — 2 Tags × 1 Topic = 2
        tt_count = db_session.execute(
            text(
                "SELECT COUNT(*) FROM topic_tags tt "
                "JOIN topics t ON tt.topic_id = t.id "
                "WHERE t.workspace_id = :ws"
            ),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).scalar_one()
        assert tt_count == 2, f"GP-A11: erwartet 2 topic_tags, gefunden {tt_count}"


# ── Layer 4: KB-Verifikation (isoliert) ──────────────────────────────────────

class TestAnalysisGoldPathKBVerifikation:
    """
    Layer 4: Wissensbasis-Integrität nach Import.
    Prüft, dass mehrere Imports idempotent sind und keine Duplikate erzeugen.
    """

    def test_doppelter_import_erzeugt_keine_duplikate(
        self, db_session: Session, auth_fixture, document_fixture
    ):
        """Zwei getrennte Jobs mit gleichen Tags/Topics → kein doppelter KB-Eintrag."""
        for _ in range(2):
            job, result = _make_completed_result(
                db_session,
                status="approved",
                doc_ids=[DOCUMENT_ID],
                tags=["sap"],
                topics=["SAP-Prozesse"],
            )
            db_session.commit()
            AnalysisResultImportService(db_session).import_result(
                workspace_id=DEFAULT_WORKSPACE_ID,
                user_id=DEFAULT_USER_ID,
                result_id=result.id,
            )

        tag_count = db_session.execute(
            text("SELECT COUNT(*) FROM tags WHERE workspace_id = :ws AND normalized_name = 'sap'"),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).scalar_one()
        assert tag_count == 1, "Duplikate: Tag 'sap' mehrfach angelegt"

        topic_count = db_session.execute(
            text("SELECT COUNT(*) FROM topics WHERE workspace_id = :ws AND slug = 'sap-prozesse'"),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).scalar_one()
        assert topic_count == 1, "Duplikate: Topic 'sap-prozesse' mehrfach angelegt"

        doc_tag_rows = db_session.execute(
            text(
                "SELECT COUNT(*) FROM document_tags "
                "WHERE document_id = :doc AND source = 'ki'"
            ),
            {"doc": DOCUMENT_ID},
        ).scalar_one()
        assert doc_tag_rows == 1, f"Duplikate: {doc_tag_rows} document_tag-Zeilen für 1 Tag"

    def test_import_schreibt_nur_source_ki(
        self, db_session: Session, auth_fixture, document_fixture
    ):
        """Alle per Import erzeugten document_tags haben source='ki'."""
        job, result = _make_completed_result(
            db_session,
            status="approved",
            doc_ids=[DOCUMENT_ID],
            tags=["test-tag"],
            topics=[],
        )
        db_session.commit()
        AnalysisResultImportService(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )
        row = db_session.execute(
            text(
                "SELECT source FROM document_tags "
                "WHERE document_id = :doc LIMIT 1"
            ),
            {"doc": DOCUMENT_ID},
        ).one()
        assert row.source == "ki"

    def test_import_topic_status_ist_draft(
        self, db_session: Session, auth_fixture, document_fixture
    ):
        """Import-erzeugte Topics haben status='draft' — kein auto-approve."""
        job, result = _make_completed_result(
            db_session,
            status="approved",
            doc_ids=[DOCUMENT_ID],
            tags=[],
            topics=["Auto-Approve-Test"],
        )
        db_session.commit()
        AnalysisResultImportService(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )
        row = db_session.execute(
            text("SELECT status FROM topics WHERE slug = 'auto-approve-test' LIMIT 1")
        ).one()
        assert row.status == "draft", "PROHIBIT: Import darf Topics nicht automatisch genehmigen"

    def test_nicht_approved_blockiert_import(
        self, db_session: Session, auth_fixture, document_fixture
    ):
        """Import auf nicht-approved Result → AnalysisResultInvalidStateApiError."""
        for bad_status in ("draft", "review", "rejected"):
            job, result = _make_completed_result(
                db_session,
                status=bad_status,
                doc_ids=[DOCUMENT_ID],
            )
            db_session.commit()
            with pytest.raises(AnalysisResultInvalidStateApiError):
                AnalysisResultImportService(db_session).import_result(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    user_id=DEFAULT_USER_ID,
                    result_id=result.id,
                )
