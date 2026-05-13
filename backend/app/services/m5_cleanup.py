from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, text, update
from sqlalchemy.orm import Session

from app.models.documents import AuthSession, BackgroundJob, Chunk, Document


TERMINAL_JOB_STATUSES = {"completed", "failed", "dead_letter", "cancelled"}
ACTIVE_JOB_STATUSES = {"pending", "running", "retryable"}


@dataclass(frozen=True)
class CleanupConfig:
    now: datetime
    retention_days: int = 7
    workspace_id: str | None = None
    temp_dir: Path | None = None
    reports_dir: Path | None = None

    @property
    def cutoff(self) -> datetime:
        return self.now - timedelta(days=self.retention_days)


class M5CleanupService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "M5CleanupService":
        return cls(session)

    def dry_run(self, *, config: CleanupConfig) -> dict[str, Any]:
        return self._build_report(config=config, execute=False)

    def execute(self, *, config: CleanupConfig) -> dict[str, Any]:
        report = self._build_report(config=config, execute=True)
        self._session.commit()
        return report

    def _build_report(self, *, config: CleanupConfig, execute: bool) -> dict[str, Any]:
        categories = {
            "orphan_cleanup": self._orphan_cleanup(execute=execute),
            "stale_index_cleanup": self._stale_index_cleanup(config=config, execute=execute),
            "temp_file_cleanup": self._temp_file_cleanup(config=config, execute=execute),
            "old_report_cleanup": self._old_report_cleanup(config=config, execute=execute),
            "expired_session_cleanup": self._expired_session_cleanup(config=config, execute=execute),
        }
        return {
            "cleanup_version": "m5-cleanup-v1",
            "mode": "execute" if execute else "dry_run",
            "checked_at": config.now.isoformat(),
            "retention_days": config.retention_days,
            "workspace_id": config.workspace_id,
            "categories": categories,
            "summary": {
                "candidate_count": sum(int(category["candidate_count"]) for category in categories.values()),
                "protected_count": sum(int(category["protected_count"]) for category in categories.values()),
                "applied_count": sum(int(category["applied_count"]) for category in categories.values()),
                "blocked_count": sum(int(category["blocked_count"]) for category in categories.values()),
            },
            "safety": {
                "dry_run_first": True,
                "destructive_primary_data_delete": False,
                "citations_preserved": True,
                "active_queue_jobs_protected": True,
                "workspace_scoped": config.workspace_id is not None,
            },
        }

    def _orphan_cleanup(self, *, execute: bool) -> dict[str, Any]:
        orphan_chunks = int(
            self._session.execute(
                text(
                    """
                    select count(*)
                    from document_chunks c
                    left join documents d on d.id = c.document_id
                    left join document_versions v on v.id = c.document_version_id
                    where d.id is null or v.id is null
                    """
                )
            ).scalar_one()
            or 0
        )
        orphan_versions = int(
            self._session.execute(
                text(
                    """
                    select count(*)
                    from document_versions v
                    left join documents d on d.id = v.document_id
                    where d.id is null
                    """
                )
            ).scalar_one()
            or 0
        )
        orphan_messages = int(
            self._session.execute(
                text(
                    """
                    select count(*)
                    from chat_messages m
                    left join chat_sessions s on s.id = m.session_id
                    where s.id is null
                    """
                )
            ).scalar_one()
            or 0
        )
        candidate_count = orphan_chunks + orphan_versions + orphan_messages
        applied = 0
        if execute and candidate_count:
            # Order matters: children before parents. Normal FK constraints should keep these counts at zero.
            applied += int(
                self._session.execute(
                    text(
                        """
                        delete from document_chunks c
                        where not exists (select 1 from documents d where d.id = c.document_id)
                           or not exists (select 1 from document_versions v where v.id = c.document_version_id)
                        """
                    )
                ).rowcount
                or 0
            )
            applied += int(
                self._session.execute(
                    text(
                        """
                        delete from document_versions v
                        where not exists (select 1 from documents d where d.id = v.document_id)
                        """
                    )
                ).rowcount
                or 0
            )
            applied += int(
                self._session.execute(
                    text(
                        """
                        delete from chat_messages m
                        where not exists (select 1 from chat_sessions s where s.id = m.session_id)
                        """
                    )
                ).rowcount
                or 0
            )
        return _category(
            candidate_count=candidate_count,
            applied_count=applied,
            protected_count=0,
            blocked_count=0,
            notes=[
                "orphan chunks, versions and messages are detected with left joins",
                "normal foreign keys should keep this category at zero",
            ],
        )

    def _stale_index_cleanup(self, *, config: CleanupConfig, execute: bool) -> dict[str, Any]:
        predicates = [
            or_(
                and_(Document.lifecycle_status == "active", Chunk.is_searchable.is_(False)),
                and_(Document.lifecycle_status != "active", Chunk.is_searchable.is_(True)),
            )
        ]
        if config.workspace_id:
            predicates.append(Document.workspace_id == config.workspace_id)
        statement = select(func.count(Chunk.id)).join(Document, Document.id == Chunk.document_id).where(*predicates)
        candidate_count = int(self._session.scalar(statement) or 0)
        applied = 0
        if execute and candidate_count:
            active_document_ids = select(Document.id).where(Document.lifecycle_status == "active")
            inactive_document_ids = select(Document.id).where(Document.lifecycle_status != "active")
            if config.workspace_id:
                active_document_ids = active_document_ids.where(Document.workspace_id == config.workspace_id)
                inactive_document_ids = inactive_document_ids.where(Document.workspace_id == config.workspace_id)
            applied += int(
                self._session.execute(
                    update(Chunk)
                    .where(Chunk.document_id.in_(active_document_ids), Chunk.is_searchable.is_(False))
                    .values(is_searchable=True)
                    .execution_options(synchronize_session=False)
                ).rowcount
                or 0
            )
            applied += int(
                self._session.execute(
                    update(Chunk)
                    .where(
                        Chunk.document_id.in_(inactive_document_ids),
                        Chunk.is_searchable.is_(True),
                    )
                    .values(is_searchable=False)
                    .execution_options(synchronize_session=False)
                ).rowcount
                or 0
            )
        return _category(
            candidate_count=candidate_count,
            applied_count=applied,
            protected_count=0,
            blocked_count=0,
            notes=["resynchronizes chunk searchability from document lifecycle; no documents or citations are deleted"],
        )

    def _temp_file_cleanup(self, *, config: CleanupConfig, execute: bool) -> dict[str, Any]:
        if config.temp_dir is None or not config.temp_dir.exists():
            return _category(candidate_count=0, applied_count=0, protected_count=0, blocked_count=0, notes=["temp dir missing"])
        referenced_active = self._active_temp_file_paths()
        candidate_paths: list[Path] = []
        protected = 0
        for path in sorted(config.temp_dir.iterdir()):
            if not path.is_file():
                continue
            resolved = str(path)
            if resolved in referenced_active:
                protected += 1
                continue
            if _mtime(path) < config.cutoff:
                candidate_paths.append(path)
        applied = 0
        if execute:
            for path in candidate_paths:
                try:
                    path.unlink()
                    applied += 1
                except FileNotFoundError:
                    pass
        return _category(
            candidate_count=len(candidate_paths),
            applied_count=applied,
            protected_count=protected,
            blocked_count=0,
            sample_ids=[path.name for path in candidate_paths[:10]],
            notes=["files referenced by active queue jobs are protected"],
        )

    def _old_report_cleanup(self, *, config: CleanupConfig, execute: bool) -> dict[str, Any]:
        if config.reports_dir is None or not config.reports_dir.exists():
            return _category(candidate_count=0, applied_count=0, protected_count=0, blocked_count=0, notes=["reports dir missing"])
        candidates: list[Path] = []
        protected = 0
        for path in sorted(config.reports_dir.rglob("*")):
            if not path.is_file() or path.suffix not in {".json", ".md"}:
                continue
            if path.name == "latest.json":
                protected += 1
                continue
            if _mtime(path) < config.cutoff:
                candidates.append(path)
        applied = 0
        if execute:
            for path in candidates:
                try:
                    path.unlink()
                    applied += 1
                except FileNotFoundError:
                    pass
        return _category(
            candidate_count=len(candidates),
            applied_count=applied,
            protected_count=protected,
            blocked_count=0,
            sample_ids=[path.name for path in candidates[:10]],
            notes=["latest.json is always protected"],
        )

    def _expired_session_cleanup(self, *, config: CleanupConfig, execute: bool) -> dict[str, Any]:
        candidate_predicate = or_(
            AuthSession.expires_at < config.cutoff,
            and_(AuthSession.revoked_at.is_not(None), AuthSession.revoked_at < config.cutoff),
        )
        candidate_count = int(self._session.scalar(select(func.count(AuthSession.id)).where(candidate_predicate)) or 0)
        active_count = int(
            self._session.scalar(
                select(func.count(AuthSession.id)).where(
                    AuthSession.expires_at >= config.now,
                    AuthSession.revoked_at.is_(None),
                )
            )
            or 0
        )
        applied = 0
        if execute and candidate_count:
            applied = int(
                self._session.execute(
                    delete(AuthSession).where(candidate_predicate).execution_options(synchronize_session=False)
                ).rowcount
                or 0
            )
        return _category(
            candidate_count=candidate_count,
            applied_count=applied,
            protected_count=active_count,
            blocked_count=0,
            notes=["active non-revoked sessions are protected"],
        )

    def _active_temp_file_paths(self) -> set[str]:
        rows = self._session.scalars(
            select(BackgroundJob.payload_).where(BackgroundJob.status.in_(ACTIVE_JOB_STATUSES))
        ).all()
        paths: set[str] = set()
        for payload in rows:
            if isinstance(payload, dict) and isinstance(payload.get("temp_file_path"), str):
                paths.add(str(payload["temp_file_path"]))
        return paths


def _category(
    *,
    candidate_count: int,
    applied_count: int,
    protected_count: int,
    blocked_count: int,
    sample_ids: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_count": candidate_count,
        "applied_count": applied_count,
        "protected_count": protected_count,
        "blocked_count": blocked_count,
        "sample_ids": sample_ids or [],
        "notes": notes or [],
    }


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
