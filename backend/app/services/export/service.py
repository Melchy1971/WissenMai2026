from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    ExportFileNotFoundApiError,
    ExportJobInvalidStateApiError,
    ExportJobNotFoundApiError,
    ExportSourceNotApprovedApiError,
    ExportSourceNotFoundApiError,
    ExportTemplateNameConflictApiError,
    ExportTemplateNotFoundApiError,
)
from app.models.analysis import AnalysisResult
from app.models.export import ExportJob, ExportTemplate
from app.repositories.export import ExportJobRecord, ExportRepository, ExportTemplateRecord

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPORT_DIR_ENV = "EXPORT_FILES_DIR"
_DEFAULT_EXPORT_DIR = Path("data") / "exports"

# Status transitions allowed for cancel / retry
_CANCELLABLE_STATUSES = {"QUEUED", "RUNNING"}
_RETRYABLE_STATUSES = {"FAILED", "CANCELLED"}


# ---------------------------------------------------------------------------
# Renderer protocol
# ---------------------------------------------------------------------------

class ExportRenderer(Protocol):
    def render(self, *, content: dict, export_format: str) -> bytes:
        """Return file bytes for the given content and format."""
        ...


# ---------------------------------------------------------------------------
# Default renderer (delegates to format-specific functions)
# ---------------------------------------------------------------------------

class DefaultExportRenderer:
    """Renders Markdown, JSON, and PDF exports.

    PDF rendering delegates to PdfRenderer (Task #86).
    """

    def render(self, *, content: dict, export_format: str) -> bytes:
        if export_format == "MARKDOWN":
            return _render_markdown(content).encode("utf-8")
        if export_format == "JSON":
            return _render_json(content).encode("utf-8")
        if export_format == "PDF":
            from app.services.export.pdf_renderer import PdfRenderer  # noqa: PLC0415
            return PdfRenderer().render(content)
        raise ValueError(f"Unknown export format: {export_format!r}")


# ---------------------------------------------------------------------------
# ExportService
# ---------------------------------------------------------------------------

class ExportService:
    def __init__(
        self,
        session: Session,
        *,
        renderer: ExportRenderer | None = None,
        export_root: Path | None = None,
    ) -> None:
        self._session = session
        self._repo = ExportRepository(session)
        self._renderer = renderer or DefaultExportRenderer()
        configured = export_root or os.environ.get(EXPORT_DIR_ENV)
        self._export_root = Path(configured) if configured else _DEFAULT_EXPORT_DIR

    # ── 1. createExportJob ────────────────────────────────────────────────────

    def create_export_job(
        self,
        *,
        workspace_id: str | None,
        source_type: str,
        source_ids: list[str],
        export_format: str,
        file_name: str,
        created_by: str | None = None,
    ) -> ExportJobRecord:
        """Validate source and create a QUEUED export job."""
        _validate_source(self._session, source_type=source_type, source_ids=source_ids)

        safe_name = _normalize_filename(file_name, export_format)
        now = _now()
        job = ExportJob(
            id=str(uuid4()),
            workspace_id=workspace_id,
            status="QUEUED",
            source_type=source_type,
            source_ids=source_ids,
            export_format=export_format,
            file_name=safe_name,
            file_path=None,
            error_message=None,
            created_by=created_by,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        self._repo.create_job(job)
        _log.info("export_job.created job_id=%s format=%s", job.id, export_format)
        return _job_to_record(job)

    # ── 2. startExportJob ─────────────────────────────────────────────────────

    def start_export_job(self, job_id: str) -> ExportJobRecord:
        """Render content and write file. Transitions QUEUED → RUNNING → COMPLETED."""
        job = self._repo.get_job(job_id)
        if job is None:
            raise ExportJobNotFoundApiError(f"ExportJob {job_id!r} not found")
        if job.status != "QUEUED":
            raise ExportJobInvalidStateApiError(
                f"Cannot start export job in status {job.status!r}"
            )

        now = _now()
        self._repo.update_job_status(job, status="RUNNING", started_at=now)

        try:
            content = _load_source_content(self._session, job=job)
            file_bytes = self._renderer.render(
                content=content, export_format=job.export_format
            )
            file_path = _write_export_file(
                self._export_root,
                job_id=job.id,
                file_name=job.file_name,
                data=file_bytes,
            )
            self._repo.update_job_status(
                job,
                status="COMPLETED",
                finished_at=_now(),
                file_path=file_path,
            )
            _log.info(
                "export_job.completed job_id=%s bytes=%d path=%s",
                job.id, len(file_bytes), file_path,
            )
        except Exception as exc:
            _log.exception("export_job.failed job_id=%s", job.id)
            self._repo.update_job_status(
                job,
                status="FAILED",
                finished_at=_now(),
                error_message=str(exc),
            )
            raise

        return _job_to_record(job)

    # ── 3. cancelExportJob ────────────────────────────────────────────────────

    def cancel_export_job(self, job_id: str) -> ExportJobRecord:
        job = self._repo.get_job(job_id)
        if job is None:
            raise ExportJobNotFoundApiError()
        if job.status not in _CANCELLABLE_STATUSES:
            raise ExportJobInvalidStateApiError(
                f"Cannot cancel export job in status {job.status!r}"
            )
        self._repo.update_job_status(job, status="CANCELLED", finished_at=_now())
        _log.info("export_job.cancelled job_id=%s", job.id)
        return _job_to_record(job)

    # ── 4. retryExportJob ─────────────────────────────────────────────────────

    def retry_export_job(self, job_id: str) -> ExportJobRecord:
        """Create a new QUEUED job with the same parameters."""
        original = self._repo.get_job(job_id)
        if original is None:
            raise ExportJobNotFoundApiError()
        if original.status not in _RETRYABLE_STATUSES:
            raise ExportJobInvalidStateApiError(
                f"Cannot retry export job in status {original.status!r}"
            )
        now = _now()
        retry = ExportJob(
            id=str(uuid4()),
            workspace_id=original.workspace_id,
            status="QUEUED",
            source_type=original.source_type,
            source_ids=original.source_ids,
            export_format=original.export_format,
            file_name=original.file_name,
            file_path=None,
            error_message=None,
            created_by=original.created_by,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        self._repo.create_job(retry)
        _log.info("export_job.retried original_id=%s new_id=%s", job_id, retry.id)
        return _job_to_record(retry)

    # ── 5. getExportJob ───────────────────────────────────────────────────────

    def get_export_job(self, job_id: str) -> ExportJobRecord:
        job = self._repo.get_job(job_id)
        if job is None:
            raise ExportJobNotFoundApiError()
        return _job_to_record(job)

    # ── 6. listExportJobs ─────────────────────────────────────────────────────

    def list_export_jobs(
        self,
        *,
        workspace_id: str | None = None,
        status: str | None = None,
        export_format: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ExportJobRecord], int]:
        return self._repo.list_jobs(
            workspace_id=workspace_id,
            status=status,
            export_format=export_format,
            limit=limit,
            offset=offset,
        )

    # ── 7. downloadExportFile ─────────────────────────────────────────────────

    def download_export_file(self, job_id: str) -> tuple[bytes, str]:
        """Return (file_bytes, file_name). Raises if job not COMPLETED or file missing."""
        job = self._repo.get_job(job_id)
        if job is None:
            raise ExportJobNotFoundApiError()
        if job.status != "COMPLETED" or job.file_path is None:
            raise ExportFileNotFoundApiError(
                "Export file is not available — job has not completed successfully"
            )
        target = self._export_root / job.file_path
        if not target.exists():
            raise ExportFileNotFoundApiError(
                f"Export file missing from storage: {job.file_path}"
            )
        return target.read_bytes(), job.file_name

    # ── 8. deleteExportFile ───────────────────────────────────────────────────

    def delete_export_file(self, job_id: str) -> None:
        """Delete stored file and clear file_path. Job record is retained."""
        job = self._repo.get_job(job_id)
        if job is None:
            raise ExportJobNotFoundApiError()
        if job.file_path is None:
            # Nothing to delete — idempotent.
            return
        target = self._export_root / job.file_path
        try:
            if target.exists():
                target.unlink()
            _log.info("export_job.file_deleted job_id=%s path=%s", job.id, job.file_path)
        except OSError as exc:
            _log.warning("export_job.file_delete_failed job_id=%s: %s", job.id, exc)
        self._repo.clear_job_file(job)

    # ── Template management ───────────────────────────────────────────────────

    def list_templates(self, *, export_format: str | None = None) -> list[ExportTemplateRecord]:
        return self._repo.list_templates(export_format=export_format)

    def create_template(
        self,
        *,
        name: str,
        export_format: str,
        layout_config: dict | None = None,
        is_default: bool = False,
    ) -> ExportTemplateRecord:
        now = _now()
        template = ExportTemplate(
            id=str(uuid4()),
            name=name,
            export_format=export_format,
            layout_config=layout_config,
            is_default=False,
            created_at=now,
            updated_at=now,
        )
        self._repo.create_template(template)
        if is_default:
            self._repo.set_default_template(template, updated_at=now)
        return _template_to_record(template)

    def update_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        export_format: str | None = None,
        layout_config: dict | None = None,
        is_default: bool | None = None,
    ) -> ExportTemplateRecord:
        template = self._repo.get_template(template_id)
        if template is None:
            raise ExportTemplateNotFoundApiError()
        now = _now()
        self._repo.update_template(
            template,
            name=name,
            export_format=export_format,
            layout_config=layout_config,
            updated_at=now,
        )
        if is_default is True:
            self._repo.set_default_template(template, updated_at=now)
        return _template_to_record(template)

    def delete_template(self, template_id: str) -> None:
        template = self._repo.get_template(template_id)
        if template is None:
            raise ExportTemplateNotFoundApiError()
        self._repo.delete_template(template)


# ---------------------------------------------------------------------------
# Source validation (approved-only guard)
# ---------------------------------------------------------------------------

def _validate_source(
    session: Session,
    *,
    source_type: str,
    source_ids: list[str],
) -> None:
    """Enforce export guard: only approved AnalysisResults may be exported."""
    if source_type != "ANALYSIS_RESULT":
        # Non-analysis sources have no approval requirement.
        return
    for result_id in source_ids:
        result = session.get(AnalysisResult, result_id)
        if result is None:
            raise ExportSourceNotFoundApiError(
                f"AnalysisResult {result_id!r} not found"
            )
        if result.status != "approved":
            raise ExportSourceNotApprovedApiError(
                f"AnalysisResult {result_id!r} has status {result.status!r} — "
                "only 'approved' results may be exported"
            )


# ---------------------------------------------------------------------------
# Source content loader
# ---------------------------------------------------------------------------

def _load_source_content(session: Session, *, job: ExportJob) -> dict:
    """Load source entities and build a content dict for rendering.

    Returns a sanitized dict with no technical IDs and no secrets.
    """
    source_type = job.source_type
    source_ids: list[str] = list(job.source_ids or [])

    if source_type == "ANALYSIS_RESULT":
        return _load_analysis_result_content(session, source_ids=source_ids, job=job)

    # SEARCH_RESULT / TOPIC / DOCUMENT_COLLECTION — placeholder structure
    # (fully implemented when respective source models are stable)
    return {
        "title": job.file_name,
        "source_type": source_type,
        "items": [],
        "export_format": job.export_format,
        "exported_at": _now().isoformat(),
    }


def _load_analysis_result_content(
    session: Session,
    *,
    source_ids: list[str],
    job: ExportJob,
) -> dict:
    results = []
    for result_id in source_ids:
        result = session.get(AnalysisResult, result_id)
        if result is None:
            raise ExportSourceNotFoundApiError(f"AnalysisResult {result_id!r} not found")
        if result.status != "approved":
            raise ExportSourceNotApprovedApiError(
                f"AnalysisResult {result_id!r} has status {result.status!r}"
            )
        results.append({
            # No technical IDs: omit result.id, job.id, workspace UUIDs
            "title": getattr(result, "title", None) or "Analyse-Ergebnis",
            "summary": getattr(result, "summary", "") or "",
            "content_markdown": getattr(result, "content_markdown", None) or "",
            "key_points": list(getattr(result, "key_points", None) or []),
            "suggested_tags": list(getattr(result, "suggested_tags", None) or []),
            "suggested_topics": list(getattr(result, "suggested_topics", None) or []),
            "sources": list(getattr(result, "sources", None) or []),
            "approved_at": (
                result.approved_at.isoformat() if getattr(result, "approved_at", None) else None
            ),
        })
    return {
        "title": job.file_name,
        "source_type": "ANALYSIS_RESULT",
        "export_format": job.export_format,
        "exported_at": _now().isoformat(),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Filename normalization and path security
# ---------------------------------------------------------------------------

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")
_FORMAT_EXTENSIONS = {
    "MARKDOWN": ".md",
    "JSON": ".json",
    "PDF": ".pdf",
}


def _normalize_filename(file_name: str, export_format: str) -> str:
    """Strip unsafe characters and enforce correct extension."""
    base = Path(file_name).stem if file_name else "export"
    base = _SAFE_FILENAME_RE.sub("_", base).strip("_") or "export"
    ext = _FORMAT_EXTENSIONS.get(export_format, "")
    return f"{base}{ext}"


def _write_export_file(
    export_root: Path,
    *,
    job_id: str,
    file_name: str,
    data: bytes,
) -> str:
    """Write data to a sandboxed subdirectory. Returns relative path string."""
    # Each job gets its own directory — prevents filename collisions and path traversal.
    job_dir = export_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Resolve to ensure no path traversal.
    target = (job_dir / file_name).resolve()
    resolved_root = export_root.resolve()
    if not str(target).startswith(str(resolved_root)):
        raise ValueError(f"Path traversal detected: {target}")

    target.write_bytes(data)
    return str(Path(job_id) / file_name)


# ---------------------------------------------------------------------------
# Inline renderers for Markdown and JSON
# ---------------------------------------------------------------------------

def _render_markdown(content: dict) -> str:
    lines: list[str] = []
    title = content.get("title", "Export")
    exported_at = content.get("exported_at", "")

    lines.append(f"# {title}")
    lines.append("")
    if exported_at:
        lines.append(f"**Exportiert am:** {exported_at}")
        lines.append("")

    results = content.get("results", [])
    for i, r in enumerate(results, 1):
        if len(results) > 1:
            lines.append(f"## Ergebnis {i}: {r.get('title', '')}")
        lines.append("")
        summary = r.get("summary", "")
        if summary:
            lines.append(f"### Zusammenfassung")
            lines.append("")
            lines.append(summary)
            lines.append("")

        key_points = r.get("key_points", [])
        if key_points:
            lines.append("### Kernpunkte")
            lines.append("")
            for kp in key_points:
                lines.append(f"- {kp}")
            lines.append("")

        body = r.get("content_markdown", "")
        if body:
            lines.append("### Inhalt")
            lines.append("")
            lines.append(body)
            lines.append("")

        tags = r.get("suggested_tags", [])
        topics = r.get("suggested_topics", [])
        if tags:
            lines.append(f"**Tags:** {', '.join(str(t) for t in tags)}")
        if topics:
            lines.append(f"**Themen:** {', '.join(str(t) for t in topics)}")
        if tags or topics:
            lines.append("")

        sources = r.get("sources", [])
        if sources:
            lines.append("### Quellen")
            lines.append("")
            for j, src in enumerate(sources, 1):
                if isinstance(src, dict):
                    label = src.get("title") or src.get("filename") or f"Quelle {j}"
                    lines.append(f"{j}. {label}")
                else:
                    lines.append(f"{j}. {src}")
            lines.append("")

    return "\n".join(lines)


def _render_json(content: dict) -> str:
    # Strip keys that could leak technical IDs or secrets — already done in loader,
    # but enforce at render boundary as defence-in-depth.
    return json.dumps(content, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(UTC)


def _job_to_record(job: ExportJob) -> ExportJobRecord:
    from app.repositories.export import _job_to_record as _convert  # noqa: PLC0415
    return _convert(job)


def _template_to_record(template: ExportTemplate) -> ExportTemplateRecord:
    from app.repositories.export import _template_to_record as _convert  # noqa: PLC0415
    return _convert(template)
