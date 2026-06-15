"""Secret Masking – Keine Secrets in API-Responses."""
import re

import pytest

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

BASE = "http://localhost:8000/api/v1"
HEADERS = {"Authorization": "Bearer test-token", "X-Workspace-Id": "ws-test"}

pytestmark = [
    pytest.mark.external_env_only,
    pytest.mark.legacy_live_http,
    pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed"),
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r'"api_key"\s*:\s*"[^"]+"'),
    re.compile(r'"password"\s*:\s*"[^"]+"'),
    re.compile(r'"private_key"\s*:\s*"[^"]+"'),
    re.compile(r'"token"\s*:\s*"[A-Za-z0-9._-]{20,}"'),
]

ENDPOINTS = [
    "/status",
    "/settings",
    "/agents",
    "/rag/documents",
    "/governance/status",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_no_secrets_in_response(path):
    r = httpx.get(f"{BASE}{path}", headers=HEADERS)
    if r.status_code not in (200,):
        pytest.skip(f"{path}: status {r.status_code}")
    body = r.text
    for pattern in SECRET_PATTERNS:
        m = pattern.search(body)
        assert m is None, (
            f"Secret-Pattern '{pattern.pattern}' in {path}: '{m.group()[:30]}'"
        )


def test_settings_secrets_endpoint_returns_no_value():
    """PATCH /settings/secrets gibt Wert NICHT zurück."""
    r = httpx.patch(
        f"{BASE}/settings/secrets",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"key": "provider.api_key", "value": "sk-test-12345"},
    )
    if r.status_code not in (200, 403, 401):
        pytest.skip(f"Endpoint not accessible: {r.status_code}")
    if r.status_code == 200:
        text = r.text
        assert "sk-test-12345" not in text


def test_auth_token_not_in_any_response():
    """Auth-Token darf nie in Responses auftauchen."""
    test_token = "Bearer test-token"
    r = httpx.get(f"{BASE}/settings", headers=HEADERS)
    if r.status_code == 200:
        assert test_token not in r.text
        assert "test-token" not in r.text


def test_rag_secret_doc_has_no_content():
    r = httpx.get(f"{BASE}/rag/documents", headers=HEADERS)
    if r.status_code != 200:
        pytest.skip("RAG endpoint not accessible")
    for doc in r.json().get("items", []):
        if doc.get("classification") == "SECRET":
            assert "content" not in doc
            assert "chunks" not in doc
            assert doc.get("index_status") == "blocked"
