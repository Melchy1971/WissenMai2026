"""Collaboration endpoints: teams, protocol-based runs, conflicts."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member
from app.api.v1.approvals import _log_audit
from app.core.redaction import redact_for_ui

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

_teams: list[dict] = []
_runs: list[dict] = []
_conflicts: list[dict] = []


class CollaborationProtocol(BaseModel):
    name: str = Field(min_length=1)
    roles: list[str] = Field(min_length=1)
    decision_policy: str = Field(min_length=1)


class CollaborationRunRequest(BaseModel):
    objective: str = Field(min_length=1)
    protocol: CollaborationProtocol


@router.get("/teams")
def list_teams(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _teams, "total": len(_teams)}


@router.post("/runs")
def create_run(body: CollaborationRunRequest, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "workspace_id": ctx.workspace_id,
        "objective": body.objective,
        "protocol": body.protocol.model_dump(),
        "status": "queued",
        "events": [{"type": "collaboration.run_created", "created_at": datetime.now(UTC).isoformat()}],
        "created_at": datetime.now(UTC).isoformat(),
    }
    _runs.append(item)
    _log_audit("COLLABORATION_RUN_CREATED", ctx.login, item["id"], item)
    return redact_for_ui(item)


@router.get("/runs")
def list_runs(
    limit: int = 50,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    safe_runs = []
    for run in [r for r in _runs if r["workspace_id"] == ctx.workspace_id][-limit:]:
        safe_run = dict(run)
        if "shared_workspace_snapshot" in safe_run:
            safe_run["shared_workspace_snapshot"] = [
                item for item in safe_run["shared_workspace_snapshot"]
                if item.get("classification") != "SECRET"
            ]
        safe_runs.append(redact_for_ui(safe_run))
    return {"items": safe_runs, "total": len(safe_runs)}


@router.get("/conflicts")
def list_conflicts(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _conflicts, "total": len(_conflicts)}
