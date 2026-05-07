from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Lock
from io import BytesIO

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.api import documents as documents_api
from app.api.dependencies.auth import AuthContext
from app.api.v1.chat import get_rag_chat_service
from app.api.v1.chat import create_chat_message
from app.api.v1.jobs import get_job
from app.api.v1.search import get_search_service
from app.api.v1.search import search_chunks
from app.models.documents import AuthSession, BackgroundJob, User, Workspace, WorkspaceMembership
from app.observability.logging import metrics_registry
from app.schemas.chat import ChatMessageCreateRequest
from app.schemas.chat import ChatCitationResponse, ChatMessageResponse
from app.schemas.search import SearchChunkResult
from app.services.auth import hash_password, hash_token
from app.services.jobs.background_jobs import BackgroundJobService, process_import_job, process_search_index_rebuild_job
from tests.conftest import DEFAULT_USER_ID, DEFAULT_WORKSPACE_ID, SESSION_TOKEN


OTHER_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"
OTHER_SESSION_TOKEN = "test-session-token-other"


class ThreadSafeFakeBackgroundJobService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._barrier = Barrier(2)
        self._counter = 0
        self.calls: list[dict[str, str]] = []
        self._session = type("BindProxy", (), {"get_bind": lambda _self: None})()

    def enqueue_import_job(self, *, workspace_id: str, requested_by_user_id: str, filename: str, mime_type: str, temp_file_path: str):
        self._barrier.wait(timeout=5)
        with self._lock:
            self._counter += 1
            job_id = f"upload-job-{self._counter}"
            self.calls.append({
                "job_id": job_id,
                "workspace_id": workspace_id,
                "requested_by_user_id": requested_by_user_id,
                "filename": filename,
                "mime_type": mime_type,
            })
        return type(
            "UploadJob",
            (),
            {
                "id": job_id,
                "job_type": "document_import",
                "status": "pending",
                "workspace_id": workspace_id,
                "requested_by_user_id": requested_by_user_id,
                "payload_": {"filename": filename, "mime_type": mime_type, "temp_file_path": temp_file_path},
                "result_": None,
                "progress_current": 0,
                "progress_total": 1,
                "progress_message": "Import wartet auf Verarbeitung",
                "error_code": None,
                "error_message": None,
                "created_at": datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
                "started_at": None,
                "finished_at": None,
            },
        )()

    def to_response(self, job):
        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "workspace_id": job.workspace_id,
            "requested_by_user_id": job.requested_by_user_id,
            "filename": job.payload_["filename"],
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "progress_current": job.progress_current,
            "progress_total": job.progress_total,
            "progress_message": job.progress_message,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "result": None,
        }


class ThreadSafeFakeSearchService:
    def __init__(self) -> None:
        self._barrier = Barrier(2)
        self.calls: list[dict[str, str | int]] = []
        self._lock = Lock()

    def search_chunks(self, workspace_id: str, query: str, limit: int, offset: int, filters=None):
        self._barrier.wait(timeout=5)
        with self._lock:
            self.calls.append({"workspace_id": workspace_id, "query": query, "limit": limit, "offset": offset})
        return [
            SearchChunkResult(
                document_id=f"doc-{workspace_id}",
                document_title=f"Document {workspace_id}",
                document_created_at=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
                document_version_id=f"ver-{workspace_id}",
                version_number=1,
                chunk_id=f"chunk-{workspace_id}",
                position=0,
                text_preview=f"preview for {workspace_id}",
                source_anchor={"type": "text", "page": None, "paragraph": 1, "char_start": 0, "char_end": 12},
                rank=0.9,
                filters={},
            )
        ]


class ThreadSafeFakeRagService:
    def __init__(self) -> None:
        self._barrier = Barrier(2)
        self.calls: list[dict[str, str | int | None]] = []
        self._lock = Lock()

    def answer_question(self, *, session_id: str, workspace_id: str, question: str, retrieval_limit: int | None = None):
        self._barrier.wait(timeout=5)
        with self._lock:
            self.calls.append(
                {
                    "session_id": session_id,
                    "workspace_id": workspace_id,
                    "question": question,
                    "retrieval_limit": retrieval_limit,
                }
            )
        now = datetime(2026, 5, 7, 12, 5, tzinfo=UTC)
        return ChatMessageResponse(
            id=f"message-{workspace_id}",
            session_id=session_id,
            role="assistant",
            content=f"Answer for {workspace_id}",
            basis_type="knowledge_base",
            created_at=now,
            citations=[
                ChatCitationResponse(
                    chunk_id=f"chunk-{workspace_id}",
                    document_id=f"doc-{workspace_id}",
                    document_title=f"Document {workspace_id}",
                    source_anchor={"type": "text", "page": None, "paragraph": 2, "char_start": 0, "char_end": 15},
                    quote_preview=f"Quote for {workspace_id}",
                    source_status="active",
                )
            ],
            confidence=None,
        )


def test_workspace_leakage_chaos_parallel_uploads_search_and_chat_remain_isolated(db_session, auth_fixture, monkeypatch, caplog) -> None:
    _seed_other_workspace(db_session)
    upload_service = ThreadSafeFakeBackgroundJobService()
    search_service = ThreadSafeFakeSearchService()
    rag_service = ThreadSafeFakeRagService()

    monkeypatch.setattr("app.api.documents.BackgroundJobService.create_temp_upload_file", lambda **_kwargs: "temp-upload-file")
    metrics_registry.reset()

    default_auth = _auth_context(DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID)
    other_auth = _auth_context(OTHER_WORKSPACE_ID, OTHER_USER_ID)
    with caplog.at_level("INFO", logger="app.observability.events"):
        with ThreadPoolExecutor(max_workers=6) as executor:
            upload_default = executor.submit(
                _run_upload,
                auth_context=default_auth,
                filename="default.txt",
                payload=b"default payload",
                job_service=upload_service,
            )
            upload_other = executor.submit(
                _run_upload,
                auth_context=other_auth,
                filename="other.txt",
                payload=b"other payload",
                job_service=upload_service,
            )
            search_default_future = executor.submit(
                search_chunks,
                auth_context=default_auth,
                q="default",
                service=search_service,
                limit=20,
                offset=0,
            )
            search_other_future = executor.submit(
                search_chunks,
                auth_context=other_auth,
                q="other",
                service=search_service,
                limit=20,
                offset=0,
            )
            chat_default_future = executor.submit(
                create_chat_message,
                session_id="session-1",
                request=ChatMessageCreateRequest(question="default question", retrieval_limit=3),
                auth_context=default_auth,
                service=rag_service,
            )
            chat_other_future = executor.submit(
                create_chat_message,
                session_id="session-2",
                request=ChatMessageCreateRequest(question="other question", retrieval_limit=3),
                auth_context=other_auth,
                service=rag_service,
            )

        upload_default_response = upload_default.result()
        upload_other_response = upload_other.result()
        search_default_response = search_default_future.result()
        search_other_response = search_other_future.result()
        chat_default_response = chat_default_future.result()
        chat_other_response = chat_other_future.result()

    assert upload_default_response["workspace_id"] == DEFAULT_WORKSPACE_ID
    assert upload_other_response["workspace_id"] == OTHER_WORKSPACE_ID
    assert {call["workspace_id"] for call in upload_service.calls} == {DEFAULT_WORKSPACE_ID, OTHER_WORKSPACE_ID}

    assert search_default_response[0].chunk_id == f"chunk-{DEFAULT_WORKSPACE_ID}"
    assert search_default_response[0].document_id == f"doc-{DEFAULT_WORKSPACE_ID}"
    assert search_other_response[0].chunk_id == f"chunk-{OTHER_WORKSPACE_ID}"
    assert search_other_response[0].document_id == f"doc-{OTHER_WORKSPACE_ID}"

    assert chat_default_response.citations[0].chunk_id == f"chunk-{DEFAULT_WORKSPACE_ID}"
    assert chat_default_response.citations[0].document_id == f"doc-{DEFAULT_WORKSPACE_ID}"
    assert chat_other_response.citations[0].chunk_id == f"chunk-{OTHER_WORKSPACE_ID}"
    assert chat_other_response.citations[0].document_id == f"doc-{OTHER_WORKSPACE_ID}"

    observability_records = [record.observability for record in caplog.records if hasattr(record, "observability")]
    assert {record["workspace_id"] for record in observability_records} == {DEFAULT_WORKSPACE_ID, OTHER_WORKSPACE_ID}
    assert metrics_registry.snapshot()["upload_received.received"] == 2
    assert metrics_registry.snapshot()["search_executed.completed"] == 2


def test_workspace_leakage_chaos_reindex_during_search_stays_workspace_scoped(test_engine, db_session, auth_fixture, monkeypatch) -> None:
    _seed_other_workspace(db_session)

    with Session(test_engine) as session:
        service = BackgroundJobService.from_session(session)
        job_default = service.enqueue_search_index_rebuild_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            requested_by_user_id=DEFAULT_USER_ID,
            target_workspace_id=DEFAULT_WORKSPACE_ID,
        )
        job_other = service.enqueue_search_index_rebuild_job(
            workspace_id=OTHER_WORKSPACE_ID,
            requested_by_user_id=OTHER_USER_ID,
            target_workspace_id=OTHER_WORKSPACE_ID,
        )
        default_job_id = job_default.id
        other_job_id = job_other.id

    rebuild_calls: list[str | None] = []
    rebuild_lock = Lock()

    class FakeRebuildService:
        @classmethod
        def from_session(cls, _session):
            return cls()

        def rebuild_search_index(self, *, workspace_id: str | None = None):
            with rebuild_lock:
                rebuild_calls.append(workspace_id)
            return {
                "workspace_id": workspace_id,
                "reindexed_chunk_count": 0,
                "reindexed_document_count": 0,
                "index_name": "ix_document_chunks_search_vector",
                "index_action": "reindexed",
                "status": "completed",
            }

    search_service = ThreadSafeFakeSearchService()
    monkeypatch.setattr("app.services.jobs.background_jobs.SearchIndexRebuildService", FakeRebuildService)

    default_auth = _auth_context(DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID)
    other_auth = _auth_context(OTHER_WORKSPACE_ID, OTHER_USER_ID)
    with ThreadPoolExecutor(max_workers=2) as executor:
        search_default_future = executor.submit(
            search_chunks,
            auth_context=default_auth,
            q="alpha",
            service=search_service,
            limit=20,
            offset=0,
        )
        search_other_future = executor.submit(
            search_chunks,
            auth_context=other_auth,
            q="beta",
            service=search_service,
            limit=20,
            offset=0,
        )

        default_response = search_default_future.result()
        other_response = search_other_future.result()

    process_search_index_rebuild_job(default_job_id, test_engine)
    process_search_index_rebuild_job(other_job_id, test_engine)

    assert default_response[0].document_id == f"doc-{DEFAULT_WORKSPACE_ID}"
    assert other_response[0].document_id == f"doc-{OTHER_WORKSPACE_ID}"
    assert rebuild_calls.count(DEFAULT_WORKSPACE_ID) == 1
    assert rebuild_calls.count(OTHER_WORKSPACE_ID) == 1


def test_workspace_leakage_chaos_retry_jobs_and_queue_recovery_preserve_workspace_boundaries(test_engine, db_session, auth_fixture, tmp_path, monkeypatch) -> None:
    _seed_other_workspace(db_session)

    default_temp = tmp_path / "default.txt"
    other_temp = tmp_path / "other.txt"
    default_temp.write_bytes(b"default")
    other_temp.write_bytes(b"other")

    with Session(test_engine) as session:
        service = BackgroundJobService.from_session(session)
        default_job = service.enqueue_import_job(
            workspace_id=DEFAULT_WORKSPACE_ID,
            requested_by_user_id=DEFAULT_USER_ID,
            filename="default.txt",
            mime_type="text/plain",
            temp_file_path=str(default_temp),
        )
        other_job = service.enqueue_import_job(
            workspace_id=OTHER_WORKSPACE_ID,
            requested_by_user_id=OTHER_USER_ID,
            filename="other.txt",
            mime_type="text/plain",
            temp_file_path=str(other_temp),
        )
        stale_at = datetime.now(UTC) - timedelta(minutes=10)
        session.query(BackgroundJob).filter(BackgroundJob.id.in_([default_job.id, other_job.id])).update(
            {
                BackgroundJob.status: "running",
                BackgroundJob.locked_at: stale_at,
                BackgroundJob.locked_by: "stale-worker",
                BackgroundJob.attempt_count: 1,
            },
            synchronize_session=False,
        )
        session.commit()
        default_job_id = default_job.id
        other_job_id = other_job.id

    with Session(test_engine) as recovery_session:
        recovered = BackgroundJobService.from_session(recovery_session).recover_stale_jobs(worker_id="chaos-recovery")
    assert recovered == 2

    class FakeImportExecutor:
        def execute(self, **kwargs):
            workspace_id = kwargs["workspace_id"]
            return {
                "document_id": f"doc-{workspace_id}",
                "version_id": f"ver-{workspace_id}",
                "import_status": "chunked",
                "duplicate_of_document_id": None,
                "chunk_count": 1,
                "parser_type": "txt-parser",
                "warnings": [],
            }

    monkeypatch.setattr("app.services.jobs.background_jobs.ImportExecutor", FakeImportExecutor)

    process_import_job(default_job_id, test_engine)
    process_import_job(other_job_id, test_engine)

    with Session(test_engine) as session:
        refreshed_default = session.get(BackgroundJob, default_job_id)
        refreshed_other = session.get(BackgroundJob, other_job_id)
        assert refreshed_default is not None
        assert refreshed_other is not None
        resolved_default_job_id = session.query(BackgroundJob.id).filter(BackgroundJob.workspace_id == DEFAULT_WORKSPACE_ID).one()[0]
        resolved_other_job_id = session.query(BackgroundJob.id).filter(BackgroundJob.workspace_id == OTHER_WORKSPACE_ID).one()[0]
        assert refreshed_default.workspace_id == DEFAULT_WORKSPACE_ID
        assert refreshed_other.workspace_id == OTHER_WORKSPACE_ID
        assert refreshed_default.status == "completed"
        assert refreshed_other.status == "completed"
        assert refreshed_default.result_["document_id"] == f"doc-{DEFAULT_WORKSPACE_ID}"
        assert refreshed_other.result_["document_id"] == f"doc-{OTHER_WORKSPACE_ID}"

    with Session(test_engine) as job_session:
        job_service = BackgroundJobService.from_session(job_session)
        own_default = get_job(resolved_default_job_id, auth_context=_auth_context(DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID), job_service=job_service)
        own_other = get_job(resolved_other_job_id, auth_context=_auth_context(OTHER_WORKSPACE_ID, OTHER_USER_ID), job_service=job_service)

    assert own_default.workspace_id == DEFAULT_WORKSPACE_ID
    assert own_other.workspace_id == OTHER_WORKSPACE_ID

    with Session(test_engine) as foreign_session:
        foreign_job_service = BackgroundJobService.from_session(foreign_session)
        try:
            get_job(resolved_other_job_id, auth_context=_auth_context(DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID), job_service=foreign_job_service)
        except Exception as exc:
            assert getattr(exc, "code", None) == "JOB_NOT_FOUND"
        else:
            raise AssertionError("Expected foreign workspace access to be rejected")

        try:
            get_job(resolved_default_job_id, auth_context=_auth_context(OTHER_WORKSPACE_ID, OTHER_USER_ID), job_service=foreign_job_service)
        except Exception as exc:
            assert getattr(exc, "code", None) == "JOB_NOT_FOUND"
        else:
            raise AssertionError("Expected foreign workspace access to be rejected")


def _seed_other_workspace(db_session) -> dict[str, str]:
    created = datetime(2026, 5, 1, 10, 5, tzinfo=UTC)
    if db_session.get(Workspace, OTHER_WORKSPACE_ID) is None:
        db_session.add(Workspace(id=OTHER_WORKSPACE_ID, name="Other Workspace", is_default=False, created_at=created))
    if db_session.get(User, OTHER_USER_ID) is None:
        db_session.add(
            User(
                id=OTHER_USER_ID,
                display_name="Other User",
                login="other-user",
                password_hash=hash_password("secret-password", salt="othersalt"),
                is_active=True,
                is_default=False,
                created_at=created,
            )
        )
    if db_session.get(AuthSession, "session-2") is None:
        db_session.add(
            WorkspaceMembership(
                id="membership-2",
                workspace_id=OTHER_WORKSPACE_ID,
                user_id=OTHER_USER_ID,
                role="owner",
                created_at=created,
                updated_at=created,
            )
        )
        db_session.add(
            AuthSession(
                id="session-2",
                user_id=OTHER_USER_ID,
                token_hash=hash_token(OTHER_SESSION_TOKEN),
                expires_at=datetime(2036, 5, 2, 10, 0, tzinfo=UTC),
                created_at=created,
                last_seen_at=created,
                revoked_at=None,
            )
        )
    db_session.commit()
    return {"workspace_id": OTHER_WORKSPACE_ID, "user_id": OTHER_USER_ID, "session_token": OTHER_SESSION_TOKEN}


def _auth_context(workspace_id: str, user_id: str) -> AuthContext:
    return AuthContext(
        session_id=f"session-{workspace_id}",
        user_id=user_id,
        login=f"login-{user_id}",
        display_name=f"User {user_id}",
        workspace_id=workspace_id,
        role="owner",
        permissions=("workspace:read", "document:import", "workspace:admin"),
    )


def _run_upload(*, auth_context: AuthContext, filename: str, payload: bytes, job_service: ThreadSafeFakeBackgroundJobService):
    upload = UploadFile(file=BytesIO(payload), filename=filename)
    return asyncio.run(
        documents_api.import_document(
            background_tasks=BackgroundTasks(),
            file=upload,
            auth_context=auth_context,
            job_service=job_service,
        )
    )