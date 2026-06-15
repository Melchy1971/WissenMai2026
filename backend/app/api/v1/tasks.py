"""Task endpoints for GUI contracts."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.api.v1.approvals import _log_audit

router = APIRouter(prefix="/tasks", tags=["tasks"])

_tasks: list[dict] = []


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""


class TaskPatch(BaseModel):
    status: str


@router.get("")
def list_tasks(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": [t for t in _tasks if t["workspace_id"] == ctx.workspace_id], "total": len(_tasks)}


@router.post("")
def create_task(body: TaskCreate, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "workspace_id": ctx.workspace_id,
        "title": body.title,
        "description": body.description,
        "status": "open",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _tasks.append(item)
    _log_audit("TASK_CREATED", ctx.login, item["id"], item)
    return item


@router.patch("/{task_id}")
def patch_task(task_id: str, body: TaskPatch, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    task = next((item for item in _tasks if item["id"] == task_id and item["workspace_id"] == ctx.workspace_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task["status"] = body.status
    _log_audit("TASK_UPDATED", ctx.login, task_id, {"status": body.status})
    return task

