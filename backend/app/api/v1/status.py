"""GET /status - system overview for GUI dashboard and AppShell."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_member

router = APIRouter(prefix="/status", tags=["status"])

UNKNOWN = "UNKNOWN"
CRITICAL_STATUSES = {"FAIL", "FAILED", "BLOCKED", "CRITICAL", "ERROR"}
WARNING_STATUSES = {"WARNING", "WARN", "DEGRADED", "PENDING", "RUNNING", "QUEUED"}
_REPORTS_DIR = Path(__file__).resolve().parents[4] / "reports" / "current"


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


def _read_report(filename: str) -> dict:
    try:
        payload = json.loads((_REPORTS_DIR / filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _release_status() -> str:
    report = _read_report("release_gate.json")
    return _upper(report.get("current_status") or report.get("verdict") or report.get("status"))


def _gui_status() -> str:
    candidates = [
        _read_report("gui_release_candidate.json").get("overall_status"),
        _read_report("gui_truth_report.json").get("status"),
    ]
    statuses = [_upper(value) for value in candidates if value is not None]
    if not statuses:
        return UNKNOWN
    priority = {
        UNKNOWN: -1,
        "OK": 0,
        "PASS": 0,
        "WARNING": 1,
        "WARN": 1,
        "DEGRADED": 1,
        "FAIL": 2,
        "FAILED": 2,
        "CRITICAL": 3,
        "BLOCKED": 4,
    }
    return max(statuses, key=lambda status: priority.get(status, 1))


def _provider_snapshot() -> tuple[str, str]:
    try:
        from app.api.v1.settings import _store

        provider = _store.get("provider") or {}
    except Exception:
        return UNKNOWN, UNKNOWN

    model = str(provider.get("model") or "").strip()
    base_url = str(provider.get("base_url") or "").strip()
    name = str(provider.get("name") or "").strip().upper()
    if not name:
        normalized_url = base_url.lower()
        if "11434" in normalized_url or "ollama" in normalized_url:
            name = "OLLAMA"
        elif "openai" in normalized_url:
            name = "OPENAI"
        elif "googleapis" in normalized_url or "gemini" in normalized_url:
            name = "GEMINI"
        elif base_url:
            name = "CUSTOM"
    status = "CONFIGURED" if model and (base_url or name) else "UNCONFIGURED"
    return status, name or UNKNOWN


def _autonomy_status() -> str:
    try:
        from app.api.v1.settings import _store

        agents = _store.get("agents") or {}
        security = _store.get("security") or {}
    except Exception:
        return UNKNOWN
    if not agents.get("agents_enabled"):
        return "DISABLED"
    if security.get("require_approval_for_high") or security.get("block_critical_by_default"):
        return "SUPERVISED"
    return "AUTONOMOUS"


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
    return "OK"


def _rag_status() -> str:
    try:
        from app.api.v1.rag_gui import _documents
    except Exception:
        return UNKNOWN
    if not _documents:
        return "EMPTY"
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
        from app.api.v1.settings import _store
    except Exception:
        return UNKNOWN
    if not (_store.get("governance") or {}).get("changesets_enabled"):
        return "DISABLED"
    if any(_upper(approval.get("risk")) == "CRITICAL" for approval in pending_approvals):
        return "CRITICAL"
    if pending_approvals or any(item.get("status") == "pending" for item in _changesets):
        return "WARNING"
    return "OK"


def _agent_status(workspace_id: str) -> str:
    try:
        from app.api.v1.orchestrator import _executions
        from app.api.v1.settings import _store
    except Exception:
        return UNKNOWN
    if not (_store.get("agents") or {}).get("agents_enabled"):
        return "DISABLED"
    items = [item for item in _executions if item.get("workspace_id") == workspace_id]
    return _status_from_runtime_items(items, empty_status="IDLE")


def _collaboration_status(workspace_id: str) -> str:
    try:
        from app.api.v1.collaboration_gui import _runs
        from app.api.v1.settings import _store
    except Exception:
        return UNKNOWN
    if not (_store.get("collaboration") or {}).get("collaboration_enabled"):
        return "DISABLED"
    items = [item for item in _runs if item.get("workspace_id") == workspace_id]
    return _status_from_runtime_items(items, empty_status="IDLE")


@router.get("", response_model=StatusResponse)
def get_status(ctx: AuthContext = Depends(require_workspace_member)) -> StatusResponse:
    """Return a dashboard-safe status snapshot without fake green defaults."""
    pending_approvals = _pending_approvals()
    critical_audit_events = _critical_audit_events()
    release_status = _release_status()
    provider_status, provider_name = _provider_snapshot()
    autonomy_level = _autonomy_status()
    governance_gate = _governance_status(pending_approvals)
    security_gate = _security_status()
    gui_gate = _gui_status()
    rag_status = _rag_status()
    agent_status = _agent_status(ctx.workspace_id)
    collaboration_status = _collaboration_status(ctx.workspace_id)
    gates = {
        "release_status": release_status,
        "governance_gate": governance_gate,
        "security_gate": security_gate,
        "gui_gate": gui_gate,
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
        release_status=release_status,
        system_health=system_health,
        provider_status=provider_status,
        workspace_status="ACTIVE",
        privacy_mode=_privacy_mode(),
        autonomy_level=autonomy_level,
        governance_gate=governance_gate,
        security_gate=security_gate,
        gui_gate=gui_gate,
        rag_status=rag_status,
        agent_status=agent_status,
        collaboration_status=collaboration_status,
        open_approvals_count=len(pending_approvals),
        critical_audit_events_count=len(critical_audit_events),
        open_blockers=blockers,
        current_user_is_admin=ctx.role in {"owner", "admin"},
        workspace_id=ctx.workspace_id,
        provider_name=provider_name,
        gates=[
            StatusGate(id="release", label="Release", status=release_status),
            StatusGate(id="governance", label="Governance", status=governance_gate),
            StatusGate(id="security", label="Security", status=security_gate),
            StatusGate(id="gui", label="GUI", status=gui_gate),
            StatusGate(id="rag", label="RAG", status=rag_status),
            StatusGate(id="agents", label="Agents", status=agent_status),
            StatusGate(id="collaboration", label="Collaboration", status=collaboration_status),
        ],
    )
