from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.documents import Base, ChatCitation, Chunk, Document, DocumentVersion
from app.services.documents.lifecycle_service import DocumentLifecycleService
from app.services.chat.persistence_service import (
    ChatCitationPayload,
    ChatPersistenceError,
    ChatPersistenceService,
    ChatSessionNotFoundError,
)


@pytest.fixture
def chat_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def chat_session(chat_engine):
    with Session(chat_engine) as session:
        created = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        document = Document(
            id="doc-1",
            workspace_id="workspace-1",
            owner_user_id="user-1",
            current_version_id=None,
            title="Current Document",
            source_type="upload",
            mime_type="text/plain",
            content_hash="hash-current",
            import_status="chunked",
            created_at=created,
            updated_at=created,
        )
        version = DocumentVersion(
            id="ver-1",
            document_id="doc-1",
            version_number=1,
            normalized_markdown="# Current\n\nBody",
            markdown_hash="markdown-hash-current",
            parser_version="1.0",
            ocr_used=False,
            ki_provider=None,
            ki_model=None,
            metadata_={},
            created_at=created,
        )
        session.add_all([document, version])
        session.flush()

        document.current_version_id = "ver-1"
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            document_version_id="ver-1",
            chunk_index=0,
            heading_path=["Current"],
            anchor="dv:ver-1:c0000",
            content="Chunk body text for citation support.",
            content_hash="chunk-hash-1",
            token_estimate=6,
            metadata_={"source_anchor": {"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 34}},
            created_at=created,
        )
        session.add_all([document, chunk])
        session.commit()
        yield session


def test_create_session_persists_chat_session(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)

    created = service.create_session(workspace_id="workspace-1", title=" Vertragspruefung ", owner_user_id="user-1")

    assert created.workspace_id == "workspace-1"
    assert created.title == "Vertragspruefung"
    assert created.owner_user_id == "user-1"


def test_list_sessions_orders_by_updated_at_desc(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    first = service.create_session(workspace_id="workspace-1", title="First", owner_user_id="user-1")
    second = service.create_session(workspace_id="workspace-1", title="Second", owner_user_id="user-1")

    sessions = service.list_sessions(workspace_id="workspace-1")

    assert [session.id for session in sessions][:2] == [second.id, first.id]


def test_create_message_persists_immutable_message_and_updates_session_timestamp(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Chat", owner_user_id="user-1")
    original_updated_at = created_session.updated_at

    first_message = service.create_message(
        session_id=created_session.id,
        role="user",
        content="Erste Frage",
        metadata={"request_id": "req-1"},
    )
    second_message = service.create_message(
        session_id=created_session.id,
        role="assistant",
        content="Erste Antwort",
        metadata={"request_id": "req-2"},
    )

    messages = service.list_messages(session_id=created_session.id)
    persisted_session = service.get_session(session_id=created_session.id)

    assert first_message.message_index == 0
    assert second_message.message_index == 1
    assert [message.content for message in messages] == ["Erste Frage", "Erste Antwort"]
    assert messages[0].metadata_ == {"request_id": "req-1"}
    assert persisted_session.updated_at >= original_updated_at

def test_create_message_persists_citations(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Chat", owner_user_id="user-1")

    message = service.create_message(
        session_id=created_session.id,
        role="assistant",
        content="Antwort mit Quelle",
        citations=[
            ChatCitationPayload(
                chunk_id="chunk-1",
                document_id="doc-1",
                document_title="Current Document",
                quote_preview="Chunk body text for citation support.",
                source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 34},
            )
        ],
    )

    citations = service.list_citations(message_id=message.id)

    assert len(citations) == 1
    assert citations[0].chunk_id == "chunk-1"
    assert citations[0].document_id == "doc-1"
    assert citations[0].document_title == "Current Document"
    assert citations[0].quote_preview == "Chunk body text for citation support."
    assert citations[0].source_status == "active"


def test_delete_of_cited_document_chunk_is_restricted(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Chat", owner_user_id="user-1")
    message = service.create_message(
        session_id=created_session.id,
        role="assistant",
        content="Antwort mit Quelle",
        citations=[
            ChatCitationPayload(
                chunk_id="chunk-1",
                document_id="doc-1",
                document_title="Current Document",
                quote_preview="Chunk body text for citation support.",
                source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 34},
            )
        ],
    )
    assert chat_session.get(ChatCitation, chat_session.scalar(select(ChatCitation.id).where(ChatCitation.message_id == message.id))) is not None

    chunk = chat_session.get(Chunk, "chunk-1")
    assert chunk is not None
    chat_session.delete(chunk)
    chat_session.commit()

    persisted = service.list_citations(message_id=message.id)
    assert persisted[0].chunk_id is None
    assert persisted[0].quote_preview == "Chunk body text for citation support."


def test_delete_of_cited_document_is_restricted(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Chat", owner_user_id="user-1")
    message = service.create_message(
        session_id=created_session.id,
        role="assistant",
        content="Antwort mit Quelle",
        citations=[
            ChatCitationPayload(
                chunk_id="chunk-1",
                document_id="doc-1",
                document_title="Current Document",
                quote_preview="Chunk body text for citation support.",
                source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 34},
            )
        ],
    )
    assert chat_session.get(ChatCitation, chat_session.scalar(select(ChatCitation.id).where(ChatCitation.message_id == message.id))) is not None

    document = chat_session.get(Document, "doc-1")
    assert document is not None
    chat_session.delete(document)
    with pytest.raises(IntegrityError):
        chat_session.commit()
    chat_session.rollback()


def test_service_rejects_citation_without_snapshot_fields(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Chat", owner_user_id="user-1")

    with pytest.raises(ChatPersistenceError, match="citation document_title must not be blank"):
        service.create_message(
            session_id=created_session.id,
            role="assistant",
            content="Antwort mit Quelle",
            citations=[
                ChatCitationPayload(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    document_title=" ",
                    quote_preview="Chunk body text for citation support.",
                    source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 34},
                )
            ],
        )


def test_service_rejects_invalid_inputs(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)

    with pytest.raises(ChatPersistenceError, match="workspace_id must not be blank"):
        service.create_session(workspace_id=" ", title="Title", owner_user_id="user-1")
    with pytest.raises(ChatPersistenceError, match="title must not be blank"):
        service.create_session(workspace_id="workspace-1", title=" ", owner_user_id="user-1")


def test_service_rejects_missing_session(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)

    with pytest.raises(ChatSessionNotFoundError, match="chat session not found"):
        service.create_message(session_id="missing", role="user", content="Hallo")


def test_historical_chat_replay_keeps_snapshot_stable_for_archived_document(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    message = _create_assistant_message_with_citation(service)
    before = _citation_snapshot(service.list_citations(message_id=message.id)[0])

    DocumentLifecycleService.from_session(chat_session).archive("doc-1", workspace_id="workspace-1")

    replayed = service.list_citations(message_id=message.id)[0]
    after = _citation_snapshot(replayed)

    assert replayed.source_status == "archived"
    assert replayed.chunk_id == "chunk-1"
    assert after == {**before, "source_status": "archived"}


def test_historical_chat_replay_keeps_snapshot_stable_for_deleted_document(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    message = _create_assistant_message_with_citation(service)
    before = _citation_snapshot(service.list_citations(message_id=message.id)[0])

    DocumentLifecycleService.from_session(chat_session).delete("doc-1", workspace_id="workspace-1")

    replayed = service.list_citations(message_id=message.id)[0]
    after = _citation_snapshot(replayed)

    assert replayed.source_status == "deleted"
    assert replayed.chunk_id == "chunk-1"
    assert after == {**before, "source_status": "deleted"}


def test_historical_chat_replay_survives_version_replacement(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    message = _create_assistant_message_with_citation(service)
    before = _citation_snapshot(service.list_citations(message_id=message.id)[0])

    created = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    replacement_version = DocumentVersion(
        id="ver-2",
        document_id="doc-1",
        version_number=2,
        normalized_markdown="# Current\n\nReplacement body",
        markdown_hash="markdown-hash-replacement",
        parser_version="2.0",
        ocr_used=False,
        ki_provider=None,
        ki_model=None,
        metadata_={},
        created_at=created,
    )
    replacement_chunk = Chunk(
        id="chunk-2",
        document_id="doc-1",
        document_version_id="ver-2",
        chunk_index=0,
        heading_path=["Replacement"],
        anchor="dv:ver-2:c0000",
        content="Replacement chunk body text.",
        content_hash="chunk-hash-2",
        token_estimate=5,
        metadata_={"source_anchor": {"type": "text", "page": None, "paragraph": 2, "char_start": 0, "char_end": 28}},
        created_at=created,
    )
    document = chat_session.get(Document, "doc-1")
    assert document is not None
    chat_session.add(replacement_version)
    chat_session.flush()
    chat_session.add(replacement_chunk)
    chat_session.flush()
    document.current_version_id = replacement_version.id
    document.updated_at = created
    chat_session.add(document)
    chat_session.commit()

    replayed = service.list_citations(message_id=message.id)[0]
    after = _citation_snapshot(replayed)

    assert replayed.chunk_id == "chunk-1"
    assert chat_session.get(Chunk, "chunk-1") is not None
    assert document.current_version_id == "ver-2"
    assert after == before


def test_historical_chat_replay_survives_rechunk_without_dangling_reference(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    message = _create_assistant_message_with_citation(service)
    before = _citation_snapshot(service.list_citations(message_id=message.id)[0])

    replacement_chunk = Chunk(
        id="chunk-3",
        document_id="doc-1",
        document_version_id="ver-1",
        chunk_index=1,
        heading_path=["Current", "Rechunked"],
        anchor="dv:ver-1:c0001",
        content="Rechunked replacement body text.",
        content_hash="chunk-hash-3",
        token_estimate=6,
        metadata_={"source_anchor": {"type": "text", "page": None, "paragraph": 3, "char_start": 0, "char_end": 31}},
        created_at=datetime(2026, 5, 2, 11, 0, tzinfo=UTC),
    )
    chat_session.add(replacement_chunk)
    chat_session.flush()

    original_chunk = chat_session.get(Chunk, "chunk-1")
    assert original_chunk is not None
    chat_session.delete(original_chunk)
    chat_session.commit()

    replayed = service.list_citations(message_id=message.id)[0]
    after = _citation_snapshot(replayed)

    assert replayed.chunk_id is None
    assert replayed.document_id == "doc-1"
    assert after == {**before, "chunk_id": None}


def test_historical_chat_replay_is_unchanged_by_search_index_state_changes(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    message = _create_assistant_message_with_citation(service)
    before = _citation_snapshot(service.list_citations(message_id=message.id)[0])

    chunk = chat_session.get(Chunk, "chunk-1")
    assert chunk is not None
    chunk.is_searchable = False
    chunk.search_vector = ""
    chat_session.add(chunk)
    chat_session.commit()

    chunk.is_searchable = True
    chunk.search_vector = "reindexed replacement vector"
    chat_session.add(chunk)
    chat_session.commit()

    replayed = service.list_citations(message_id=message.id)[0]
    after = _citation_snapshot(replayed)

    assert replayed.chunk_id == "chunk-1"
    assert after == before


def test_live_status_lookup_returns_missing_for_absent_document(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)

    statuses = service.list_document_live_statuses(["doc-1", "missing-doc"])

    assert statuses == {"doc-1": "active", "missing-doc": "missing"}


def test_service_accepts_missing_citation_source_status(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Missing Citation", owner_user_id="user-1")

    message = service.create_message(
        session_id=created_session.id,
        role="assistant",
        content="Antwort mit fehlender Quelle",
        citations=[
            ChatCitationPayload(
                chunk_id=None,
                document_id="doc-1",
                document_title="Current Document",
                quote_preview="Historische Quelle ohne Live-Dokument.",
                source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 35},
                source_status="missing",
            )
        ],
    )

    citation = service.list_citations(message_id=message.id)[0]

    assert citation.source_status == "missing"


def test_service_rejects_unknown_citation_source_status(chat_session: Session) -> None:
    service = ChatPersistenceService(chat_session)
    created_session = service.create_session(workspace_id="workspace-1", title="Invalid Citation", owner_user_id="user-1")

    with pytest.raises(ChatPersistenceError, match="citation source_status must be one of: active, archived, deleted, missing"):
        service.create_message(
            session_id=created_session.id,
            role="assistant",
            content="Antwort mit ungueltiger Quelle",
            citations=[
                ChatCitationPayload(
                    chunk_id=None,
                    document_id="doc-1",
                    document_title="Current Document",
                    quote_preview="Historische Quelle ohne Live-Dokument.",
                    source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 35},
                    source_status="unknown",
                )
            ],
        )


def _create_assistant_message_with_citation(service: ChatPersistenceService):
    created_session = service.create_session(workspace_id="workspace-1", title="Replay", owner_user_id="user-1")
    return service.create_message(
        session_id=created_session.id,
        role="assistant",
        content="Historische Antwort mit Quelle",
        citations=[
            ChatCitationPayload(
                chunk_id="chunk-1",
                document_id="doc-1",
                document_title="Current Document",
                quote_preview="Chunk body text for citation support.",
                source_anchor={"type": "text", "page": None, "paragraph": None, "char_start": 0, "char_end": 34},
                source_status="active",
            )
        ],
    )


def _citation_snapshot(citation: ChatCitation) -> dict:
    return {
        "chunk_id": citation.chunk_id,
        "document_id": citation.document_id,
        "document_title": citation.document_title,
        "quote_preview": citation.quote_preview,
        "source_anchor": citation.source_anchor,
        "source_status": citation.source_status,
    }