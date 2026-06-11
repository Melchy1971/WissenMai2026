"""Governance-Endpunkte: status, changesets, rollback, policy-decisions, privacy-mode."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import (
    require_workspace_member,
    require_workspace_admin,
    AuthContext,
)
from app.api.v1.approvals import create_approval, _log_audit

router = APIRouter(prefix="/governance", tags=["governance"])

# ── In-Memory Stores ─────────────────────────────────────────────────────────
_privacy_mode: bool = False
_changesets: list[dict] = []
_rollback_points: list[dict] = [
    {
        "id": "rp-initial",
        "label": "Initial State",
        "created_at": "2026-01-01T00:00:00Z",
        "description": "Systemzustand bei Erstinstallation",
    }
]
_policy_decisions: list[dict] = []


class PrivacyModeRequest(BaseModel):
    enabled: bool


class ChangesetApplyRequest(BaseModel):
    comment: str = ""


class RollbackRequest(BaseModel):
    reason: str


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
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    global _privacy_mode
    _privacy_mode = body.enabled
    _log_audit(
        "PRIVACY_MODE_CHANGED", ctx.login, "system",
        {"enabled": body.enabled},
    )
    return {"ok": True, "privacy_mode": _privacy_mode}


@router.get("/changesets")
def list_changesets(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _changesets, "total": len(_changesets)}


@router.post("/changesets/{changeset_id}/apply")
def apply_changeset(
    changeset_id: str,
    body: ChangesetApplyRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    cs = next((c for c in _changesets if c["id"] == changeset_id), None)
    if not cs:
        raise HTTPException(status_code=404, detail="Changeset not found")
    if cs["status"] != "pending":
        raise HTTPException(status_code=409, detail="Changeset already applied")
    # Riskante Aktion → Approval erzeugen statt direkt ausführen
    approval = create_approval(
        action="CHANGESET_APPLY",
        risk="HIGH",
        category="governance",
        context={"changeset_id": changeset_id, "comment": body.comment},
    )
    return {"ok": True, "approval_required": True, "approval_id": approval["id"]}


@router.get("/rollback-points")
def list_rollback_points(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _rollback_points, "total": len(_rollback_points)}


@router.post("/rollback/{rollback_id}")
def execute_rollback(
    rollback_id: str,
    body: RollbackRequest,
    ctx: AuthContext = Depends(require_workspace_admin),  # Rollback nur mit Admin Permission
) -> dict:
    rp = next((r for r in _rollback_points if r["id"] == rollback_id), None)
    if not rp:
        raise HTTPException(status_code=404, detail="Rollback point not found")
    # Rollback ist CRITICAL → Approval erzeugen
    approval = create_approval(
        action="ROLLBACK",
        risk="CRITICAL",
        category="governance",
        context={"rollback_id": rollback_id, "reason": body.reason},
    )
    _log_audit("ROLLBACK_REQUESTED", ctx.login, rollback_id, {"reason": body.reason})
    return {"ok": True, "approval_required": True, "approval_id": approval["id"]}


@router.get("/policy-decisions")
def list_policy_decisions(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {"items": _policy_decisions, "total": len(_policy_decisions)}
