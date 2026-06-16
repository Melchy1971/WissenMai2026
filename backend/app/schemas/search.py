from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.documents import DocumentChunkSourceAnchor


# -- Legacy chunk result (kept for /search/chunks backward compat) -------------

class SearchChunkResult(BaseModel):
    model_config = ConfigDict(strict=True)

    document_id: str
    document_title: str
    document_created_at: datetime
    document_version_id: str
    version_number: int
    chunk_id: str
    position: int
    text_preview: str
    source_anchor: DocumentChunkSourceAnchor
    rank: float
    filters: dict[str, Any] = {}


# -- Unified search ------------------------------------------------------------

SearchKind = Literal["chunk", "topic", "document"]
SearchSort = Literal["score_desc", "created_at_desc", "created_at_asc", "title_asc"]

_VALID_SORTS: frozenset[str] = frozenset({"score_desc", "created_at_desc", "created_at_asc", "title_asc"})


class UnifiedSearchFilters(BaseModel):
    model_config = ConfigDict(strict=False)

    kind: list[SearchKind] | None = None
    status: list[str] | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None


class UnifiedSearchHit(BaseModel):
    model_config = ConfigDict(strict=True)

    kind: SearchKind
    id: str
    title: str
    highlight: str
    score: float
    status: str | None = None
    created_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)


class UnifiedSearchResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    hits: list[UnifiedSearchHit]
    total: int
    next_cursor: str | None
    has_more: bool
    query: str
    sort: SearchSort
    filters_applied: dict[str, Any] = Field(default_factory=dict)


# -- Cursor helpers ------------------------------------------------------------

def encode_cursor(offset: int) -> str:
    payload = json.dumps({"o": offset}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(token: str) -> int:
    try:
        payload = base64.urlsafe_b64decode(token.encode() + b"==").decode()
        data = json.loads(payload)
        return int(data.get("o", 0))
    except Exception:
        return 0
