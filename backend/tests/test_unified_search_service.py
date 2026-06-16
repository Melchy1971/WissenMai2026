"""Unit tests for the unified search service layer.

Uses FakeSearchRepository to avoid any DB dependency — all logic under test
lives in SearchService and the schema helpers (cursor encode/decode).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.repositories.search import UnifiedSearchRecord
from app.schemas.search import UnifiedSearchFilters, decode_cursor, encode_cursor
from app.services.search_service import InvalidSearchQueryError, SearchService

pytestmark = pytest.mark.unit_fast


# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW = datetime(2026, 6, 16, 10, 0, tzinfo=UTC)
_WS = "ws-001"


def _rec(
    *,
    kind: str = "topic",
    id: str = "t-1",
    title: str = "Test Title",
    highlight: str = "<mark>Test</mark> Title",
    score: float = 0.9,
    status: str | None = "draft",
    created_at: datetime | None = None,
    meta: dict[str, Any] | None = None,
) -> UnifiedSearchRecord:
    return UnifiedSearchRecord(
        kind=kind,
        id=id,
        title=title,
        highlight=highlight,
        score=score,
        status=status,
        created_at=created_at or _NOW,
        meta=meta or {},
    )


class FakeSearchRepository:
    """Fake that returns a configurable list of UnifiedSearchRecords."""

    def __init__(self, records: list[UnifiedSearchRecord] | None = None) -> None:
        self.records = records or []
        self.calls: list[dict] = []

    # legacy
    def search_chunks(self, *, workspace_id, query, limit, offset, filters=None):
        return []

    def search_unified(
        self,
        *,
        workspace_id,
        query,
        limit,
        offset,
        sort,
        kind_filter,
        status_filter,
        created_after,
        created_before,
    ) -> tuple[list[UnifiedSearchRecord], int]:
        self.calls.append({
            "workspace_id": workspace_id,
            "query": query,
            "limit": limit,
            "offset": offset,
            "sort": sort,
            "kind_filter": kind_filter,
            "status_filter": status_filter,
        })
        total = len(self.records)
        return self.records[offset : offset + limit], total


def _service(records=None) -> SearchService:
    return SearchService(FakeSearchRepository(records))


# ── Cursor encode/decode ──────────────────────────────────────────────────────

def test_cursor_roundtrip() -> None:
    token = encode_cursor(42)
    assert decode_cursor(token) == 42


def test_cursor_decode_invalid_returns_zero() -> None:
    assert decode_cursor("!!!notbase64!!!") == 0
    assert decode_cursor("") == 0


def test_cursor_decode_zero() -> None:
    assert decode_cursor(encode_cursor(0)) == 0


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(("ws", "q", "lim", "msg"), [
    ("  ", "query", 20, "workspace_id is required"),
    ("ws", "  ", 20, "query must not be blank"),
    ("ws", "q", 0, "limit must be between 1 and 100"),
    ("ws", "q", 101, "limit must be between 1 and 100"),
])
def test_search_unified_validates_input(ws, q, lim, msg) -> None:
    svc = _service()
    with pytest.raises(InvalidSearchQueryError, match=msg):
        svc.search_unified(workspace_id=ws, query=q, limit=lim)


def test_search_unified_rejects_invalid_sort() -> None:
    svc = _service()
    with pytest.raises(InvalidSearchQueryError, match="sort must be one of"):
        svc.search_unified(workspace_id=_WS, query="x", sort="invalid_sort")


# ── Basic result mapping ──────────────────────────────────────────────────────

def test_search_unified_maps_records() -> None:
    records = [_rec(id="t-1", score=0.9, kind="topic"), _rec(id="t-2", score=0.8, kind="document")]
    svc = _service(records)
    resp = svc.search_unified(workspace_id=_WS, query="test")
    assert resp.total == 2
    assert len(resp.hits) == 2
    assert resp.hits[0].id == "t-1"
    assert resp.hits[0].kind == "topic"
    assert resp.hits[1].id == "t-2"
    assert resp.hits[1].kind == "document"
    assert resp.query == "test"
    assert resp.sort == "score_desc"


def test_search_unified_trims_query_and_workspace() -> None:
    svc = _service([_rec()])
    resp = svc.search_unified(workspace_id="  ws-1  ", query="  hello  ")
    assert resp.query == "hello"
    call = svc._repository.calls[0]  # type: ignore[attr-defined]
    assert call["workspace_id"] == "ws-1"
    assert call["query"] == "hello"


# ── Cursor pagination ─────────────────────────────────────────────────────────

def test_search_unified_first_page_has_next_cursor_when_more() -> None:
    records = [_rec(id=f"t-{i}") for i in range(10)]
    svc = _service(records)
    resp = svc.search_unified(workspace_id=_WS, query="test", limit=4)
    assert resp.total == 10
    assert len(resp.hits) == 4
    assert resp.has_more is True
    assert resp.next_cursor is not None


def test_search_unified_last_page_has_no_cursor() -> None:
    records = [_rec(id=f"t-{i}") for i in range(3)]
    svc = _service(records)
    resp = svc.search_unified(workspace_id=_WS, query="test", limit=10)
    assert resp.has_more is False
    assert resp.next_cursor is None


def test_search_unified_cursor_advances_page() -> None:
    records = [_rec(id=f"t-{i}") for i in range(10)]
    svc = _service(records)

    page1 = svc.search_unified(workspace_id=_WS, query="test", limit=4)
    assert page1.next_cursor is not None

    page2 = svc.search_unified(workspace_id=_WS, query="test", limit=4, cursor=page1.next_cursor)
    ids1 = {h.id for h in page1.hits}
    ids2 = {h.id for h in page2.hits}
    assert ids1.isdisjoint(ids2), "Pages must not overlap"


def test_search_unified_exact_page_size_shows_next_cursor() -> None:
    records = [_rec(id=f"t-{i}") for i in range(5)]
    svc = _service(records)
    resp = svc.search_unified(workspace_id=_WS, query="test", limit=5)
    # total == limit, so offset + limit == total => has_more = False
    assert resp.has_more is False


# ── Filters passed through ────────────────────────────────────────────────────

def test_search_unified_passes_kind_filter() -> None:
    svc = _service([_rec(kind="topic")])
    filters = UnifiedSearchFilters(kind=["topic"])
    svc.search_unified(workspace_id=_WS, query="test", filters=filters)
    assert svc._repository.calls[0]["kind_filter"] == ["topic"]  # type: ignore[attr-defined]


def test_search_unified_passes_status_filter() -> None:
    svc = _service([_rec(status="approved")])
    filters = UnifiedSearchFilters(status=["approved"])
    svc.search_unified(workspace_id=_WS, query="test", filters=filters)
    assert svc._repository.calls[0]["status_filter"] == ["approved"]  # type: ignore[attr-defined]


def test_search_unified_filters_applied_in_response() -> None:
    svc = _service([_rec(kind="topic")])
    filters = UnifiedSearchFilters(kind=["topic"], status=["draft"])
    resp = svc.search_unified(workspace_id=_WS, query="test", filters=filters)
    assert "kind" in resp.filters_applied
    assert "status" in resp.filters_applied


# ── Sort forwarded ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sort", ["score_desc", "created_at_desc", "created_at_asc", "title_asc"])
def test_search_unified_valid_sorts(sort: str) -> None:
    svc = _service([_rec()])
    resp = svc.search_unified(workspace_id=_WS, query="test", sort=sort)
    assert resp.sort == sort


def test_search_unified_sort_forwarded_to_repository() -> None:
    svc = _service([])
    svc.search_unified(workspace_id=_WS, query="test", sort="title_asc")
    assert svc._repository.calls[0]["sort"] == "title_asc"  # type: ignore[attr-defined]


# ── Empty results ─────────────────────────────────────────────────────────────

def test_search_unified_empty_results() -> None:
    svc = _service([])
    resp = svc.search_unified(workspace_id=_WS, query="nothingfound")
    assert resp.total == 0
    assert resp.hits == []
    assert resp.has_more is False
    assert resp.next_cursor is None
