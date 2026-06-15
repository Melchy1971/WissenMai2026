"""Read-only agent catalog endpoints for GUI."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.api.v1.orchestrator import _executions

router = APIRouter(prefix="/agents", tags=["agents"])

_agents: list[dict] = []


@router.get("")
def list_agents(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _agents, "total": len(_agents)}


@router.get("/executions")
def list_executions(
    limit: int = 50,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    items = [e for e in _executions if e["workspace_id"] == ctx.workspace_id]
    return {"items": items[-limit:], "total": len(items)}


@router.get("/{agent_id}")
def get_agent(
    agent_id: str,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    agent = next((a for a in _agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
