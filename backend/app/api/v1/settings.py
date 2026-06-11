"""GET /settings + PATCH /settings + PATCH /settings/secrets."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.api.dependencies.auth import require_workspace_member, require_workspace_admin, AuthContext

router = APIRouter(prefix="/settings", tags=["settings"])

# ── In-Memory Store (ersetzt DB bis persistentes Modell vorliegt) ────────────
_DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": {
        "model": "gpt-4",
        "base_url": "http://localhost:11434",
        "timeout_seconds": 30,
        "max_retries": 3,
        # api_key wird NIEMALS zurückgegeben
    },
    "voice": {"enabled": False, "provider": "azure", "language": "de"},
    "security": {
        "require_approval_for_high": True,
        "block_critical_by_default": True,
        "audit_all_actions": True,
    },
    "governance": {"approval_expiry_minutes": 60, "require_two_approvers": False},
    "rag": {
        "chunk_size": 500,
        "chunk_overlap": 50,
        "min_score": 0.7,
        "max_chunks": 10,
    },
    "memory": {"max_entries": 1000, "decay_rate": 0.1, "auto_review": True},
    "agents": {"max_steps": 50, "max_tool_calls": 20, "max_runtime_seconds": 600},
    "collaboration": {"max_agents": 5, "revision_cycles": 3},
    "ui": {"dark_mode": False, "compact_view": False, "language": "de"},
}
_store: dict[str, Any] = {k: dict(v) for k, v in _DEFAULT_SETTINGS.items()}


def _validate_provider(data: dict) -> list[str]:
    errs = []
    t = data.get("timeout_seconds")
    if t is not None and not (1 <= int(t) <= 300):
        errs.append("provider.timeout_seconds: must be 1–300")
    r = data.get("max_retries")
    if r is not None and not (0 <= int(r) <= 5):
        errs.append("provider.max_retries: must be 0–5")
    return errs


def _validate_rag(data: dict) -> list[str]:
    errs = []
    cs = data.get("chunk_size")
    co = data.get("chunk_overlap")
    if cs is not None and not (100 <= int(cs) <= 2000):
        errs.append("rag.chunk_size: must be 100–2000")
    if cs is not None and co is not None and int(co) >= int(cs):
        errs.append("rag.chunk_overlap: must be < chunk_size")
    s = data.get("min_score")
    if s is not None and not (0.0 <= float(s) <= 1.0):
        errs.append("rag.min_score: must be 0.0–1.0")
    mc = data.get("max_chunks")
    if mc is not None and not (1 <= int(mc) <= 20):
        errs.append("rag.max_chunks: must be 1–20")
    return errs


def _validate_agents(data: dict) -> list[str]:
    errs = []
    ms = data.get("max_steps")
    if ms is not None and not (1 <= int(ms) <= 100):
        errs.append("agents.max_steps: must be 1–100")
    tc = data.get("max_tool_calls")
    if tc is not None and not (0 <= int(tc) <= 50):
        errs.append("agents.max_tool_calls: must be 0–50")
    rt = data.get("max_runtime_seconds")
    if rt is not None and not (1 <= int(rt) <= 3600):
        errs.append("agents.max_runtime_seconds: must be 1–3600")
    return errs


def _validate_collaboration(data: dict) -> list[str]:
    errs = []
    ma = data.get("max_agents")
    if ma is not None and not (1 <= int(ma) <= 10):
        errs.append("collaboration.max_agents: must be 1–10")
    rc = data.get("revision_cycles")
    if rc is not None and not (0 <= int(rc) <= 10):
        errs.append("collaboration.revision_cycles: must be 0–10")
    return errs


def _validate_governance(data: dict) -> list[str]:
    errs = []
    ae = data.get("approval_expiry_minutes")
    if ae is not None and not (1 <= int(ae) <= 1440):
        errs.append("governance.approval_expiry_minutes: must be 1–1440")
    return errs


_VALIDATORS = {
    "provider": _validate_provider,
    "rag": _validate_rag,
    "agents": _validate_agents,
    "collaboration": _validate_collaboration,
    "governance": _validate_governance,
}


@router.get("")
def get_settings(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    """Settings zurückgeben – api_key und alle Secrets werden NIEMALS zurückgegeben."""
    result = {}
    for section, data in _store.items():
        # Secrets aus jeder Sektion entfernen
        cleaned = {
            k: v for k, v in data.items()
            if k not in ("api_key", "password", "secret", "token", "private_key")
        }
        result[section] = cleaned
    return result


class SecretUpdateRequest(BaseModel):
    key: str = Field(..., description="z.B. provider.api_key")
    value: str = Field(..., min_length=1)


@router.patch("/secrets")
def update_secret(
    body: SecretUpdateRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    """Secret-Feld updaten – Wert wird niemals in Response zurückgegeben."""
    # key format: "section.field"
    parts = body.key.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="key must be 'section.field'")
    section, field = parts
    if section not in _store:
        _store[section] = {}
    # Secret nur speichern, nicht zurückgeben
    _store[section][field] = body.value  # stored server-side only
    return {"ok": True, "message": "Secret gespeichert (nicht zurückgegeben)"}


@router.patch("")
def patch_settings(
    body: dict,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    """Settings sektionsweise updaten mit Validierung."""
    errors: list[str] = []
    for section, data in body.items():
        if not isinstance(data, dict):
            errors.append(f"{section}: must be an object")
            continue
        validator = _VALIDATORS.get(section)
        if validator:
            errors.extend(validator(data))

    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    for section, data in body.items():
        if section not in _store:
            _store[section] = {}
        # Secrets aus PATCH-Body niemals persistent übernehmen (nur via /secrets)
        safe_data = {
            k: v for k, v in data.items()
            if k not in ("api_key", "password", "secret", "token", "private_key")
        }
        _store[section].update(safe_data)

    return get_settings(ctx)
