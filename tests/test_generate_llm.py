"""Tests for LLM abstraction layer."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_cli.core.generate.llm import (
    LLMError,
    _build_response_format,
    _check_ollama_running,
    _is_format_error,
    call_llm_structured,
    detect_model,
    ensure_litellm,
)
from context_cli.core.models import LlmsTxtContent


class TestEnsureLitellm:
    def test_succeeds_when_installed(self):
        # litellm is in dev deps, so should succeed
        ensure_litellm()

    def test_raises_when_not_installed(self):
        with patch.dict("sys.modules", {"litellm": None}):
            with pytest.raises(ImportError, match="pip install context-cli\\[generate\\]"):
                ensure_litellm()


class TestCheckOllamaRunning:
    def test_returns_true_when_running(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            assert _check_ollama_running() is True

    def test_returns_false_on_connection_error(self):
        with patch("httpx.get", side_effect=ConnectionError("refused")):
            assert _check_ollama_running() is False

    def test_returns_false_on_non_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.get", return_value=mock_resp):
            assert _check_ollama_running() is False


class TestDetectModel:
    def test_openai_key_returns_gpt(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
            assert detect_model() == "gpt-4o-mini"

    def test_anthropic_key_returns_claude(self):
        env = {"ANTHROPIC_API_KEY": "sk-ant-test"}
        with patch.dict("os.environ", env, clear=True):
            assert detect_model() == "claude-3-haiku-20240307"

    def test_openai_takes_priority_over_anthropic(self):
        env = {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"}
        with patch.dict("os.environ", env, clear=True):
            assert detect_model() == "gpt-4o-mini"

    def test_ollama_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "context_cli.core.llm._check_ollama_running", return_value=True
            ):
                assert detect_model() == "ollama/llama3.2"

    def test_no_provider_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "context_cli.core.llm._check_ollama_running", return_value=False
            ):
                with pytest.raises(LLMError, match="No LLM provider found"):
                    detect_model()


class TestBuildResponseFormat:
    def test_returns_json_schema_format(self):
        fmt = _build_response_format(LlmsTxtContent)
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"]["name"] == "LlmsTxtContent"
        assert "schema" in fmt["json_schema"]

    def test_schema_contains_properties(self):
        fmt = _build_response_format(LlmsTxtContent)
        schema = fmt["json_schema"]["schema"]
        assert "properties" in schema
        assert "title" in schema["properties"]


class TestIsFormatError:
    def test_detects_response_format_error(self):
        err = Exception("response_format is not supported for this model")
        assert _is_format_error(err) is True

    def test_detects_json_schema_error(self):
        err = Exception("json_schema mode not available")
        assert _is_format_error(err) is True

    def test_ignores_unrelated_error(self):
        err = Exception("rate limit exceeded")
        assert _is_format_error(err) is False

    def test_detects_not_supported(self):
        err = Exception("structured output not supported")
        assert _is_format_error(err) is True


class TestCallLlmStructured:
    async def test_success_path(self):
        expected = {
            "title": "Test",
            "description": "A test",
            "sections": [],
        }
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(expected)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await call_llm_structured(
                messages=[{"role": "user", "content": "test"}],
                model="gpt-4o-mini",
                response_model=LlmsTxtContent,
            )
            assert result == expected
            mock_llm.assert_called_once()

    async def test_fallback_on_format_error(self):
        fallback_data = {
            "title": "Fallback",
            "description": "Used json_mode",
            "sections": [],
        }
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(fallback_data)
        mock_fallback_response = MagicMock()
        mock_fallback_response.choices = [mock_choice]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("response_format is not supported")
            return mock_fallback_response

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = side_effect
            result = await call_llm_structured(
                messages=[{"role": "user", "content": "test"}],
                model="ollama/llama3.2",
                response_model=LlmsTxtContent,
            )
            assert result == fallback_data
            assert call_count == 2

    async def test_non_format_error_raises_llm_error(self):
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("rate limit exceeded")
            with pytest.raises(LLMError, match="LLM call failed"):
                await call_llm_structured(
                    messages=[{"role": "user", "content": "test"}],
                    model="gpt-4o-mini",
                    response_model=LlmsTxtContent,
                )
