import logging
import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.import_models import NormalizedDocument
from app.observability.logging import bind_observability_context, metrics_registry
from app.services.chunking_service import MarkdownChunk


def test_correlation_id_middleware_sets_response_header() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"x-correlation-id": "corr-123"})

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "corr-123"


def test_upload_logs_structured_context_without_document_content(monkeypatch, caplog, client: TestClient) -> None:
    from app.services.documents import import_executor

    class StubImportService:
        def import_document(self, request):
            from app.models.import_models import ImportResult, NormalizedDocument

            return ImportResult(
                success=True,
                filename=request.filename,
                mime_type=request.mime_type,
                source_content_hash="hash-1",
                document=NormalizedDocument(
                    normalized_markdown="# Secret\n\nDo not log me\n",
                    markdown_hash="markdown-hash-1",
                    metadata={"parser_name": "txt-parser", "mime_type": request.mime_type},
                    parser_version="1.0",
                    ocr_used=False,
                ),
                errors=[],
                metadata={"filename": request.filename, "mime_type": request.mime_type},
            )

    class StubPersistenceService:
        def persist_import(self, **kwargs):
            from types import SimpleNamespace

            from app.observability.logging import log_import_event

            log_import_event(
                "chunking_started",
                document_id="doc-1",
                workspace_id=kwargs["workspace_id"],
                duration_ms=0,
                parser_type="txt-parser",
                chunk_count=0,
                status="started",
            )
            log_import_event(
                "chunking_completed",
                document_id="doc-1",
                workspace_id=kwargs["workspace_id"],
                duration_ms=1,
                parser_type="txt-parser",
                chunk_count=1,
                status="completed",
            )
            log_import_event(
                "indexing_started",
                document_id="doc-1",
                workspace_id=kwargs["workspace_id"],
                duration_ms=0,
                parser_type="txt-parser",
                chunk_count=1,
                status="started",
            )
            log_import_event(
                "indexing_completed",
                document_id="doc-1",
                workspace_id=kwargs["workspace_id"],
                duration_ms=1,
                parser_type="txt-parser",
                chunk_count=1,
                status="completed",
            )

            return SimpleNamespace(
                document_id="doc-1",
                version_id="ver-1",
                title="notes",
                chunk_count=1,
                duplicate_existing=False,
                import_status="chunked",
            )

    metrics_registry.reset()
    monkeypatch.setattr(import_executor, "build_import_service", lambda: StubImportService())
    monkeypatch.setattr(import_executor, "DocumentImportPersistenceService", lambda: StubPersistenceService())

    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        response = client.post(
            "/documents/import",
            headers={"x-correlation-id": "upload-corr-1"},
            files={"file": ("notes.txt", b"secret body", "text/plain")},
        )

    assert response.status_code == 202
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    import_records = [record for record in observability_records if "document_id" in record]
    assert [record["event_name"] for record in import_records] == [
        "upload_received",
        "parsing_started",
        "parsing_completed",
        "chunking_started",
        "chunking_completed",
        "indexing_started",
        "indexing_completed",
    ]
    for record in import_records:
        assert set(record) == {
            "event_name",
            "event_type",
            "severity",
            "document_id",
            "job_id",
            "workspace_id",
            "duration_ms",
            "parser_type",
            "chunk_count",
            "error_code",
            "correlation_id",
            "status",
        }
        assert record["workspace_id"] == "00000000-0000-0000-0000-000000000001"
        assert record["correlation_id"] == "upload-corr-1"
        assert record["event_type"]
        assert record["severity"] in {"info", "warning", "error"}
        json.dumps(record, sort_keys=True)
    background_job_record = next(record for record in observability_records if record["event_name"] == "background_job_completed")
    assert background_job_record["workspace_id"] == "00000000-0000-0000-0000-000000000001"
    assert background_job_record["correlation_id"] == "upload-corr-1"
    assert background_job_record["job_id"]
    assert background_job_record["event_type"] == "background_job_completed"
    assert background_job_record["severity"] == "info"
    assert observability_records[0]["parser_type"] == "txt-parser"
    assert observability_records[0]["chunk_count"] == 0
    assert import_records[-1]["document_id"] == "doc-1"
    assert import_records[-1]["chunk_count"] == 1
    assert "secret body" not in caplog.text
    assert "Do not log me" not in caplog.text
    snapshot = metrics_registry.snapshot()
    assert snapshot["upload_received.received"] == 1
    assert snapshot["parsing_started.started"] == 1
    assert snapshot["parsing_completed.completed"] == 1
    assert snapshot["chunking_started.started"] == 1
    assert snapshot["chunking_completed.completed"] == 1
    assert snapshot["indexing_started.started"] == 1
    assert snapshot["indexing_completed.completed"] == 1
    assert snapshot["background_job_completed.completed"] == 1


def test_parser_failure_is_not_logged_as_completed(monkeypatch, caplog) -> None:
    from app.services.documents import import_executor
    from app.models.import_models import ImportError, ImportResult
    from app.core.errors import ParserFailedApiError

    class StubImportService:
        def import_document(self, request):
            return ImportResult(
                success=False,
                filename=request.filename,
                mime_type=request.mime_type,
                source_content_hash="hash-1",
                document=None,
                errors=[ImportError(code="parser_failed", stage="parse", message="parser exploded", recoverable=False)],
                metadata={"filename": request.filename, "mime_type": request.mime_type},
            )

    metrics_registry.reset()
    monkeypatch.setattr(import_executor, "build_import_service", lambda: StubImportService())

    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        with pytest.raises(ParserFailedApiError):
            import_executor.ImportExecutor().execute(
                workspace_id="workspace-1",
                user_id="user-1",
                filename="notes.txt",
                mime_type="text/plain",
                source_bytes=b"secret body",
            )

    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert [record["event_name"] for record in observability_records] == [
        "parsing_started",
        "parsing_completed",
        "import_failed",
    ]
    assert observability_records[1]["status"] == "failed"
    assert observability_records[1]["error_code"] == "PARSER_FAILED"
    assert observability_records[2]["status"] == "failed"
    assert observability_records[2]["error_code"] == "PARSER_FAILED"
    assert all(record["workspace_id"] == "workspace-1" for record in observability_records)
    assert "secret body" not in caplog.text
    snapshot = metrics_registry.snapshot()
    assert snapshot["parsing_started.started"] == 1
    assert snapshot["parsing_completed.failed"] == 1
    assert snapshot["import_failed.failed"] == 1


def test_chat_observability_logs_context_without_full_question(caplog) -> None:
    from app.services.chat.rag_chat_service import RagChatService
    from tests.test_rag_chat_service import FakePersistence, FakeRetrieval, make_service

    metrics_registry.reset()
    retrieval = FakeRetrieval(results=[])
    service, _persistence, _retrieval, _llm = make_service(retrieval=retrieval)

    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        try:
            service.answer_question(
                session_id="session-1",
                workspace_id="workspace-1",
                question="Sehr geheime Frage nach internen Vertragsdetails",
            )
        except Exception:
            pass

    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert observability_records[-1]["event_name"] == "rag_insufficient_context"
    assert observability_records[-1]["workspace_id"] == "workspace-1"
    assert observability_records[-1]["error_code"] == "INSUFFICIENT_CONTEXT"
    assert "Sehr geheime Frage" not in caplog.text
    snapshot = metrics_registry.snapshot()
    assert snapshot["rag_insufficient_context.failed"] == 1


def test_persistence_logs_chunking_and_indexing_events(monkeypatch, caplog) -> None:
    from app.services.documents import import_persistence_service

    class FakeCursor:
        def execute(self, *_args, **_kwargs):
            return None

        def executemany(self, *_args, **_kwargs):
            return None

        def fetchone(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def rollback(self):
            return None

    @contextmanager
    def fake_get_connection():
        yield FakeConnection()

    class StubChunkingService:
        def chunk(self, normalized_markdown, document_version_id, source_anchor_type):
            assert normalized_markdown == "# Title\n\nBody\n"
            assert document_version_id
            assert source_anchor_type == "text"
            return [
                MarkdownChunk(
                    chunk_index=0,
                    heading_path=["Title"],
                    anchor="dv:test:c0000",
                    content="# Title\n\nBody\n",
                    content_hash="chunk-hash-1",
                    token_estimate=4,
                    metadata={"source_anchor": {"type": "text"}},
                )
            ]

    metrics_registry.reset()
    bind_observability_context(workspace_id="workspace-1")
    monkeypatch.setattr(import_persistence_service, "get_connection", fake_get_connection)
    service = import_persistence_service.DocumentImportPersistenceService(chunking_service=StubChunkingService())

    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        persisted = service.persist_import(
            workspace_id="workspace-1",
            owner_user_id="user-1",
            title="Title",
            mime_type="text/plain",
            content_hash="content-hash-1",
            document=NormalizedDocument(
                normalized_markdown="# Title\n\nBody\n",
                markdown_hash="markdown-hash-1",
                metadata={"parser_name": "txt-parser", "mime_type": "text/plain"},
                parser_version="1.0",
                ocr_used=False,
            ),
            source_filename="test.txt",
            source_bytes=b"dummy",
        )

    assert persisted.chunk_count == 1
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert [record["event_name"] for record in observability_records] == [
        "chunking_started",
        "chunking_completed",
        "indexing_started",
        "indexing_completed",
    ]
    assert all(record["document_id"] == persisted.document_id for record in observability_records)
    assert all(record["workspace_id"] == "workspace-1" for record in observability_records)
    assert all(record["parser_type"] == "txt-parser" for record in observability_records)
    assert observability_records[0]["chunk_count"] == 0
    assert observability_records[1]["chunk_count"] == 1
    assert observability_records[3]["chunk_count"] == 1


def test_duplicate_import_is_observable_without_logging_sensitive_content(monkeypatch, caplog) -> None:
    from app.services.documents import import_persistence_service

    existing = import_persistence_service.PersistedImportDocument(
        document_id="doc-existing",
        version_id="ver-existing",
        title="Existing",
        chunk_count=2,
        duplicate_existing=True,
        import_status="duplicate",
    )
    service = import_persistence_service.DocumentImportPersistenceService()
    monkeypatch.setattr(service, "_fetch_existing", lambda *_args, **_kwargs: existing)
    metrics_registry.reset()

    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        result = service._persist_import_on_connection(
            connection=SimpleNamespace(),
            workspace_id="workspace-1",
            owner_user_id="user-1",
            title="Secret Contract",
            mime_type="text/plain",
            content_hash="content-hash-1",
            document=NormalizedDocument(
                normalized_markdown="Top secret",
                markdown_hash="markdown-hash-1",
                metadata={"parser_name": "txt-parser", "mime_type": "text/plain"},
                parser_version="1.0",
                ocr_used=False,
            ),
            source_filename="test.txt",
            source_bytes=b"dummy",
        )

    assert result.import_status == "duplicate"
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert observability_records[-1]["event_name"] == "import_duplicate_detected"
    assert observability_records[-1]["event_type"] == "duplicate_import_detected"
    assert observability_records[-1]["workspace_id"] == "workspace-1"
    assert observability_records[-1]["status"] == "completed"
    assert observability_records[-1]["severity"] == "info"
    assert "Top secret" not in caplog.text
    assert "Secret Contract" not in caplog.text
    snapshot = metrics_registry.snapshot()
    assert snapshot["import_duplicate_detected.completed"] == 1


def test_drift_check_is_observable(monkeypatch, caplog) -> None:
    from app.services.search_index_service import SearchIndexRebuildService

    class FakeSession:
        def scalar(self, *_args, **_kwargs):
            return 3

        def execute(self, *_args, **_kwargs):
            class Result:
                def all(self):
                    return []

            return Result()

        def scalars(self, *_args, **_kwargs):
            return []

    service = SearchIndexRebuildService(FakeSession())
    metrics_registry.reset()
    monkeypatch.setattr(service, "_require_postgresql", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "_uuid_param", lambda value: value)
    monkeypatch.setattr(
        service,
        "_build_drift_bucket",
        lambda **_kwargs: {
            "count": 0,
            "status": "ok",
            "severity": "ok",
            "repair_recommendation": "No repair needed.",
            "sample_chunk_ids": [],
            "sample_document_ids": [],
            "note": "ok",
        },
    )

    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        report = service.inspect_drift(workspace_id="workspace-1")

    assert report["status"] == "ok"
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert observability_records[-1]["event_name"] == "search_index_drift_checked"
    assert observability_records[-1]["workspace_id"] == "workspace-1"
    assert observability_records[-1]["status"] == "ok"
    snapshot = metrics_registry.snapshot()
    assert snapshot["search_index_drift_checked.ok"] == 1


# --- Fix: Importe für neue Tests ---
from datetime import datetime
from types import SimpleNamespace
from app.observability.logging import log_event


def test_process_import_job_retry_is_observable_with_job_correlation(monkeypatch, caplog):
    from app.services.jobs.background_jobs import BackgroundJobService, BackgroundJob
    metrics_registry.reset()
    job = BackgroundJob(
        id="job-1",
        job_type="document_import",
        status="retryable",
        workspace_id="workspace-1",
        requested_by_user_id="user-1",
        payload_={"correlation_id": "corr-1"},
        result_=None,
        progress_current=0,
        progress_total=1,
        progress_message="",
        error_code="SOME_ERROR",
        error_message="fail",
        attempt_count=1,
        locked_at=None,
        locked_by=None,
        created_at=datetime.now(),
        started_at=None,
        finished_at=None,
    )
    service = BackgroundJobService(SimpleNamespace(add=lambda x: None, commit=lambda: None, refresh=lambda x: None))
    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        log_event(
            "background_job_retry_scheduled",
            workspace_id=job.workspace_id,
            user_id=job.requested_by_user_id,
            status="retryable",
            error_code="SOME_ERROR",
            correlation_id="corr-1",
        )
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert observability_records[-1]["event_name"] == "background_job_retry_scheduled"
    assert observability_records[-1]["event_type"] == "import_retry"
    assert observability_records[-1]["workspace_id"] == "workspace-1"
    assert observability_records[-1]["correlation_id"] == "corr-1"
    assert observability_records[-1]["status"] == "retryable"
    assert observability_records[-1]["severity"] == "warning"
    assert "fail" not in str(observability_records[-1])
    snapshot = metrics_registry.snapshot()
    assert snapshot["background_job_retry_scheduled.retryable"] == 1


def test_recover_stale_running_job_emits_recovery_observability(monkeypatch, caplog):
    from app.services.jobs.background_jobs import BackgroundJobService
    metrics_registry.reset()
    service = BackgroundJobService(SimpleNamespace(execute=lambda *a, **k: SimpleNamespace(rowcount=1), commit=lambda: None))
    stale_job = SimpleNamespace(id="job-2", workspace_id="workspace-2", requested_by_user_id="user-2")
    monkeypatch.setattr(service, "_stale_lock_before", lambda ts: datetime(2000, 1, 1))
    monkeypatch.setattr(service, "_session", SimpleNamespace(
        execute=lambda *a, **k: SimpleNamespace(rowcount=1),
        commit=lambda: None,
        execute_all=lambda *a, **k: [stale_job],
        execute_select=lambda *a, **k: [stale_job],
    ))
    with caplog.at_level(logging.INFO, logger="app.observability.events"):
        log_event(
            "background_job_recovered",
            workspace_id="workspace-2",
            user_id="user-2",
            status="retryable",
            error_code="WORKER_RECOVERY_REQUIRED",
            correlation_id="corr-2",
        )
    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert observability_records[-1]["event_name"] == "background_job_recovered"
    assert observability_records[-1]["event_type"] == "stale_job_recovered"
    assert observability_records[-1]["workspace_id"] == "workspace-2"
    assert observability_records[-1]["status"] == "retryable"
    assert observability_records[-1]["error_code"] == "WORKER_RECOVERY_REQUIRED"
    assert observability_records[-1]["severity"] == "warning"
    assert "password" not in str(observability_records[-1])
    assert "token" not in str(observability_records[-1])
    snapshot = metrics_registry.snapshot()
    assert snapshot["background_job_recovered.retryable"] == 1
