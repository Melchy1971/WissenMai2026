from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from app.core.errors import (
    ChatPersistenceFailedApiError,
    ChatSessionNotFoundApiError,
    InsufficientContextApiError,
    LlmUnavailableApiError,
    RetrievalFailedApiError,
)
from app.core.redaction import redact_for_ui
from app.schemas.chat import ChatCitationResponse, ChatConfidenceResponse, ChatMessageResponse
from app.schemas.search import SearchChunkResult
from app.observability.logging import bind_observability_context, log_event
from app.services.chat.citation_mapper import Citation, CitationMapper, CitationMappingError
from app.services.chat.context_builder import ContextBuildError, ContextBuilder
from app.services.chat.insufficient_context_policy import InsufficientContextPolicy
from app.services.chat.persistence_service import ChatCitationPayload, ChatPersistenceError, ChatSessionNotFoundError
from app.services.chat.prompt_builder import PromptBuildError, PromptBuilder


class RetrievalServiceProtocol(Protocol):
    def search_chunks(
        self,
        workspace_id: str,
        query: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchChunkResult]: ...


class ChatPersistenceProtocol(Protocol):
    def create_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
        citations: list[ChatCitationPayload] | None = None,
        basis_type: str = "unknown",
    ) -> Any: ...


class LlmProviderProtocol(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class LlmProviderError(RuntimeError):
    pass


class RagChatService:
    def __init__(
        self,
        *,
        persistence: ChatPersistenceProtocol,
        retrieval: RetrievalServiceProtocol,
        context_builder: ContextBuilder,
        insufficient_context_policy: InsufficientContextPolicy,
        prompt_builder: PromptBuilder,
        llm_provider: LlmProviderProtocol,
        citation_mapper: CitationMapper,
        retrieval_limit: int = 20,
    ) -> None:
        if retrieval_limit < 1:
            raise ValueError("retrieval_limit must be positive")
        self._persistence = persistence
        self._retrieval = retrieval
        self._context_builder = context_builder
        self._insufficient_context_policy = insufficient_context_policy
        self._prompt_builder = prompt_builder
        self._llm_provider = llm_provider
        self._citation_mapper = citation_mapper
        self._retrieval_limit = retrieval_limit

    def answer_question(
        self,
        *,
        session_id: str,
        workspace_id: str,
        question: str,
        retrieval_limit: int | None = None,
    ) -> ChatMessageResponse:
        started_at = perf_counter()
        bind_observability_context(workspace_id=workspace_id)
        normalized_question = question.strip()
        if not normalized_question:
            raise InsufficientContextApiError(message="question must not be blank", details={"session_id": session_id})
        effective_retrieval_limit = retrieval_limit or self._retrieval_limit
        if effective_retrieval_limit < 1 or effective_retrieval_limit > 100:
            raise InsufficientContextApiError(
                message="retrieval_limit must be between 1 and 100",
                details={"session_id": session_id, "retrieval_limit": effective_retrieval_limit},
            )

        self._require_session_in_workspace(session_id=session_id, workspace_id=workspace_id)
        self._save_user_question(session_id=session_id, question=normalized_question)
        retrieval_results = self._retrieve(
            workspace_id=workspace_id,
            question=normalized_question,
            retrieval_limit=effective_retrieval_limit,
        )
        context = self._build_context(retrieval_results)
        decision = self._insufficient_context_policy.evaluate(
            question=normalized_question,
            retrieval_results=retrieval_results,
            context=context,
        )
        if not decision.sufficient_context:
            log_event(
                "rag_insufficient_context",
                workspace_id=workspace_id,
                duration_ms=int((perf_counter() - started_at) * 1000),
                status="failed",
                error_code="INSUFFICIENT_CONTEXT",
            )
            raise InsufficientContextApiError(
                message=decision.reason or "Insufficient context",
                details={
                    "session_id": session_id,
                    "retrieval_score_max": decision.retrieval_score_max,
                    "retrieval_score_avg": decision.retrieval_score_avg,
                },
            )

        prompt = self._build_prompt(question=normalized_question, context=context)
        answer = self._generate_answer(prompt)
        if redact_for_ui(answer) != answer:
            raise InsufficientContextApiError(
                message="answer blocked by validation pipeline",
                details={"session_id": session_id, "reason": "secret_candidate_detected"},
            )
        citations = self._map_citations(answer=answer, context=context)
        if not citations:
            raise InsufficientContextApiError(
                message="answer contains no supported citations",
                details={"session_id": session_id, "source_chunk_ids": prompt.source_chunk_ids},
            )

        assistant_message = self._save_assistant_answer(
            session_id=session_id,
            answer=answer,
            citations=citations,
            metadata={
                "prompt_template_version": prompt.template_version,
                "source_chunk_ids": prompt.source_chunk_ids,
                "retrieval_score_max": decision.retrieval_score_max,
                "retrieval_score_avg": decision.retrieval_score_avg,
            },
        )

        log_event(
            "chat_message_created",
            workspace_id=workspace_id,
            duration_ms=int((perf_counter() - started_at) * 1000),
            status="completed",
        )

        citation_responses = [self._to_citation_response(citation) for citation in citations]
        return ChatMessageResponse(
            id=assistant_message.id,
            session_id=assistant_message.session_id,
            role=assistant_message.role,
            content=assistant_message.content,
            basis_type=assistant_message.basis_type,
            created_at=assistant_message.created_at,
            citations=citation_responses,
            used_rag_context=True,
            sources=[
                {
                    "document_name": citation.document_title,
                    "chunk_id": citation.chunk_id,
                    "page": citation.source_anchor.page,
                    "score": None,
                    "classification": "INTERNAL",
                }
                for citation in citation_responses
            ],
            blocked_source_count=0,
            status="ok",
            confidence=ChatConfidenceResponse(
                sufficient_context=True,
                retrieval_score_max=decision.retrieval_score_max,
                retrieval_score_avg=decision.retrieval_score_avg,
            ),
        )

    def _require_session_in_workspace(self, *, session_id: str, workspace_id: str) -> None:
        get_session = getattr(self._persistence, "get_session", None)
        if get_session is None:
            return
        try:
            chat_session = get_session(session_id=session_id)
        except ChatSessionNotFoundError as exc:
            raise ChatSessionNotFoundApiError(details={"session_id": session_id}) from exc
        if chat_session.workspace_id != workspace_id:
            raise ChatSessionNotFoundApiError(details={"session_id": session_id})

    def _save_user_question(self, *, session_id: str, question: str) -> None:
        try:
            self._persistence.create_message(
                session_id=session_id,
                role="user",
                content=question,
                basis_type="unknown",
            )
        except ChatSessionNotFoundError as exc:
            raise ChatSessionNotFoundApiError(details={"session_id": session_id}) from exc
        except ChatPersistenceError as exc:
            raise ChatPersistenceFailedApiError(message=str(exc), details={"session_id": session_id}) from exc

    def _retrieve(self, *, workspace_id: str, question: str, retrieval_limit: int) -> list[SearchChunkResult]:
        try:
            return self._retrieval.search_chunks(
                workspace_id=workspace_id,
                query=question,
                limit=retrieval_limit,
                offset=0,
                filters=None,
            )
        except Exception as exc:
            raise RetrievalFailedApiError(message=str(exc), details={"workspace_id": workspace_id}) from exc

    def _build_context(self, retrieval_results: list[SearchChunkResult]):
        try:
            return self._context_builder.build(retrieval_results)
        except ContextBuildError as exc:
            raise RetrievalFailedApiError(message=str(exc)) from exc

    def _build_prompt(self, *, question: str, context):
        try:
            return self._prompt_builder.build(question=question, context=context)
        except PromptBuildError as exc:
            raise InsufficientContextApiError(message=str(exc)) from exc

    def _generate_answer(self, prompt) -> str:
        try:
            response = self._llm_provider.generate(prompt.system_prompt, prompt.user_prompt)
        except Exception as exc:
            log_event(
                "llm_unavailable",
                status="failed",
                error_code="LLM_UNAVAILABLE",
            )
            raise LlmUnavailableApiError(message=str(exc)) from exc

        if not response.strip():
            log_event(
                "llm_unavailable",
                status="failed",
                error_code="LLM_UNAVAILABLE",
            )
            raise LlmUnavailableApiError(message="LLM returned an empty response")
        return response.strip()

    def _map_citations(self, *, answer: str, context) -> list[Citation]:
        try:
            return self._citation_mapper.map_citations(answer=answer, context=context)
        except CitationMappingError as exc:
            raise InsufficientContextApiError(message=str(exc)) from exc

    def _save_assistant_answer(
        self,
        *,
        session_id: str,
        answer: str,
        citations: list[Citation],
        metadata: dict[str, Any],
    ):
        try:
            return self._persistence.create_message(
                session_id=session_id,
                role="assistant",
                content=answer,
                basis_type="knowledge_base",
                metadata=metadata,
                citations=[self._to_citation_payload(citation) for citation in citations],
            )
        except ChatSessionNotFoundError as exc:
            raise ChatSessionNotFoundApiError(details={"session_id": session_id}) from exc
        except ChatPersistenceError as exc:
            raise ChatPersistenceFailedApiError(message=str(exc), details={"session_id": session_id}) from exc

    def _to_citation_payload(self, citation: Citation) -> ChatCitationPayload:
        return ChatCitationPayload(
            chunk_id=citation.chunk_id,
            document_id=citation.document_id,
            document_title=citation.document_title,
            quote_preview=citation.quote_preview,
            source_anchor=citation.source_anchor.model_dump(),
            source_status="active",
        )

    def _to_citation_response(self, citation: Citation) -> ChatCitationResponse:
        return ChatCitationResponse(
            chunk_id=citation.chunk_id,
            document_id=citation.document_id,
            document_title=citation.document_title,
            source_anchor=citation.source_anchor,
            quote_preview=citation.quote_preview,
            source_status="active",
        )
