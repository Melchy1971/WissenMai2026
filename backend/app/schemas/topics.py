from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TopicStatus = Literal["draft", "review", "approved", "archived"]
TopicRelationType = Literal["primary", "related", "reference"]
TopicMergeProvider = Literal["ollama", "openai", "gemini"]


class TopicCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=500)
    summary: str | None = None
    status: TopicStatus = "draft"


class TopicUpdate(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str | None = Field(default=None, min_length=1, max_length=500)
    slug: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = None


class TopicDocumentItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    document_id: str
    relation_type: TopicRelationType
    created_at: datetime


class TopicTagItem(BaseModel):
    model_config = ConfigDict(strict=True)

    tag_id: str
    created_at: datetime


class TopicListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    title: str
    slug: str
    status: TopicStatus
    created_at: datetime
    updated_at: datetime
    doc_count: int
    tag_count: int


class TopicDetail(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    workspace_id: str
    title: str
    slug: str
    summary: str | None
    status: TopicStatus
    created_by: str
    approved_at: datetime | None
    approved_by: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    documents: list[TopicDocumentItem]
    tags: list[TopicTagItem]


class TopicListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[TopicListItem]
    total: int
    limit: int
    offset: int


class AttachDocumentRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    document_id: str
    relation_type: TopicRelationType = "related"


class AddTagRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    tag_id: str


class TopicMergeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    document_ids: list[str] = Field(..., min_length=1)
    provider: TopicMergeProvider = "ollama"


class TopicMergeResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str
    summary: str
    sources: list[str]
