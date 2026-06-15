"""GET /audit — Audit-Log, SECRET-Einträge gefiltert."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_workspace_member, AuthContext
from app.api.v1.approvals import get_audit_log
from app.core.redaction import redact_for_ui

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def get_audit(
    limit: int = 50,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    """Audit-Log zurückgeben. SECRET-Einträge werden nie angezeigt."""
    all_events = get_audit_log()
    # SECRET-Klassifizierung niemals zurückgeben
    visible = [redact_for_ui(e) for e in all_events if e.get("classification") != "SECRET"]
    return {"items": visible[-limit:], "total": len(visible)}
