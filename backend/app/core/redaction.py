from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


SECRET_FIELD_NAMES = {
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
}

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{8,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s,;}]+"),
)


def is_secret_field(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return normalized in SECRET_FIELD_NAMES or any(part in normalized for part in ("secret", "token", "password", "api_key"))


def mask_secret_value(value: Any) -> str:
    if value in (None, ""):
        return "missing"
    return "present"


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def mask_object_recursive(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if is_secret_field(key_text):
                result[key_text] = {"status": mask_secret_value(item)}
            else:
                result[key_text] = mask_object_recursive(item)
        return result
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [mask_object_recursive(item) for item in value]
    return value


def redact_for_ui(value: Any) -> Any:
    return mask_object_recursive(value)


def redact_for_log(value: Any) -> Any:
    return mask_object_recursive(value)
