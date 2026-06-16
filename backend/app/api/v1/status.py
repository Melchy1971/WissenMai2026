"""GET /status - system overview for GUI dashboard and AppShell."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member

router = APIRouter(prefix="/status", tags=["status"])

UNKNOWN = "UNKNOWN"
CRITICAL_STATUSES = {"FAIL", "FAILED", "BLOCKED", "CRITICAL", "ERROR"}
WARNING_STATUSES = {"WARNING", "WARN", "DEGRADED", "PENDING", "RUNNING", "QUEUED"}


class StatusBlocker(BaseModel):
    id: str
    severity: str = "CRITICAL"
    title: str
    source: str
    status: str = "OPEN"


class StatusGate(BaseModel):
    id: str
    label: str
    status: str = UNKNOWN


class StatusResponse(BaseModel):
    release_status: str = UNKNOWN
    system_health: str = UNKNOWN
    provider_status: str = UNKNOWN
    workspace_status: str = UNKNOWN
    privacy_mode: bool | None = None
    autonomy_level: str = UNKNOWN
    governance_gate: str = UNKNOWN
    security_gate: str = UNKNOWN
    gui_gate: str = UNKNOWN
    rag_status: str = UNKNOWN
    agent_status: str = UNKNOWN
    collaboration_status: str = UNKNOWN
    open_approvals_count: int = 0
    critical_audit_events_count: int = 0
    open_blockers: list[StatusBlocker] = Field(default_factory=list)
    current_user_is_admin: bool = False
    workspace_id: str
    provider_name: str = UNKNOWN
    gates: list[StatusGate] = Field(default_factory=list)


def _upper(value: object) -> str:
    if value is None:
        return UNKNOWN
    text = str(value).strip()
    return text.upper() if text else UNKNOWN


def _is_critical(value: object) -> bool:
    return _upper(value) in CRITICAL_STATUSES


def _is_warning(value: object) -> bool:
    return _upper(value) in WARNING_STATUSES


def _status_from_runtime_items(items: list[dict], *, empty_status: str = UNKNOWN) -> str:
    if not items:
        return empty_status
    statuses = [_upper(item.get("status")) for item in items]
    if any(status in CRITICAL_STATUSES for status in statuses):
        return "CRITICAL"
    if any(status in WARNING_STATUSES for status in statuses):
        return "WARNING"
    return "OK"


def _security_status() -> str:
    try:
        from app.api.v1.security import get_security_status

        payload = get_security_status()  # type: ignore[call-arg]
    except Exception:
        return UNKNOWN
    if payload.get("auth_token_logging") is True:
        return "CRITICAL"
    if payload.get("secret_masking_enabled") is False:
        return "CRITICAL"
    if payload.get("audit_all_actions") is False:
        return "WARNING"
    return UNKNOWN


def _rag_status() -> str:
    try:
        from app.api.v1.rag_gui import _documents
    except Exception:
        return UNKNOWN
    if not _documents:
        return UNKNOWN
    statuses = [_upper(doc.get("index_status")) for doc in _documents]
    if any(status == "BLOCKED" for status in statuses):
        return "WARNING"
    if any(status in {"PENDING", "RUNNING"} for status in statuses):
        return "WARNING"
    if all(status == "INDEXED" for status in statuses):
        return "OK"
    return UNKNOWN


def _critical_audit_events() -> list[dict]:
    try:
        from app.api.v1.approvals import get_audit_log
    except Exception:
        return []
    events = []
    for event in get_audit_log():
        details = event.get("details") or {}
        if event.get("classification") == "SECRET":
            continue
        if _upper(event.get("severity")) == "CRITICAL" or _upper(details.get("risk")) == "CRITICAL":
            events.append(event)
        elif str(event.get("action", "")).endswith("_BLOCKED"):
            events.append(event)
    return events


def _pending_approvals() -> list[dict]:
    try:
        from app.api.v1.approvals import get_approval_store
    except Exception:
        return []
    return [approval for approval in get_approval_store() if approval.get("status") == "pending"]


def _build_blockers(
    *,
    pending_approvals: list[dict],
    critical_audit_events: list[dict],
    gates: dict[str, str],
) -> list[StatusBlocker]:
    blockers: list[StatusBlocker] = []
    for approval in pending_approvals:
        if _upper(approval.get("risk")) == "CRITICAL":
            blockers.append(
                StatusBlocker(
                    id=str(approval.get("id", "approval")),
                    severity="CRITICAL",
                    title=f"Approval required: {approval.get('action', 'unknown action')}",
                    source="approvals",
                )
            )
    for event in critical_audit_events:
        blockers.append(
            StatusBlocker(
                id=str(event.get("id", "audit-event")),
                severity="CRITICAL",
                title=f"Critical audit event: {event.get('action', 'unknown action')}",
                source="audit",
            )
        )
    for gate_name, gate_status in gates.items():
        if _is_critical(gate_status):
            blockers.append(
                StatusBlocker(
                    id=f"gate:{gate_name}",
                    severity="CRITICAL",
                    title=f"{gate_name.replace('_', ' ').title()} is {gate_status}",
                    source="status",
                )
            )
    return blockers


def _privacy_mode() -> bool | None:
    try:
        from app.api.v1.governance import _privacy_mode as enabled
    except Exception:
        return None
    return bool(enabled)


def _governance_status(pending_approvals: list[dict]) -> str:
    try:
        from app.api.v1.governance import _changesets
    except Exception:
        return UNKNOWN
    if any(_upper(approval.get("risk")) == "CRITICAL" for approval in pending_approvals):
        return "CRITICAL"
    if pending_approvals or any(item.get("status") == "pending" for item in _changesets):
        return "WARNING"
    return UNKNOWN


def _agent_status(workspace_id: str) -> str:
    try:
        from app.api.v1.orchestrator import _executions
    except Exception:
        return UNKNOWN
    items = [item for item in _executions if item.get("workspace_id") == workspace_id]
    return _status_from_runtime_items(items)


def _collaboration_status(workspace_id: str) -> str:
    try:
        from app.api.v1.collaboration_gui import _runs
    except Exception:
        return UNKNOWN
    items = [item for item in _runs if item.get("workspace_id") == workspace_id]
    return _status_from_runtime_items(items)


@router.get("", response_model=StatusResponse)
def get_status(ctx: AuthContext = Depends(require_workspace_member)) -> StatusResponse:
    """Return a dashboard-safe status snapshot without fake green defaults."""
    pending_approvals = _pending_approvals()
    critical_audit_events = _critical_audit_events()
    governance_gate = _governance_status(pending_approvals)
    security_gate = _security_status()
    rag_status = _rag_status()
    agent_status = _agent_status(ctx.workspace_id)
    collaboration_status = _collaboration_status(ctx.workspace_id)
    gates = {
        "governance_gate": governance_gate,
        "security_gate": security_gate,
        "gui_gate": UNKNOWN,
        "rag_status": rag_status,
        "agent_status": agent_status,
        "collaboration_status": collaboration_status,
    }
    blockers = _build_blockers(
        pending_approvals=pending_approvals,
        critical_audit_events=critical_audit_events,
        gates=gates,
    )
    if blockers or any(_is_critical(value) for value in gates.values()):
        system_health = "CRITICAL"
    elif any(_is_warning(value) for value in gates.values()):
        system_health = "WARNING"
    else:
        system_health = UNKNOWN

    return StatusResponse(
        release_status=UNKNOWN,
        system_health=system_health,
        provider_status=UNKNOWN,
        workspace_status="ACTIVE",
        privacy_mode=_privacy_mode(),
        autonomy_level=UNKNOWN,
        governance_gate=governance_gate,
        security_gate=security_gate,
        gui_gate=UNKNOWN,
        rag_status=rag_status,
        agent_status=agent_status,
        collaboration_status=collaboration_status,
        open_approvals_count=len(pending_approvals),
        critical_audit_events_count=len(critical_audit_events),
        open_blockers=blockers,
        current_user_is_admin=ctx.role in {"owner", "admin"},
        workspace_id=ctx.workspace_id,
        provider_name=UNKNOWN,
        gates=[
            StatusGate(id="governance", label="Governance", status=governance_gate),
            StatusGate(id="security", label="Security", status=security_gate),
            StatusGate(id="gui", label="GUI", status=UNKNOWN),
            StatusGate(id="rag", label="RAG", status=rag_status),
            StatusGate(id="agents", label="Agents", status=agent_status),
            StatusGate(id="collaboration", label="Collaboration", status=collaboration_status),
        ],
    )
