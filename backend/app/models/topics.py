from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.documents import Base


TOPIC_STATUS_VALUES = ("draft", "review", "approved", "archived")
TOPIC_RELATION_TYPE_VALUES = ("primary", "related", "reference")


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft', 'review', 'approved', 'archived')",
            name="ck_topics_status_allowed",
        ),
        CheckConstraint("length(trim(title)) > 0", name="ck_topics_title_not_blank"),
        CheckConstraint("length(trim(slug)) > 0", name="ck_topics_slug_not_blank"),
        UniqueConstraint("workspace_id", "slug", name="uq_topics_workspace_slug"),
        Index("ix_topics_workspace_id", "workspace_id"),
        Index("ix_topics_status", "status"),
        Index("ix_topics_created_by", "created_by"),
        Index("ix_topics_created_at", "created_at"),
        Index("ix_topics_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_topics_workspace_id_workspaces"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft")
    created_by: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_topics_created_by_users"),
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_topics_approved_by_users"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TopicDocument(Base):
    __tablename__ = "topic_documents"
    __table_args__ = (
        CheckConstraint(
            "relation_type in ('primary', 'related', 'reference')",
            name="ck_topic_documents_relation_type_allowed",
        ),
        UniqueConstraint("topic_id", "document_id", name="uq_topic_documents_topic_document"),
        Index("ix_topic_documents_topic_id", "topic_id"),
        Index("ix_topic_documents_document_id", "document_id"),
        Index("ix_topic_documents_relation_type", "relation_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    topic_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("topics.id", ondelete="CASCADE", name="fk_topic_documents_topic_id_topics"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE", name="fk_topic_documents_document_id_documents"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="related")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TopicTag(Base):
    __tablename__ = "topic_tags"
    __table_args__ = (
        UniqueConstraint("topic_id", "tag_id", name="uq_topic_tags_topic_tag"),
        Index("ix_topic_tags_topic_id", "topic_id"),
        Index("ix_topic_tags_tag_id", "tag_id"),
    )

    topic_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("topics.id", ondelete="CASCADE", name="fk_topic_tags_topic_id_topics"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tags.id", ondelete="CASCADE", name="fk_topic_tags_tag_id_tags"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
