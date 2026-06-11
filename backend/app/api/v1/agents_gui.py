"""Agent- und Execution-Endpunkte für GUI."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import require_workspace_member, AuthContext

router = APIRouter(prefix="/agents", tags=["agents"])

_agents: list[dict] = [
    {
        "id": "ag-planner",
        "name": "Planner",
        "type": "planner",
        "status": "idle",
        "limits": {"max_steps": 50, "max_tool_calls": 20, "max_runtime_seconds": 600},
        "execution_plan": None,
        "validation_report": {"passed": True, "checks": []},
    },
    {
        "id": "ag-researcher",
        "name": "Researcher",
        "type": "researcher",
        "status": "idle",
        "limits": {"max_steps": 30, "max_tool_calls": 10, "max_runtime_seconds": 300},
        "execution_plan": {
            "steps": [
                {"order": 1, "action": "retrieve_context", "tool": "rag_search"},
                {"order": 2, "action": "summarize", "tool": "llm_call"},
            ]
        },
        "validation_report": {"passed": True, "checks": ["limits_ok", "tools_available"]},
    },
]

_executions: list[dict] = []


@router.get("")
def list_agents(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _agents, "total": len(_agents)}


@router.get("/executions")
def list_executions(
    limit: int = 50,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    return {"items": _executions[-limit:], "total": len(_executions)}


@router.get("/{agent_id}")
def get_agent(
    agent_id: str,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    agent = next((a for a in _agents if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
