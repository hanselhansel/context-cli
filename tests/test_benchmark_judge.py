"""Tests for benchmark judge module — LLM-as-judge classification."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from context_cli.core.benchmark.judge import judge_all, judge_response
from context_cli.core.models import JudgeResult, PromptBenchmarkResult, PromptEntry

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_completion_response(content: str) -> SimpleNamespace:
    """Build a fake litellm acompletion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _judge_json(
    brands: list[str] | None = None,
    recommended: str | None = None,
    position: int | None = None,
    sentiment: str = "neutral",
) -> str:
    """Build a JSON string matching JudgeResult schema."""
    return json.dumps(
        {
            "brands_mentioned": brands or [],
            "recommended_brand": recommended,
            "target_brand_position": position,
            "sentiment": sentiment,
        }
    )


def _pe(text: str) -> PromptEntry:
    """Shorthand to create a PromptEntry."""
    return PromptEntry(prompt=text)


# ── judge_response tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_judge_response_basic() -> None:
    """judge_response returns correct JudgeResult from LLM JSON output."""
    fake_json = _judge_json(
        brands=["BrandA", "BrandB"],
        recommended="BrandA",
        position=1,
        sentiment="positive",
    )
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        result = await judge_response(
            response_text="I recommend BrandA over BrandB.",
            brand="BrandA",
            competitors=["BrandB"],
        )

    assert isinstance(result, JudgeResult)
    assert result.brands_mentioned == ["BrandA", "BrandB"]
    assert result.recommended_brand == "BrandA"
    assert result.target_brand_position == 1
    assert result.sentiment == "positive"


@pytest.mark.asyncio
async def test_judge_response_no_mention() -> None:
    """judge_response handles case where no brands mentioned."""
    fake_json = _judge_json(brands=[], recommended=None, position=None, sentiment="neutral")
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        result = await judge_response(
            response_text="Use any product you like.",
            brand="BrandA",
            competitors=["BrandB"],
        )

    assert result.brands_mentioned == []
    assert result.recommended_brand is None
    assert result.target_brand_position is None
    assert result.sentiment == "neutral"


@pytest.mark.asyncio
async def test_judge_response_custom_model() -> None:
    """judge_response passes model parameter to litellm."""
    fake_json = _judge_json(brands=["X"], recommended="X", position=1, sentiment="positive")
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        result = await judge_response(
            response_text="X is the best.",
            brand="X",
            competitors=[],
            model="gpt-4o",
        )

    # Verify the model was passed through
    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"
    assert result.recommended_brand == "X"


@pytest.mark.asyncio
async def test_judge_response_system_prompt_contents() -> None:
    """judge_response sends proper system prompt with brand and competitors."""
    fake_json = _judge_json()
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        await judge_response(
            response_text="some response",
            brand="Acme",
            competitors=["Rival1", "Rival2"],
        )

    call_kwargs = mock_acompletion.call_args[1]
    messages = call_kwargs["messages"]
    # System message should mention the brand and competitors
    system_msg = messages[0]["content"]
    assert "Acme" in system_msg
    assert "Rival1" in system_msg
    assert "Rival2" in system_msg


@pytest.mark.asyncio
async def test_judge_response_uses_json_object_format() -> None:
    """judge_response requests JSON object response format."""
    fake_json = _judge_json()
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        await judge_response(
            response_text="test",
            brand="X",
            competitors=[],
        )

    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_judge_response_exception_returns_defaults() -> None:
    """judge_response returns empty defaults on LLM exception."""
    mock_acompletion = AsyncMock(side_effect=Exception("API error"))

    with patch("litellm.acompletion", mock_acompletion):
        result = await judge_response(
            response_text="some text",
            brand="X",
            competitors=["Y"],
        )

    assert result.brands_mentioned == []
    assert result.recommended_brand is None
    assert result.target_brand_position is None
    assert result.sentiment == "neutral"


@pytest.mark.asyncio
async def test_judge_response_invalid_json_returns_defaults() -> None:
    """judge_response handles invalid JSON gracefully."""
    mock_acompletion = AsyncMock(
        return_value=_make_completion_response("not valid json {{{")
    )

    with patch("litellm.acompletion", mock_acompletion):
        result = await judge_response(
            response_text="some text",
            brand="X",
            competitors=[],
        )

    assert result.brands_mentioned == []
    assert result.recommended_brand is None
    assert result.sentiment == "neutral"


@pytest.mark.asyncio
async def test_judge_response_partial_json() -> None:
    """judge_response handles partial JSON with missing fields."""
    partial_json = json.dumps({"brands_mentioned": ["A"], "sentiment": "positive"})
    mock_acompletion = AsyncMock(
        return_value=_make_completion_response(partial_json)
    )

    with patch("litellm.acompletion", mock_acompletion):
        result = await judge_response(
            response_text="A is good",
            brand="A",
            competitors=[],
        )

    assert result.brands_mentioned == ["A"]
    assert result.recommended_brand is None  # missing -> default
    assert result.sentiment == "positive"


@pytest.mark.asyncio
async def test_judge_response_default_model() -> None:
    """judge_response uses gpt-4o-mini as default model."""
    fake_json = _judge_json()
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        await judge_response(
            response_text="test",
            brand="X",
            competitors=[],
        )

    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"


# ── judge_all tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_judge_all_basic() -> None:
    """judge_all sets judge_result on each result."""
    results = [
        PromptBenchmarkResult(
            prompt=_pe("test1"),
            model="gpt-4o-mini",
            run_index=0,
            response_text="BrandA is great",
        ),
        PromptBenchmarkResult(
            prompt=_pe("test2"),
            model="gpt-4o-mini",
            run_index=0,
            response_text="BrandB is better",
        ),
    ]

    fake_json_a = _judge_json(brands=["BrandA"], recommended="BrandA", sentiment="positive")
    fake_json_b = _judge_json(brands=["BrandB"], recommended="BrandB", sentiment="neutral")

    call_count = 0

    async def mock_acompletion(**kwargs: object) -> SimpleNamespace:
        nonlocal call_count
        call_count += 1
        content = fake_json_a if call_count == 1 else fake_json_b
        return _make_completion_response(content)

    with patch("litellm.acompletion", side_effect=mock_acompletion):
        updated = await judge_all(results, brand="BrandA", competitors=["BrandB"])

    assert len(updated) == 2
    assert updated[0].judge_result is not None
    assert updated[0].judge_result.recommended_brand == "BrandA"
    assert updated[1].judge_result is not None
    assert updated[1].judge_result.recommended_brand == "BrandB"


@pytest.mark.asyncio
async def test_judge_all_skips_errors() -> None:
    """judge_all skips results that have errors."""
    results = [
        PromptBenchmarkResult(
            prompt=_pe("test1"),
            model="gpt-4o-mini",
            run_index=0,
            response_text="BrandA rocks",
        ),
        PromptBenchmarkResult(
            prompt=_pe("test2"),
            model="gpt-4o-mini",
            run_index=0,
            response_text="",
            error="API timeout",
        ),
    ]

    fake_json = _judge_json(brands=["BrandA"], recommended="BrandA", sentiment="positive")
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        updated = await judge_all(results, brand="BrandA", competitors=[])

    assert updated[0].judge_result is not None
    assert updated[1].judge_result is None  # skipped because of error
    # Only one call should have been made
    assert mock_acompletion.call_count == 1


@pytest.mark.asyncio
async def test_judge_all_empty_list() -> None:
    """judge_all handles empty results list."""
    mock_acompletion = AsyncMock()

    with patch("litellm.acompletion", mock_acompletion):
        updated = await judge_all([], brand="X", competitors=[])

    assert updated == []
    assert mock_acompletion.call_count == 0


@pytest.mark.asyncio
async def test_judge_all_custom_model() -> None:
    """judge_all passes judge_model to judge_response."""
    results = [
        PromptBenchmarkResult(
            prompt=_pe("test"),
            model="gpt-4o-mini",
            run_index=0,
            response_text="Some text",
        ),
    ]

    fake_json = _judge_json()
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        await judge_all(
            results,
            brand="X",
            competitors=[],
            judge_model="claude-3-haiku-20240307",
        )

    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs["model"] == "claude-3-haiku-20240307"


@pytest.mark.asyncio
async def test_judge_all_rate_limiting() -> None:
    """judge_all uses semaphore for rate limiting (max 5 concurrent)."""
    # Create 10 results to exceed concurrency limit
    results = [
        PromptBenchmarkResult(
            prompt=_pe(f"test{i}"),
            model="gpt-4o-mini",
            run_index=0,
            response_text=f"Response {i}",
        )
        for i in range(10)
    ]

    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    original_judge_json = _judge_json()

    async def mock_acompletion(**kwargs: object) -> SimpleNamespace:
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > max_concurrent:
                max_concurrent = current_concurrent
        # Simulate some work
        await asyncio.sleep(0.01)
        async with lock:
            current_concurrent -= 1
        return _make_completion_response(original_judge_json)

    with patch("litellm.acompletion", side_effect=mock_acompletion):
        updated = await judge_all(results, brand="X", competitors=[])

    assert len(updated) == 10
    # Semaphore(5) means max_concurrent should be <= 5
    assert max_concurrent <= 5


@pytest.mark.asyncio
async def test_judge_all_preserves_original_fields() -> None:
    """judge_all preserves prompt, model, response_text, error fields."""
    original_prompt = _pe("original prompt")
    results = [
        PromptBenchmarkResult(
            prompt=original_prompt,
            model="gpt-4o",
            run_index=0,
            response_text="original response",
        ),
    ]

    fake_json = _judge_json(brands=["X"], sentiment="positive")
    mock_acompletion = AsyncMock(return_value=_make_completion_response(fake_json))

    with patch("litellm.acompletion", mock_acompletion):
        updated = await judge_all(results, brand="X", competitors=[])

    assert updated[0].prompt == original_prompt
    assert updated[0].model == "gpt-4o"
    assert updated[0].response_text == "original response"
    assert updated[0].error is None
    assert updated[0].judge_result is not None
