"""Memory GUI endpoints without production sample data."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import AuthContext, require_workspace_member

router = APIRouter(prefix="/memory", tags=["memory"])

_memories: list[dict] = []
_review_queue: list[dict] = []
_conflicts: list[dict] = []


@router.get("")
def list_memory(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _memories, "total": len(_memories)}


@router.get("/search")
def search_memory(q: str = "", ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": [], "total": 0, "query": q}


@router.get("/review-queue")
def review_queue(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _review_queue, "total": len(_review_queue)}


@router.get("/conflicts")
def memory_conflicts(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _conflicts, "total": len(_conflicts)}

