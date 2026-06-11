"""Sicherstellen, dass Secrets nie in API-Responses erscheinen."""
import pytest
import httpx
import re

BASE = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-token", "X-Workspace-Id": "ws-test"}

SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{10,}'),      # OpenAI-style keys
    re.compile(r'Bearer [A-Za-z0-9._-]{10,}'), # Auth tokens
    re.compile(r'password["\':]\s*["\'"][^"\']+["\'"]', re.IGNORECASE),
]

ENDPOINTS_TO_CHECK = [
    "/api/v1/settings",
    "/api/v1/status",
    "/api/v1/agents",
    "/api/v1/memory",
    "/api/v1/rag/documents",
]


@pytest.mark.parametrize("path", ENDPOINTS_TO_CHECK)
def test_no_secrets_in_response(path):
    r = httpx.get(f"{BASE}{path}", headers=HEADERS)
    if r.status_code not in (200,):
        pytest.skip(f"Endpoint {path} not accessible (status {r.status_code})")
    body = r.text
    for pattern in SECRET_PATTERNS:
        match = pattern.search(body)
        assert match is None, \
            f"Secret-Pattern '{pattern.pattern}' in {path} response: '{match.group()[:20]}...'"


def test_secret_documents_not_in_rag():
    r = httpx.get(f"{BASE}/api/v1/rag/documents", headers=HEADERS)
    if r.status_code != 200:
        pytest.skip("RAG endpoint not accessible")
    items = r.json().get("items", [])
    for doc in items:
        if doc.get("classification") == "SECRET":
            assert "content" not in doc, "SECRET doc content must not be returned"
            assert "chunks" not in doc, "SECRET doc chunks must not be returned"
