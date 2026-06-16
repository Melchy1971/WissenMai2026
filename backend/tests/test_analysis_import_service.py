"""
Tests for AnalysisResultImportService.

Covers:
  - Guard: non-approved result raises AnalysisResultInvalidStateApiError
  - Guard: wrong workspace raises AnalysisResultNotFoundApiError
  - Guard: missing result raises AnalysisResultNotFoundApiError
  - _slugify / _normalize_tag helpers
  - Tags: new tags created, existing tags found
  - Document tags: inserted with source='ki', skipped on duplicate
  - Topics: created with correct slug, found by slug on second call
  - Topics: docs and tags attached, skipped on duplicate
  - ImportStats counts are accurate for create-path and find-path
  - End-to-end: full approved result with tags, topics, source docs
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.errors import AnalysisResultInvalidStateApiError, AnalysisResultNotFoundApiError
from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.topics import Topic, TopicDocument, TopicTag
from app.services.analysis.import_service import (
    AnalysisResultImportService,
    ImportStats,
    _slugify,
    _normalize_tag,
)
from tests.conftest import DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, DOCUMENT_ID, OLDER_DOCUMENT_ID

pytestmark = pytest.mark.unit_fast

OTHER_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_job(db_session: Session, *, workspace_id: str = DEFAULT_WORKSPACE_ID,
              doc_ids: list[str] | None = None) -> AnalysisJob:
    from datetime import datetime, timezone
    from uuid import uuid4
    job = AnalysisJob(
        id=str(uuid4()),
        workspace_id=workspace_id,
        status="completed",
        analysis_type="summarize",
        source_document_ids=doc_ids or [],
        prompt="test",
        created_by=DEFAULT_USER_ID,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.flush()
    return job


def _make_result(
    db_session: Session,
    job: AnalysisJob,
    *,
    status: str = "approved",
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    confidence: float | None = 0.9,
) -> AnalysisResult:
    from datetime import datetime, timezone
    from uuid import uuid4
    result = AnalysisResult(
        id=str(uuid4()),
        job_id=job.id,
        summary="s",
        key_points=[],
        suggested_tags=tags or [],
        suggested_topics=topics or [],
        confidence=confidence,
        status=status,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(result)
    db_session.flush()
    return result


def _svc(db_session: Session) -> AnalysisResultImportService:
    return AnalysisResultImportService(db_session)


# ── unit: pure helpers ─────────────────────────────────────────────────────────

class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("C# & .NET") == "c-net"

    def test_leading_trailing_hyphens(self):
        assert _slugify("  --foo--  ") == "foo"

    def test_empty_fallback(self):
        assert _slugify("!!!") == "topic"

    def test_truncate_200(self):
        long = "a" * 300
        assert len(_slugify(long)) == 200

    def test_unicode_lowercased(self):
        assert _slugify("Ärger") == "rger"  # non-word chars stripped


class TestNormalizeTag:
    def test_lowercase(self):
        assert _normalize_tag("Python") == "python"

    def test_strip(self):
        assert _normalize_tag("  sap ") == "sap"

    def test_truncate_255(self):
        assert len(_normalize_tag("x" * 300)) == 255


# ── guard tests ────────────────────────────────────────────────────────────────

class TestImportGuards:
    def test_missing_result_raises_not_found(self, db_session, auth_fixture):
        svc = _svc(db_session)
        with pytest.raises(AnalysisResultNotFoundApiError):
            svc.import_result(
                workspace_id=DEFAULT_WORKSPACE_ID,
                user_id=DEFAULT_USER_ID,
                result_id="00000000-0000-0000-0000-deadbeef0000",
            )

    def test_wrong_workspace_raises_not_found(self, db_session, auth_fixture):
        job = _make_job(db_session, workspace_id=DEFAULT_WORKSPACE_ID)
        result = _make_result(db_session, job, status="approved")
        db_session.commit()

        svc = _svc(db_session)
        with pytest.raises(AnalysisResultNotFoundApiError):
            svc.import_result(
                workspace_id=OTHER_WORKSPACE_ID,
                user_id=DEFAULT_USER_ID,
                result_id=result.id,
            )

    def test_non_approved_status_raises_invalid_state(self, db_session, auth_fixture):
        for bad_status in ("draft", "review", "rejected"):
            job = _make_job(db_session)
            result = _make_result(db_session, job, status=bad_status)
            db_session.commit()

            svc = _svc(db_session)
            with pytest.raises(AnalysisResultInvalidStateApiError):
                svc.import_result(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    user_id=DEFAULT_USER_ID,
                    result_id=result.id,
                )


# ── tag logic ─────────────────────────────────────────────────────────────────

class TestEnsureTags:
    def test_creates_new_tags(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=["Python", "SAP"], topics=[])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.tags_created == 2
        assert stats.tags_found == 0

    def test_finds_existing_tag(self, db_session, auth_fixture, document_fixture):
        from datetime import datetime, timezone
        from uuid import uuid4
        # pre-insert a tag
        tag_id = str(uuid4())
        now = datetime.now(timezone.utc)
        db_session.execute(
            text(
                "INSERT INTO tags (id, workspace_id, name, normalized_name, created_at, updated_at) "
                "VALUES (:id, :ws, :name, :norm, :now, :now)"
            ),
            {"id": tag_id, "ws": DEFAULT_WORKSPACE_ID, "name": "Python", "norm": "python", "now": now},
        )
        db_session.commit()

        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=["Python", "SAP"], topics=[])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.tags_found == 1
        assert stats.tags_created == 1

    def test_no_tags_produces_zero_counts(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=[], topics=[])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.tags_created == 0
        assert stats.tags_found == 0
        assert stats.document_tags_applied == 0


# ── document tags ─────────────────────────────────────────────────────────────

class TestApplyDocumentTags:
    def test_document_tags_inserted(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID, OLDER_DOCUMENT_ID])
        result = _make_result(db_session, job, tags=["go"], topics=[])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        # 1 tag × 2 docs = 2 rows
        assert stats.document_tags_applied == 2
        assert stats.source_document_count == 2

    def test_duplicate_document_tags_skipped(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=["rust"], topics=[])
        db_session.commit()

        svc = _svc(db_session)
        svc.import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        # second import on same result: tags already exist, document_tags already present
        job2 = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result2 = _make_result(db_session, job2, tags=["rust"], topics=[])
        db_session.commit()

        stats2 = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result2.id,
        )

        # tag found (not created), document_tag already exists → 0 new rows
        assert stats2.tags_found == 1
        assert stats2.tags_created == 0
        assert stats2.document_tags_applied == 0

    def test_no_source_docs_no_document_tags(self, db_session, auth_fixture):
        job = _make_job(db_session, doc_ids=[])
        result = _make_result(db_session, job, tags=["kotlin"], topics=[])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.document_tags_applied == 0
        assert stats.source_document_count == 0


# ── topic logic ───────────────────────────────────────────────────────────────

class TestEnsureTopics:
    def test_creates_new_topic(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=[], topics=["Machine Learning"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.topics_created == 1
        assert stats.topics_found == 0

        topic = db_session.execute(
            text("SELECT slug, status FROM topics WHERE workspace_id = :ws LIMIT 1"),
            {"ws": DEFAULT_WORKSPACE_ID},
        ).one()
        assert topic.slug == "machine-learning"
        assert topic.status == "draft"

    def test_finds_existing_topic_by_slug(self, db_session, auth_fixture, document_fixture):
        from datetime import datetime, timezone
        from uuid import uuid4
        # pre-create topic with matching slug
        now = datetime.now(timezone.utc)
        db_session.add(Topic(
            id=str(uuid4()),
            workspace_id=DEFAULT_WORKSPACE_ID,
            title="Machine Learning",
            slug="machine-learning",
            status="draft",
            created_by=DEFAULT_USER_ID,
            created_at=now,
            updated_at=now,
        ))
        db_session.commit()

        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=[], topics=["Machine Learning"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.topics_found == 1
        assert stats.topics_created == 0

    def test_docs_attached_to_topic(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID, OLDER_DOCUMENT_ID])
        result = _make_result(db_session, job, tags=[], topics=["AI"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.topic_docs_attached == 2

    def test_tags_attached_to_topic(self, db_session, auth_fixture, document_fixture):
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=["go", "python"], topics=["Backend"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.topic_tags_applied == 2

    def test_duplicate_topic_doc_attachment_skipped(self, db_session, auth_fixture, document_fixture):
        from datetime import datetime, timezone
        from uuid import uuid4
        # pre-create topic and TopicDocument
        now = datetime.now(timezone.utc)
        topic = Topic(
            id=str(uuid4()),
            workspace_id=DEFAULT_WORKSPACE_ID,
            title="AI",
            slug="ai",
            status="draft",
            created_by=DEFAULT_USER_ID,
            created_at=now,
            updated_at=now,
        )
        db_session.add(topic)
        db_session.flush()
        db_session.add(TopicDocument(
            id=str(uuid4()),
            topic_id=topic.id,
            document_id=DOCUMENT_ID,
            relation_type="related",
            created_at=now,
        ))
        db_session.commit()

        job = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        result = _make_result(db_session, job, tags=[], topics=["AI"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        # doc already attached — should not create a duplicate
        assert stats.topic_docs_attached == 0
        assert stats.topics_found == 1

    def test_duplicate_topic_tag_attachment_skipped(self, db_session, auth_fixture, document_fixture):
        from datetime import datetime, timezone
        from uuid import uuid4
        now = datetime.now(timezone.utc)
        # pre-insert tag
        tag_id = str(uuid4())
        db_session.execute(
            text(
                "INSERT INTO tags (id, workspace_id, name, normalized_name, created_at, updated_at) "
                "VALUES (:id, :ws, :name, :norm, :now, :now)"
            ),
            {"id": tag_id, "ws": DEFAULT_WORKSPACE_ID, "name": "go", "norm": "go", "now": now},
        )
        # pre-create topic with that tag already attached
        topic = Topic(
            id=str(uuid4()),
            workspace_id=DEFAULT_WORKSPACE_ID,
            title="Backend",
            slug="backend",
            status="draft",
            created_by=DEFAULT_USER_ID,
            created_at=now,
            updated_at=now,
        )
        db_session.add(topic)
        db_session.flush()
        db_session.add(TopicTag(topic_id=topic.id, tag_id=tag_id, created_at=now))
        db_session.commit()

        job = _make_job(db_session, doc_ids=[])
        result = _make_result(db_session, job, tags=["go"], topics=["Backend"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.topic_tags_applied == 0
        assert stats.tags_found == 1


# ── end-to-end ────────────────────────────────────────────────────────────────

class TestImportResultEndToEnd:
    def test_full_approved_result(self, db_session, auth_fixture, document_fixture):
        """Full path: 2 tags, 2 source docs, 2 topics → verify all stat fields."""
        job = _make_job(db_session, doc_ids=[DOCUMENT_ID, OLDER_DOCUMENT_ID])
        result = _make_result(
            db_session, job,
            status="approved",
            tags=["SAP", "Telekom"],
            topics=["Process Design", "IT Governance"],
            confidence=0.85,
        )
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=result.id,
        )

        assert stats.result_id == result.id
        assert stats.source_document_count == 2
        assert stats.tags_created == 2
        assert stats.tags_found == 0
        # 2 tags × 2 docs
        assert stats.document_tags_applied == 4
        assert stats.topics_created == 2
        assert stats.topics_found == 0
        # 2 docs × 2 topics
        assert stats.topic_docs_attached == 4
        # 2 tags × 2 topics
        assert stats.topic_tags_applied == 4

    def test_idempotent_second_import_different_result(self, db_session, auth_fixture, document_fixture):
        """Second result with same tags/topics → all found, no new rows."""
        job1 = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        r1 = _make_result(db_session, job1, tags=["SAP"], topics=["Process"])
        db_session.commit()
        _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=r1.id,
        )

        job2 = _make_job(db_session, doc_ids=[DOCUMENT_ID])
        r2 = _make_result(db_session, job2, tags=["SAP"], topics=["Process"])
        db_session.commit()

        stats = _svc(db_session).import_result(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            result_id=r2.id,
        )

        assert stats.tags_created == 0
        assert stats.tags_found == 1
        assert stats.document_tags_applied == 0
        assert stats.topics_created == 0
        assert stats.topics_found == 1
        assert stats.topic_docs_attached == 0
        assert stats.topic_tags_applied == 0
