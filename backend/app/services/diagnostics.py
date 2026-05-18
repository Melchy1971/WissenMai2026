from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.documents import BackgroundJob, ChatMessage, ChatSession, Chunk, Document, DocumentVersion
from app.observability.logging import get_observability_context
from app.schemas.admin import (
    DiagnosticsAuthResponse,
    DiagnosticsCountsResponse,
    DiagnosticsDatabaseResponse,
    DiagnosticsDriftAwarenessResponse,
    DiagnosticsIndicatorResponse,
    DiagnosticsImportsResponse,
    DiagnosticsOperationalMetricResponse,
    DiagnosticsResponse,
    DiagnosticsSearchResponse,
    DiagnosticsSystemResponse,
    DiagnosticsWarningModelResponse,
)
from app.services.queue_aging_service import QueueAgingService


REPO_ROOT = Path(__file__).resolve().parents[3]
RETRIEVAL_LATEST_REPORT = REPO_ROOT / "reports" / "m5_retrieval" / "latest.json"
RESTORE_TRUTH_REPORT = REPO_ROOT / "reports" / "restore_truth_report.md"
RESTORE_RUNTIME_STATUS = REPO_ROOT / "reports" / "restore_runtime_status.json"


def _format_age_days(age_days: float) -> str:
    return f"{age_days:.1f}".rstrip("0").rstrip(".")


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
        operational_metrics = self._operational_metrics(workspace_id=workspace_id, search=search)
        drift_awareness = self._drift_awareness(workspace_id=workspace_id, search=search)

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
            correlation_id=get_observability_context().correlation_id,
            operational_metrics=operational_metrics,
            drift_awareness=drift_awareness,
        )

    def _operational_metrics(
        self,
        *,
        workspace_id: str,
        search: DiagnosticsSearchResponse,
    ) -> list[DiagnosticsOperationalMetricResponse]:
        return [
            self._queue_degraded_metric(workspace_id=workspace_id),
            self._search_drift_metric(search=search),
            self._backup_staleness_metric(),
            self._reindex_running_metric(workspace_id=workspace_id),
            self._restore_mode_metric(),
            self._retrieval_regression_metric(),
        ]

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

    def _drift_awareness(
        self,
        *,
        workspace_id: str,
        search: DiagnosticsSearchResponse,
    ) -> DiagnosticsDriftAwarenessResponse:
        indicators = [
            self._search_drift_indicator(search=search),
            self._queue_degraded_indicator(workspace_id=workspace_id),
            self._restore_mode_indicator(),
            self._reindex_running_indicator(),
            self._retrieval_regression_indicator(),
            self._backup_staleness_indicator(),
        ]
        return DiagnosticsDriftAwarenessResponse(
            concept=[
                "Degradierte Betriebszustaende muessen sichtbar bleiben, auch wenn Fachdaten noch lesbar sind.",
                "Fehlende oder veraltete Evidenz wird als Warnsignal gerendert und nie als gesund angenommen.",
                "Der hoechste aktive Schweregrad steuert die Wahrnehmung; Warnungen duerfen nicht im Kartenraster verschwinden.",
            ],
            warning_model=DiagnosticsWarningModelResponse(
                no_silent_degradation=True,
                no_fake_green=True,
                no_hidden_warnings=True,
                unknown_is_not_ok=True,
                highest_severity_wins=True,
            ),
            indicators=indicators,
        )

    def _search_drift_metric(self, *, search: DiagnosticsSearchResponse) -> DiagnosticsOperationalMetricResponse:
        indicator = self._search_drift_indicator(search=search)
        return DiagnosticsOperationalMetricResponse(
            key="search_drift",
            label="Drift erkannt",
            state="active" if indicator.state == "active" else "inactive",
            severity=indicator.severity,
            value="Index fehlt" if not search.index_available else str(search.stale_index_entries),
            summary=indicator.summary,
            source=indicator.source,
        )

    def _search_drift_indicator(self, *, search: DiagnosticsSearchResponse) -> DiagnosticsIndicatorResponse:
        if not search.index_available:
            return DiagnosticsIndicatorResponse(
                key="search_drift",
                label="Search Drift erkannt",
                state="active",
                severity="critical",
                summary="Search-Index ist nicht verfuegbar; jede Suchanzeige ist damit verdachtsbehaftet.",
                source="diagnostics.search.index_available",
            )
        if search.stale_index_entries > 0:
            return DiagnosticsIndicatorResponse(
                key="search_drift",
                label="Search Drift erkannt",
                state="active",
                severity="warning",
                summary=f"{search.stale_index_entries} stale Index-Eintraege weichen vom Lifecycle-/Searchability-Zustand ab.",
                source="diagnostics.search.stale_index_entries",
            )
        return DiagnosticsIndicatorResponse(
            key="search_drift",
            label="Search Drift erkannt",
            state="inactive",
            severity="info",
            summary="Kein Search-Drift im aktuellen Diagnostics-Snapshot erkannt.",
            source="diagnostics.search.stale_index_entries",
        )

    def _queue_degraded_indicator(self, *, workspace_id: str) -> DiagnosticsIndicatorResponse:
        queue_report = QueueAgingService.from_session(self.session).get_aging_report(workspace_id=workspace_id)
        severity = queue_report["severity"]
        if severity == "critical":
            return DiagnosticsIndicatorResponse(
                key="queue_degraded",
                label="Queue degraded",
                state="active",
                severity="critical",
                summary=f"Queue kritisch: {queue_report['queue_backlog_count']} aktive Jobs, {queue_report['stuck_running_count']} stuck running, {queue_report['dead_letter_count']} dead-letter.",
                source="queue_aging_report",
            )
        if severity == "warning":
            return DiagnosticsIndicatorResponse(
                key="queue_degraded",
                label="Queue degraded",
                state="active",
                severity="warning",
                summary=f"Queue unter Druck: Backlog {queue_report['queue_backlog_count']}, Retry-Rate {queue_report['retry_rate_per_hour']:.1f}/h, Dead-Letter {queue_report['dead_letter_count']}.",
                source="queue_aging_report",
            )
        return DiagnosticsIndicatorResponse(
            key="queue_degraded",
            label="Queue degraded",
            state="inactive",
            severity="info",
            summary="Queue-Aging-Report meldet keine Degradierung fuer den aktiven Workspace.",
            source="queue_aging_report",
        )

    def _queue_degraded_metric(self, *, workspace_id: str) -> DiagnosticsOperationalMetricResponse:
        queue_report = QueueAgingService.from_session(self.session).get_aging_report(workspace_id=workspace_id)
        indicator = self._queue_degraded_indicator(workspace_id=workspace_id)
        return DiagnosticsOperationalMetricResponse(
            key=indicator.key,
            label=indicator.label,
            state="active" if indicator.state == "active" else "inactive",
            severity=indicator.severity,
            value=(
                f"Backlog {queue_report['queue_backlog_count']}"
                f" · Dead-Letter {queue_report['dead_letter_count']}"
                f" · Retry {queue_report['retry_rate_per_hour']:.1f}/h"
            ),
            summary=indicator.summary,
            source=indicator.source,
        )

    def _restore_mode_indicator(self) -> DiagnosticsIndicatorResponse:
        metric = self._restore_mode_metric()
        return DiagnosticsIndicatorResponse(
            key=metric.key,
            label=metric.label,
            state=metric.state,
            severity=metric.severity,
            summary=metric.summary,
            source=metric.source,
        )

    def _reindex_running_indicator(self) -> DiagnosticsIndicatorResponse:
        metric = self._reindex_running_metric(workspace_id=None)
        return DiagnosticsIndicatorResponse(
            key=metric.key,
            label=metric.label,
            state=metric.state,
            severity=metric.severity,
            summary=metric.summary,
            source=metric.source,
        )

    def _reindex_running_metric(self, *, workspace_id: str | None) -> DiagnosticsOperationalMetricResponse:
        filters = [BackgroundJob.job_type == "search_index_rebuild", BackgroundJob.status.in_(("pending", "running"))]
        if workspace_id is not None:
            filters.append(BackgroundJob.workspace_id == workspace_id)

        active_count = self._scalar_count(select(func.count()).select_from(BackgroundJob).where(*filters))
        if active_count > 1:
            return DiagnosticsOperationalMetricResponse(
                key="reindex_running",
                label="Reindex aktiv",
                state="active",
                severity="critical",
                value=str(active_count),
                summary=f"{active_count} Reindex-Jobs sind gleichzeitig aktiv oder pending; das ist operativ auffaellig.",
                source="background_jobs.search_index_rebuild",
            )
        if active_count == 1:
            return DiagnosticsOperationalMetricResponse(
                key="reindex_running",
                label="Reindex aktiv",
                state="active",
                severity="warning",
                value="1",
                summary="Ein Reindex-Job ist im Backend aktiv oder pending.",
                source="background_jobs.search_index_rebuild",
            )
        return DiagnosticsOperationalMetricResponse(
            key="reindex_running",
            label="Reindex aktiv",
            state="inactive",
            severity="info",
            value="0",
            summary="Kein aktiver Reindex-Job im Backend gefunden.",
            source="background_jobs.search_index_rebuild",
        )

    def _retrieval_regression_indicator(self) -> DiagnosticsIndicatorResponse:
        metric = self._retrieval_regression_metric()
        return DiagnosticsIndicatorResponse(
            key=metric.key,
            label=metric.label,
            state=metric.state,
            severity=metric.severity,
            summary=metric.summary,
            source=metric.source,
        )

    def _retrieval_regression_metric(self) -> DiagnosticsOperationalMetricResponse:
        if not RETRIEVAL_LATEST_REPORT.exists():
            return DiagnosticsOperationalMetricResponse(
                key="retrieval_regression",
                label="Retrieval Regression erkannt",
                state="active",
                severity="warning",
                value="kein Report",
                summary="Kein Retrieval-Benchmark-Report gefunden; Retrieval-Qualitaet ist derzeit nicht nachgewiesen.",
                source="reports/m5_retrieval/latest.json",
            )

        report = json.loads(RETRIEVAL_LATEST_REPORT.read_text(encoding="utf-8"))
        summary = report.get("summary", {})
        thresholds = report.get("thresholds", {})
        regressions = report.get("regressions", [])
        lifecycle_violations = report.get("lifecycle_violations", [])
        failed_metrics = [
            key
            for key, threshold in thresholds.items()
            if key in summary and isinstance(threshold, (int, float)) and float(summary[key]) < float(threshold)
        ]
        if summary.get("status") != "pass" or regressions or lifecycle_violations or failed_metrics:
            failed = ", ".join(failed_metrics[:3]) or "status/regressions"
            return DiagnosticsOperationalMetricResponse(
                key="retrieval_regression",
                label="Retrieval Regression erkannt",
                state="active",
                severity="critical",
                value=f"{len(regressions)} Regressionen",
                summary=f"Retrieval-Benchmark unterschreitet Baseline ({failed}). Regressionen: {len(regressions)}, Lifecycle-Verstoesse: {len(lifecycle_violations)}.",
                source="reports/m5_retrieval/latest.json",
            )
        return DiagnosticsOperationalMetricResponse(
            key="retrieval_regression",
            label="Retrieval Regression erkannt",
            state="inactive",
            severity="info",
            value=str(summary.get("status") or "pass"),
            summary="Aktueller Retrieval-Benchmark liegt innerhalb der definierten Baseline.",
            source="reports/m5_retrieval/latest.json",
        )

    def _backup_staleness_indicator(self) -> DiagnosticsIndicatorResponse:
        metric = self._backup_staleness_metric()
        return DiagnosticsIndicatorResponse(
            key=metric.key,
            label=metric.label,
            state=metric.state,
            severity=metric.severity,
            summary=metric.summary,
            source=metric.source,
        )

    def _backup_staleness_metric(self) -> DiagnosticsOperationalMetricResponse:
        if not RESTORE_TRUTH_REPORT.exists():
            return DiagnosticsOperationalMetricResponse(
                key="backup_stale",
                label="Backup veraltet",
                state="active",
                severity="warning",
                value="kein Nachweis",
                summary="Kein aktueller Restore-/Backup-Nachweis gefunden; Backup-Frische ist damit nicht belegt.",
                source="reports/restore_truth_report.md",
            )

        age_days = (datetime.now(UTC) - datetime.fromtimestamp(RESTORE_TRUTH_REPORT.stat().st_mtime, tz=UTC)).total_seconds() / 86400
        if age_days > 7:
            return DiagnosticsOperationalMetricResponse(
                key="backup_stale",
                label="Backup veraltet",
                state="active",
                severity="critical",
                value=f"{_format_age_days(age_days)} Tage",
                summary=f"Letzter Restore-/Backup-Nachweis ist {_format_age_days(age_days)} Tage alt und ueberschreitet die 7-Tage-Grenze.",
                source="reports/restore_truth_report.md",
            )
        if age_days > 6:
            return DiagnosticsOperationalMetricResponse(
                key="backup_stale",
                label="Backup veraltet",
                state="active",
                severity="warning",
                value=f"{_format_age_days(age_days)} Tage",
                summary=f"Letzter Restore-/Backup-Nachweis ist {_format_age_days(age_days)} Tage alt und naehrt die Veraltet-Schwelle.",
                source="reports/restore_truth_report.md",
            )
        return DiagnosticsOperationalMetricResponse(
            key="backup_stale",
            label="Backup veraltet",
            state="inactive",
            severity="info",
            value=f"{_format_age_days(age_days)} Tage",
            summary=f"Restore-/Backup-Nachweis ist {_format_age_days(age_days)} Tage alt und damit noch innerhalb der Frische-Schwelle.",
            source="reports/restore_truth_report.md",
        )

    def _restore_mode_metric(self) -> DiagnosticsOperationalMetricResponse:
        if not RESTORE_RUNTIME_STATUS.exists():
            return DiagnosticsOperationalMetricResponse(
                key="restore_mode",
                label="Restore aktiv",
                state="inactive",
                severity="info",
                value="0",
                summary="Kein aktiver Restore-Lauf im Backend markiert.",
                source="reports/restore_runtime_status.json",
            )

        payload = json.loads(RESTORE_RUNTIME_STATUS.read_text(encoding="utf-8"))
        if payload.get("active") is True:
            started_at = str(payload.get("started_at") or "unbekannt")
            return DiagnosticsOperationalMetricResponse(
                key="restore_mode",
                label="Restore aktiv",
                state="active",
                severity="warning",
                value="1",
                summary=f"Ein Restore-Lauf ist im Backend aktiv. Start: {started_at}.",
                source="reports/restore_runtime_status.json",
            )

        return DiagnosticsOperationalMetricResponse(
            key="restore_mode",
            label="Restore aktiv",
            state="inactive",
            severity="info",
            value="0",
            summary="Restore-Runtime-Marker ist vorhanden, meldet aber keinen aktiven Lauf.",
            source="reports/restore_runtime_status.json",
        )

    def _environment(self) -> str:
        if settings.app_env in {"local", "test", "production"}:
            return settings.app_env
        return "local"

    def _scalar_count(self, statement) -> int:
        return int(self.session.execute(statement).scalar_one() or 0)
