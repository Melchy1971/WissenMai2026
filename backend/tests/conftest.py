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


CRITICAL_GATE_MARKERS = {"m4a_gate", "m4b_gate", "m4c_gate"}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        marker_names = {marker.name for marker in item.iter_markers()}
        critical_markers = sorted(CRITICAL_GATE_MARKERS.intersection(marker_names))
        if critical_markers and "postgres_truth" not in marker_names:
            joined = ", ".join(critical_markers)
            raise pytest.UsageError(
                f"Critical gate test {item.nodeid} uses {joined} but is missing the required postgres_truth marker"
            )


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
