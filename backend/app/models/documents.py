from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def json_column() -> JSON:
    """JSON auf SQLite, JSONB auf PostgreSQL.

    Deckungsgleich mit dem Muster der Migrationen. Ohne die Variante erzeugt
    ``create_all`` auf PostgreSQL ``json`` statt ``jsonb`` — die GIN-Indizes aus
    Migration 20260618_0026 waeren dort nicht anlegbar.
    """
    return JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


def _kind_from_is_default(context) -> str:
    """Leitet ``workspaces.kind`` aus ``is_default`` ab.

    Die DB erzwingt ``(kind='shared') <=> (is_default=true)``
    (ck_workspaces_kind_default_consistency, Migration 20260724_0027). Beide
    Spalten sind damit voneinander abhaengig; ein statischer Default 'private'
    wuerde bei ``is_default=True`` die Invariante verletzen. Der Wert wird
    deshalb abgeleitet, nicht geraten.
    """
    params = context.get_current_parameters() if context is not None else {}
    return "shared" if params.get("is_default") else "private"


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_workspaces_name_not_blank"),
        CheckConstraint("kind in ('private','shared')", name="ck_workspaces_kind_allowed"),
        CheckConstraint(
            "(kind = 'shared' AND is_default) OR (kind = 'private' AND NOT is_default)",
            name="ck_workspaces_kind_default_consistency",
        ),
        # Genau ein gemeinsamer Workspace (Singleton ueber is_default).
        Index(
            "ux_workspaces_single_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default"),
        ),
        # Hoechstens ein privater Workspace je User.
        Index(
            "uq_workspaces_owner_private",
            "owner_user_id",
            unique=True,
            postgresql_where=text("owner_user_id IS NOT NULL"),
            sqlite_where=text("owner_user_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Multi-user V1 (Story 1): 'private' = per-user area, 'shared' = single common area.
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default=_kind_from_is_default, server_default="private"
    )
    # Set for private workspaces (their owner); NULL for the shared workspace.
    owner_user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(display_name)) > 0", name="ck_users_display_name_not_blank"),
        UniqueConstraint("login", name="uq_users_login"),
        # Genau ein Default-User.
        Index(
            "ux_users_single_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),
        CheckConstraint("role in ('owner', 'admin', 'member')", name="ck_workspace_memberships_role_allowed"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "content_hash", name="uq_documents_workspace_content_hash"),
        CheckConstraint("length(trim(title)) > 0", name="ck_documents_title_not_blank"),
        CheckConstraint("length(trim(source_type)) > 0", name="ck_documents_source_type_not_blank"),
        CheckConstraint("length(trim(content_hash)) > 0", name="ck_documents_content_hash_not_blank"),
        CheckConstraint(
            "import_status in ('pending', 'parsing', 'parsed', 'chunked', 'failed', 'duplicate')",
            name="ck_documents_import_status_allowed",
        ),
        # 'pending' ist hier bewusst NICHT erlaubt: die API validiert gegen
        # active/archived/deleted (app/api/documents.py) und die DB ebenso.
        CheckConstraint(
            "lifecycle_status in ('active', 'archived', 'deleted')",
            name="ck_documents_lifecycle_status_allowed",
        ),
        CheckConstraint(
            "import_status in ('pending', 'parsing', 'failed') OR current_version_id IS NOT NULL",
            name="ck_documents_readable_status_requires_current_version",
        ),
        Index("ix_documents_workspace_id", "workspace_id"),
        Index("ix_documents_owner_user_id", "owner_user_id"),
        Index("ix_documents_content_hash", "content_hash"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_current_version_id", "current_version_id"),
        Index(
            "ix_documents_workspace_lifecycle_created_at",
            "workspace_id",
            "lifecycle_status",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("document_versions.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    import_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_document_versions_version_number_positive"),
        CheckConstraint(
            "length(trim(markdown_hash)) > 0", name="ck_document_versions_markdown_hash_not_blank"
        ),
        CheckConstraint(
            "length(trim(parser_version)) > 0", name="ck_document_versions_parser_version_not_blank"
        ),
        UniqueConstraint(
            "document_id", "version_number", name="uq_document_versions_document_version_number"
        ),
        # Zielspalten fuer den zusammengesetzten FK aus document_chunks.
        UniqueConstraint("document_id", "id", name="uq_document_versions_document_id_id"),
        Index("ix_document_versions_document_id", "document_id"),
        Index("ix_document_versions_markdown_hash", "markdown_hash"),
        Index("ix_document_versions_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ocr_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ki_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ki_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_column(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Chunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index_non_negative"),
        CheckConstraint("length(trim(anchor)) > 0", name="ck_document_chunks_anchor_not_blank"),
        CheckConstraint("length(trim(content)) > 0", name="ck_document_chunks_content_not_blank"),
        CheckConstraint(
            "length(trim(content_hash)) > 0", name="ck_document_chunks_content_hash_not_blank"
        ),
        CheckConstraint(
            "token_estimate IS NULL OR token_estimate >= 0",
            name="ck_document_chunks_token_estimate_non_negative",
        ),
        UniqueConstraint(
            "document_version_id", "chunk_index", name="uq_document_chunks_version_chunk_index"
        ),
        UniqueConstraint("document_version_id", "anchor", name="uq_document_chunks_version_anchor"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_document_version_id", "document_version_id"),
        Index("ix_document_chunks_content_hash", "content_hash"),
        Index("ix_document_chunks_anchor", "anchor"),
        Index("ix_document_chunks_metadata", "metadata", postgresql_using="gin"),
    )
    # Nicht im Modell abbildbar (nur PostgreSQL, Migration 20260504_0007):
    # ck_document_chunks_source_anchor_normalized nutzt jsonb-Operatoren
    # (?, jsonb_typeof), die SQLite nicht kennt. Wird ausschliesslich in der
    # Migration erzwungen und im PostgreSQL-Verifikationslauf geprueft.

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("document_versions.id"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(json_column(), nullable=False)
    anchor: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=True,
    )
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", json_column(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_chat_sessions_title_not_blank"),
        Index("ix_chat_sessions_workspace_id", "workspace_id"),
        Index("ix_chat_sessions_owner_user_id", "owner_user_id"),
        Index("ix_chat_sessions_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("message_index >= 0", name="ck_chat_messages_message_index_non_negative"),
        CheckConstraint("role in ('system', 'user', 'assistant')", name="ck_chat_messages_role_allowed"),
        CheckConstraint("length(trim(content)) > 0", name="ck_chat_messages_content_not_blank"),
        CheckConstraint(
            "basis_type in ('knowledge_base', 'general', 'mixed', 'unknown')",
            name="ck_chat_messages_basis_type_allowed",
        ),
        UniqueConstraint("session_id", "message_index", name="uq_chat_messages_session_message_index"),
        Index("ix_chat_messages_session_id", "session_id"),
        Index("ix_chat_messages_role", "role"),
        Index("ix_chat_messages_basis_type", "basis_type"),
        Index("ix_chat_messages_metadata", "metadata", postgresql_using="gin"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    basis_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="unknown")
    metadata_: Mapped[dict] = mapped_column("metadata", json_column(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatCitation(Base):
    __tablename__ = "chat_citations"
    __table_args__ = (
        CheckConstraint(
            "source_status in ('active', 'archived', 'deleted', 'missing')",
            name="ck_chat_citations_source_status_allowed",
        ),
        Index("ix_chat_citations_message_id", "message_id"),
        Index("ix_chat_citations_chunk_id", "chunk_id"),
        Index("ix_chat_citations_document_id", "document_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(String, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False)
    document_title: Mapped[str] = mapped_column(String(500), nullable=False)
    quote_preview: Mapped[str] = mapped_column(Text, nullable=False)
    source_anchor: Mapped[dict] = mapped_column(json_column(), nullable=False)
    source_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type in ('document_import', 'search_index_rebuild')",
            name="ck_background_jobs_job_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'retryable', 'failed', 'dead_letter', "
            "'cancelled')",
            name="ck_background_jobs_status_allowed",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_background_jobs_attempt_count_non_negative"),
        Index("ix_background_jobs_status_created_at", "status", "created_at"),
        Index(
            "ix_background_jobs_workspace_job_type_created_at",
            "workspace_id",
            "job_type",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    requested_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Bewusst plain JSON, nicht json_column(): Migration 20260505_0015 legt diese
    # Spalten als sa.JSON() an (auf PostgreSQL also 'json'). Es existiert kein
    # GIN-Index darauf, deshalb keine Umstellung auf jsonb.
    payload_: Mapped[dict] = mapped_column("payload", JSON, nullable=False, default=dict)
    result_: Mapped[dict | None] = mapped_column("result", JSON, nullable=True)
    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    progress_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_categories_name_not_blank"),
        UniqueConstraint("workspace_id", "name", name="uq_categories_workspace_name"),
        Index("ix_categories_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_categories_workspace_id_workspaces"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_tags_name_not_blank"),
        CheckConstraint("length(trim(normalized_name)) > 0", name="ck_tags_normalized_name_not_blank"),
        UniqueConstraint("workspace_id", "normalized_name", name="uq_tags_workspace_normalized_name"),
        Index("ix_tags_workspace_id", "workspace_id"),
        Index("ix_tags_normalized_name", "normalized_name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_tags_workspace_id_workspaces"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentTag(Base):
    __tablename__ = "document_tags"
    __table_args__ = (
        CheckConstraint("source in ('manual', 'ki', 'import')", name="ck_document_tags_source_allowed"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_document_tags_confidence_range",
        ),
        Index("ix_document_tags_document_id", "document_id"),
        Index("ix_document_tags_tag_id", "tag_id"),
        Index("ix_document_tags_source", "source"),
        Index("ix_document_tags_created_by_user_id", "created_by_user_id"),
    )

    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE", name="fk_document_tags_document_id_documents"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tags.id", ondelete="CASCADE", name="fk_document_tags_tag_id_tags"),
        primary_key=True,
    )
    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(precision=5, scale=4), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_document_tags_created_by_user_id_users"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

