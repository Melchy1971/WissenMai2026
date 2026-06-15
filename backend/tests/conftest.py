from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import documents as documents_api
from app.db import session as db_session_module
from app.main import app
from app.models.documents import AuthSession, Base, Chunk, Document, DocumentVersion, User, Workspace, WorkspaceMembership
from app.repositories.documents import DocumentRepository
from app.services.auth import hash_password, hash_token
from app.services.documents.lifecycle_service import DocumentLifecycleService
from app.services.documents.import_recovery_service import DocumentImportRecoveryService
from app.services.documents.read_service import DocumentReadService
from app.services.jobs.background_jobs import BackgroundJobService


GATE_MARKERS = {
    "frontend_truth",
    "m3a_truth",
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
    "m5_truth",
    "governance_truth",
    "observability_truth",
    "unit_fast",
    "chaos_truth",
    "slow_truth",
}
FINAL_TRUTH_MARKERS = {
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
    "m5_truth",
    "governance_truth",
    "observability_truth",
    "unit_fast",
}
M4_BLOCKING_MARKERS = {
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
}
LEGACY_CRITICAL_GATE_MARKERS = {"m4a_gate", "m4b_gate", "m4c_gate"}
M4C_MINIMAL_NODEIDS = {
    "tests/integration/test_m3b_search.py::test_lifecycle_e2e_excludes_archived_deleted_from_search_chat_and_reindex",
    "tests/postgres_truth/test_m4c_lifecycle_retrieval_truth.py::test_m4c_historical_citations_reflect_live_source_status",
}

TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest-tmp"
DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
DOCUMENT_ID = "00000000-0000-0000-0000-000000000101"
OLDER_DOCUMENT_ID = "00000000-0000-0000-0000-000000000102"
VERSION_ID = "00000000-0000-0000-0000-000000000201"
OLDER_VERSION_ID = "00000000-0000-0000-0000-000000000202"
CHUNK_ID = "00000000-0000-0000-0000-000000000301"
SECOND_CHUNK_ID = "00000000-0000-0000-0000-000000000302"
SESSION_TOKEN = "test-session-token"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    unclassified: list[str] = []
    ambiguous: list[str] = []

    for item in items:
        marker_names = {marker.name for marker in item.iter_markers()}
        nodeid = item.nodeid.replace("\\", "/")
        if _is_m4c_minimal_test(nodeid):
            item.add_marker(pytest.mark.m4c_lifecycle_retrieval_truth)
            marker_names.add("m4c_lifecycle_retrieval_truth")
        final_truth_markers = sorted(FINAL_TRUTH_MARKERS.intersection(marker_names))
        is_postgres_truth = "postgres_truth" in marker_names or "postgres_truth/" in nodeid
        explicit_gate_markers = sorted(GATE_MARKERS.intersection(marker_names))
        if is_postgres_truth and not final_truth_markers:
            unclassified.append(item.nodeid)
        elif not explicit_gate_markers:
            marker = _classify_truth_gate(item, marker_names)
            if marker is None:
                unclassified.append(item.nodeid)
            else:
                item.add_marker(getattr(pytest.mark, marker))
                explicit_gate_markers = [marker]
        if len(final_truth_markers) > 1:
            ambiguous.append(f"{item.nodeid} -> {', '.join(final_truth_markers)}")

        critical_markers = sorted(LEGACY_CRITICAL_GATE_MARKERS.intersection(marker_names))
        if critical_markers and "postgres_truth" not in marker_names:
            joined = ", ".join(critical_markers)
            raise pytest.UsageError(
                f"Critical gate test {item.nodeid} uses {joined} but is missing the required postgres_truth marker"
            )

    if unclassified or ambiguous:
        details: list[str] = []
        if unclassified:
            details.append("Unclassified truth tests:")
            details.extend(f"- {nodeid}" for nodeid in unclassified)
        if ambiguous:
            details.append("Ambiguous truth tests:")
            details.extend(f"- {nodeid}" for nodeid in ambiguous)
        raise pytest.UsageError("\n".join(details))


def _classify_truth_gate(item: pytest.Item, marker_names: set[str]) -> str | None:
    nodeid = item.nodeid.replace("\\", "/").lower()

    if _is_m4c_minimal_test(nodeid):
        return "m4c_lifecycle_retrieval_truth"

    if "test_frontend_backend_contracts.py" in nodeid:
        return "frontend_truth"
    if nodeid.startswith("tests/api/") or nodeid.startswith("tests/ui/") or nodeid.startswith("tests/unit/"):
        return "unit_fast"

    if "postgres_truth/" in nodeid:
        return _classify_postgres_truth_gate(nodeid, marker_names)

    if "test_backup_restore" in nodeid:
        return "m4e_backup_restore_truth"
    if "observability" in nodeid:
        return "observability_truth"
    if "chaos" in nodeid or "workspace_leakage" in nodeid or "lifecycle_reindex" in nodeid:
        return "chaos_truth"
    if "test_m5_longrun_simulation.py" in nodeid or "test_m5_retrieval_benchmark.py" in nodeid:
        return "slow_truth"
    if "test_m5_" in nodeid:
        return "m5_truth"
    if (
        "test_health.py" in nodeid
        or "test_preflight.py" in nodeid
        or "/unit/" in nodeid
        or "test_migrations.py" in nodeid
        or "test_truth_split_report_generator.py" in nodeid
        or "test_gate_hierarchy_validator.py" in nodeid
        or "test_release_candidate_model.py" in nodeid
    ):
        return "m3a_truth"
    if "test_m4a_auth" in nodeid or "secure_api" in nodeid:
        return "m4a_auth_truth"
    if "upload" in nodeid or "import" in nodeid or "queue" in nodeid or "retry_import" in nodeid:
        return "m4b_upload_queue_truth"
    if "admin_search_index" in nodeid or "diagnostics" in nodeid or "reindex" in nodeid:
        return "governance_truth"
    if (
        "document" in nodeid
        or "search" in nodeid
        or "chat" in nodeid
        or "citation" in nodeid
        or "retrieval" in nodeid
        or "context_builder" in nodeid
        or "prompt_builder" in nodeid
        or "insufficient_context" in nodeid
        or "rag_chat" in nodeid
        or "fake_llm" in nodeid
    ):
        return "unit_fast"
    return None


def _is_m4c_minimal_test(nodeid: str) -> bool:
    return nodeid.replace("\\", "/").lower() in M4C_MINIMAL_NODEIDS


def _classify_postgres_truth_gate(nodeid: str, marker_names: set[str]) -> str:
    if "test_m4a_auth_workspace_truth.py" in nodeid:
        return "m4a_auth_truth"
    if "test_auth_bootstrap_truth.py" in nodeid or "test_workspace_bootstrap_truth.py" in nodeid:
        return "m4a_auth_truth"
    if "test_m4b_upload_queue_truth.py" in nodeid:
        return "m4b_upload_queue_truth"
    if "test_m4c_lifecycle_retrieval_truth.py" in nodeid:
        return "m4c_lifecycle_retrieval_truth" if _is_m4c_minimal_test(nodeid) else "governance_truth"
    if "test_m4_crash_recovery_truth.py" in nodeid or "test_m4_truth_flows.py" in nodeid:
        if "m4a_gate" in marker_names:
            return "m4a_auth_truth"
        if "m4b_gate" in marker_names:
            return "m4b_upload_queue_truth"
        if "m4c_gate" in marker_names:
            return "m4c_lifecycle_retrieval_truth"
        return "m4_truth"
    if "test_rc3_chaos_truth.py" in nodeid:
        return "chaos_truth"
    if "test_m5_cleanup_truth.py" in nodeid or "test_entropy_truth.py" in nodeid or "test_queue_aging_truth.py" in nodeid:
        return "m5_truth"
    if (
        "test_cleanup_governance_truth.py" in nodeid
        or "test_reindex_governance_truth.py" in nodeid
        or "test_citation_longevity_truth.py" in nodeid
    ):
        return "governance_truth"
    return "m4_truth"


@pytest.fixture(autouse=True)
def local_temp_dir(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(TEST_TEMP_ROOT))
    yield


@pytest.fixture
def test_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    original_engine = db_session_module._engine
    db_session_module._engine = engine
    try:
        yield engine
    finally:
        db_session_module._engine = original_engine
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def workspace_id() -> str:
    return DEFAULT_WORKSPACE_ID


@pytest.fixture
def document_id() -> str:
    return DOCUMENT_ID


@pytest.fixture
def version_id() -> str:
    return VERSION_ID


@pytest.fixture
def chunk_id() -> str:
    return CHUNK_ID


@pytest.fixture
def auth_fixture(db_session: Session) -> dict[str, str]:
    created = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)

    db_session.add(
        Workspace(
            id=DEFAULT_WORKSPACE_ID,
            name="Default Workspace",
            is_default=True,
            created_at=created,
        )
    )
    db_session.add(
        User(
            id=DEFAULT_USER_ID,
            display_name="Default User",
            login="default-user",
            password_hash=hash_password("secret-password", salt="testsalt"),
            is_active=True,
            is_default=True,
            created_at=created,
        )
    )
    db_session.add(
        WorkspaceMembership(
            id="membership-1",
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=DEFAULT_USER_ID,
            role="owner",
            created_at=created,
            updated_at=created,
        )
    )
    db_session.add(
        AuthSession(
            id="session-1",
            user_id=DEFAULT_USER_ID,
            token_hash=hash_token(SESSION_TOKEN),
            expires_at=datetime(2036, 5, 2, 10, 0, tzinfo=UTC),
            created_at=created,
            last_seen_at=created,
            revoked_at=None,
        )
    )
    db_session.commit()

    return {
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "user_id": DEFAULT_USER_ID,
        "session_token": SESSION_TOKEN,
    }


@pytest.fixture
def document_fixture(db_session: Session, auth_fixture: dict[str, str]) -> dict[str, str]:
    created = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    updated = datetime(2026, 5, 1, 11, 0, tzinfo=UTC)
    older_created = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)

    document = Document(
        id=DOCUMENT_ID,
        workspace_id=DEFAULT_WORKSPACE_ID,
        owner_user_id=DEFAULT_USER_ID,
        current_version_id=None,
        title="Current Document",
        source_type="upload",
        mime_type="text/plain",
        content_hash="hash-current",
        import_status="chunked",
        created_at=created,
        updated_at=updated,
    )
    older_document = Document(
        id=OLDER_DOCUMENT_ID,
        workspace_id=DEFAULT_WORKSPACE_ID,
        owner_user_id=DEFAULT_USER_ID,
        current_version_id=None,
        title="Older Document",
        source_type="upload",
        mime_type="text/markdown",
        content_hash="hash-older",
        import_status="parsed",
        created_at=older_created,
        updated_at=older_created,
    )
    db_session.add_all([document, older_document])
    db_session.flush()

    version = DocumentVersion(
        id=VERSION_ID,
        document_id=DOCUMENT_ID,
        version_number=1,
        normalized_markdown="# Current\n\n" + ("x" * 260),
        markdown_hash="markdown-hash-current",
        parser_version="1.0",
        ocr_used=False,
        ki_provider=None,
        ki_model=None,
        metadata_={"parser_name": "txt-parser", "source_filename": "current.txt"},
        created_at=created,
    )
    older_version = DocumentVersion(
        id=OLDER_VERSION_ID,
        document_id=OLDER_DOCUMENT_ID,
        version_number=1,
        normalized_markdown="# Older\n",
        markdown_hash="markdown-hash-older",
        parser_version="1.0",
        ocr_used=False,
        ki_provider=None,
        ki_model=None,
        metadata_={},
        created_at=older_created,
    )
    db_session.add_all([version, older_version])
    db_session.flush()

    document.current_version_id = VERSION_ID
    older_document.current_version_id = OLDER_VERSION_ID
    db_session.add_all(
        [
            Chunk(
                id=SECOND_CHUNK_ID,
                document_id=DOCUMENT_ID,
                document_version_id=VERSION_ID,
                chunk_index=1,
                heading_path=["Current"],
                anchor="dv:current:c0001",
                content="Second chunk",
                content_hash="chunk-hash-2",
                token_estimate=3,
                metadata_={
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": None,
                        "char_start": 261,
                        "char_end": 273,
                    }
                },
                created_at=created,
            ),
            Chunk(
                id=CHUNK_ID,
                document_id=DOCUMENT_ID,
                document_version_id=VERSION_ID,
                chunk_index=0,
                heading_path=["Current"],
                anchor="dv:current:c0000",
                content="x" * 260,
                content_hash="chunk-hash-1",
                token_estimate=65,
                metadata_={
                    "source_anchor": {
                        "type": "text",
                        "page": None,
                        "paragraph": None,
                        "char_start": 0,
                        "char_end": 260,
                    }
                },
                created_at=created,
            ),
        ]
    )
    db_session.commit()

    return {
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "document_id": DOCUMENT_ID,
        "version_id": VERSION_ID,
        "chunk_id": CHUNK_ID,
    }


@pytest.fixture
def client(db_session: Session, auth_fixture: dict[str, str]) -> Iterator[TestClient]:
    def override_document_read_service() -> Iterator[DocumentReadService]:
        yield DocumentReadService(DocumentRepository(db_session))

    def override_document_lifecycle_service() -> Iterator[DocumentLifecycleService]:
        yield DocumentLifecycleService.from_session(db_session)

    def override_background_job_service() -> Iterator[BackgroundJobService]:
        yield BackgroundJobService.from_session(db_session)

    def override_document_import_recovery_service() -> Iterator[DocumentImportRecoveryService]:
        yield DocumentImportRecoveryService.from_session(db_session)

    app.dependency_overrides[documents_api.get_document_read_service] = override_document_read_service
    app.dependency_overrides[documents_api.get_document_lifecycle_service] = override_document_lifecycle_service
    app.dependency_overrides[documents_api.get_background_job_service] = override_background_job_service
    app.dependency_overrides[documents_api.get_document_import_recovery_service] = override_document_import_recovery_service
    try:
        yield TestClient(
            app,
            headers={
                "Authorization": f"Bearer {SESSION_TOKEN}",
                "X-Workspace-Id": DEFAULT_WORKSPACE_ID,
            },
        )
    finally:
        app.dependency_overrides.clear()
