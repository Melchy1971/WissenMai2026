from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.documents import BackgroundJob, ChatMessage, ChatSession, Chunk, Document, DocumentVersion
from app.schemas.admin import (
    DiagnosticsAuthResponse,
    DiagnosticsCountsResponse,
    DiagnosticsDatabaseResponse,
    DiagnosticsImportsResponse,
    DiagnosticsResponse,
    DiagnosticsSearchResponse,
    DiagnosticsSystemResponse,
)


@dataclass(frozen=True)
class DiagnosticsService:
    session: Session

    @classmethod
    def from_session(cls, session: Session) -> "DiagnosticsService":
        return cls(session=session)

    def get_diagnostics(self, *, workspace_id: str) -> DiagnosticsResponse:
        database = self._database_status()
        counts = self._counts(workspace_id=workspace_id)
        imports = self._imports(workspace_id=workspace_id)
        search = self._search(workspace_id=workspace_id)
        system_status = self._system_status(database=database, search=search)

        return DiagnosticsResponse(
            system=DiagnosticsSystemResponse(
                status=system_status,
                version="0.1.0",
                environment=self._environment(),
            ),
            database=database,
            counts=counts,
            imports=imports,
            search=search,
            auth=DiagnosticsAuthResponse(auth_enabled=True, workspace_isolation_enabled=True),
        )

    def _database_status(self) -> DiagnosticsDatabaseResponse:
        self.session.execute(text("select 1")).scalar_one()
        current_revision = self._current_revision()
        migration_head = self._migration_head()
        return DiagnosticsDatabaseResponse(
            reachable=True,
            migration_head=migration_head,
            current_revision=current_revision,
            is_current=bool(current_revision and migration_head and current_revision == migration_head),
        )

    def _current_revision(self) -> str | None:
        context = MigrationContext.configure(self.session.connection())
        return context.get_current_revision()

    def _migration_head(self) -> str | None:
        backend_root = Path(__file__).resolve().parents[2]
        config = Config(str(backend_root / "alembic.ini"))
        config.set_main_option("script_location", str(backend_root / "migrations"))
        heads = ScriptDirectory.from_config(config).get_heads()
        if not heads:
            return None
        if len(heads) == 1:
            return heads[0]
        return ",".join(sorted(heads))

    def _counts(self, *, workspace_id: str) -> DiagnosticsCountsResponse:
        return DiagnosticsCountsResponse(
            documents=self._scalar_count(select(func.count()).select_from(Document).where(Document.workspace_id == workspace_id)),
            versions=self._scalar_count(
                select(func.count())
                .select_from(DocumentVersion)
                .join(Document, Document.id == DocumentVersion.document_id)
                .where(Document.workspace_id == workspace_id)
            ),
            chunks=self._scalar_count(
                select(func.count())
                .select_from(Chunk)
                .join(Document, Document.id == Chunk.document_id)
                .where(Document.workspace_id == workspace_id)
            ),
            chat_sessions=self._scalar_count(
                select(func.count()).select_from(ChatSession).where(ChatSession.workspace_id == workspace_id)
            ),
            chat_messages=self._scalar_count(
                select(func.count())
                .select_from(ChatMessage)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(ChatSession.workspace_id == workspace_id)
            ),
        )

    def _imports(self, *, workspace_id: str) -> DiagnosticsImportsResponse:
        since = datetime.now(UTC) - timedelta(hours=24)
        last_error_code = self.session.execute(
            select(BackgroundJob.error_code)
            .where(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.job_type == "document_import",
                BackgroundJob.status == "failed",
                BackgroundJob.error_code.is_not(None),
            )
            .order_by(BackgroundJob.finished_at.desc().nullslast(), BackgroundJob.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        return DiagnosticsImportsResponse(
            running_jobs=self._scalar_count(
                select(func.count()).select_from(BackgroundJob).where(
                    BackgroundJob.workspace_id == workspace_id,
                    BackgroundJob.job_type == "document_import",
                    BackgroundJob.status == "running",
                )
            ),
            failed_jobs_last_24h=self._scalar_count(
                select(func.count()).select_from(BackgroundJob).where(
                    BackgroundJob.workspace_id == workspace_id,
                    BackgroundJob.job_type == "document_import",
                    BackgroundJob.status == "failed",
                    BackgroundJob.finished_at >= since,
                )
            ),
            last_error_code=last_error_code,
        )

    def _search(self, *, workspace_id: str) -> DiagnosticsSearchResponse:
        indexed_chunks = self._scalar_count(
            select(func.count())
            .select_from(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.workspace_id == workspace_id, Chunk.is_searchable.is_(True))
        )
        stale_entries = self._scalar_count(
            select(func.count())
            .select_from(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Document.workspace_id == workspace_id,
                (
                    ((Document.lifecycle_status != "active") & Chunk.is_searchable.is_(True))
                    | ((Document.lifecycle_status == "active") & Chunk.is_searchable.is_(False))
                ),
            )
        )
        return DiagnosticsSearchResponse(index_available=True, indexed_chunks=indexed_chunks, stale_index_entries=stale_entries)

    def _system_status(self, *, database: DiagnosticsDatabaseResponse, search: DiagnosticsSearchResponse) -> str:
        if not database.reachable:
            return "error"
        if not database.is_current or not search.index_available or search.stale_index_entries > 0:
            return "degraded"
        return "ok"

    def _environment(self) -> str:
        if settings.app_env in {"local", "test", "production"}:
            return settings.app_env
        return "local"

    def _scalar_count(self, statement) -> int:
        return int(self.session.execute(statement).scalar_one() or 0)
