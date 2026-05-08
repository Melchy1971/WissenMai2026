from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatCitationResponse,
    ChatConfidenceResponse,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetail,
    ChatSessionSummary,
)


CREATED_AT = datetime(2026, 5, 5, 8, 0, tzinfo=UTC)


def source_anchor() -> dict:
    return {
        "type": "text",
        "page": None,
        "paragraph": None,
        "char_start": 12,
        "char_end": 48,
    }


def test_chat_session_request_and_summary_are_strict() -> None:
    request = ChatSessionCreateRequest(title="Contract Review")
    summary = ChatSessionSummary(
        id="session-1",
        workspace_id="workspace-1",
        title=request.title or "Untitled",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )

    assert summary.model_dump()["workspace_id"] == "workspace-1"

    with pytest.raises(ValidationError):
        ChatSessionCreateRequest(title="Contract Review", metadata={"leak": True})


def test_chat_message_response_contains_filtered_citations_and_confidence() -> None:
    citation = ChatCitationResponse(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_title="Document Title",
        source_anchor=source_anchor(),
        quote_preview="Quoted text",
        source_status="active",
    )
    confidence = ChatConfidenceResponse(
        sufficient_context=True,
        retrieval_score_max=0.91,
        retrieval_score_avg=0.75,
    )

    message = ChatMessageResponse(
        id="message-1",
        session_id="session-1",
        role="assistant",
        content="Answer with a source.",
        basis_type="knowledge_base",
        created_at=CREATED_AT,
        citations=[citation],
        confidence=confidence,
    )

    assert message.model_dump()["citations"] == [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "document_title": "Document Title",
            "source_anchor": source_anchor(),
            "quote_preview": "Quoted text",
            "source_status": "active",
        }
    ]
    assert "metadata" not in message.model_dump()


def test_chat_session_detail_nests_messages_without_orm_mode() -> None:
    detail = ChatSessionDetail(
        id="session-1",
        workspace_id="workspace-1",
        title="Contract Review",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        messages=[
            ChatMessageResponse(
                id="message-1",
                session_id="session-1",
                role="user",
                content="Question",
                basis_type="unknown",
                created_at=CREATED_AT,
            )
        ],
    )

    assert detail.messages[0].citations == []
    assert detail.messages[0].confidence is None


def test_message_create_request_requires_workspace_question_and_valid_limit() -> None:
    request = ChatMessageCreateRequest(question="Question")

    assert request.question == "Question"
    assert request.retrieval_limit == 8

    with pytest.raises(ValidationError):
        ChatMessageCreateRequest(workspace_id="workspace-1", question="Question")
    with pytest.raises(ValidationError):
        ChatMessageCreateRequest(question="")
    with pytest.raises(ValidationError):
        ChatMessageCreateRequest(question="Question", retrieval_limit=0)
    with pytest.raises(ValidationError):
        ChatMessageCreateRequest(question="Question", retrieval_limit=101)


def test_response_models_reject_extra_metadata_fields() -> None:
    with pytest.raises(ValidationError):
        ChatCitationResponse(
            chunk_id="chunk-1",
            document_id="doc-1",
            document_title="Document Title",
            source_anchor=source_anchor(),
            quote_preview="Quoted text",
            source_status="active",
            metadata={"raw": "must not leak"},
        )

    with pytest.raises(ValidationError):
        ChatMessageResponse(
            id="message-1",
            session_id="session-1",
            role="assistant",
            content="Answer",
            basis_type="knowledge_base",
            created_at=CREATED_AT,
            metadata_={"raw": "must not leak"},
        )


def test_chat_citation_response_accepts_missing_source_status() -> None:
    citation = ChatCitationResponse(
        chunk_id=None,
        document_id="doc-1",
        document_title="Missing Document",
        source_anchor=source_anchor(),
        quote_preview="Historical citation remains readable.",
        source_status="missing",
    )

    assert citation.source_status == "missing"


def test_chat_citation_response_rejects_unknown_source_status() -> None:
    with pytest.raises(ValidationError):
        ChatCitationResponse(
            chunk_id=None,
            document_id="doc-1",
            document_title="Unknown Document",
            source_anchor=source_anchor(),
            quote_preview="Historical citation remains readable.",
            source_status="unknown",
        )


def test_response_models_do_not_accept_raw_orm_objects() -> None:
    class OrmLikeSession:
        id = "session-1"
        workspace_id = "workspace-1"
        title = "Contract Review"
        created_at = CREATED_AT
        updated_at = CREATED_AT

    with pytest.raises(ValidationError):
        ChatSessionSummary.model_validate(OrmLikeSession())
