from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.models.topics import Topic, TopicDocument, TopicTag


# ---------------------------------------------------------------------------
# Dataclass records (immutable, passed to service layer)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TopicListRecord:
    id: str
    title: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime
    doc_count: int
    tag_count: int


@dataclass(frozen=True)
class TopicDocumentRecord:
    id: str
    document_id: str
    relation_type: str
    created_at: datetime


@dataclass(frozen=True)
class TopicTagRecord:
    tag_id: str
    created_at: datetime


@dataclass(frozen=True)
class TopicDetailRecord:
    id: str
    workspace_id: str
    title: str
    slug: str
    summary: str | None
    status: str
    created_by: str
    approved_at: datetime | None
    approved_by: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    documents: list[TopicDocumentRecord]
    tags: list[TopicTagRecord]


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class TopicRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _active(self) -> object:
        """Filter expression: not soft-deleted."""
        return Topic.deleted_at.is_(None)

    def _in_workspace(self, workspace_id: str) -> object:
        return Topic.workspace_id == workspace_id

    def _load_documents(self, topic_id: str) -> list[TopicDocumentRecord]:
        rows = self._session.execute(
            select(
                TopicDocument.id,
                TopicDocument.document_id,
                TopicDocument.relation_type,
                TopicDocument.created_at,
            )
            .where(TopicDocument.topic_id == topic_id)
            .order_by(TopicDocument.created_at.asc())
        ).all()
        return [
            TopicDocumentRecord(
                id=row.id,
                document_id=row.document_id,
                relation_type=row.relation_type,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def _load_tags(self, topic_id: str) -> list[TopicTagRecord]:
        rows = self._session.execute(
            select(TopicTag.tag_id, TopicTag.created_at)
            .where(TopicTag.topic_id == topic_id)
            .order_by(TopicTag.created_at.asc())
        ).all()
        return [TopicTagRecord(tag_id=row.tag_id, created_at=row.created_at) for row in rows]

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

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
    ) -> tuple[list[TopicListRecord], int]:
        doc_count_sq = (
            select(func.count(TopicDocument.id))
            .where(TopicDocument.topic_id == Topic.id)
            .correlate(Topic)
            .scalar_subquery()
        )
        tag_count_sq = (
            select(func.count(TopicTag.tag_id))
            .where(TopicTag.topic_id == Topic.id)
            .correlate(Topic)
            .scalar_subquery()
        )

        conditions = [
            self._in_workspace(workspace_id),
            self._active(),
        ]
        if status is not None:
            conditions.append(Topic.status == status)
        if created_after is not None:
            conditions.append(Topic.created_at >= created_after)
        if created_before is not None:
            conditions.append(Topic.created_at <= created_before)

        base_query = select(Topic.id).where(*conditions)

        if tag_id is not None:
            base_query = base_query.where(
                Topic.id.in_(
                    select(TopicTag.topic_id).where(TopicTag.tag_id == tag_id)
                )
            )

        total: int = self._session.execute(
            select(func.count()).select_from(base_query.subquery())
        ).scalar_one()

        order_expr = (
            desc(Topic.created_at) if order_by == "created_at_desc"
            else Topic.created_at if order_by == "created_at_asc"
            else Topic.title if order_by == "title_asc"
            else desc(Topic.title)
        )

        list_conditions = list(conditions)
        if tag_id is not None:
            list_conditions.append(
                Topic.id.in_(
                    select(TopicTag.topic_id).where(TopicTag.tag_id == tag_id)
                )
            )

        rows = self._session.execute(
            select(
                Topic.id,
                Topic.title,
                Topic.slug,
                Topic.status,
                Topic.created_at,
                Topic.updated_at,
                func.coalesce(doc_count_sq, 0).label("doc_count"),
                func.coalesce(tag_count_sq, 0).label("tag_count"),
            )
            .where(*list_conditions)
            .order_by(order_expr)
            .limit(limit)
            .offset(offset)
        ).all()

        records = [
            TopicListRecord(
                id=row.id,
                title=row.title,
                slug=row.slug,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
                doc_count=row.doc_count,
                tag_count=row.tag_count,
            )
            for row in rows
        ]
        return records, total

    def get_topic(self, topic_id: str, *, workspace_id: str) -> TopicDetailRecord | None:
        row = self._session.execute(
            select(Topic).where(
                Topic.id == topic_id,
                self._in_workspace(workspace_id),
                self._active(),
            )
        ).scalar_one_or_none()

        if row is None:
            return None

        return TopicDetailRecord(
            id=row.id,
            workspace_id=row.workspace_id,
            title=row.title,
            slug=row.slug,
            summary=row.summary,
            status=row.status,
            created_by=row.created_by,
            approved_at=row.approved_at,
            approved_by=row.approved_by,
            deleted_at=row.deleted_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            documents=self._load_documents(row.id),
            tags=self._load_tags(row.id),
        )

    def slug_exists(self, slug: str, *, workspace_id: str, exclude_id: str | None = None) -> bool:
        conditions = [
            Topic.workspace_id == workspace_id,
            Topic.slug == slug,
            self._active(),
        ]
        if exclude_id is not None:
            conditions.append(Topic.id != exclude_id)
        return (
            self._session.execute(
                select(Topic.id).where(*conditions)
            ).scalar_one_or_none()
            is not None
        )

    def search_topics(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
    ) -> tuple[list[TopicListRecord], int]:
        """Full-text search via ILIKE on title and summary."""
        pattern = f"%{query}%"
        doc_count_sq = (
            select(func.count(TopicDocument.id))
            .where(TopicDocument.topic_id == Topic.id)
            .correlate(Topic)
            .scalar_subquery()
        )
        tag_count_sq = (
            select(func.count(TopicTag.tag_id))
            .where(TopicTag.topic_id == Topic.id)
            .correlate(Topic)
            .scalar_subquery()
        )
        conditions = [
            self._in_workspace(workspace_id),
            self._active(),
            (Topic.title.ilike(pattern) | Topic.summary.ilike(pattern)),
        ]
        total: int = self._session.execute(
            select(func.count(Topic.id)).where(*conditions)
        ).scalar_one()

        rows = self._session.execute(
            select(
                Topic.id,
                Topic.title,
                Topic.slug,
                Topic.status,
                Topic.created_at,
                Topic.updated_at,
                func.coalesce(doc_count_sq, 0).label("doc_count"),
                func.coalesce(tag_count_sq, 0).label("tag_count"),
            )
            .where(*conditions)
            .order_by(desc(Topic.updated_at))
            .limit(limit)
            .offset(offset)
        ).all()

        records = [
            TopicListRecord(
                id=row.id,
                title=row.title,
                slug=row.slug,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
                doc_count=row.doc_count,
                tag_count=row.tag_count,
            )
            for row in rows
        ]
        return records, total

    # ------------------------------------------------------------------
    # Write — topic lifecycle
    # ------------------------------------------------------------------

    def create_topic(self, topic: Topic) -> None:
        self._session.add(topic)
        self._session.flush()

    def update_topic(self, topic: Topic) -> None:
        self._session.flush()

    def get_topic_orm(self, topic_id: str, *, workspace_id: str) -> Topic | None:
        """Return the ORM object for mutation (service layer calls flush/commit)."""
        return self._session.execute(
            select(Topic).where(
                Topic.id == topic_id,
                self._in_workspace(workspace_id),
                self._active(),
            )
        ).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Write — document relations
    # ------------------------------------------------------------------

    def attach_document(self, relation: TopicDocument) -> None:
        self._session.add(relation)
        self._session.flush()

    def detach_document(self, topic_id: str, document_id: str) -> bool:
        """Returns True if a row was deleted."""
        row = self._session.execute(
            select(TopicDocument).where(
                and_(
                    TopicDocument.topic_id == topic_id,
                    TopicDocument.document_id == document_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def document_attached(self, topic_id: str, document_id: str) -> bool:
        return (
            self._session.execute(
                select(TopicDocument.id).where(
                    and_(
                        TopicDocument.topic_id == topic_id,
                        TopicDocument.document_id == document_id,
                    )
                )
            ).scalar_one_or_none()
            is not None
        )

    # ------------------------------------------------------------------
    # Write — tags
    # ------------------------------------------------------------------

    def add_tag(self, relation: TopicTag) -> None:
        self._session.add(relation)
        self._session.flush()

    def remove_tag(self, topic_id: str, tag_id: str) -> bool:
        """Returns True if a row was deleted."""
        row = self._session.execute(
            select(TopicTag).where(
                and_(
                    TopicTag.topic_id == topic_id,
                    TopicTag.tag_id == tag_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def tag_exists(self, topic_id: str, tag_id: str) -> bool:
        return (
            self._session.execute(
                select(TopicTag.tag_id).where(
                    and_(
                        TopicTag.topic_id == topic_id,
                        TopicTag.tag_id == tag_id,
                    )
                )
            ).scalar_one_or_none()
            is not None
        )
