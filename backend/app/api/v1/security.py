"""GET /security/status."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_workspace_member, AuthContext

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/status")
def get_security_status(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return {
        "require_approval_for_high": True,
        "block_critical_by_default": True,
        "audit_all_actions": True,
        "secret_masking_enabled": True,
        "auth_token_logging": False,  # NEVER log tokens
        "privacy_mode": False,
    }
