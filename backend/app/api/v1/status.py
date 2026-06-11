"""GET /status — System-Übersicht für GUI Dashboard und AppShell."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_workspace_member, AuthContext

router = APIRouter(prefix="/status", tags=["status"])


@router.get("")
def get_status(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    """System-Status: Privacy Mode, Provider, Gates, Autonomie-Level."""
    return {
        "privacy_mode": False,
        "provider_name": "local",
        "autonomy_level": "supervised",
        "release_status": "beta",
        "current_user_is_admin": ctx.role in {"owner", "admin"},
        "workspace_id": ctx.workspace_id,
        "gates": [
            {"id": "rag",           "label": "RAG",           "status": "PASS"},
            {"id": "memory",        "label": "Memory",        "status": "PASS"},
            {"id": "agents",        "label": "Agents",        "status": "PASS"},
            {"id": "governance",    "label": "Governance",    "status": "PASS"},
            {"id": "collaboration", "label": "Collaboration", "status": "PASS"},
            {"id": "settings",      "label": "Settings",      "status": "PASS"},
        ],
    }
