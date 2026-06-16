from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.data_quality import DataQualityRun
from app.models.documents import BackgroundJob, Document
from app.models.drift import DriftRun
from app.models.topics import Topic, TopicTag
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardActivityResponse,
    DashboardAnalysisItem,
    DashboardAnalysisResponse,
    DashboardImportItem,
    DashboardImportsResponse,
    DashboardQualityItem,
    DashboardQualityResponse,
    DashboardSummary,
    DashboardTopicItem,
    DashboardTopicsResponse,
    TopicsDayCount,
    TopicTagCount,
    TopicsWidgetData,
)


class DashboardSummaryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_summary(self, *, workspace_id: str) -> DashboardSummary:
        document_count = self._count_documents(workspace_id)
        active_document_count = self._count_documents(workspace_id, lifecycle_status="active")
        archived_document_count = self._count_documents(workspace_id, lifecycle_status="archived")

        return DashboardSummary(
            document_count=document_count,
            active_document_count=active_document_count,
            archived_document_count=archived_document_count,
            new_imports_count=self._count_new_imports(workspace_id),
            open_analysis_count=self._count_open_analysis(workspace_id),
            topic_count=self._count_topics(workspace_id),
            quality_score=self._latest_quality_score(workspace_id),
            drift_status=self._latest_drift_status(workspace_id),
        )

    def list_activity(self, *, workspace_id: str, limit: int = 20) -> DashboardActivityResponse:
        items: list[DashboardActivityItem] = []
        items.extend(
            DashboardActivityItem(
                id=document.id,
                item_type="document",
                title=document.title,
                status=document.lifecycle_status,
                created_at=document.created_at,
            )
            for document in self._session.scalars(
                select(Document)
                .where(Document.workspace_id == workspace_id)
                .order_by(Document.created_at.desc())
                .limit(limit)
            )
        )
        items.extend(
            DashboardActivityItem(
                id=job.id,
                item_type="import",
                title=_safe_import_title(job.payload_),
                status=job.status,
                created_at=job.created_at,
            )
            for job in self._session.scalars(
                select(BackgroundJob)
                .where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.job_type == "document_import")
                .order_by(BackgroundJob.created_at.desc())
                .limit(limit)
            )
        )
        items.extend(
            DashboardActivityItem(
                id=job.id,
                item_type="analysis",
                title=job.analysis_type,
                status=job.status,
                created_at=job.created_at,
            )
            for job in self._session.scalars(
                select(AnalysisJob)
                .where(AnalysisJob.workspace_id == workspace_id)
                .order_by(AnalysisJob.created_at.desc())
                .limit(limit)
            )
        )
        items.extend(
            DashboardActivityItem(
                id=run.id,
                item_type="quality",
                title="Data quality",
                status=run.status,
                created_at=run.started_at,
            )
            for run in self._session.scalars(
                select(DataQualityRun)
                .where(DataQualityRun.workspace_id == workspace_id)
                .order_by(DataQualityRun.started_at.desc())
                .limit(limit)
            )
        )
        items.extend(
            DashboardActivityItem(
                id=run.id,
                item_type="drift",
                title="Drift detection",
                status=run.status,
                created_at=run.created_at,
            )
            for run in self._session.scalars(
                select(DriftRun)
                .where(DriftRun.workspace_id == workspace_id)
                .order_by(DriftRun.created_at.desc())
                .limit(limit)
            )
        )
        items.sort(key=lambda item: item.created_at, reverse=True)
        return DashboardActivityResponse(items=items[:limit], total=len(items))

    def list_imports(self, *, workspace_id: str, limit: int = 20) -> DashboardImportsResponse:
        jobs = self._session.scalars(
            select(BackgroundJob)
            .where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.job_type == "document_import")
            .order_by(BackgroundJob.created_at.desc())
            .limit(limit)
        ).all()
        return DashboardImportsResponse(
            items=[
                DashboardImportItem(
                    id=job.id,
                    status=job.status,
                    filename=_safe_import_filename(job.payload_),
                    mime_type=_safe_import_mime_type(job.payload_),
                    created_at=job.created_at,
                    started_at=job.started_at,
                    finished_at=job.finished_at,
                )
                for job in jobs
            ],
            total=len(jobs),
        )

    def list_analysis(self, *, workspace_id: str, limit: int = 20) -> DashboardAnalysisResponse:
        jobs = self._session.scalars(
            select(AnalysisJob)
            .where(AnalysisJob.workspace_id == workspace_id)
            .order_by(AnalysisJob.created_at.desc())
            .limit(limit)
        ).all()
        return DashboardAnalysisResponse(
            items=[
                DashboardAnalysisItem(
                    id=job.id,
                    status=job.status,
                    analysis_type=job.analysis_type,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    finished_at=job.finished_at,
                )
                for job in jobs
            ],
            total=len(jobs),
        )

    def list_quality(self, *, workspace_id: str, limit: int = 20) -> DashboardQualityResponse:
        runs = self._session.scalars(
            select(DataQualityRun)
            .where(DataQualityRun.workspace_id == workspace_id)
            .order_by(DataQualityRun.started_at.desc())
            .limit(limit)
        ).all()
        return DashboardQualityResponse(
            items=[
                DashboardQualityItem(
                    id=run.id,
                    status=run.status,
                    quality_score=run.quality_score,
                    total_findings=run.total_findings,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                )
                for run in runs
            ],
            total=len(runs),
        )

    def list_topics(self, *, workspace_id: str, limit: int = 50) -> DashboardTopicsResponse:
        rows = self._session.execute(
            select(AnalysisJob.id, AnalysisJob.created_at, AnalysisResult.suggested_topics)
            .join(AnalysisResult, AnalysisResult.job_id == AnalysisJob.id)
            .where(AnalysisJob.workspace_id == workspace_id)
            .order_by(AnalysisJob.created_at.desc())
        ).all()
        topic_counts: dict[str, int] = {}
        latest_job_by_topic: dict[str, str] = {}
        for job_id, _created_at, suggested_topics in rows:
            if not isinstance(suggested_topics, list):
                continue
            for topic in suggested_topics:
                name = str(topic).strip()
                if not name:
                    continue
                topic_counts[name] = topic_counts.get(name, 0) + 1
                latest_job_by_topic.setdefault(name, job_id)
        items = [
            DashboardTopicItem(name=name, count=count, latest_job_id=latest_job_by_topic.get(name))
            for name, count in sorted(topic_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return DashboardTopicsResponse(items=items[:limit], total=len(items))

    def _count_documents(self, workspace_id: str, *, lifecycle_status: str | None = None) -> int:
        query = select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
        if lifecycle_status is not None:
            query = query.where(Document.lifecycle_status == lifecycle_status)
        return int(self._session.scalar(query) or 0)

    def _count_new_imports(self, workspace_id: str) -> int:
        return int(
            self._session.scalar(
                select(func.count(Document.id)).where(
                    Document.workspace_id == workspace_id,
                    Document.import_status.in_(("pending", "parsing")),
                    Document.lifecycle_status != "deleted",
                )
            )
            or 0
        )

    def _count_open_analysis(self, workspace_id: str) -> int:
        return int(
            self._session.scalar(
                select(func.count(AnalysisJob.id)).where(
                    AnalysisJob.workspace_id == workspace_id,
                    AnalysisJob.status.in_(("pending", "running")),
                )
            )
            or 0
        )

    def _count_topics(self, workspace_id: str) -> int:
        rows = self._session.scalars(
            select(AnalysisResult.suggested_topics)
            .join(AnalysisJob, AnalysisJob.id == AnalysisResult.job_id)
            .where(AnalysisJob.workspace_id == workspace_id)
        ).all()
        topics: set[str] = set()
        for row in rows:
            if isinstance(row, list):
                topics.update(str(item).strip() for item in row if str(item).strip())
        return len(topics)

    def _latest_quality_score(self, workspace_id: str) -> float | None:
        return self._session.scalar(
            select(DataQualityRun.quality_score)
            .where(
                DataQualityRun.workspace_id == workspace_id,
                DataQualityRun.status == "completed",
            )
            .order_by(DataQualityRun.started_at.desc())
            .limit(1)
        )

    def _latest_drift_status(self, workspace_id: str) -> str | None:
        return self._session.scalar(
            select(DriftRun.status)
            .where(DriftRun.workspace_id == workspace_id)
            .order_by(DriftRun.created_at.desc())
            .limit(1)
        )


def _safe_import_filename(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("filename")
    return str(value) if value is not None else None


def _safe_import_mime_type(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("mime_type")
    return str(value) if value is not None else None


def _safe_import_title(payload: dict | None) -> str:
    return _safe_import_filename(payload) or "Document import"

    # -- Topics widget data ----------------------------------------------------

    def get_topics_widgets(self, *, workspace_id: str) -> TopicsWidgetData:
        """Aggregate Topics-model stats for dashboard widgets."""
        from datetime import UTC, datetime, timedelta
        from sqlalchemy import case, func, literal_column, select, text

        # 1. Total + by_status
        status_rows = self._session.execute(
            select(Topic.status, func.count(Topic.id).label("cnt"))
            .where(Topic.workspace_id == workspace_id, Topic.deleted_at.is_(None))
            .group_by(Topic.status)
        ).all()

        by_status: dict[str, int] = {"draft": 0, "review": 0, "approved": 0, "archived": 0}
        total = 0
        for status, cnt in status_rows:
            by_status[status] = int(cnt)
            total += int(cnt)

        unreviewed = by_status.get("draft", 0) + by_status.get("review", 0)

        # 2. New last 7 days + per-day breakdown
        cutoff = datetime.now(UTC) - timedelta(days=7)
        new_rows = self._session.scalars(
            select(Topic.created_at)
            .where(
                Topic.workspace_id == workspace_id,
                Topic.deleted_at.is_(None),
                Topic.created_at >= cutoff,
            )
        ).all()

        day_counts: dict[str, int] = {}
        for dt in new_rows:
            day_key = dt.strftime("%Y-%m-%d")
            day_counts[day_key] = day_counts.get(day_key, 0) + 1

        # Fill last 7 days including zeros
        new_per_day: list[TopicsDayCount] = []
        for i in range(6, -1, -1):
            d = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            new_per_day.append(TopicsDayCount(date=d, count=day_counts.get(d, 0)))

        new_last_7_days = sum(day_counts.values())

        # 3. Top tags via JOIN to tags table (no ORM model — use text)
        bind = self._session.get_bind()
        dialect = bind.dialect.name if bind else "sqlite"

        if dialect == "postgresql":
            tag_sql = text("""
                SELECT t.name, COUNT(tt.topic_id) AS cnt
                FROM tags t
                JOIN topic_tags tt ON tt.tag_id = t.id
                JOIN topics tp ON tp.id = tt.topic_id
                WHERE tp.workspace_id = :ws AND tp.deleted_at IS NULL
                GROUP BY t.name
                ORDER BY cnt DESC
                LIMIT 10
            """)
        else:
            tag_sql = text("""
                SELECT t.name, COUNT(tt.topic_id) AS cnt
                FROM tags t
                JOIN topic_tags tt ON tt.tag_id = t.id
                JOIN topics tp ON tp.id = tt.topic_id
                WHERE tp.workspace_id = :ws AND tp.deleted_at IS NULL
                GROUP BY t.name
                ORDER BY cnt DESC
                LIMIT 10
            """)

        tag_rows = self._session.execute(tag_sql, {"ws": workspace_id}).all()
        top_tags = [TopicTagCount(name=str(row[0]), count=int(row[1])) for row in tag_rows]

        return TopicsWidgetData(
            total=total,
            by_status=by_status,
            new_last_7_days=new_last_7_days,
            new_per_day=new_per_day,
            unreviewed=unreviewed,
            top_tags=top_tags,
        )
