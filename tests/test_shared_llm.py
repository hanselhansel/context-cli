"""Tests for shared LLM layer (core/llm.py) and cost estimation (core/cost.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from context_cli.core.cost import MODEL_COSTS, estimate_cost, format_cost
from context_cli.core.llm import (
    LLMError,
    call_llm_structured,
    detect_model,
    ensure_litellm,
)

# ── ensure_litellm ──────────────────────────────────────────────────────────


def test_ensure_litellm_installed():
    """Should not raise when litellm is available."""
    with patch.dict("sys.modules", {"litellm": MagicMock()}):
        ensure_litellm()


def test_ensure_litellm_missing():
    """Should raise ImportError when litellm is not installed."""
    with patch.dict("sys.modules", {"litellm": None}):
        with pytest.raises(ImportError, match="litellm is required"):
            ensure_litellm()


# ── detect_model ─────────────────────────────────────────────────────────────


def test_detect_model_openai():
    """Should prefer OpenAI when OPENAI_API_KEY is set."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False):
        assert detect_model() == "gpt-4o-mini"


def test_detect_model_anthropic():
    """Should use Anthropic when only ANTHROPIC_API_KEY is set."""
    env = {"ANTHROPIC_API_KEY": "sk-test"}
    with patch.dict("os.environ", env, clear=True):
        assert detect_model() == "claude-3-haiku-20240307"


def test_detect_model_ollama():
    """Should use Ollama when running locally."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("context_cli.core.llm._check_ollama_running", return_value=True):
            assert detect_model() == "ollama/llama3.2"


def test_detect_model_none():
    """Should raise LLMError when no provider found."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("context_cli.core.llm._check_ollama_running", return_value=False):
            with pytest.raises(LLMError, match="No LLM provider found"):
                detect_model()


# ── _check_ollama_running ────────────────────────────────────────────────────


def test_check_ollama_running_true():
    """Should return True when Ollama responds with 200."""
    from context_cli.core.llm import _check_ollama_running

    mock_resp = MagicMock(status_code=200)
    with patch("context_cli.core.llm.httpx.get", return_value=mock_resp):
        assert _check_ollama_running() is True


def test_check_ollama_running_false():
    """Should return False when Ollama is not running."""
    from context_cli.core.llm import _check_ollama_running

    with patch("context_cli.core.llm.httpx.get", side_effect=ConnectionError):
        assert _check_ollama_running() is False


# ── call_llm_structured ─────────────────────────────────────────────────────


class SampleResponse(BaseModel):
    name: str
    score: float


async def test_call_llm_structured_success():
    """Should call litellm and parse response."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = '{"name":"test","score":42.0}'

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
        with patch("context_cli.core.llm.ensure_litellm"):
            result = await call_llm_structured(
                [{"role": "user", "content": "test"}],
                "gpt-4o-mini",
                SampleResponse,
            )
    assert result["name"] == "test"
    assert result["score"] == 42.0


async def test_call_llm_structured_format_error_fallback():
    """Should fall back to json_mode on format errors."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = '{"name":"fallback","score":1.0}'

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[Exception("response_format not supported"), mock_resp],
    ):
        with patch("context_cli.core.llm.ensure_litellm"):
            result = await call_llm_structured(
                [{"role": "user", "content": "test"}],
                "ollama/llama3.2",
                SampleResponse,
            )
    assert result["name"] == "fallback"


async def test_call_llm_structured_non_format_error():
    """Should raise LLMError on non-format errors."""
    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=Exception("rate limit"),
    ):
        with patch("context_cli.core.llm.ensure_litellm"):
            with pytest.raises(LLMError, match="LLM call failed"):
                await call_llm_structured(
                    [{"role": "user", "content": "test"}],
                    "gpt-4o-mini",
                    SampleResponse,
                )


# ── _build_response_format ───────────────────────────────────────────────────


def test_build_response_format():
    """Should build litellm-compatible response format dict."""
    from context_cli.core.llm import _build_response_format

    fmt = _build_response_format(SampleResponse)
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "SampleResponse"
    assert "properties" in fmt["json_schema"]["schema"]


# ── _is_format_error ─────────────────────────────────────────────────────────


def test_is_format_error_true():
    """Should detect response_format errors."""
    from context_cli.core.llm import _is_format_error

    assert _is_format_error(Exception("response_format not supported")) is True
    assert _is_format_error(Exception("json_schema error")) is True
    assert _is_format_error(Exception("structured output failed")) is True


def test_is_format_error_false():
    """Should not match non-format errors."""
    from context_cli.core.llm import _is_format_error

    assert _is_format_error(Exception("rate limit exceeded")) is False
    assert _is_format_error(Exception("connection timeout")) is False


# ── cost.py ──────────────────────────────────────────────────────────────────


def test_model_costs_has_common_models():
    """Should have pricing for common models."""
    assert "gpt-4o" in MODEL_COSTS
    assert "gpt-4o-mini" in MODEL_COSTS
    assert "claude-3-haiku-20240307" in MODEL_COSTS


def test_estimate_cost_known_model():
    """Should estimate cost based on token count."""
    cost = estimate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
    assert cost > 0


def test_estimate_cost_unknown_model():
    """Should return 0 for unknown models."""
    cost = estimate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
    assert cost == 0.0


def test_format_cost_dollars():
    """Should format cost as dollar string."""
    assert format_cost(1.50) == "$1.50"
    assert format_cost(0.003) == "$0.003"
    assert format_cost(0.0) == "$0.00"


def test_format_cost_small_amounts():
    """Should handle very small costs."""
    result = format_cost(0.0001)
    assert result.startswith("$")


def test_estimate_cost_zero_tokens():
    """Should return 0 for zero tokens."""
    cost = estimate_cost("gpt-4o-mini", input_tokens=0, output_tokens=0)
    assert cost == 0.0


# ── backward compat ──────────────────────────────────────────────────────────


def test_generate_llm_re_exports():
    """generate/llm.py should re-export from core/llm.py."""
    from context_cli.core.generate.llm import (
        LLMError as GenLLMError,
    )
    from context_cli.core.generate.llm import (
        call_llm_structured as gen_call,
    )
    from context_cli.core.generate.llm import (
        detect_model as gen_detect,
    )
    from context_cli.core.generate.llm import (
        ensure_litellm as gen_ensure,
    )
    from context_cli.core.llm import (
        LLMError as CoreLLMError,
    )
    from context_cli.core.llm import (
        call_llm_structured as core_call,
    )
    from context_cli.core.llm import (
        detect_model as core_detect,
    )
    from context_cli.core.llm import (
        ensure_litellm as core_ensure,
    )

    assert GenLLMError is CoreLLMError
    assert gen_call is core_call
    assert gen_detect is core_detect
    assert gen_ensure is core_ensure
