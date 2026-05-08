from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import DocumentChunkSourceAnchor


ChatRole = Literal["system", "user", "assistant"]
ChatBasisType = Literal["knowledge_base", "general", "mixed", "unknown"]


class StrictChatModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class ChatSessionCreateRequest(StrictChatModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)


class ChatSessionSummary(StrictChatModel):
    id: str
    workspace_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_user_question_preview: str | None = None


class ChatMessageCreateRequest(StrictChatModel):
    question: str = Field(min_length=1)
    retrieval_limit: int = Field(default=8, ge=1, le=100)


class ChatCitationResponse(StrictChatModel):
    chunk_id: str | None
    document_id: str
    document_title: str
    source_anchor: DocumentChunkSourceAnchor
    quote_preview: str
    source_status: Literal["active", "archived", "deleted", "missing"]


class ChatConfidenceResponse(StrictChatModel):
    sufficient_context: bool
    retrieval_score_max: float | None = None
    retrieval_score_avg: float | None = None


class ChatMessageResponse(StrictChatModel):
    id: str
    session_id: str
    role: ChatRole
    content: str
    basis_type: ChatBasisType
    created_at: datetime
    citations: list[ChatCitationResponse] = Field(default_factory=list)
    confidence: ChatConfidenceResponse | None = None


class ChatSessionDetail(ChatSessionSummary):
    messages: list[ChatMessageResponse] = Field(default_factory=list)
