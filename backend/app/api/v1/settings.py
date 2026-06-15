"""GET /settings + PATCH /settings + PATCH /settings/secrets."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies.auth import AuthContext, require_workspace_admin, require_workspace_member
from app.api.v1.approvals import _log_audit
from app.core.redaction import is_secret_field, redact_for_ui

router = APIRouter(prefix="/settings", tags=["settings"])

_DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": {
        "model": "gpt-4",
        "base_url": "http://localhost:11434",
        "timeout_seconds": 30,
        "max_retries": 3,
    },
    "voice": {"enabled": False, "provider": "azure", "language": "de"},
    "security": {
        "require_approval_for_high": True,
        "block_critical_by_default": True,
        "audit_all_actions": True,
        "source_required": True,
        "review_queue_required": True,
        "validation_pipeline_enabled": True,
        "rollback_enabled": True,
        "plugin_sandbox_enabled": True,
        "plugins_enabled": False,
    },
    "governance": {
        "approval_expiry_minutes": 60,
        "require_two_approvers": False,
        "changesets_enabled": True,
    },
    "rag": {
        "chunk_size": 500,
        "chunk_overlap": 50,
        "min_score": 0.7,
        "max_chunks": 10,
    },
    "memory": {
        "max_entries": 1000,
        "decay_rate": 0.1,
        "auto_review": True,
        "memory_extraction_enabled": True,
    },
    "agents": {
        "max_steps": 50,
        "max_tool_calls": 20,
        "max_runtime_seconds": 600,
        "agents_enabled": True,
    },
    "collaboration": {
        "max_agents": 5,
        "revision_cycles": 3,
        "collaboration_enabled": True,
        "arbitration_enabled": True,
    },
    "ui": {"dark_mode": False, "compact_view": False, "language": "de"},
}
_store: dict[str, Any] = {k: dict(v) for k, v in _DEFAULT_SETTINGS.items()}


def _int_between(data: dict, key: str, section: str, low: int, high: int, errors: list[str]) -> None:
    value = data.get(key)
    if value is None:
        return
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        errors.append(f"{section}.{key}: must be an integer")
        return
    if not low <= parsed <= high:
        errors.append(f"{section}.{key}: must be {low}-{high}")


def _float_between(data: dict, key: str, section: str, low: float, high: float, errors: list[str]) -> None:
    value = data.get(key)
    if value is None:
        return
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        errors.append(f"{section}.{key}: must be a number")
        return
    if not low <= parsed <= high:
        errors.append(f"{section}.{key}: must be {low}-{high}")


def _validate_provider(data: dict) -> list[str]:
    errors: list[str] = []
    _int_between(data, "timeout_seconds", "provider", 1, 300, errors)
    _int_between(data, "max_retries", "provider", 0, 5, errors)
    return errors


def _validate_rag(data: dict) -> list[str]:
    errors: list[str] = []
    _int_between(data, "chunk_size", "rag", 100, 2000, errors)
    _int_between(data, "chunk_overlap", "rag", 0, 1999, errors)
    _float_between(data, "min_score", "rag", 0.0, 1.0, errors)
    _int_between(data, "max_chunks", "rag", 1, 20, errors)
    if data.get("chunk_size") is not None and data.get("chunk_overlap") is not None:
        try:
            if int(data["chunk_overlap"]) >= int(data["chunk_size"]):
                errors.append("rag.chunk_overlap: must be < chunk_size")
        except (TypeError, ValueError):
            pass
    return errors


def _validate_agents(data: dict) -> list[str]:
    errors: list[str] = []
    _int_between(data, "max_steps", "agents", 1, 100, errors)
    _int_between(data, "max_tool_calls", "agents", 0, 50, errors)
    _int_between(data, "max_runtime_seconds", "agents", 1, 3600, errors)
    return errors


def _validate_collaboration(data: dict) -> list[str]:
    errors: list[str] = []
    _int_between(data, "max_agents", "collaboration", 1, 10, errors)
    _int_between(data, "revision_cycles", "collaboration", 0, 10, errors)
    return errors


def _validate_governance(data: dict) -> list[str]:
    errors: list[str] = []
    _int_between(data, "approval_expiry_minutes", "governance", 1, 1440, errors)
    return errors


def _validate_memory(data: dict) -> list[str]:
    errors: list[str] = []
    _int_between(data, "max_entries", "memory", 1, 100000, errors)
    _float_between(data, "decay_rate", "memory", 0.0, 1.0, errors)
    return errors


def _validate_language_section(section: str, data: dict) -> list[str]:
    language = data.get("language")
    if language is not None and language not in {"de", "en"}:
        return [f"{section}.language: must be de or en"]
    return []


_VALIDATORS = {
    "provider": _validate_provider,
    "rag": _validate_rag,
    "agents": _validate_agents,
    "collaboration": _validate_collaboration,
    "governance": _validate_governance,
    "memory": _validate_memory,
    "voice": lambda data: _validate_language_section("voice", data),
    "ui": lambda data: _validate_language_section("ui", data),
    "security": lambda data: [],
}


def _merged_settings(body: dict) -> dict[str, Any]:
    merged = {k: dict(v) for k, v in _store.items()}
    for section, data in body.items():
        if isinstance(data, dict):
            merged.setdefault(section, {})
            merged[section].update({k: v for k, v in data.items() if not is_secret_field(k)})
    return merged


def _validate_dependencies(body: dict, ctx: AuthContext) -> list[str]:
    merged = _merged_settings(body)
    security = merged.get("security", {})
    governance = merged.get("governance", {})
    memory = merged.get("memory", {})
    agents = merged.get("agents", {})
    collaboration = merged.get("collaboration", {})
    errors: list[str] = []

    if security.get("source_required") is False and ctx.role not in {"owner", "admin"}:
        errors.append("security.source_required: only admins may disable source_required")
    if memory.get("memory_extraction_enabled") and security.get("review_queue_required") is False:
        errors.append("security.review_queue_required: cannot be disabled while memory_extraction_enabled is active")
    if agents.get("agents_enabled") and security.get("validation_pipeline_enabled") is False:
        errors.append("security.validation_pipeline_enabled: cannot be disabled while agents_enabled is active")
    if collaboration.get("collaboration_enabled") and collaboration.get("arbitration_enabled") is False:
        errors.append("collaboration.arbitration_enabled: cannot be disabled while collaboration_enabled is active")
    if governance.get("changesets_enabled") and security.get("rollback_enabled") is False:
        errors.append("security.rollback_enabled: cannot be disabled while ChangeSets are active")
    if security.get("plugins_enabled") and security.get("plugin_sandbox_enabled") is False:
        errors.append("security.plugin_sandbox_enabled: cannot be disabled while Plugins are active")
    return errors


def _public_settings() -> dict:
    result = {}
    for section, data in _store.items():
        result[section] = {k: v for k, v in data.items() if not is_secret_field(k)}
    return redact_for_ui(result)


@router.get("")
def get_settings(ctx: AuthContext = Depends(require_workspace_member)) -> dict:
    return _public_settings()


class SecretUpdateRequest(BaseModel):
    key: str = Field(..., description="z.B. provider.api_key")
    value: str = Field(..., min_length=1)


@router.patch("/secrets")
def update_secret(
    body: SecretUpdateRequest,
    ctx: AuthContext = Depends(require_workspace_admin),
) -> dict:
    parts = body.key.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="key must be 'section.field'")
    section, field = parts
    if section not in _store:
        _store[section] = {}
    _store[section][field] = body.value
    _log_audit("SETTING_SECRET_UPDATED", ctx.login, body.key, {"key": body.key, "value": body.value})
    return {"ok": True, "message": "Secret gespeichert (nicht zurueckgegeben)", "status": "present"}


@router.patch("")
def patch_settings(
    body: dict,
    ctx: AuthContext = Depends(require_workspace_member),
) -> dict:
    errors: list[str] = []
    for section, data in body.items():
        if not isinstance(data, dict):
            errors.append(f"{section}: must be an object")
            continue
        validator = _VALIDATORS.get(section)
        if validator is None:
            errors.append(f"{section}: unknown settings section")
            continue
        errors.extend(validator(data))

    errors.extend(_validate_dependencies(body, ctx))
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    for section, data in body.items():
        _store.setdefault(section, {})
        _store[section].update({k: v for k, v in data.items() if not is_secret_field(k)})

    _log_audit("SETTINGS_UPDATED", ctx.login, "settings", body)
    return _public_settings()
