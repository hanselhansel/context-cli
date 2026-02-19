"""Tests for citation radar query dispatcher — multi-model LLM querying."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_cli.core.models import ModelRadarResult, RadarConfig
from context_cli.core.radar.query import query_model, query_models


class TestQueryModel:
    """Tests for query_model — single model query."""

    @pytest.mark.asyncio
    async def test_success_returns_result(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Here is the answer with https://example.com"))
        ]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            result = await query_model("test prompt", "gpt-4o-mini")

        assert isinstance(result, ModelRadarResult)
        assert result.model == "gpt-4o-mini"
        assert "https://example.com" in result.response_text
        assert result.error is None

    @pytest.mark.asyncio
    async def test_error_captured_in_result(self) -> None:
        with patch(
            "litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=Exception("API rate limit"),
        ):
            result = await query_model("test prompt", "gpt-4o-mini")

        assert isinstance(result, ModelRadarResult)
        assert result.model == "gpt-4o-mini"
        assert result.response_text == ""
        assert result.error is not None
        assert "API rate limit" in result.error

    @pytest.mark.asyncio
    async def test_system_prompt_included(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
        with patch(
            "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
        ) as mock_call:
            await query_model("What is AEO?", "gpt-4o-mini")

        # Verify system prompt was sent
        call_args = mock_call.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "cite" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What is AEO?"

    @pytest.mark.asyncio
    async def test_citations_extracted(self) -> None:
        response_text = (
            "According to https://example.com/article, the results are clear."
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=response_text))]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            result = await query_model("test prompt", "gpt-4o-mini")

        assert len(result.citations) >= 1
        assert result.citations[0].url == "https://example.com/article"


class TestQueryModels:
    """Tests for query_models — multi-model query with runs_per_model."""

    @pytest.mark.asyncio
    async def test_multiple_models(self) -> None:
        config = RadarConfig(
            prompt="test prompt",
            models=["gpt-4o-mini", "claude-3-haiku-20240307"],
            runs_per_model=1,
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            results = await query_models(config)

        assert len(results) == 2
        models_used = {r.model for r in results}
        assert models_used == {"gpt-4o-mini", "claude-3-haiku-20240307"}

    @pytest.mark.asyncio
    async def test_runs_per_model(self) -> None:
        config = RadarConfig(
            prompt="test prompt",
            models=["gpt-4o-mini"],
            runs_per_model=3,
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            results = await query_models(config)

        assert len(results) == 3
        assert all(r.model == "gpt-4o-mini" for r in results)

    @pytest.mark.asyncio
    async def test_multiple_models_with_runs(self) -> None:
        config = RadarConfig(
            prompt="test prompt",
            models=["gpt-4o-mini", "claude-3-haiku-20240307"],
            runs_per_model=2,
        )
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            results = await query_models(config)

        assert len(results) == 4  # 2 models * 2 runs

    @pytest.mark.asyncio
    async def test_partial_failure(self) -> None:
        """One model fails, others succeed — all results returned."""
        config = RadarConfig(
            prompt="test prompt",
            models=["good-model", "bad-model"],
            runs_per_model=1,
        )

        async def mock_acompletion(**kwargs: object) -> MagicMock:
            model = kwargs.get("model", "")
            if model == "bad-model":
                raise Exception("Model not found")
            resp = MagicMock()
            resp.choices = [MagicMock(message=MagicMock(content="Good response"))]
            return resp

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            results = await query_models(config)

        assert len(results) == 2
        good = [r for r in results if r.error is None]
        bad = [r for r in results if r.error is not None]
        assert len(good) == 1
        assert len(bad) == 1
        assert good[0].model == "good-model"
        assert bad[0].model == "bad-model"

    @pytest.mark.asyncio
    async def test_brands_detected(self) -> None:
        config = RadarConfig(
            prompt="test prompt",
            models=["gpt-4o-mini"],
            brands=["Shopee", "Lazada"],
            runs_per_model=1,
        )
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Shopee is a leading platform. Tokopedia also competes."
                )
            )
        ]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            results = await query_models(config)

        assert len(results) == 1
        assert "Shopee" in results[0].brands_mentioned
        assert "Lazada" not in results[0].brands_mentioned

    @pytest.mark.asyncio
    async def test_default_config(self) -> None:
        """Default RadarConfig works (single model, 1 run)."""
        config = RadarConfig(prompt="test prompt")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Answer"))]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            results = await query_models(config)

        assert len(results) == 1
        assert results[0].model == "gpt-4o-mini"
