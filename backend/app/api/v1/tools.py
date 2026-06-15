"""Tool and plugin governance endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import AuthContext, require_workspace_admin, require_workspace_member
from app.api.v1.approvals import _log_audit, create_approval

router = APIRouter(prefix="/tools", tags=["tools"])

_tools: list[dict] = []
_plugins: list[dict] = []


class ToggleRequest(BaseModel):
    enabled: bool
    reason: str = ""


def _approval(action: str, resource_id: str, enabled: bool, reason: str, ctx: AuthContext) -> dict:
    approval = create_approval(
        action=action,
        risk="HIGH",
        category="governance",
        context={"resource_id": resource_id, "enabled": enabled, "reason": reason},
    )
    _log_audit(f"{action}_APPROVAL_REQUIRED", ctx.login, resource_id, {"approval_id": approval["id"], "enabled": enabled})
    return {"ok": True, "approval_required": True, "approval_id": approval["id"], "risk": "HIGH"}


@router.get("")
def list_tools(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _tools, "total": len(_tools)}


@router.get("/{tool_id}/health")
def tool_health(tool_id: str, ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    item = next((tool for tool in _tools if tool["id"] == tool_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"id": tool_id, "status": "unknown"}


@router.patch("/{tool_id}/toggle")
def toggle_tool(tool_id: str, body: ToggleRequest, ctx: AuthContext = Depends(require_workspace_admin)) -> dict:
    return _approval("TOOL_TOGGLE", tool_id, body.enabled, body.reason, ctx)


@router.get("/plugins/list")
def list_plugins(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _plugins, "total": len(_plugins)}


@router.patch("/plugins/{plugin_id}/toggle")
def toggle_plugin(plugin_id: str, body: ToggleRequest, ctx: AuthContext = Depends(require_workspace_admin)) -> dict:
    return _approval("PLUGIN_TOGGLE", plugin_id, body.enabled, body.reason, ctx)

