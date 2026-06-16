"""Integration tests for TopicRepository against in-memory SQLite.

These tests operate one layer below the service, directly on the repository
to verify query logic, soft-delete filtering, slug uniqueness checks, and
tag/document relation operations.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

# Must be imported before Base.metadata.create_all runs
import app.models.topics  # noqa: F401

from app.models.topics import Topic, TopicDocument, TopicTag
from app.repositories.topics import TopicRepository
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID

pytestmark = pytest.mark.unit_fast

OTHER_WORKSPACE_ID = "other-workspace-id"
TAG_A = "tag-00000000-0001"
TAG_B = "tag-00000000-0002"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(UTC)


def _make_topic(
    *,
    id: str | None = None,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    slug: str = "test-slug",
    title: str = "Test Topic",
    status: str = "draft",
    deleted_at: datetime | None = None,
) -> Topic:
    now = _now()
    return Topic(
        id=id or str(uuid4()),
        workspace_id=workspace_id,
        title=title,
        slug=slug,
        summary=None,
        status=status,
        created_by=DEFAULT_USER_ID,
        approved_at=None,
        approved_by=None,
        deleted_at=deleted_at,
        created_at=now,
        updated_at=now,
    )


def _add_topic(db_session: Session, **kwargs: object) -> Topic:
    t = _make_topic(**kwargs)
    db_session.add(t)
    db_session.flush()
    return t


# ---------------------------------------------------------------------------
# slug_exists
# ---------------------------------------------------------------------------

def test_slug_exists_returns_true_if_present(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="my-slug")
    repo = TopicRepository(db_session)
    assert repo.slug_exists("my-slug", workspace_id=DEFAULT_WORKSPACE_ID) is True


def test_slug_exists_returns_false_if_absent(db_session: Session, auth_fixture: dict) -> None:
    repo = TopicRepository(db_session)
    assert repo.slug_exists("missing", workspace_id=DEFAULT_WORKSPACE_ID) is False


def test_slug_exists_excludes_self(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session, slug="own-slug")
    repo = TopicRepository(db_session)
    assert repo.slug_exists("own-slug", workspace_id=DEFAULT_WORKSPACE_ID, exclude_id=t.id) is False


def test_slug_exists_ignores_soft_deleted(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="deleted-slug", deleted_at=_now())
    repo = TopicRepository(db_session)
    assert repo.slug_exists("deleted-slug", workspace_id=DEFAULT_WORKSPACE_ID) is False


def test_slug_exists_is_workspace_scoped(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="shared", workspace_id=DEFAULT_WORKSPACE_ID)
    repo = TopicRepository(db_session)
    # Same slug in different workspace must not trigger exists
    assert repo.slug_exists("shared", workspace_id=OTHER_WORKSPACE_ID) is False


# ---------------------------------------------------------------------------
# list_topics
# ---------------------------------------------------------------------------

def test_list_topics_excludes_soft_deleted(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="active")
    _add_topic(db_session, slug="dead", deleted_at=_now())
    repo = TopicRepository(db_session)
    records, total = repo.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0)
    assert total == 1
    assert records[0].slug == "active"


def test_list_topics_filter_status(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="d", status="draft")
    _add_topic(db_session, slug="r", status="review")
    repo = TopicRepository(db_session)
    records, total = repo.list_topics(
        workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0, status="review"
    )
    assert total == 1
    assert records[0].status == "review"


def test_list_topics_filter_by_tag(db_session: Session, auth_fixture: dict) -> None:
    t1 = _add_topic(db_session, slug="tagged")
    _add_topic(db_session, slug="untagged")
    db_session.add(TopicTag(topic_id=t1.id, tag_id=TAG_A, created_at=_now()))
    db_session.flush()
    repo = TopicRepository(db_session)
    records, total = repo.list_topics(
        workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0, tag_id=TAG_A
    )
    assert total == 1
    assert records[0].id == t1.id


def test_list_topics_pagination(db_session: Session, auth_fixture: dict) -> None:
    for i in range(6):
        _add_topic(db_session, slug=f"s{i}", title=f"T{i}")
    repo = TopicRepository(db_session)
    _, total = repo.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=100, offset=0)
    assert total == 6

    page1, _ = repo.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=4, offset=0)
    page2, _ = repo.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=4, offset=4)
    assert len(page1) == 4
    assert len(page2) == 2


def test_list_topics_doc_and_tag_counts(db_session: Session, document_fixture: dict) -> None:
    t = _add_topic(db_session, slug="with-stuff")
    db_session.add(
        TopicDocument(
            id=str(uuid4()),
            topic_id=t.id,
            document_id=DOCUMENT_ID,
            relation_type="related",
            created_at=_now(),
        )
    )
    db_session.add(TopicTag(topic_id=t.id, tag_id=TAG_A, created_at=_now()))
    db_session.flush()

    repo = TopicRepository(db_session)
    records, _ = repo.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0)
    assert records[0].doc_count == 1
    assert records[0].tag_count == 1


# ---------------------------------------------------------------------------
# get_topic
# ---------------------------------------------------------------------------

def test_get_topic_returns_none_if_missing(db_session: Session, auth_fixture: dict) -> None:
    repo = TopicRepository(db_session)
    assert repo.get_topic("nope", workspace_id=DEFAULT_WORKSPACE_ID) is None


def test_get_topic_returns_none_for_soft_deleted(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session, deleted_at=_now())
    repo = TopicRepository(db_session)
    assert repo.get_topic(t.id, workspace_id=DEFAULT_WORKSPACE_ID) is None


def test_get_topic_includes_documents_and_tags(db_session: Session, document_fixture: dict) -> None:
    t = _add_topic(db_session, slug="rich")
    db_session.add(
        TopicDocument(
            id=str(uuid4()),
            topic_id=t.id,
            document_id=DOCUMENT_ID,
            relation_type="primary",
            created_at=_now(),
        )
    )
    db_session.add(TopicTag(topic_id=t.id, tag_id=TAG_A, created_at=_now()))
    db_session.flush()

    repo = TopicRepository(db_session)
    record = repo.get_topic(t.id, workspace_id=DEFAULT_WORKSPACE_ID)
    assert record is not None
    assert len(record.documents) == 1
    assert record.documents[0].document_id == DOCUMENT_ID
    assert record.documents[0].relation_type == "primary"
    assert len(record.tags) == 1
    assert record.tags[0].tag_id == TAG_A


# ---------------------------------------------------------------------------
# document_attached / attach / detach
# ---------------------------------------------------------------------------

def test_document_attached_returns_false_initially(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session)
    repo = TopicRepository(db_session)
    assert repo.document_attached(t.id, DOCUMENT_ID) is False


def test_attach_and_detach_document(db_session: Session, document_fixture: dict) -> None:
    t = _add_topic(db_session)
    relation = TopicDocument(
        id=str(uuid4()),
        topic_id=t.id,
        document_id=DOCUMENT_ID,
        relation_type="related",
        created_at=_now(),
    )
    repo = TopicRepository(db_session)
    repo.attach_document(relation)
    assert repo.document_attached(t.id, DOCUMENT_ID) is True

    removed = repo.detach_document(t.id, DOCUMENT_ID)
    assert removed is True
    assert repo.document_attached(t.id, DOCUMENT_ID) is False


def test_detach_document_returns_false_if_not_attached(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session)
    repo = TopicRepository(db_session)
    assert repo.detach_document(t.id, "ghost-doc") is False


# ---------------------------------------------------------------------------
# tag_exists / add_tag / remove_tag
# ---------------------------------------------------------------------------

def test_tag_exists_returns_false_initially(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session)
    repo = TopicRepository(db_session)
    assert repo.tag_exists(t.id, TAG_A) is False


def test_add_and_remove_tag(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session)
    repo = TopicRepository(db_session)
    repo.add_tag(TopicTag(topic_id=t.id, tag_id=TAG_A, created_at=_now()))
    assert repo.tag_exists(t.id, TAG_A) is True

    removed = repo.remove_tag(t.id, TAG_A)
    assert removed is True
    assert repo.tag_exists(t.id, TAG_A) is False


def test_remove_tag_returns_false_if_not_present(db_session: Session, auth_fixture: dict) -> None:
    t = _add_topic(db_session)
    repo = TopicRepository(db_session)
    assert repo.remove_tag(t.id, "nonexistent") is False


# ---------------------------------------------------------------------------
# search_topics
# ---------------------------------------------------------------------------

def test_search_topics_matches_title(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="a", title="Vertragsanalyse")
    _add_topic(db_session, slug="b", title="Rechnungslegung")
    repo = TopicRepository(db_session)
    records, total = repo.search_topics(
        workspace_id=DEFAULT_WORKSPACE_ID, query="Vertrags", limit=10, offset=0
    )
    assert total == 1
    assert records[0].title == "Vertragsanalyse"


def test_search_topics_case_insensitive(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="c", title="Compliance Report")
    repo = TopicRepository(db_session)
    records, total = repo.search_topics(
        workspace_id=DEFAULT_WORKSPACE_ID, query="compliance", limit=10, offset=0
    )
    assert total == 1


def test_search_topics_excludes_soft_deleted(db_session: Session, auth_fixture: dict) -> None:
    _add_topic(db_session, slug="gone", title="Deleted Topic", deleted_at=_now())
    repo = TopicRepository(db_session)
    records, total = repo.search_topics(
        workspace_id=DEFAULT_WORKSPACE_ID, query="Deleted", limit=10, offset=0
    )
    assert total == 0
