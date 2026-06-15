"""Orchestrator endpoints for agent execution."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.api.v1.approvals import _log_audit

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_executions: list[dict] = []


class ExecutionPlan(BaseModel):
    steps: list[dict] = Field(min_length=1)


class GoalCreate(BaseModel):
    goal: str = Field(min_length=1)
    execution_plan: ExecutionPlan


@router.post("/goals")
def create_goal(body: GoalCreate, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "workspace_id": ctx.workspace_id,
        "goal": body.goal,
        "execution_plan": body.execution_plan.model_dump(),
        "status": "queued",
        "events": [
            {
                "type": "orchestrator.goal_created",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
        "created_at": datetime.now(UTC).isoformat(),
    }
    _executions.append(item)
    _log_audit("ORCHESTRATOR_GOAL_CREATED", ctx.login, item["id"], {"goal": body.goal})
    return item


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = next((e for e in _executions if e["id"] == execution_id and e["workspace_id"] == ctx.workspace_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return item
