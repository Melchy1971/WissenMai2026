from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import Text as SqlText
from sqlalchemy import and_, cast, distinct, func, literal, or_, select, text, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.core.errors import ServiceUnavailableApiError
from app.models.documents import Chunk, Document
from app.observability.logging import bind_observability_context, log_event


logger = logging.getLogger(__name__)

SEARCH_VECTOR_INDEX = "ix_document_chunks_search_vector"


class SearchIndexRebuildService:
    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: Session) -> "SearchIndexRebuildService":
        return cls(session)

    def rebuild_search_index(self, workspace_id: str | None = None) -> dict[str, int | str | None]:
        self._require_postgresql("Search index rebuild requires PostgreSQL")

        normalized_workspace_id = workspace_id.strip() if workspace_id else None
        active_conditions = [Document.lifecycle_status == "active"]
        scoped_conditions: list = []
        if normalized_workspace_id:
            workspace_condition = Document.workspace_id == self._uuid_param(normalized_workspace_id)
            active_conditions.append(workspace_condition)
            scoped_conditions.append(workspace_condition)

        chunk_count = int(
            self._session.scalar(
                select(func.count(Chunk.id)).join(Document, Document.id == Chunk.document_id).where(*active_conditions)
            )
            or 0
        )
        document_count = int(
            self._session.scalar(select(func.count(distinct(Document.id))).where(*active_conditions)) or 0
        )

        logger.info(
            "search index rebuild started workspace_id=%s active_documents=%s active_chunks=%s",
            normalized_workspace_id or "ALL",
            document_count,
            chunk_count,
        )

        active_document_ids = select(Document.id).where(*active_conditions)
        inactive_document_conditions = list(scoped_conditions)
        inactive_document_conditions.append(Document.lifecycle_status != "active")
        inactive_document_ids = select(Document.id).where(*inactive_document_conditions)

        self._session.execute(
            update(Chunk)
            .where(Chunk.document_id.in_(active_document_ids))
            .values(is_searchable=True)
        )
        self._session.execute(
            update(Chunk)
            .where(Chunk.document_id.in_(inactive_document_ids))
            .values(is_searchable=False)
        )

        updated = self._session.execute(
            update(Chunk)
            .where(Chunk.document_id.in_(select(Document.id).where(*scoped_conditions)) if scoped_conditions else text("TRUE"))
            .values(content=Chunk.content)
        )

        index_exists = bool(
            self._session.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = current_schema() AND indexname = :index_name"
                    ")"
                ),
                {"index_name": SEARCH_VECTOR_INDEX},
            ).scalar()
        )

        if index_exists:
            self._session.execute(text(f"REINDEX INDEX {SEARCH_VECTOR_INDEX}"))
            index_action = "reindexed"
        else:
            self._session.execute(
                text(
                    f"CREATE INDEX {SEARCH_VECTOR_INDEX} "
                    "ON document_chunks USING gin (search_vector)"
                )
            )
            index_action = "created"

        self._session.commit()

        logger.info(
            "search index rebuild finished workspace_id=%s updated_chunks=%s index_action=%s",
            normalized_workspace_id or "ALL",
            updated.rowcount or 0,
            index_action,
        )

        return {
            "workspace_id": normalized_workspace_id,
            "reindexed_chunk_count": int(updated.rowcount or 0),
            "reindexed_document_count": document_count,
            "index_name": SEARCH_VECTOR_INDEX,
            "index_action": index_action,
            "status": "completed",
        }

    def inspect_inconsistencies(self, workspace_id: str | None = None) -> dict[str, object]:
        self._require_postgresql("Search index consistency checks require PostgreSQL")

        normalized_workspace_id = workspace_id.strip() if workspace_id else None
        scoped_conditions: list = []
        if normalized_workspace_id:
            scoped_conditions.append(Document.workspace_id == self._uuid_param(normalized_workspace_id))

        searchable_chunk_count = int(
            self._session.scalar(
                select(func.count(Chunk.id))
                .join(Document, Document.id == Chunk.document_id)
                .where(*scoped_conditions, Chunk.is_searchable.is_(True))
            )
            or 0
        )

        missing_index_predicate = [
            *scoped_conditions,
            Chunk.is_searchable.is_(True),
            ((Chunk.search_vector.is_(None)) | (cast(Chunk.search_vector, SqlText) == "")),
        ]
        deleted_index_predicate = [
            *scoped_conditions,
            Document.lifecycle_status == "deleted",
            ((Chunk.is_searchable.is_(True)) | (Chunk.search_vector.is_not(None))),
        ]
        archived_index_predicate = [
            *scoped_conditions,
            Document.lifecycle_status == "archived",
            ((Chunk.is_searchable.is_(True)) | (Chunk.search_vector.is_not(None))),
        ]

        missing_index_entries = self._build_bucket(
            predicates=missing_index_predicate,
            note_ok="All searchable chunks have an indexable search vector.",
        )
        deleted_documents_in_index = self._build_bucket(
            predicates=deleted_index_predicate,
            note_ok="No deleted documents are present in the active search index.",
        )
        archived_documents_in_active_index = self._build_bucket(
            predicates=archived_index_predicate,
            note_ok="No archived documents are present in the active search index.",
        )

        bucket_statuses = {
            missing_index_entries["status"],
            deleted_documents_in_index["status"],
            archived_documents_in_active_index["status"],
        }

        return {
            "workspace_id": normalized_workspace_id,
            "checked_at": datetime.now(UTC),
            "index_name": SEARCH_VECTOR_INDEX,
            "status": "inconsistent" if "inconsistent" in bucket_statuses else "ok",
            "searchable_chunk_count": searchable_chunk_count,
            "missing_index_entries": missing_index_entries,
            "orphan_index_entries": {
                "count": 0,
                "status": "not_applicable",
                "sample_chunk_ids": [],
                "sample_document_ids": [],
                "note": "GIN index entries are derived from document_chunks.search_vector and cannot be enumerated as standalone rows.",
            },
            "deleted_documents_in_index": deleted_documents_in_index,
            "archived_documents_in_active_index": archived_documents_in_active_index,
        }

    def inspect_drift(self, workspace_id: str | None = None) -> dict[str, object]:
        self._require_postgresql("Search index drift checks require PostgreSQL")

        normalized_workspace_id = workspace_id.strip() if workspace_id else None
        scoped_conditions: list = []
        if normalized_workspace_id:
            scoped_conditions.append(Document.workspace_id == self._uuid_param(normalized_workspace_id))

        searchable_chunk_count = int(
            self._session.scalar(
                select(func.count(Chunk.id))
                .join(Document, Document.id == Chunk.document_id)
                .where(*scoped_conditions, Chunk.is_searchable.is_(True))
            )
            or 0
        )

        chunks_without_index = self._build_drift_bucket(
            predicates=[
                *scoped_conditions,
                Chunk.is_searchable.is_(True),
                or_(Chunk.search_vector.is_(None), cast(Chunk.search_vector, SqlText) == ""),
            ],
            severity_if_present="high",
            repair_recommendation="Run search index rebuild after restoring missing search vectors for searchable chunks.",
            note_ok="All searchable chunks have a populated search vector.",
        )

        index_without_chunk = {
            "count": 0,
            "status": "not_applicable",
            "severity": "info",
            "repair_recommendation": "No direct repair needed. GIN index entries are derived from document_chunks.search_vector and are rebuilt from chunk rows.",
            "sample_chunk_ids": [],
            "sample_document_ids": [],
            "note": "Standalone index rows cannot be enumerated in the current PostgreSQL GIN design; rebuild from document_chunks if index corruption is suspected.",
        }

        deleted_documents_in_index = self._build_drift_bucket(
            predicates=[
                *scoped_conditions,
                Document.lifecycle_status == "deleted",
                or_(Chunk.is_searchable.is_(True), Chunk.search_vector.is_not(None)),
            ],
            severity_if_present="critical",
            repair_recommendation="Clear deleted documents from the active index by rebuilding searchability flags and reindexing the workspace.",
            note_ok="No deleted documents are exposed through indexed chunk state.",
        )

        archived_documents_in_active_index = self._build_drift_bucket(
            predicates=[
                *scoped_conditions,
                Document.lifecycle_status == "archived",
                or_(Chunk.is_searchable.is_(True), Chunk.search_vector.is_not(None)),
            ],
            severity_if_present="high",
            repair_recommendation="Rebuild searchability flags for archived documents and reindex the affected workspace.",
            note_ok="No archived documents are present in the active index.",
        )

        duplicate_rows = self._session.execute(
            select(
                Chunk.document_id,
                Chunk.anchor,
                Chunk.content_hash,
                func.count(Chunk.id).label("duplicate_count"),
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(
                *scoped_conditions,
                Chunk.is_searchable.is_(True),
                Document.lifecycle_status == "active",
                Chunk.search_vector.is_not(None),
                cast(Chunk.search_vector, SqlText) != "",
            )
            .group_by(Chunk.document_id, Chunk.anchor, Chunk.content_hash)
            .having(func.count(Chunk.id) > 1)
            .order_by(func.count(Chunk.id).desc(), Chunk.document_id.asc(), Chunk.anchor.asc())
            .limit(10)
        ).all()
        duplicate_chunk_ids: list[str] = []
        duplicate_document_ids: list[str] = []
        duplicate_count = 0
        if duplicate_rows:
            duplicate_keys = [
                and_(Chunk.document_id == row.document_id, Chunk.anchor == row.anchor, Chunk.content_hash == row.content_hash)
                for row in duplicate_rows
            ]
            duplicate_count = sum(int(row.duplicate_count) - 1 for row in duplicate_rows)
            duplicate_chunk_ids = list(
                self._session.scalars(
                    select(Chunk.id)
                    .join(Document, Document.id == Chunk.document_id)
                    .where(
                        *scoped_conditions,
                        Chunk.is_searchable.is_(True),
                        Document.lifecycle_status == "active",
                        Chunk.search_vector.is_not(None),
                        cast(Chunk.search_vector, SqlText) != "",
                        or_(*duplicate_keys),
                    )
                    .order_by(Chunk.document_id.asc(), Chunk.anchor.asc(), Chunk.id.asc())
                    .limit(10)
                )
            )
            duplicate_document_ids = list(dict.fromkeys([row.document_id for row in duplicate_rows]))[:10]
        duplicate_index_entries = {
            "count": duplicate_count,
            "status": "inconsistent" if duplicate_count else "ok",
            "severity": "high" if duplicate_count else "ok",
            "repair_recommendation": "Deduplicate active searchable chunks with identical document, anchor and content hash before reindexing." if duplicate_count else "No repair needed.",
            "sample_chunk_ids": duplicate_chunk_ids,
            "sample_document_ids": duplicate_document_ids,
            "note": None if duplicate_count else "No duplicate searchable index entries were detected.",
        }

        invalid_lifecycle_rows = self._session.execute(
            select(
                Document.id.label("document_id"),
                Chunk.id.label("chunk_id"),
                Document.lifecycle_status.label("lifecycle_status"),
                Chunk.is_searchable.label("is_searchable"),
                Chunk.search_vector.label("search_vector"),
            )
            .join(Chunk, Chunk.document_id == Document.id)
            .where(
                *scoped_conditions,
                or_(
                    and_(Document.lifecycle_status == "active", Chunk.is_searchable.is_(False)),
                    and_(Document.lifecycle_status == "archived", Chunk.is_searchable.is_(True)),
                    and_(Document.lifecycle_status == "deleted", Chunk.is_searchable.is_(True)),
                ),
            )
            .order_by(Document.id.asc(), Chunk.id.asc())
            .limit(10)
        ).all()
        invalid_lifecycle_status = {
            "count": len(invalid_lifecycle_rows),
            "status": "inconsistent" if invalid_lifecycle_rows else "ok",
            "severity": "medium" if invalid_lifecycle_rows else "ok",
            "repair_recommendation": "Resynchronize chunk searchability from document lifecycle state and then rebuild the index." if invalid_lifecycle_rows else "No repair needed.",
            "sample_chunk_ids": [row.chunk_id for row in invalid_lifecycle_rows],
            "sample_document_ids": list(dict.fromkeys([row.document_id for row in invalid_lifecycle_rows]))[:10],
            "note": None if invalid_lifecycle_rows else "Chunk searchability is aligned with document lifecycle state.",
        }

        buckets = {
            "chunks_without_index": chunks_without_index,
            "index_without_chunk": index_without_chunk,
            "deleted_documents_in_index": deleted_documents_in_index,
            "archived_documents_in_active_index": archived_documents_in_active_index,
            "duplicate_index_entries": duplicate_index_entries,
            "invalid_lifecycle_status": invalid_lifecycle_status,
        }
        severity = self._aggregate_drift_severity(buckets)
        drift_score = self._calculate_drift_score(buckets)
        status = "drifted" if any(bucket["status"] == "inconsistent" for bucket in buckets.values()) else "ok"
        bind_observability_context(workspace_id=normalized_workspace_id)
        log_event(
            "search_index_drift_checked",
            workspace_id=normalized_workspace_id,
            status=status,
            error_code="SEARCH_INDEX_DRIFT_DETECTED" if status == "drifted" else None,
        )

        return {
            "workspace_id": normalized_workspace_id,
            "checked_at": datetime.now(UTC),
            "index_name": SEARCH_VECTOR_INDEX,
            "status": status,
            "severity": severity,
            "drift_score": drift_score,
            "repair_recommendation": self._build_drift_recommendation(buckets),
            "searchable_chunk_count": searchable_chunk_count,
            **buckets,
        }

    def _build_bucket(self, *, predicates: list, note_ok: str) -> dict[str, object]:
        count = int(
            self._session.scalar(
                select(func.count(Chunk.id)).join(Document, Document.id == Chunk.document_id).where(*predicates)
            )
            or 0
        )
        sample_chunk_ids = list(
            self._session.scalars(
                select(Chunk.id)
                .join(Document, Document.id == Chunk.document_id)
                .where(*predicates)
                .order_by(Chunk.id.asc())
                .limit(10)
            )
        )
        sample_document_ids = list(
            self._session.scalars(
                select(distinct(Document.id))
                .join(Chunk, Chunk.document_id == Document.id)
                .where(*predicates)
                .order_by(Document.id.asc())
                .limit(10)
            )
        )

        return {
            "count": count,
            "status": "inconsistent" if count else "ok",
            "sample_chunk_ids": sample_chunk_ids,
            "sample_document_ids": sample_document_ids,
            "note": None if count else note_ok,
        }

    def _build_drift_bucket(
        self,
        *,
        predicates: list,
        severity_if_present: str,
        repair_recommendation: str,
        note_ok: str,
    ) -> dict[str, object]:
        bucket = self._build_bucket(predicates=predicates, note_ok=note_ok)
        count = int(bucket["count"])
        bucket["severity"] = severity_if_present if count else "ok"
        bucket["repair_recommendation"] = repair_recommendation if count else "No repair needed."
        return bucket

    def _aggregate_drift_severity(self, buckets: dict[str, dict[str, object]]) -> str:
        ranking = {"ok": 0, "info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
        worst = max((str(bucket["severity"]) for bucket in buckets.values()), key=lambda value: ranking.get(value, 0))
        return worst

    def _calculate_drift_score(self, buckets: dict[str, dict[str, object]]) -> int:
        penalties = {
            "chunks_without_index": 20,
            "index_without_chunk": 0,
            "deleted_documents_in_index": 30,
            "archived_documents_in_active_index": 20,
            "duplicate_index_entries": 15,
            "invalid_lifecycle_status": 15,
        }
        score = 100
        for name, penalty in penalties.items():
            bucket = buckets[name]
            if bucket["status"] == "inconsistent":
                score -= penalty
        return max(0, score)

    def _build_drift_recommendation(self, buckets: dict[str, dict[str, object]]) -> str:
        actions = [
            str(bucket["repair_recommendation"])
            for bucket in buckets.values()
            if bucket["status"] == "inconsistent"
        ]
        if not actions:
            return "No repair needed. Search index state matches database lifecycle state."
        return " ".join(dict.fromkeys(actions))

    def _require_postgresql(self, message: str) -> None:
        bind = self._session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            raise ServiceUnavailableApiError(message=message)

    def _uuid_param(self, value: str):
        bind = self._session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            return cast(value, postgresql.UUID(as_uuid=False))
        return value