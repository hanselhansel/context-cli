"""Tests for benchmark dispatcher — async multi-model query dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_cli.core.benchmark.dispatcher import dispatch_queries
from context_cli.core.models import BenchmarkConfig, PromptBenchmarkResult, PromptEntry


def _make_mock_response(content: str = "Test response") -> MagicMock:
    """Create a mock litellm response with given content."""
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content=content))]
    return mock


class TestDispatchQueries:
    """Tests for dispatch_queries — the core dispatcher function."""

    @pytest.mark.asyncio
    async def test_single_prompt_single_model_single_run(self) -> None:
        """Dispatches one query for one prompt, one model, one run."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("I recommend TestBrand laptops.")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert len(results) == 1
        assert isinstance(results[0], PromptBenchmarkResult)
        assert results[0].prompt.prompt == "Best laptop?"
        assert results[0].model == "gpt-4o-mini"
        assert results[0].run_index == 0
        assert results[0].response_text == "I recommend TestBrand laptops."
        assert results[0].judge_result is None
        assert results[0].error is None

    @pytest.mark.asyncio
    async def test_multiple_prompts(self) -> None:
        """Dispatches queries for multiple prompts."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[
                PromptEntry(prompt="Best laptop?"),
                PromptEntry(prompt="Best phone?"),
            ],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert len(results) == 2
        prompts_queried = {r.prompt.prompt for r in results}
        assert prompts_queried == {"Best laptop?", "Best phone?"}

    @pytest.mark.asyncio
    async def test_multiple_models(self) -> None:
        """Dispatches queries across multiple models."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["gpt-4o-mini", "claude-3-haiku-20240307"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert len(results) == 2
        models_used = {r.model for r in results}
        assert models_used == {"gpt-4o-mini", "claude-3-haiku-20240307"}

    @pytest.mark.asyncio
    async def test_runs_per_model(self) -> None:
        """Each prompt-model pair is repeated runs_per_model times."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["gpt-4o-mini"],
            runs_per_model=3,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert len(results) == 3
        run_indices = sorted(r.run_index for r in results)
        assert run_indices == [0, 1, 2]
        assert all(r.model == "gpt-4o-mini" for r in results)

    @pytest.mark.asyncio
    async def test_full_combinatorics(self) -> None:
        """2 prompts x 2 models x 3 runs = 12 results."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[
                PromptEntry(prompt="Best laptop?"),
                PromptEntry(prompt="Best phone?"),
            ],
            models=["gpt-4o-mini", "claude-3-haiku-20240307"],
            runs_per_model=3,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert len(results) == 12

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Failed queries capture error and set response_text to empty."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        with patch(
            "litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=Exception("API rate limit exceeded"),
        ):
            results = await dispatch_queries(config)

        assert len(results) == 1
        assert results[0].response_text == ""
        assert results[0].error is not None
        assert "API rate limit exceeded" in results[0].error

    @pytest.mark.asyncio
    async def test_partial_failure(self) -> None:
        """Some queries fail while others succeed."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["good-model", "bad-model"],
            runs_per_model=1,
        )

        async def mock_acompletion(**kwargs: object) -> MagicMock:
            model = kwargs.get("model", "")
            if model == "bad-model":
                raise Exception("Model not available")
            return _make_mock_response("Success")

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            results = await dispatch_queries(config)

        assert len(results) == 2
        good = [r for r in results if r.error is None]
        bad = [r for r in results if r.error is not None]
        assert len(good) == 1
        assert len(bad) == 1
        assert good[0].model == "good-model"
        assert good[0].response_text == "Success"
        assert bad[0].model == "bad-model"
        assert bad[0].response_text == ""

    @pytest.mark.asyncio
    async def test_system_prompt_content(self) -> None:
        """Verify the system prompt mentions brands and reasoning."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("Response")
        with patch(
            "litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp
        ) as mock_call:
            await dispatch_queries(config)

        call_args = mock_call.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "brand" in messages[0]["content"].lower()
        assert "reasoning" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Best laptop?"

    @pytest.mark.asyncio
    async def test_judge_result_is_none(self) -> None:
        """Dispatcher does NOT populate judge_result — that is for the judge agent."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert all(r.judge_result is None for r in results)

    @pytest.mark.asyncio
    async def test_empty_prompts_returns_empty(self) -> None:
        """Config with no prompts returns empty results list."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert results == []

    @pytest.mark.asyncio
    async def test_prompt_entry_preserved(self) -> None:
        """The full PromptEntry (with category/intent) is preserved in results."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[
                PromptEntry(prompt="Best laptop?", category="comparison", intent="transactional"),
            ],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert results[0].prompt.category == "comparison"
        assert results[0].prompt.intent == "transactional"

    @pytest.mark.asyncio
    async def test_concurrency_semaphore(self) -> None:
        """Verify that concurrency is limited (semaphore is used)."""
        import asyncio

        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt=f"Prompt {i}") for i in range(10)],
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_acompletion(**kwargs: object) -> MagicMock:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)
            async with lock:
                current_concurrent -= 1
            return _make_mock_response("Response")

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            results = await dispatch_queries(config)

        assert len(results) == 10
        # Semaphore should limit concurrency to 5
        assert max_concurrent <= 5

    @pytest.mark.asyncio
    async def test_default_config_values(self) -> None:
        """Default config values work correctly (single model, 3 runs)."""
        config = BenchmarkConfig(
            brand="TestBrand",
            prompts=[PromptEntry(prompt="Best laptop?")],
        )
        assert config.models == ["gpt-4o-mini"]
        assert config.runs_per_model == 3

        mock_resp = _make_mock_response("Response")
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            results = await dispatch_queries(config)

        assert len(results) == 3
