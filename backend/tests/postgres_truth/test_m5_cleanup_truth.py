from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.documents import AuthSession, BackgroundJob, ChatCitation, ChatMessage, ChatSession, Chunk, Document, DocumentVersion
from app.services.auth import hash_token
from app.services.m5_cleanup import CleanupConfig, M5CleanupService
from tests.postgres_truth.support import TruthIds


pytestmark = pytest.mark.postgres_truth

NOW = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)


def test_m5_cleanup_truth_orphan_cleanup_dry_run_is_safe(
    truth_session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    tmp_path: Path,
) -> None:
    seeded = _seed_document_with_citation(truth_session, truth_seed, truth_ids, label="orphan")
    service = M5CleanupService.from_session(truth_session)
    config = _config(tmp_path, workspace_id=truth_seed["workspace_id"])

    dry_run = service.dry_run(config=config)
    execute = service.execute(config=config)

    assert dry_run["mode"] == "dry_run"
    assert dry_run["categories"]["orphan_cleanup"]["candidate_count"] == 0
    assert dry_run["categories"]["orphan_cleanup"]["applied_count"] == 0
    assert execute["categories"]["orphan_cleanup"]["applied_count"] == 0
    _assert_document_citation_and_queue_safety(truth_session, seeded)


def test_m5_cleanup_truth_stale_index_cleanup_respects_lifecycle_and_citations(
    truth_session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    tmp_path: Path,
) -> None:
    active = _seed_document_with_citation(truth_session, truth_seed, truth_ids, label="active")
    archived = _seed_document_with_citation(
        truth_session,
        truth_seed,
        truth_ids,
        label="archived",
        lifecycle_status="archived",
        chunk_is_searchable=True,
    )
    active_chunk = truth_session.get(Chunk, active["chunk_id"])
    assert active_chunk is not None
    active_chunk.is_searchable = False
    truth_session.commit()

    service = M5CleanupService.from_session(truth_session)
    config = _config(tmp_path, workspace_id=truth_seed["workspace_id"])

    dry_run = service.dry_run(config=config)
    execute = service.execute(config=config)
    truth_session.expire_all()

    assert dry_run["categories"]["stale_index_cleanup"]["candidate_count"] == 2
    assert dry_run["categories"]["stale_index_cleanup"]["applied_count"] == 0
    assert execute["categories"]["stale_index_cleanup"]["applied_count"] == 2
    assert truth_session.get(Chunk, active["chunk_id"]).is_searchable is True
    assert truth_session.get(Chunk, archived["chunk_id"]).is_searchable is False
    _assert_document_citation_and_queue_safety(truth_session, active)
    _assert_document_citation_and_queue_safety(truth_session, archived)


def test_m5_cleanup_truth_temp_file_cleanup_protects_active_queue_jobs(
    truth_session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    tmp_path: Path,
) -> None:
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    orphan_temp = temp_dir / "orphan-upload.bin"
    protected_temp = temp_dir / "active-upload.bin"
    orphan_temp.write_bytes(b"old-orphan")
    protected_temp.write_bytes(b"active-job")
    _set_mtime(orphan_temp, NOW - timedelta(days=30))
    _set_mtime(protected_temp, NOW - timedelta(days=30))
    job_id = _seed_job(
        truth_session,
        truth_seed,
        truth_ids,
        label="temp-active",
        status="pending",
        temp_file_path=str(protected_temp),
    )

    service = M5CleanupService.from_session(truth_session)
    config = _config(tmp_path, temp_dir=temp_dir, workspace_id=truth_seed["workspace_id"])

    dry_run = service.dry_run(config=config)
    execute = service.execute(config=config)

    assert dry_run["categories"]["temp_file_cleanup"]["candidate_count"] == 1
    assert dry_run["categories"]["temp_file_cleanup"]["protected_count"] == 1
    assert dry_run["categories"]["temp_file_cleanup"]["applied_count"] == 0
    assert execute["categories"]["temp_file_cleanup"]["applied_count"] == 1
    assert not orphan_temp.exists()
    assert protected_temp.exists()
    assert truth_session.get(BackgroundJob, job_id).status == "pending"


def test_m5_cleanup_truth_old_report_cleanup_keeps_latest_and_fresh_reports(
    truth_session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    old_report = reports_dir / "20260101_000000.json"
    fresh_report = reports_dir / "20260512_100000.json"
    latest_report = reports_dir / "latest.json"
    old_report.write_text('{"status":"old"}\n', encoding="utf-8")
    fresh_report.write_text('{"status":"fresh"}\n', encoding="utf-8")
    latest_report.write_text('{"status":"latest"}\n', encoding="utf-8")
    _set_mtime(old_report, NOW - timedelta(days=30))
    _set_mtime(fresh_report, NOW)
    _set_mtime(latest_report, NOW - timedelta(days=30))
    seeded = _seed_document_with_citation(truth_session, truth_seed, truth_ids, label="report")

    service = M5CleanupService.from_session(truth_session)
    config = _config(tmp_path, reports_dir=reports_dir, workspace_id=truth_seed["workspace_id"])

    dry_run = service.dry_run(config=config)
    execute = service.execute(config=config)

    assert dry_run["categories"]["old_report_cleanup"]["candidate_count"] == 1
    assert dry_run["categories"]["old_report_cleanup"]["protected_count"] == 1
    assert execute["categories"]["old_report_cleanup"]["applied_count"] == 1
    assert not old_report.exists()
    assert fresh_report.exists()
    assert latest_report.exists()
    _assert_document_citation_and_queue_safety(truth_session, seeded)


def test_m5_cleanup_truth_expired_session_cleanup_keeps_active_sessions(
    truth_session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    tmp_path: Path,
) -> None:
    expired_session_id = f"truth-{truth_ids.slug}-expired-session"
    active_session_id = truth_seed["ids"].session_id
    truth_session.add(
        AuthSession(
            id=expired_session_id,
            user_id=truth_seed["user_id"],
            token_hash=hash_token(f"expired-token-{truth_ids.namespace}"),
            expires_at=NOW - timedelta(days=30),
            created_at=NOW - timedelta(days=60),
            last_seen_at=NOW - timedelta(days=31),
            revoked_at=None,
        )
    )
    seeded = _seed_document_with_citation(truth_session, truth_seed, truth_ids, label="session")
    truth_session.commit()

    service = M5CleanupService.from_session(truth_session)
    config = _config(tmp_path, workspace_id=truth_seed["workspace_id"])

    dry_run = service.dry_run(config=config)
    execute = service.execute(config=config)

    assert dry_run["categories"]["expired_session_cleanup"]["candidate_count"] == 1
    assert dry_run["categories"]["expired_session_cleanup"]["applied_count"] == 0
    assert execute["categories"]["expired_session_cleanup"]["applied_count"] == 1
    assert truth_session.get(AuthSession, expired_session_id) is None
    assert truth_session.get(AuthSession, active_session_id) is not None
    _assert_document_citation_and_queue_safety(truth_session, seeded)


def _config(
    tmp_path: Path,
    *,
    workspace_id: str,
    temp_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> CleanupConfig:
    return CleanupConfig(
        now=NOW,
        retention_days=7,
        workspace_id=workspace_id,
        temp_dir=temp_dir or tmp_path / "missing-temp",
        reports_dir=reports_dir or tmp_path / "missing-reports",
    )


def _seed_document_with_citation(
    session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    *,
    label: str,
    lifecycle_status: str = "active",
    chunk_is_searchable: bool = True,
) -> dict[str, str]:
    document_id = truth_ids.document_id(label)
    version_id = truth_ids.version_id(label)
    chunk_id = truth_ids.chunk_id(label)
    chat_session_id = truth_ids.chat_session_id(label)
    chat_message_id = truth_ids.chat_message_id(label)
    citation_id = truth_ids.citation_id(label)
    document = Document(
        id=document_id,
        workspace_id=truth_seed["workspace_id"],
        owner_user_id=truth_seed["user_id"],
        current_version_id=None,
        title=f"Truth Cleanup {label}",
        source_type="markdown",
        mime_type="text/markdown",
        content_hash=truth_ids.content_hash(label),
        import_status="chunked",
        lifecycle_status=lifecycle_status,
        archived_at=NOW if lifecycle_status == "archived" else None,
        deleted_at=NOW if lifecycle_status == "deleted" else None,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(document)
    session.flush()
    version = DocumentVersion(
        id=version_id,
        document_id=document_id,
        version_number=1,
        normalized_markdown=f"# Cleanup {label}",
        markdown_hash=truth_ids.content_hash(f"{label}-markdown"),
        parser_version="truth-parser",
        ocr_used=False,
        ki_provider=None,
        ki_model=None,
        metadata_={"truth": label},
        created_at=NOW,
    )
    session.add(version)
    session.flush()
    document.current_version_id = version_id
    chunk = Chunk(
        id=chunk_id,
        document_id=document_id,
        document_version_id=version_id,
        chunk_index=0,
        heading_path=["Cleanup"],
        anchor=f"cleanup-{label}",
        content=f"Cleanup truth content {label}",
        is_searchable=chunk_is_searchable,
        search_vector=None,
        content_hash=truth_ids.content_hash(f"{label}-chunk"),
        token_estimate=5,
        metadata_={"truth": label},
        created_at=NOW,
    )
    chat_session = ChatSession(
        id=chat_session_id,
        workspace_id=truth_seed["workspace_id"],
        owner_user_id=truth_seed["user_id"],
        title=f"Cleanup Chat {label}",
        created_at=NOW,
        updated_at=NOW,
    )
    chat_message = ChatMessage(
        id=chat_message_id,
        session_id=chat_session_id,
        message_index=0,
        role="assistant",
        content=f"Cleanup answer {label}",
        basis_type="knowledge_base",
        metadata_={},
        created_at=NOW,
    )
    citation = ChatCitation(
        id=citation_id,
        message_id=chat_message_id,
        chunk_id=chunk_id,
        document_id=document_id,
        document_title=document.title,
        quote_preview="Cleanup citation preview",
        source_anchor={"type": "heading", "value": f"cleanup-{label}"},
        source_status=lifecycle_status,
    )
    session.add_all([chunk, chat_session, chat_message, citation])
    session.commit()
    return {
        "document_id": document_id,
        "version_id": version_id,
        "chunk_id": chunk_id,
        "chat_session_id": chat_session_id,
        "chat_message_id": chat_message_id,
        "citation_id": citation_id,
    }


def _seed_job(
    session: Session,
    truth_seed: dict[str, str],
    truth_ids: TruthIds,
    *,
    label: str,
    status: str,
    temp_file_path: str,
) -> str:
    job_id = truth_ids.job_id(label)
    session.add(
        BackgroundJob(
            id=job_id,
            job_type="document_import",
            status=status,
            workspace_id=truth_seed["workspace_id"],
            requested_by_user_id=truth_seed["user_id"],
            payload_={"temp_file_path": temp_file_path, "filename": "cleanup.md", "mime_type": "text/markdown"},
            result_=None,
            progress_current=0,
            progress_total=1,
            progress_message="cleanup truth",
            error_code=None,
            error_message=None,
            attempt_count=0,
            locked_at=None,
            locked_by=None,
            created_at=NOW,
            started_at=None,
            finished_at=None,
        )
    )
    session.commit()
    return job_id


def _assert_document_citation_and_queue_safety(session: Session, seeded: dict[str, str]) -> None:
    assert session.get(Document, seeded["document_id"]) is not None
    assert session.get(DocumentVersion, seeded["version_id"]) is not None
    assert session.get(Chunk, seeded["chunk_id"]) is not None
    assert session.get(ChatSession, seeded["chat_session_id"]) is not None
    assert session.get(ChatMessage, seeded["chat_message_id"]) is not None
    citation = session.get(ChatCitation, seeded["citation_id"])
    assert citation is not None
    assert citation.document_id == seeded["document_id"]
    assert citation.chunk_id == seeded["chunk_id"]
    assert citation.quote_preview == "Cleanup citation preview"
    assert session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.status.in_(["pending", "running", "retryable"]))) is not None


def _set_mtime(path: Path, timestamp: datetime) -> None:
    epoch = timestamp.timestamp()
    os.utime(path, (epoch, epoch))
