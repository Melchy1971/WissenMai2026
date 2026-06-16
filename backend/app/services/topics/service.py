from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import (
    DocumentNotFoundApiError,
    TopicDocumentAlreadyAttachedApiError,
    TopicDocumentNotFoundApiError,
    TopicDuplicateSlugApiError,
    TopicInvalidStatusTransitionApiError,
    TopicNotFoundApiError,
    TopicTagAlreadyExistsApiError,
)
from app.models.documents import Document
from app.models.topics import Topic, TopicDocument, TopicTag
from app.repositories.topics import TopicDetailRecord, TopicListRecord, TopicRepository
from app.schemas.topics import (
    AttachDocumentRequest,
    TopicCreate,
    TopicDetail,
    TopicDocumentItem,
    TopicListItem,
    TopicListResponse,
    TopicTagItem,
    TopicUpdate,
)


# Status transition graph: key → allowed next states
_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"review", "archived"}),
    "review": frozenset({"approved", "draft", "archived"}),
    "approved": frozenset({"archived"}),
    "archived": frozenset(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_document_in_workspace(session: Session, document_id: str, workspace_id: str) -> None:
    from sqlalchemy import select
    exists = session.execute(
        select(Document.id).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
            Document.lifecycle_status != "deleted",
        )
    ).scalar_one_or_none()
    if exists is None:
        raise DocumentNotFoundApiError()


def _to_list_item(r: TopicListRecord) -> TopicListItem:
    return TopicListItem(
        id=r.id,
        title=r.title,
        slug=r.slug,
        status=r.status,  # type: ignore[arg-type]
        created_at=r.created_at,
        updated_at=r.updated_at,
        doc_count=r.doc_count,
        tag_count=r.tag_count,
    )


def _to_detail(r: TopicDetailRecord) -> TopicDetail:
    return TopicDetail(
        id=r.id,
        workspace_id=r.workspace_id,
        title=r.title,
        slug=r.slug,
        summary=r.summary,
        status=r.status,  # type: ignore[arg-type]
        created_by=r.created_by,
        approved_at=r.approved_at,
        approved_by=r.approved_by,
        deleted_at=r.deleted_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
        documents=[
            TopicDocumentItem(
                id=d.id,
                document_id=d.document_id,
                relation_type=d.relation_type,  # type: ignore[arg-type]
                created_at=d.created_at,
            )
            for d in r.documents
        ],
        tags=[
            TopicTagItem(tag_id=t.tag_id, created_at=t.created_at)
            for t in r.tags
        ],
    )


class TopicService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = TopicRepository(session)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_topic(self, *, workspace_id: str, user_id: str, request: TopicCreate) -> TopicDetail:
        slug = request.slug.strip()
        if self._repo.slug_exists(slug, workspace_id=workspace_id):
            raise TopicDuplicateSlugApiError()

        now = _now()
        topic = Topic(
            id=str(uuid4()),
            workspace_id=workspace_id,
            title=request.title.strip(),
            slug=slug,
            summary=request.summary,
            status=request.status,
            created_by=user_id,
            approved_at=None,
            approved_by=None,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        self._repo.create_topic(topic)
        self._session.commit()
        self._session.refresh(topic)

        record = self._repo.get_topic(topic.id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)

    def get_topic(self, topic_id: str, *, workspace_id: str) -> TopicDetail:
        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        if record is None:
            raise TopicNotFoundApiError()
        return _to_detail(record)

    def list_topics(
        self,
        *,
        workspace_id: str,
        limit: int,
        offset: int,
        status: str | None = None,
        tag_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        order_by: str = "created_at_desc",
    ) -> TopicListResponse:
        records, total = self._repo.list_topics(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            status=status,
            tag_id=tag_id,
            created_after=created_after,
            created_before=created_before,
            order_by=order_by,
        )
        return TopicListResponse(
            items=[_to_list_item(r) for r in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    def search_topics(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
    ) -> TopicListResponse:
        records, total = self._repo.search_topics(
            workspace_id=workspace_id,
            query=query,
            limit=limit,
            offset=offset,
        )
        return TopicListResponse(
            items=[_to_list_item(r) for r in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    def update_topic(self, topic_id: str, *, workspace_id: str, request: TopicUpdate) -> TopicDetail:
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()

        if request.slug is not None:
            slug = request.slug.strip()
            if self._repo.slug_exists(slug, workspace_id=workspace_id, exclude_id=topic_id):
                raise TopicDuplicateSlugApiError()
            topic.slug = slug

        if request.title is not None:
            topic.title = request.title.strip()

        if request.summary is not None:
            topic.summary = request.summary

        topic.updated_at = _now()
        self._repo.update_topic(topic)
        self._session.commit()
        self._session.refresh(topic)

        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)

    def delete_topic(self, topic_id: str, *, workspace_id: str) -> None:
        """Soft-delete."""
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()
        now = _now()
        topic.deleted_at = now
        topic.updated_at = now
        self._session.commit()

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def _transition_status(self, topic_id: str, *, workspace_id: str, target: str, user_id: str | None = None) -> TopicDetail:
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()

        allowed = _STATUS_TRANSITIONS.get(topic.status, frozenset())
        if target not in allowed:
            raise TopicInvalidStatusTransitionApiError(
                message=f"Cannot transition from '{topic.status}' to '{target}'",
                details={"current": topic.status, "target": target, "allowed": sorted(allowed)},
            )

        now = _now()
        topic.status = target
        topic.updated_at = now

        if target == "approved" and user_id is not None:
            topic.approved_at = now
            topic.approved_by = user_id

        self._session.commit()
        self._session.refresh(topic)

        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)

    def approve_topic(self, topic_id: str, *, workspace_id: str, user_id: str) -> TopicDetail:
        return self._transition_status(topic_id, workspace_id=workspace_id, target="approved", user_id=user_id)

    def archive_topic(self, topic_id: str, *, workspace_id: str) -> TopicDetail:
        return self._transition_status(topic_id, workspace_id=workspace_id, target="archived")

    # ------------------------------------------------------------------
    # Document relations
    # ------------------------------------------------------------------

    def attach_document(self, topic_id: str, *, workspace_id: str, request: AttachDocumentRequest) -> TopicDetail:
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()

        _assert_document_in_workspace(self._session, request.document_id, workspace_id)

        if self._repo.document_attached(topic_id, request.document_id):
            raise TopicDocumentAlreadyAttachedApiError()

        relation = TopicDocument(
            id=str(uuid4()),
            topic_id=topic_id,
            document_id=request.document_id,
            relation_type=request.relation_type,
            created_at=_now(),
        )
        self._repo.attach_document(relation)

        topic.updated_at = _now()
        self._session.commit()

        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)

    def detach_document(self, topic_id: str, document_id: str, *, workspace_id: str) -> TopicDetail:
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()

        removed = self._repo.detach_document(topic_id, document_id)
        if not removed:
            raise TopicDocumentNotFoundApiError()

        topic.updated_at = _now()
        self._session.commit()

        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def add_tag(self, topic_id: str, *, workspace_id: str, tag_id: str) -> TopicDetail:
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()

        if self._repo.tag_exists(topic_id, tag_id):
            raise TopicTagAlreadyExistsApiError()

        relation = TopicTag(
            topic_id=topic_id,
            tag_id=tag_id,
            created_at=_now(),
        )
        self._repo.add_tag(relation)

        topic.updated_at = _now()
        self._session.commit()

        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)

    def remove_tag(self, topic_id: str, tag_id: str, *, workspace_id: str) -> TopicDetail:
        topic = self._repo.get_topic_orm(topic_id, workspace_id=workspace_id)
        if topic is None:
            raise TopicNotFoundApiError()

        removed = self._repo.remove_tag(topic_id, tag_id)
        if not removed:
            raise TopicNotFoundApiError(message="Tag not assigned to this topic")

        topic.updated_at = _now()
        self._session.commit()

        record = self._repo.get_topic(topic_id, workspace_id=workspace_id)
        assert record is not None
        return _to_detail(record)
