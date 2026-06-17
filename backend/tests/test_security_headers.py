"""Tests für Security Headers Middleware (GA-SEC-01).

Prüft: CSP-Header vorhanden, Inline-Script-Block, External-Script-Block, Iframe-Block.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability.security_headers import SecurityHeadersMiddleware, _build_csp


# ── Fixtures ──────────────────────────────────────────────────────────────── #

def _make_app(dev_mode: bool = False) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, dev_mode=dev_mode)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


@pytest.fixture
def prod_client():
    return TestClient(_make_app(dev_mode=False), raise_server_exceptions=True)


@pytest.fixture
def dev_client():
    return TestClient(_make_app(dev_mode=True), raise_server_exceptions=True)


# ── Tests: Header vorhanden ────────────────────────────────────────────────── #

def test_csp_header_present(prod_client):
    r = prod_client.get("/ping")
    assert r.status_code == 200
    assert "content-security-policy" in r.headers


def test_x_content_type_options(prod_client):
    r = prod_client.get("/ping")
    assert r.headers.get("x-content-type-options") == "nosniff"


def test_referrer_policy(prod_client):
    r = prod_client.get("/ping")
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_permissions_policy_present(prod_client):
    r = prod_client.get("/ping")
    assert "permissions-policy" in r.headers


def test_x_frame_options_deny(prod_client):
    r = prod_client.get("/ping")
    assert r.headers.get("x-frame-options") == "DENY"


# ── Tests: CSP-Direktiven ─────────────────────────────────────────────────── #

def test_csp_default_src_self(prod_client):
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "default-src 'self'" in csp


def test_csp_frame_src_none(prod_client):
    """iframe-Block: frame-src 'none'"""
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "frame-src 'none'" in csp


def test_csp_object_src_none(prod_client):
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "object-src 'none'" in csp


def test_csp_frame_ancestors_none(prod_client):
    """Verhindert Embedding in iframes von Fremddomain."""
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp


def test_csp_no_unsafe_eval_in_prod(prod_client):
    """Prod: kein 'unsafe-eval' in script-src."""
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "'unsafe-eval'" not in csp


def test_csp_script_src_self_only_prod(prod_client):
    """Extern geladene Scripts geblockt (nur 'self' erlaubt)."""
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "script-src 'self'" in csp


def test_csp_upgrade_insecure_requests(prod_client):
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "upgrade-insecure-requests" in csp


# ── Tests: Provider-Origins in connect-src ───────────────────────────────── #

def test_csp_connect_src_ollama(prod_client):
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "http://localhost:11434" in csp


def test_csp_connect_src_openai(prod_client):
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "https://api.openai.com" in csp


def test_csp_connect_src_gemini(prod_client):
    csp = prod_client.get("/ping").headers["content-security-policy"]
    assert "https://generativelanguage.googleapis.com" in csp


# ── Tests: Dev-Override ───────────────────────────────────────────────────── #

def test_dev_mode_allows_unsafe_eval(dev_client):
    """Dev: 'unsafe-eval' für Vite HMR erlaubt."""
    csp = dev_client.get("/ping").headers["content-security-policy"]
    assert "'unsafe-eval'" in csp


# ── Unit: CSP Builder ─────────────────────────────────────────────────────── #

def test_build_csp_prod_no_unsafe():
    csp = _build_csp(is_dev=False)
    assert "'unsafe-eval'" not in csp
    assert "frame-src 'none'" in csp
    assert "upgrade-insecure-requests" in csp


def test_build_csp_dev_has_unsafe_eval():
    csp = _build_csp(is_dev=True)
    assert "'unsafe-eval'" in csp
