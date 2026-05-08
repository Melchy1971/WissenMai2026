from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import RequestAuthContext, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import (
    ChatPersistenceFailedApiError,
    ChatSessionNotFoundApiError,
    ServiceUnavailableApiError,
)
from app.db.session import get_session
from app.models.documents import ChatCitation, ChatMessage, ChatSession
from app.schemas.chat import (
    ChatCitationResponse,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetail,
    ChatSessionSummary,
)
from app.services.chat.citation_mapper import CitationMapper
from app.services.chat.context_builder import ContextBuilder
from app.services.chat.insufficient_context_policy import InsufficientContextPolicy
from app.services.chat.persistence_service import (
    ChatPersistenceError,
    ChatPersistenceService,
    ChatSessionNotFoundError,
)
from app.services.chat.prompt_builder import PromptBuilder
from app.services.chat.rag_chat_service import RagChatService
from app.services.search_service import SearchService


router = APIRouter(prefix="/chat", tags=["chat"])


class UnconfiguredLlmProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("LLM provider is not configured")


def get_chat_service() -> Iterator[ChatPersistenceService]:
    try:
        for session in get_session():
            yield ChatPersistenceService.from_session(session)
    except DatabaseConfigurationError as exc:
        raise ServiceUnavailableApiError(message=str(exc)) from exc


def get_rag_chat_service() -> Iterator[RagChatService]:
    try:
        for session in get_session():
            yield RagChatService(
                persistence=ChatPersistenceService.from_session(session),
                retrieval=SearchService.from_session(session),
                context_builder=ContextBuilder(max_context_chars=12000, max_context_tokens=2500, min_chunk_chars=40),
                insufficient_context_policy=InsufficientContextPolicy(),
                prompt_builder=PromptBuilder(),
                llm_provider=UnconfiguredLlmProvider(),
                citation_mapper=CitationMapper(),
                retrieval_limit=8,
            )
    except DatabaseConfigurationError as exc:
        raise ServiceUnavailableApiError(message=str(exc)) from exc


@router.post("/sessions", response_model=ChatSessionSummary, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    request: ChatSessionCreateRequest,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ChatPersistenceService, Depends(get_chat_service)],
) -> ChatSessionSummary:
    try:
        chat_session = service.create_session(
            workspace_id=auth_context.workspace_id,
            title=request.title or "Untitled chat",
            owner_user_id=auth_context.user_id,
        )
    except ChatPersistenceError as exc:
        raise ChatPersistenceFailedApiError(message=str(exc)) from exc
    return to_session_summary(chat_session)


@router.get("/sessions", response_model=list[ChatSessionSummary])
def list_chat_sessions(
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ChatPersistenceService, Depends(get_chat_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ChatSessionSummary]:
    try:
        sessions = service.list_sessions(workspace_id=auth_context.workspace_id, limit=limit, offset=offset)
    except ChatPersistenceError as exc:
        raise ChatPersistenceFailedApiError(message=str(exc)) from exc
    return [to_session_summary(chat_session) for chat_session in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session_detail(
    session_id: str,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[ChatPersistenceService, Depends(get_chat_service)],
) -> ChatSessionDetail:
    try:
        chat_session = service.get_session(session_id=session_id)
        if chat_session.workspace_id != auth_context.workspace_id:
            raise ChatSessionNotFoundError(session_id)
        messages = service.list_messages(session_id=session_id)
        all_citations: list[list[ChatCitation]] = [
            service.list_citations(message_id=message.id) for message in messages
        ]
        all_document_ids = [c.document_id for clist in all_citations for c in clist]
        live_statuses = service.list_document_live_statuses(all_document_ids)
        message_responses = [
            to_message_response(message, citations, live_statuses)
            for message, citations in zip(messages, all_citations)
        ]
    except ChatSessionNotFoundError as exc:
        raise ChatSessionNotFoundApiError(details={"session_id": session_id}) from exc
    except ChatPersistenceError as exc:
        raise ChatPersistenceFailedApiError(message=str(exc)) from exc

    return ChatSessionDetail(
        **to_session_summary(chat_session).model_dump(),
        messages=message_responses,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def create_chat_message(
    session_id: str,
    request: ChatMessageCreateRequest,
    auth_context: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[RagChatService, Depends(get_rag_chat_service)],
) -> ChatMessageResponse:
    return service.answer_question(
        session_id=session_id,
        workspace_id=auth_context.workspace_id,
        question=request.question,
        retrieval_limit=request.retrieval_limit,
    )


def to_session_summary(chat_session: ChatSession) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=chat_session.id,
        workspace_id=chat_session.workspace_id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
    )


def to_message_response(
    message: ChatMessage,
    citations: list[ChatCitation],
    live_statuses: dict[str, str] | None = None,
) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        basis_type=message.basis_type,
        created_at=message.created_at,
        citations=[to_citation_response(citation, live_statuses) for citation in citations],
        confidence=None,
    )


def to_citation_response(citation: ChatCitation, live_statuses: dict[str, str] | None = None) -> ChatCitationResponse:
    source_status = citation.source_status
    if live_statuses is not None:
        live = live_statuses.get(citation.document_id)
        if live is not None:
            source_status = live
    return ChatCitationResponse(
        chunk_id=citation.chunk_id,
        document_id=citation.document_id,
        document_title=citation.document_title,
        source_anchor=citation.source_anchor,
        quote_preview=citation.quote_preview,
        source_status=source_status,
    )
