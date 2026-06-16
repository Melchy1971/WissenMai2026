"""Unit tests for TopicService — uses in-memory SQLite via db_session fixture.

Topics models must be imported before Base.metadata.create_all runs (done via
the test_engine fixture in conftest.py) so their tables are present.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

# Import topics models to register them with Base.metadata before create_all
import app.models.topics  # noqa: F401

from app.core.errors import (
    TopicDocumentAlreadyAttachedApiError,
    TopicDocumentNotFoundApiError,
    TopicDuplicateSlugApiError,
    TopicInvalidStatusTransitionApiError,
    TopicNotFoundApiError,
    TopicTagAlreadyExistsApiError,
)
from app.schemas.topics import AttachDocumentRequest, TopicCreate, TopicUpdate
from app.services.topics.service import TopicService
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, DOCUMENT_ID

pytestmark = pytest.mark.unit_fast

TAG_ID = "00000000-0000-0000-0000-000000000401"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(db_session: Session) -> TopicService:
    return TopicService(db_session)


def _create_topic(
    db_session: Session,
    *,
    title: str = "Test Topic",
    slug: str = "test-topic",
    status: str = "draft",
) -> str:
    service = _make_service(db_session)
    result = service.create_topic(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        request=TopicCreate(title=title, slug=slug, status=status),  # type: ignore[arg-type]
    )
    return result.id


# ---------------------------------------------------------------------------
# create_topic
# ---------------------------------------------------------------------------

def test_create_topic_returns_detail(db_session: Session, auth_fixture: dict) -> None:
    service = _make_service(db_session)
    result = service.create_topic(
        workspace_id=DEFAULT_WORKSPACE_ID,
        user_id=DEFAULT_USER_ID,
        request=TopicCreate(title="My Topic", slug="my-topic"),
    )
    assert result.title == "My Topic"
    assert result.slug == "my-topic"
    assert result.status == "draft"
    assert result.workspace_id == DEFAULT_WORKSPACE_ID
    assert result.created_by == DEFAULT_USER_ID
    assert result.documents == []
    assert result.tags == []


def test_create_topic_rejects_duplicate_slug(db_session: Session, auth_fixture: dict) -> None:
    _create_topic(db_session, slug="unique-slug")
    with pytest.raises(TopicDuplicateSlugApiError):
        _create_topic(db_session, slug="unique-slug", title="Different Title")


def test_create_topic_allows_same_slug_in_different_workspace(
    db_session: Session, auth_fixture: dict
) -> None:
    """Slug uniqueness is workspace-scoped."""
    _create_topic(db_session, slug="shared-slug")
    service = _make_service(db_session)
    result = service.create_topic(
        workspace_id="other-workspace",
        user_id=DEFAULT_USER_ID,
        request=TopicCreate(title="Other", slug="shared-slug"),
    )
    assert result.slug == "shared-slug"


# ---------------------------------------------------------------------------
# get_topic
# ---------------------------------------------------------------------------

def test_get_topic_raises_if_not_found(db_session: Session, auth_fixture: dict) -> None:
    service = _make_service(db_session)
    with pytest.raises(TopicNotFoundApiError):
        service.get_topic("nonexistent-id", workspace_id=DEFAULT_WORKSPACE_ID)


def test_get_topic_raises_if_wrong_workspace(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    with pytest.raises(TopicNotFoundApiError):
        service.get_topic(topic_id, workspace_id="wrong-workspace")


def test_get_topic_returns_correct_detail(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, title="Detail Topic", slug="detail-topic")
    service = _make_service(db_session)
    result = service.get_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)
    assert result.id == topic_id
    assert result.title == "Detail Topic"


# ---------------------------------------------------------------------------
# list_topics
# ---------------------------------------------------------------------------

def test_list_topics_returns_all_in_workspace(db_session: Session, auth_fixture: dict) -> None:
    _create_topic(db_session, slug="t1", title="T1")
    _create_topic(db_session, slug="t2", title="T2")
    service = _make_service(db_session)
    resp = service.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0)
    assert resp.total == 2
    assert len(resp.items) == 2


def test_list_topics_filters_by_status(db_session: Session, auth_fixture: dict) -> None:
    _create_topic(db_session, slug="draft-1", status="draft")
    _create_topic(db_session, slug="review-1", status="review")
    service = _make_service(db_session)
    resp = service.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0, status="draft")
    assert resp.total == 1
    assert resp.items[0].status == "draft"


def test_list_topics_pagination(db_session: Session, auth_fixture: dict) -> None:
    for i in range(5):
        _create_topic(db_session, slug=f"slug-{i}", title=f"T{i}")
    service = _make_service(db_session)
    page1 = service.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=3, offset=0)
    page2 = service.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=3, offset=3)
    assert page1.total == 5
    assert len(page1.items) == 3
    assert len(page2.items) == 2


def test_list_topics_excludes_soft_deleted(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, slug="to-delete")
    service = _make_service(db_session)
    service.delete_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)
    resp = service.list_topics(workspace_id=DEFAULT_WORKSPACE_ID, limit=20, offset=0)
    assert resp.total == 0


# ---------------------------------------------------------------------------
# update_topic
# ---------------------------------------------------------------------------

def test_update_topic_title_and_slug(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, title="Old", slug="old-slug")
    service = _make_service(db_session)
    result = service.update_topic(
        topic_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        request=TopicUpdate(title="New", slug="new-slug"),
    )
    assert result.title == "New"
    assert result.slug == "new-slug"


def test_update_topic_rejects_duplicate_slug(db_session: Session, auth_fixture: dict) -> None:
    _create_topic(db_session, slug="existing")
    topic_id = _create_topic(db_session, slug="other-topic")
    service = _make_service(db_session)
    with pytest.raises(TopicDuplicateSlugApiError):
        service.update_topic(
            topic_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            request=TopicUpdate(slug="existing"),
        )


def test_update_topic_same_slug_is_allowed(db_session: Session, auth_fixture: dict) -> None:
    """Updating slug to its own current value must not raise duplicate error."""
    topic_id = _create_topic(db_session, slug="my-slug")
    service = _make_service(db_session)
    result = service.update_topic(
        topic_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        request=TopicUpdate(title="Updated Title", slug="my-slug"),
    )
    assert result.title == "Updated Title"
    assert result.slug == "my-slug"


def test_update_topic_raises_if_not_found(db_session: Session, auth_fixture: dict) -> None:
    service = _make_service(db_session)
    with pytest.raises(TopicNotFoundApiError):
        service.update_topic(
            "nonexistent",
            workspace_id=DEFAULT_WORKSPACE_ID,
            request=TopicUpdate(title="X"),
        )


# ---------------------------------------------------------------------------
# delete_topic (soft-delete)
# ---------------------------------------------------------------------------

def test_delete_topic_soft_deletes(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    service.delete_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)
    with pytest.raises(TopicNotFoundApiError):
        service.get_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)


def test_delete_topic_raises_if_not_found(db_session: Session, auth_fixture: dict) -> None:
    service = _make_service(db_session)
    with pytest.raises(TopicNotFoundApiError):
        service.delete_topic("nonexistent", workspace_id=DEFAULT_WORKSPACE_ID)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

def test_approve_topic_from_review(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, status="review")
    service = _make_service(db_session)
    result = service.approve_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID)
    assert result.status == "approved"
    assert result.approved_by == DEFAULT_USER_ID
    assert result.approved_at is not None


def test_approve_topic_from_draft_raises(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, status="draft")
    service = _make_service(db_session)
    with pytest.raises(TopicInvalidStatusTransitionApiError):
        service.approve_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID)


def test_archive_topic_from_approved(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, status="review")
    service = _make_service(db_session)
    service.approve_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID, user_id=DEFAULT_USER_ID)
    result = service.archive_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)
    assert result.status == "archived"


def test_archive_topic_cannot_be_re_archived(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session, status="draft")
    service = _make_service(db_session)
    service.archive_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)
    with pytest.raises(TopicInvalidStatusTransitionApiError):
        service.archive_topic(topic_id, workspace_id=DEFAULT_WORKSPACE_ID)


# ---------------------------------------------------------------------------
# Document relations
# ---------------------------------------------------------------------------

def test_attach_document(db_session: Session, document_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    result = service.attach_document(
        topic_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        request=AttachDocumentRequest(document_id=DOCUMENT_ID, relation_type="primary"),
    )
    assert len(result.documents) == 1
    assert result.documents[0].document_id == DOCUMENT_ID
    assert result.documents[0].relation_type == "primary"


def test_attach_document_duplicate_raises(db_session: Session, document_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    service.attach_document(
        topic_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        request=AttachDocumentRequest(document_id=DOCUMENT_ID),
    )
    with pytest.raises(TopicDocumentAlreadyAttachedApiError):
        service.attach_document(
            topic_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            request=AttachDocumentRequest(document_id=DOCUMENT_ID),
        )


def test_detach_document(db_session: Session, document_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    service.attach_document(
        topic_id,
        workspace_id=DEFAULT_WORKSPACE_ID,
        request=AttachDocumentRequest(document_id=DOCUMENT_ID),
    )
    result = service.detach_document(topic_id, DOCUMENT_ID, workspace_id=DEFAULT_WORKSPACE_ID)
    assert result.documents == []


def test_detach_document_not_attached_raises(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    with pytest.raises(TopicDocumentNotFoundApiError):
        service.detach_document(topic_id, "nonexistent-doc", workspace_id=DEFAULT_WORKSPACE_ID)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_add_and_remove_tag(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    result = service.add_tag(topic_id, workspace_id=DEFAULT_WORKSPACE_ID, tag_id=TAG_ID)
    assert any(t.tag_id == TAG_ID for t in result.tags)

    result = service.remove_tag(topic_id, TAG_ID, workspace_id=DEFAULT_WORKSPACE_ID)
    assert result.tags == []


def test_add_duplicate_tag_raises(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    service.add_tag(topic_id, workspace_id=DEFAULT_WORKSPACE_ID, tag_id=TAG_ID)
    with pytest.raises(TopicTagAlreadyExistsApiError):
        service.add_tag(topic_id, workspace_id=DEFAULT_WORKSPACE_ID, tag_id=TAG_ID)


def test_remove_tag_not_assigned_raises(db_session: Session, auth_fixture: dict) -> None:
    topic_id = _create_topic(db_session)
    service = _make_service(db_session)
    with pytest.raises(TopicNotFoundApiError):
        service.remove_tag(topic_id, "nonexistent-tag", workspace_id=DEFAULT_WORKSPACE_ID)


# ---------------------------------------------------------------------------
# search_topics
# ---------------------------------------------------------------------------

def test_search_topics_by_title(db_session: Session, auth_fixture: dict) -> None:
    _create_topic(db_session, title="Vertragsanalyse", slug="vertragsanalyse")
    _create_topic(db_session, title="Rechnungslegung", slug="rechnungslegung")
    service = _make_service(db_session)
    resp = service.search_topics(
        workspace_id=DEFAULT_WORKSPACE_ID,
        query="Vertrags",
        limit=10,
        offset=0,
    )
    assert resp.total == 1
    assert resp.items[0].title == "Vertragsanalyse"


def test_search_topics_returns_empty_for_no_match(db_session: Session, auth_fixture: dict) -> None:
    _create_topic(db_session, slug="something")
    service = _make_service(db_session)
    resp = service.search_topics(
        workspace_id=DEFAULT_WORKSPACE_ID,
        query="xxxxxxxxxxxxxxxxx",
        limit=10,
        offset=0,
    )
    assert resp.total == 0
    assert resp.items == []
