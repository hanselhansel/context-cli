"""Tests for the citation radar CLI command, MCP tool, and models."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from aeo_cli.core.models import (
    BrandMention,
    CitationSource,
    DomainCategory,
    ModelRadarResult,
    RadarConfig,
    RadarReport,
)
from aeo_cli.main import app
from aeo_cli.server import radar as radar_tool

runner = CliRunner()

_PATCH_QUERY = "aeo_cli.core.radar.query.query_models"
_PATCH_ANALYZER = "aeo_cli.core.radar.analyzer.build_radar_report"


def _mock_model_results() -> list[ModelRadarResult]:
    """Build known per-model results for mocking."""
    return [
        ModelRadarResult(
            model="gpt-4o-mini",
            response_text="Dove body wash is highly rated on reddit.com",
            citations=[
                CitationSource(
                    url="https://reddit.com/r/bodywash",
                    title="Best Body Wash",
                    domain="reddit.com",
                    snippet="Dove is recommended",
                )
            ],
            brands_mentioned=["Dove"],
        ),
    ]


def _mock_radar_report() -> RadarReport:
    """Build a known RadarReport for CLI output assertions."""
    return RadarReport(
        prompt="best body wash",
        model_results=[
            ModelRadarResult(
                model="gpt-4o-mini",
                response_text="Dove body wash is highly rated on reddit.com",
                citations=[
                    CitationSource(
                        url="https://reddit.com/r/bodywash",
                        title="Best Body Wash",
                        domain="reddit.com",
                        snippet="Dove is recommended",
                    )
                ],
                brands_mentioned=["Dove"],
            ),
        ],
        brand_mentions=[
            BrandMention(
                brand="Dove",
                count=3,
                sentiment="positive",
                context_snippets=["Dove is recommended"],
            ),
        ],
        domain_breakdown=[
            DomainCategory(domain="reddit.com", category="reddit"),
        ],
        total_citations=2,
    )


async def _fake_query_models(config: RadarConfig) -> list[ModelRadarResult]:
    """Async mock for query_models."""
    return _mock_model_results()


def _fake_build_report(
    config: RadarConfig, results: list[ModelRadarResult]
) -> RadarReport:
    """Sync mock for build_radar_report."""
    return _mock_radar_report()


# ── CLI: basic invocation ────────────────────────────────────────────────────


def test_radar_basic_invocation():
    """radar command should produce Rich output with prompt and citation count."""
    with (
        patch(_PATCH_QUERY, side_effect=_fake_query_models),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(app, ["radar", "best body wash"])

    assert result.exit_code == 0
    assert "Citation Radar" in result.output
    assert "best body wash" in result.output
    assert "Total citations: 2" in result.output
    assert "Models queried: 1" in result.output


def test_radar_brand_mentions_displayed():
    """radar command should display brand mentions in Rich output."""
    with (
        patch(_PATCH_QUERY, side_effect=_fake_query_models),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(app, ["radar", "best body wash"])

    assert result.exit_code == 0
    assert "Dove" in result.output
    assert "3x" in result.output
    assert "positive" in result.output


def test_radar_domain_breakdown_displayed():
    """radar command should display domain breakdown in Rich output."""
    with (
        patch(_PATCH_QUERY, side_effect=_fake_query_models),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(app, ["radar", "best body wash"])

    assert result.exit_code == 0
    assert "reddit.com" in result.output
    assert "reddit" in result.output


# ── CLI: JSON output ─────────────────────────────────────────────────────────


def test_radar_json_output():
    """radar --json should output valid JSON with expected fields."""
    with (
        patch(_PATCH_QUERY, side_effect=_fake_query_models),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(app, ["radar", "best body wash", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["prompt"] == "best body wash"
    assert data["total_citations"] == 2
    assert len(data["model_results"]) == 1
    assert data["model_results"][0]["model"] == "gpt-4o-mini"
    assert len(data["brand_mentions"]) == 1
    assert data["brand_mentions"][0]["brand"] == "Dove"
    assert len(data["domain_breakdown"]) == 1


# ── CLI: --brand flags ───────────────────────────────────────────────────────


def test_radar_multiple_brands():
    """radar --brand should pass multiple brands to config."""
    configs_captured: list[RadarConfig] = []

    async def _capture_query(config: RadarConfig) -> list[ModelRadarResult]:
        configs_captured.append(config)
        return _mock_model_results()

    with (
        patch(_PATCH_QUERY, side_effect=_capture_query),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(
            app,
            ["radar", "best body wash", "--brand", "Dove", "--brand", "Olay"],
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].brands == ["Dove", "Olay"]


# ── CLI: --model flags ───────────────────────────────────────────────────────


def test_radar_multiple_models():
    """radar --model should pass multiple models to config."""
    configs_captured: list[RadarConfig] = []

    async def _capture_query(config: RadarConfig) -> list[ModelRadarResult]:
        configs_captured.append(config)
        return _mock_model_results()

    with (
        patch(_PATCH_QUERY, side_effect=_capture_query),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(
            app,
            [
                "radar",
                "best body wash",
                "--model",
                "gpt-4o-mini",
                "--model",
                "claude-3-haiku-20240307",
            ],
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].models == ["gpt-4o-mini", "claude-3-haiku-20240307"]


# ── CLI: --runs flag ─────────────────────────────────────────────────────────


def test_radar_runs_flag():
    """radar --runs should pass runs_per_model to config."""
    configs_captured: list[RadarConfig] = []

    async def _capture_query(config: RadarConfig) -> list[ModelRadarResult]:
        configs_captured.append(config)
        return _mock_model_results()

    with (
        patch(_PATCH_QUERY, side_effect=_capture_query),
        patch(_PATCH_ANALYZER, side_effect=_fake_build_report),
    ):
        result = runner.invoke(
            app, ["radar", "best body wash", "--runs", "5"]
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].runs_per_model == 5


# ── CLI: litellm import error ────────────────────────────────────────────────


def test_radar_litellm_import_error():
    """radar should show install hint when litellm is not available."""
    import builtins

    original_import = builtins.__import__

    def _mock_import(name, *args, **kwargs):
        if name == "aeo_cli.core.radar.query":
            raise ImportError("No module named 'litellm'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_mock_import):
        result = runner.invoke(app, ["radar", "best body wash"])

    assert result.exit_code == 1
    assert "litellm" in result.output


# ── CLI: exception handling ──────────────────────────────────────────────────


def test_radar_query_runtime_error():
    """radar should handle runtime errors gracefully."""

    async def _raise(config: RadarConfig) -> list[ModelRadarResult]:
        raise RuntimeError("LLM service unavailable")

    with patch(_PATCH_QUERY, side_effect=_raise):
        result = runner.invoke(app, ["radar", "best body wash"])

    assert result.exit_code == 1
    assert "LLM service unavailable" in result.output


def test_radar_analyzer_runtime_error():
    """radar should handle analyzer errors gracefully."""

    def _raise_analyzer(
        config: RadarConfig, results: list[ModelRadarResult]
    ) -> RadarReport:
        raise RuntimeError("Analyzer failed")

    with (
        patch(_PATCH_QUERY, side_effect=_fake_query_models),
        patch(_PATCH_ANALYZER, side_effect=_raise_analyzer),
    ):
        result = runner.invoke(app, ["radar", "best body wash"])

    assert result.exit_code == 1
    assert "Analyzer failed" in result.output


# ── CLI: no brand mentions or domains (empty report) ─────────────────────────


def test_radar_empty_report():
    """radar should handle report with no brands or domains gracefully."""
    empty_report = RadarReport(
        prompt="test query",
        model_results=[
            ModelRadarResult(
                model="gpt-4o-mini", response_text="No citations found."
            ),
        ],
        brand_mentions=[],
        domain_breakdown=[],
        total_citations=0,
    )

    def _empty_build(
        config: RadarConfig, results: list[ModelRadarResult]
    ) -> RadarReport:
        return empty_report

    with (
        patch(_PATCH_QUERY, side_effect=_fake_query_models),
        patch(_PATCH_ANALYZER, side_effect=_empty_build),
    ):
        result = runner.invoke(app, ["radar", "test query"])

    assert result.exit_code == 0
    assert "Total citations: 0" in result.output
    # No Brand Mentions or Source Domains sections
    assert "Brand Mentions" not in result.output
    assert "Source Domains" not in result.output


# ── main.py: radar command registered ────────────────────────────────────────


def test_radar_command_registered():
    """The radar command should be registered in the Typer app."""
    result = runner.invoke(app, ["--help"])
    assert "radar" in result.output


# ── MCP tool: radar ──────────────────────────────────────────────────────────

_mcp_fn = radar_tool.fn if hasattr(radar_tool, "fn") else radar_tool


@pytest.mark.asyncio
async def test_mcp_radar_returns_dict():
    """MCP radar tool should return a plain dict."""
    with (
        patch(_PATCH_QUERY, new_callable=AsyncMock) as mock_query,
        patch(_PATCH_ANALYZER) as mock_analyzer,
    ):
        mock_query.return_value = _mock_model_results()
        mock_analyzer.return_value = _mock_radar_report()

        result = await _mcp_fn(prompt="best body wash")

    assert isinstance(result, dict)
    assert result["prompt"] == "best body wash"
    assert result["total_citations"] == 2
    assert len(result["model_results"]) == 1
    assert len(result["brand_mentions"]) == 1


@pytest.mark.asyncio
async def test_mcp_radar_passes_config():
    """MCP radar tool should pass all params through to RadarConfig."""
    with (
        patch(_PATCH_QUERY, new_callable=AsyncMock) as mock_query,
        patch(_PATCH_ANALYZER) as mock_analyzer,
    ):
        mock_query.return_value = _mock_model_results()
        mock_analyzer.return_value = _mock_radar_report()

        await _mcp_fn(
            prompt="best body wash",
            models=["gpt-4o", "claude-3-haiku-20240307"],
            brands=["Dove", "Olay"],
            runs_per_model=3,
        )

    config = mock_query.call_args[0][0]
    assert config.prompt == "best body wash"
    assert config.models == ["gpt-4o", "claude-3-haiku-20240307"]
    assert config.brands == ["Dove", "Olay"]
    assert config.runs_per_model == 3


@pytest.mark.asyncio
async def test_mcp_radar_default_params():
    """MCP radar tool should use sensible defaults."""
    with (
        patch(_PATCH_QUERY, new_callable=AsyncMock) as mock_query,
        patch(_PATCH_ANALYZER) as mock_analyzer,
    ):
        mock_query.return_value = _mock_model_results()
        mock_analyzer.return_value = _mock_radar_report()

        await _mcp_fn(prompt="test query")

    config = mock_query.call_args[0][0]
    assert config.models == ["gpt-4o-mini"]
    assert config.brands == []
    assert config.runs_per_model == 1


# ── Model tests ──────────────────────────────────────────────────────────────


def test_radar_config_defaults():
    """RadarConfig should have sensible defaults."""
    config = RadarConfig(prompt="test")
    assert config.models == ["gpt-4o-mini"]
    assert config.brands == []
    assert config.runs_per_model == 1


def test_radar_config_custom():
    """RadarConfig should accept custom values."""
    config = RadarConfig(
        prompt="best soap",
        models=["gpt-4o", "claude-3-haiku-20240307"],
        brands=["Dove", "Olay"],
        runs_per_model=3,
    )
    assert config.prompt == "best soap"
    assert config.models == ["gpt-4o", "claude-3-haiku-20240307"]
    assert config.brands == ["Dove", "Olay"]
    assert config.runs_per_model == 3


def test_citation_source_defaults():
    """CitationSource should default all fields to None."""
    cs = CitationSource()
    assert cs.url is None
    assert cs.title is None
    assert cs.domain is None
    assert cs.snippet is None


def test_brand_mention_defaults():
    """BrandMention should default sentiment to neutral."""
    bm = BrandMention(brand="Dove", count=1)
    assert bm.sentiment == "neutral"
    assert bm.context_snippets == []


def test_model_radar_result_defaults():
    """ModelRadarResult should default citations/brands to empty."""
    mr = ModelRadarResult(model="gpt-4o-mini", response_text="test")
    assert mr.citations == []
    assert mr.brands_mentioned == []
    assert mr.error is None


def test_radar_report_defaults():
    """RadarReport should default aggregate fields."""
    rr = RadarReport(prompt="test", model_results=[])
    assert rr.brand_mentions == []
    assert rr.domain_breakdown == []
    assert rr.total_citations == 0


def test_domain_category_fields():
    """DomainCategory should store domain and category."""
    dc = DomainCategory(domain="reddit.com", category="reddit")
    assert dc.domain == "reddit.com"
    assert dc.category == "reddit"


# ── Stub modules importable ──────────────────────────────────────────────────


def test_radar_package_importable():
    """The radar package should be importable."""
    import aeo_cli.core.radar  # noqa: F401


def test_radar_query_stub_raises():
    """query_models stub should raise NotImplementedError."""
    from aeo_cli.core.radar.query import query_models

    with pytest.raises(NotImplementedError):
        import asyncio

        asyncio.run(query_models(RadarConfig(prompt="test")))


def test_radar_analyzer_stub_raises():
    """build_radar_report stub should raise NotImplementedError."""
    from aeo_cli.core.radar.analyzer import build_radar_report

    with pytest.raises(NotImplementedError):
        build_radar_report(RadarConfig(prompt="test"), [])
