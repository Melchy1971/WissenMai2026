"""Governance endpoints for status, changesets, rollback and protected actions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import AuthContext, require_workspace_admin, require_workspace_member
from app.api.v1.approvals import _log_audit, create_approval

router = APIRouter(prefix="/governance", tags=["governance"])

_privacy_mode: bool = False
_changesets: list[dict] = []
_rollback_points: list[dict] = []
_policy_decisions: list[dict] = []


class PrivacyModeRequest(BaseModel):
    enabled: bool
    reason: str = ""


class ChangesetApplyRequest(BaseModel):
    comment: str = ""


class RollbackRequest(BaseModel):
    reason: str


class PolicyReloadRequest(BaseModel):
    reason: str = ""


class RetentionCleanupRequest(BaseModel):
    reason: str
    dry_run: bool = True


def _approval_response(action: str, risk: str, category: str, context: dict, ctx: AuthContext) -> dict:
    if risk == "CRITICAL" and ctx.role not in {"owner", "admin"}:
        _log_audit(f"{action}_BLOCKED", ctx.login, category, {"risk": risk, "reason": "admin_required", **context})
        raise HTTPException(status_code=403, detail="CRITICAL action requires admin and approval")
    approval = create_approval(action=action, risk=risk, category=category, context=context)
    _log_audit(f"{action}_APPROVAL_REQUIRED", ctx.login, approval["id"], {"risk": risk, **context})
    return {"ok": True, "risk": risk, "approval_required": True, "approval_id": approval["id"]}


@router.get("/status")
def get_governance_status(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {
        "privacy_mode": _privacy_mode,
        "current_user_is_admin": ctx.role in {"owner", "admin"},
        "pending_approvals": 0,
        "open_changesets": len([c for c in _changesets if c["status"] == "pending"]),
        "rollback_points_count": len(_rollback_points),
    }


@router.patch("/privacy-mode")
def toggle_privacy_mode(
    body: PrivacyModeRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    return _approval_response(
        "PRIVACY_MODE_CHANGE",
        "HIGH",
        "governance",
        {"enabled": body.enabled, "reason": body.reason},
        ctx,
    )


@router.get("/changesets")
def list_changesets(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _changesets, "total": len(_changesets)}


@router.post("/changesets/{changeset_id}/apply")
def apply_changeset(
    changeset_id: str,
    body: ChangesetApplyRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    cs = next((c for c in _changesets if c["id"] == changeset_id), None)
    if not cs:
        raise HTTPException(status_code=404, detail="Changeset not found")
    if cs["status"] != "pending":
        raise HTTPException(status_code=409, detail="Changeset already applied")
    return _approval_response(
        "CHANGESET_APPLY",
        "HIGH",
        "governance",
        {"changeset_id": changeset_id, "comment": body.comment},
        ctx,
    )


@router.get("/rollback-points")
def list_rollback_points(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _rollback_points, "total": len(_rollback_points)}


@router.post("/rollback/{rollback_id}")
def execute_rollback(
    rollback_id: str,
    body: RollbackRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    rp = next((r for r in _rollback_points if r["id"] == rollback_id), None)
    if not rp:
        raise HTTPException(status_code=404, detail="Rollback point not found")
    return _approval_response(
        "ROLLBACK",
        "CRITICAL",
        "governance",
        {"rollback_id": rollback_id, "reason": body.reason},
        ctx,
    )


@router.post("/rollback")
def execute_default_rollback(
    body: RollbackRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    return _approval_response(
        "ROLLBACK",
        "CRITICAL",
        "governance",
        {"rollback_id": "latest", "reason": body.reason},
        ctx,
    )


@router.post("/policy/reload")
def reload_policy(
    body: PolicyReloadRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    return _approval_response("POLICY_RELOAD", "HIGH", "governance", {"reason": body.reason}, ctx)


@router.post("/retention/cleanup")
def retention_cleanup(
    body: RetentionCleanupRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    risk = "HIGH" if body.dry_run else "CRITICAL"
    return _approval_response("RETENTION_CLEANUP", risk, "governance", body.model_dump(), ctx)


@router.get("/policy-decisions")
def list_policy_decisions(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _policy_decisions, "total": len(_policy_decisions)}
