"""Project endpoints for GUI contracts."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.api.v1.approvals import _log_audit

router = APIRouter(prefix="/projects", tags=["projects"])

_projects: list[dict] = []


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


@router.get("")
def list_projects(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    items = [item for item in _projects if item["workspace_id"] == ctx.workspace_id]
    return {"items": items, "total": len(items)}


@router.post("")
def create_project(body: ProjectCreate, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "workspace_id": ctx.workspace_id,
        "name": body.name,
        "description": body.description,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _projects.append(item)
    _log_audit("PROJECT_CREATED", ctx.login, item["id"], item)
    return item


@router.get("/{project_id}")
def get_project(project_id: str, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = next((p for p in _projects if p["id"] == project_id and p["workspace_id"] == ctx.workspace_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return item

