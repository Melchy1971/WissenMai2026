"""GET /approvals, POST /approvals/{id}/approve, POST /approvals/{id}/reject."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import require_workspace_member, require_workspace_admin, AuthContext

router = APIRouter(prefix="/approvals", tags=["approvals"])

# ── In-Memory Store ──────────────────────────────────────────────────────────
_approvals: list[dict] = []
_audit_log: list[dict] = []  # shared with audit router (importiert dort)


def _log_audit(action: str, actor: str, resource_id: str, details: dict | None = None) -> None:
    _audit_log.append({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "actor": actor,
        "resource_id": resource_id,
        "classification": "INTERNAL",
        "details": details or {},
    })


def get_approval_store() -> list[dict]:
    return _approvals


def get_audit_log() -> list[dict]:
    return _audit_log


class ApproveRequest(BaseModel):
    comment: str = ""


class RejectRequest(BaseModel):
    reason: str = ""


@router.get("")
def list_approvals(
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    items = list(_approvals)
    if status:
        items = [a for a in items if a["status"] == status]
    if category:
        items = [a for a in items if a.get("category") == category]
    return {"items": items[:limit], "total": len(items)}


@router.post("/{approval_id}/approve")
def approve(
    approval_id: str,
    body: ApproveRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    approval = next((a for a in _approvals if a["id"] == approval_id), None)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval["status"] != "pending":
        raise HTTPException(status_code=409, detail="Approval is not pending")
    approval["status"] = "approved"
    approval["decided_by"] = ctx.login
    approval["decided_at"] = datetime.now(UTC).isoformat()
    approval["comment"] = body.comment
    # Approval-Entscheidungen auditieren
    _log_audit("APPROVAL_APPROVED", ctx.login, approval_id, {"comment": body.comment})
    return {"ok": True, "approval": approval}


@router.post("/{approval_id}/reject")
def reject(
    approval_id: str,
    body: RejectRequest,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    approval = next((a for a in _approvals if a["id"] == approval_id), None)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval["status"] != "pending":
        raise HTTPException(status_code=409, detail="Approval is not pending")
    approval["status"] = "rejected"
    approval["decided_by"] = ctx.login
    approval["decided_at"] = datetime.now(UTC).isoformat()
    approval["reason"] = body.reason
    # Approval-Entscheidungen auditieren
    _log_audit("APPROVAL_REJECTED", ctx.login, approval_id, {"reason": body.reason})
    return {"ok": True, "approval": approval}


def create_approval(action: str, risk: str, category: str, context: dict) -> dict:
    """Hilfsfunktion: riskante Aktionen erzeugen Approval statt Direkt-Ausführung."""
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "risk": risk,
        "category": category,
        "context": context,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "decided_by": None,
        "decided_at": None,
    }
    _approvals.append(entry)
    return entry
