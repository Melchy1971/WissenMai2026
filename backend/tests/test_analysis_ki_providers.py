"""Tests for Task #76: KI-Provider-Interface.

Covers:
- Ollama: mocked HTTP, timeout, retry, privacy mode, JSON parsing
- OpenAI: mocked HTTP, auth error, rate limit, response parsing
- Gemini: mocked HTTP, auth error, response parsing
- Registry: build_provider factory, unknown provider, missing key
- KiBackedAnalysisProvider adapter: happy path, provider error mapping
"""
from __future__ import annotations

import json
import logging
import urllib.error
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from app.services.ai_providers.analysis_provider import AnalysisSummaryResult, DocumentSummaryInput
from app.services.ai_providers.errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.services.ai_providers.gemini import GeminiAnalysisProvider
from app.services.ai_providers.ollama import OllamaAnalysisProvider
from app.services.ai_providers.openai_provider import OpenAiAnalysisProvider
from app.services.ai_providers.registry import build_provider, list_provider_names
from app.services.analysis.ki_backed_provider import (
    KiBackedAnalysisProvider,
    KiProviderError,
    KiProviderUnavailableError,
)

pytestmark = pytest.mark.unit_fast

# ── Shared fixtures ────────────────────────────────────────────────────────────

_DOC_A = DocumentSummaryInput(document_id="doc-a", title="Handbuch A", content="Inhalt A")
_DOC_B = DocumentSummaryInput(document_id="doc-b", title="Handbuch B", content="Inhalt B")

_VALID_JSON_PAYLOAD = json.dumps({
    "summary": "Kurze Zusammenfassung.",
    "key_points": ["Punkt 1", "Punkt 2"],
    "suggested_tags": ["tag1"],
    "suggested_topics": ["thema1"],
    "confidence": 0.88,
})


def _make_http_response(body: str | bytes, status: int = 200) -> MagicMock:
    if isinstance(body, str):
        body = body.encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="", code=code, msg="", hdrs=None, fp=BytesIO(b""))  # type: ignore


# ── Ollama ─────────────────────────────────────────────────────────────────────

class TestOllamaProvider:
    def _provider(self, **kw) -> OllamaAnalysisProvider:
        return OllamaAnalysisProvider(model="llama3", timeout_seconds=5.0, max_retries=1, **kw)

    def _ollama_response(self, text: str) -> bytes:
        return json.dumps({"response": text, "eval_count": 42}).encode()

    def test_happy_path_returns_summary(self):
        provider = self._provider()
        resp = _make_http_response(self._ollama_response(_VALID_JSON_PAYLOAD))

        with patch("urllib.request.urlopen", return_value=resp):
            result = provider.generate_analysis_summary(
                job_id="j1",
                documents=[_DOC_A],
                prompt="Fasse zusammen.",
            )

        assert result.summary == "Kurze Zusammenfassung."
        assert result.key_points == ["Punkt 1", "Punkt 2"]
        assert result.suggested_tags == ["tag1"]
        assert result.suggested_topics == ["thema1"]
        assert abs(result.confidence - 0.88) < 0.001
        assert result.provider == "ollama"
        assert result.model == "llama3"
        assert result.tokens_used == 42

    def test_json_in_markdown_fence_is_parsed(self):
        provider = self._provider()
        fenced = f"```json\n{_VALID_JSON_PAYLOAD}\n```"
        resp = _make_http_response(self._ollama_response(fenced))

        with patch("urllib.request.urlopen", return_value=resp):
            result = provider.generate_analysis_summary(
                job_id="j2", documents=[_DOC_A], prompt="p"
            )
        assert result.summary == "Kurze Zusammenfassung."

    def test_timeout_raises_provider_timeout_error(self):
        provider = self._provider(max_retries=0)
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            with pytest.raises(ProviderTimeoutError) as exc_info:
                provider.generate_analysis_summary(job_id="j3", documents=[_DOC_A], prompt="p")
        assert exc_info.value.provider == "ollama"

    def test_retry_on_timeout_then_succeeds(self):
        provider = self._provider(max_retries=1)
        good_resp = _make_http_response(self._ollama_response(_VALID_JSON_PAYLOAD))
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError()
            return good_resp

        with patch("urllib.request.urlopen", side_effect=side_effect):
            with patch("time.sleep"):  # don't actually sleep in tests
                result = provider.generate_analysis_summary(
                    job_id="j4", documents=[_DOC_A], prompt="p"
                )
        assert call_count == 2
        assert result.summary == "Kurze Zusammenfassung."

    def test_privacy_mode_does_not_log_content(self, caplog):
        provider = self._provider()
        resp = _make_http_response(self._ollama_response(_VALID_JSON_PAYLOAD))

        with patch("urllib.request.urlopen", return_value=resp):
            with caplog.at_level(logging.DEBUG, logger="app.services.ai_providers.ollama"):
                provider.generate_analysis_summary(
                    job_id="j5", documents=[_DOC_A], prompt="p", privacy_mode=True
                )

        # Document content must not appear in log output
        assert "Inhalt A" not in caplog.text

    def test_invalid_json_raises_response_error(self):
        provider = self._provider(max_retries=0)
        resp = _make_http_response(self._ollama_response("kein JSON hier"))
        with patch("urllib.request.urlopen", return_value=resp):
            with pytest.raises(ProviderResponseError):
                provider.generate_analysis_summary(job_id="j6", documents=[_DOC_A], prompt="p")

    def test_connection_error_after_retries_raises_connection_error(self):
        provider = self._provider(max_retries=1)
        import urllib.error as _ue
        err = _ue.URLError("connection refused")
        with patch("urllib.request.urlopen", side_effect=err):
            with patch("time.sleep"):
                with pytest.raises(ProviderConnectionError):
                    provider.generate_analysis_summary(job_id="j7", documents=[_DOC_A], prompt="p")


# ── OpenAI ─────────────────────────────────────────────────────────────────────

class TestOpenAiProvider:
    def _provider(self, **kw) -> OpenAiAnalysisProvider:
        return OpenAiAnalysisProvider(
            api_key="sk-test", model="gpt-4o", timeout_seconds=5.0, max_retries=0, **kw
        )

    def _openai_response(self, text: str, tokens: int = 55) -> bytes:
        return json.dumps({
            "choices": [{"message": {"content": text}}],
            "usage": {"total_tokens": tokens},
        }).encode()

    def test_happy_path(self):
        provider = self._provider()
        resp = _make_http_response(self._openai_response(_VALID_JSON_PAYLOAD))
        with patch("urllib.request.urlopen", return_value=resp):
            result = provider.generate_analysis_summary(
                job_id="oa1", documents=[_DOC_A, _DOC_B], prompt="Analyse"
            )
        assert result.summary == "Kurze Zusammenfassung."
        assert result.provider == "openai"
        assert result.tokens_used == 55

    def test_auth_error_401_raises_provider_auth_error(self):
        provider = self._provider()
        with patch("urllib.request.urlopen", side_effect=_make_http_error(401)):
            with pytest.raises(ProviderAuthError) as exc_info:
                provider.generate_analysis_summary(job_id="oa2", documents=[_DOC_A], prompt="p")
        assert exc_info.value.provider == "openai"

    def test_rate_limit_429_raises_provider_rate_limit_error(self):
        provider = self._provider()
        with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
            with pytest.raises(ProviderRateLimitError):
                provider.generate_analysis_summary(job_id="oa3", documents=[_DOC_A], prompt="p")

    def test_api_key_not_in_log_output(self, caplog):
        provider = self._provider()
        resp = _make_http_response(self._openai_response(_VALID_JSON_PAYLOAD))
        with patch("urllib.request.urlopen", return_value=resp):
            with caplog.at_level(logging.DEBUG):
                provider.generate_analysis_summary(job_id="oa4", documents=[_DOC_A], prompt="p")
        assert "sk-test" not in caplog.text


# ── Gemini ─────────────────────────────────────────────────────────────────────

class TestGeminiProvider:
    def _provider(self, **kw) -> GeminiAnalysisProvider:
        return GeminiAnalysisProvider(
            api_key="AIza-test", model="gemini-1.5-flash",
            timeout_seconds=5.0, max_retries=0, **kw
        )

    def _gemini_response(self, text: str, tokens: int = 60) -> bytes:
        return json.dumps({
            "candidates": [{"content": {"parts": [{"text": text}]}}],
            "usageMetadata": {"totalTokenCount": tokens},
        }).encode()

    def test_happy_path(self):
        provider = self._provider()
        resp = _make_http_response(self._gemini_response(_VALID_JSON_PAYLOAD))
        with patch("urllib.request.urlopen", return_value=resp):
            result = provider.generate_analysis_summary(
                job_id="g1", documents=[_DOC_A], prompt="Analyse"
            )
        assert result.summary == "Kurze Zusammenfassung."
        assert result.provider == "gemini"
        assert result.tokens_used == 60

    def test_auth_error_403_raises_provider_auth_error(self):
        provider = self._provider()
        with patch("urllib.request.urlopen", side_effect=_make_http_error(403)):
            with pytest.raises(ProviderAuthError):
                provider.generate_analysis_summary(job_id="g2", documents=[_DOC_A], prompt="p")

    def test_rate_limit_429_raises_provider_rate_limit_error(self):
        provider = self._provider()
        with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
            with pytest.raises(ProviderRateLimitError):
                provider.generate_analysis_summary(job_id="g3", documents=[_DOC_A], prompt="p")

    def test_api_key_not_in_log_output(self, caplog):
        """API key embedded in URL must never appear in any log record."""
        provider = self._provider()
        resp = _make_http_response(self._gemini_response(_VALID_JSON_PAYLOAD))
        with patch("urllib.request.urlopen", return_value=resp):
            with caplog.at_level(logging.DEBUG):
                provider.generate_analysis_summary(job_id="g4", documents=[_DOC_A], prompt="p")
        assert "AIza-test" not in caplog.text


# ── Registry ───────────────────────────────────────────────────────────────────

class TestProviderRegistry:
    def test_list_provider_names_contains_all_three(self):
        names = list_provider_names()
        assert {"ollama", "openai", "gemini"} <= set(names)

    def test_build_ollama_returns_ollama_instance(self):
        provider = build_provider("ollama", model="mistral")
        assert isinstance(provider, OllamaAnalysisProvider)
        assert provider.model_name == "mistral"

    def test_build_openai_with_explicit_key(self):
        provider = build_provider("openai", model="gpt-4o", api_key="sk-explicit")
        assert isinstance(provider, OpenAiAnalysisProvider)
        assert provider.model_name == "gpt-4o"

    def test_build_openai_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        provider = build_provider("openai")
        assert isinstance(provider, OpenAiAnalysisProvider)

    def test_build_openai_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="requires an API key"):
            build_provider("openai")

    def test_build_gemini_with_explicit_key(self):
        provider = build_provider("gemini", api_key="AIza-xyz")
        assert isinstance(provider, GeminiAnalysisProvider)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            build_provider("nonexistent")


# ── KiBackedAnalysisProvider adapter ─────────────────────────────────────────

class TestKiBackedAnalysisProvider:
    def _make_adapter(self, provider_mock, doc_rows=None):
        repo = MagicMock()
        repo.get_source_document_ids.return_value = ["doc-a"]
        # Simulate DB row query
        row = {"title": "Handbuch A", "content": "Inhalt A"} if doc_rows is None else doc_rows
        session_mock = MagicMock()
        session_mock.execute.return_value.mappings.return_value.first.return_value = row
        repo._session = session_mock
        return KiBackedAnalysisProvider(provider=provider_mock, repo=repo)

    def _make_provider_mock(self, result: AnalysisSummaryResult | None = None, exc=None):
        mock = MagicMock()
        mock.provider_name = "ollama"
        mock.model_name = "llama3"
        if exc is not None:
            mock.generate_analysis_summary.side_effect = exc
        else:
            mock.generate_analysis_summary.return_value = result or AnalysisSummaryResult(
                summary="Zusammenfassung",
                key_points=["K1"],
                suggested_tags=["t1"],
                suggested_topics=["th1"],
                confidence=0.9,
                provider="ollama",
                model="llama3",
                tokens_used=100,
            )
        return mock

    def test_happy_path_returns_result_dict(self):
        provider = self._make_provider_mock()
        adapter = self._make_adapter(provider)
        job = MagicMock()
        job.id = "job-1"
        job.prompt = "Analyse"

        result = adapter.run(job=job, privacy_mode=True)
        assert result.summary == "Zusammenfassung"
        assert result.provider == "ollama"
        assert result.tokens_used == 100
        d = result.as_dict()
        assert d["key_points"] == ["K1"]

    def test_provider_timeout_maps_to_unavailable_error(self):
        exc = ProviderTimeoutError("timeout", provider="ollama", model="llama3")
        provider = self._make_provider_mock(exc=exc)
        adapter = self._make_adapter(provider)
        job = MagicMock()
        job.id = "job-2"
        job.prompt = "p"

        with pytest.raises(KiProviderUnavailableError):
            adapter.run(job=job)

    def test_provider_connection_error_maps_to_unavailable_error(self):
        exc = ProviderConnectionError("conn", provider="ollama", model="llama3")
        provider = self._make_provider_mock(exc=exc)
        adapter = self._make_adapter(provider)
        job = MagicMock()
        job.id = "job-3"
        job.prompt = "p"

        with pytest.raises(KiProviderUnavailableError):
            adapter.run(job=job)

    def test_provider_auth_error_maps_to_ki_provider_error(self):
        exc = ProviderAuthError("auth", provider="openai", model="gpt-4o")
        provider = self._make_provider_mock(exc=exc)
        adapter = self._make_adapter(provider)
        job = MagicMock()
        job.id = "job-4"
        job.prompt = "p"

        with pytest.raises(KiProviderError) as exc_info:
            adapter.run(job=job)
        # Must NOT be the unavailable subclass
        assert type(exc_info.value) is KiProviderError

    def test_no_document_content_logged_in_privacy_mode(self, caplog):
        provider = self._make_provider_mock()
        adapter = self._make_adapter(provider, doc_rows={"title": "Geheimes Dokument", "content": "TOP SECRET"})
        job = MagicMock()
        job.id = "job-5"
        job.prompt = "p"

        with caplog.at_level(logging.DEBUG):
            adapter.run(job=job, privacy_mode=True)

        assert "TOP SECRET" not in caplog.text
