"""
AnalysisResultImportService

Imports an approved analysis result into the knowledge base.

Behaviour:
  1. Guard: result.status must be 'approved' — raises AnalysisResultInvalidStateApiError otherwise.
  2. Tags: for each suggested_tag string → find-or-create Tag row, then attach to source
     documents via document_tags (source='ki') and to each created/found Topic.
  3. Topics: for each suggested_topic string → find-or-create Topic (slug derived from title),
     attach source documents (relation_type='related'), attach resolved tag IDs.

All writes happen in a single transaction; the caller must commit or it is rolled back on error.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import AnalysisResultInvalidStateApiError, AnalysisResultNotFoundApiError
from app.models.analysis import AnalysisResult
from app.models.topics import Topic, TopicDocument, TopicTag


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    v = value.lower().strip()
    v = re.sub(r"[^\w\s-]", "", v)
    v = re.sub(r"[\s_-]+", "-", v)
    v = re.sub(r"^-+|-+$", "", v)
    return v[:200] or "topic"


def _normalize_tag(name: str) -> str:
    return name.lower().strip()[:255]


@dataclass
class ImportStats:
    result_id: str = ""
    tags_created: int = 0
    tags_found: int = 0
    document_tags_applied: int = 0
    topics_created: int = 0
    topics_found: int = 0
    topic_docs_attached: int = 0
    topic_tags_applied: int = 0
    source_document_count: int = 0


class AnalysisResultImportService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Public API ────────────────────────────────────────────────────────────

    def import_result(
        self,
        *,
        workspace_id: str,
        user_id: str,
        result_id: str,
    ) -> ImportStats:
        result = self._load_approved_result(workspace_id=workspace_id, result_id=result_id)
        source_doc_ids = self._source_doc_ids(result)

        stats = ImportStats(
            result_id=result_id,
            source_document_count=len(source_doc_ids),
        )

        tag_ids = self._ensure_tags(
            workspace_id=workspace_id,
            tag_names=list(result.suggested_tags),
            stats=stats,
        )

        if tag_ids and source_doc_ids:
            self._apply_document_tags(
                document_ids=source_doc_ids,
                tag_ids=tag_ids,
                user_id=user_id,
                confidence=result.confidence,
                stats=stats,
            )

        self._ensure_topics(
            workspace_id=workspace_id,
            user_id=user_id,
            topic_names=list(result.suggested_topics),
            source_doc_ids=source_doc_ids,
            tag_ids=tag_ids,
            stats=stats,
        )

        self._session.commit()
        return stats

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_approved_result(self, *, workspace_id: str, result_id: str) -> AnalysisResult:
        result = self._session.execute(
            select(AnalysisResult)
            .join(AnalysisResult.job)
            .where(AnalysisResult.id == result_id)
        ).scalar_one_or_none()

        if result is None:
            raise AnalysisResultNotFoundApiError()

        job = result.job
        if job is None or job.workspace_id != workspace_id:
            raise AnalysisResultNotFoundApiError()

        if result.status != "approved":
            raise AnalysisResultInvalidStateApiError(
                details={
                    "result_id": result_id,
                    "status": result.status,
                    "detail": "Import requires result status=approved.",
                }
            )

        return result

    def _source_doc_ids(self, result: AnalysisResult) -> list[str]:
        job = result.job
        if job is None:
            return []
        return list(job.source_document_ids)

    def _ensure_tags(
        self,
        *,
        workspace_id: str,
        tag_names: list[str],
        stats: ImportStats,
    ) -> list[str]:
        tag_ids: list[str] = []
        now = _now()

        for raw in tag_names:
            name = raw.strip()
            if not name:
                continue
            normalized = _normalize_tag(name)

            existing_id: str | None = self._session.execute(
                text(
                    "SELECT id FROM tags "
                    "WHERE workspace_id = :ws AND normalized_name = :norm"
                ),
                {"ws": workspace_id, "norm": normalized},
            ).scalar_one_or_none()

            if existing_id:
                stats.tags_found += 1
                tag_ids.append(existing_id)
            else:
                new_id = str(uuid4())
                self._session.execute(
                    text(
                        "INSERT INTO tags "
                        "(id, workspace_id, name, normalized_name, created_at, updated_at) "
                        "VALUES (:id, :ws, :name, :norm, :now, :now)"
                    ),
                    {"id": new_id, "ws": workspace_id, "name": name, "norm": normalized, "now": now},
                )
                stats.tags_created += 1
                tag_ids.append(new_id)

        return tag_ids

    def _apply_document_tags(
        self,
        *,
        document_ids: list[str],
        tag_ids: list[str],
        user_id: str,
        confidence: float | None,
        stats: ImportStats,
    ) -> None:
        now = _now()
        for doc_id in document_ids:
            for tag_id in tag_ids:
                exists = self._session.execute(
                    text(
                        "SELECT 1 FROM document_tags "
                        "WHERE document_id = :doc AND tag_id = :tag AND source = 'ki'"
                    ),
                    {"doc": doc_id, "tag": tag_id},
                ).scalar_one_or_none()

                if not exists:
                    self._session.execute(
                        text(
                            "INSERT INTO document_tags "
                            "(document_id, tag_id, source, confidence, created_by_user_id, created_at) "
                            "VALUES (:doc, :tag, 'ki', :conf, :user, :now)"
                        ),
                        {
                            "doc": doc_id,
                            "tag": tag_id,
                            "conf": confidence,
                            "user": user_id,
                            "now": now,
                        },
                    )
                    stats.document_tags_applied += 1

    def _ensure_topics(
        self,
        *,
        workspace_id: str,
        user_id: str,
        topic_names: list[str],
        source_doc_ids: list[str],
        tag_ids: list[str],
        stats: ImportStats,
    ) -> None:
        for raw in topic_names:
            title = raw.strip()
            if not title:
                continue
            slug = _slugify(title)

            topic = self._session.execute(
                select(Topic).where(
                    Topic.workspace_id == workspace_id,
                    Topic.slug == slug,
                    Topic.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            if topic is None:
                now = _now()
                topic = Topic(
                    id=str(uuid4()),
                    workspace_id=workspace_id,
                    title=title,
                    slug=slug,
                    summary=None,
                    status="draft",
                    created_by=user_id,
                    approved_at=None,
                    approved_by=None,
                    deleted_at=None,
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(topic)
                self._session.flush()
                stats.topics_created += 1
            else:
                stats.topics_found += 1

            self._attach_docs_to_topic(topic, source_doc_ids, stats)
            self._attach_tags_to_topic(topic, tag_ids, stats)

    def _attach_docs_to_topic(
        self,
        topic: Topic,
        doc_ids: list[str],
        stats: ImportStats,
    ) -> None:
        for doc_id in doc_ids:
            exists = self._session.execute(
                select(TopicDocument).where(
                    TopicDocument.topic_id == topic.id,
                    TopicDocument.document_id == doc_id,
                )
            ).scalar_one_or_none()
            if exists is None:
                self._session.add(
                    TopicDocument(
                        id=str(uuid4()),
                        topic_id=topic.id,
                        document_id=doc_id,
                        relation_type="related",
                        created_at=_now(),
                    )
                )
                stats.topic_docs_attached += 1

    def _attach_tags_to_topic(
        self,
        topic: Topic,
        tag_ids: list[str],
        stats: ImportStats,
    ) -> None:
        for tag_id in tag_ids:
            exists = self._session.execute(
                select(TopicTag).where(
                    TopicTag.topic_id == topic.id,
                    TopicTag.tag_id == tag_id,
                )
            ).scalar_one_or_none()
            if exists is None:
                self._session.add(
                    TopicTag(
                        topic_id=topic.id,
                        tag_id=tag_id,
                        created_at=_now(),
                    )
                )
                stats.topic_tags_applied += 1
