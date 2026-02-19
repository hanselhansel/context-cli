"""Tests for the generate-batch CLI command and MCP tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from context_cli.core.models import (
    BatchGenerateConfig,
    BatchGenerateResult,
    BatchPageResult,
    ProfileType,
)
from context_cli.main import app
from context_cli.server import generate_batch_tool

runner = CliRunner()


_PATCH_TARGET = "context_cli.core.generate.batch.generate_batch"


def _mock_batch_result(
    total: int = 2,
    succeeded: int = 2,
    failed: int = 0,
) -> BatchGenerateResult:
    """Build a known BatchGenerateResult for test assertions."""
    results = [
        BatchPageResult(
            url="https://example.com",
            success=True,
            llms_txt_path="out/example.com/llms.txt",
            schema_jsonld_path="out/example.com/schema.jsonld",
            error=None,
        ),
        BatchPageResult(
            url="https://example.org",
            success=True,
            llms_txt_path="out/example.org/llms.txt",
            schema_jsonld_path="out/example.org/schema.jsonld",
            error=None,
        ),
    ]
    if failed > 0:
        results[1] = BatchPageResult(
            url="https://example.org",
            success=False,
            llms_txt_path=None,
            schema_jsonld_path=None,
            error="Connection timeout",
        )
    return BatchGenerateResult(
        total=total,
        succeeded=succeeded,
        failed=failed,
        results=results[:total],
        model_used="gpt-4o-mini",
        profile=ProfileType.generic,
        output_dir="./context-output",
    )


async def _fake_generate_batch(config: BatchGenerateConfig) -> BatchGenerateResult:
    """Async mock for generate_batch."""
    return _mock_batch_result()


# ── CLI: basic invocation ────────────────────────────────────────────────────


def test_generate_batch_basic(tmp_path):
    """generate-batch should produce Rich summary output."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\nhttps://example.org\n")

    with patch(_PATCH_TARGET, side_effect=_fake_generate_batch):
        result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 0
    assert "2/2 succeeded" in result.output
    assert "gpt-4o-mini" in result.output
    assert "example.com" in result.output


def test_generate_batch_json_output(tmp_path):
    """generate-batch --json should output valid JSON."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\nhttps://example.org\n")

    with patch(_PATCH_TARGET, side_effect=_fake_generate_batch):
        result = runner.invoke(app, ["generate-batch", str(url_file), "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] == 2
    assert data["succeeded"] == 2
    assert data["model_used"] == "gpt-4o-mini"
    assert len(data["results"]) == 2


# ── CLI: file handling ───────────────────────────────────────────────────────


def test_generate_batch_file_not_found():
    """generate-batch with nonexistent file should exit with error."""
    result = runner.invoke(app, ["generate-batch", "/nonexistent/urls.txt"])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_generate_batch_empty_file(tmp_path):
    """generate-batch with empty file should exit with error."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("")

    result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 1
    assert "No URLs found" in result.output


def test_generate_batch_comments_and_blanks(tmp_path):
    """generate-batch should skip comments and blank lines."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "# This is a comment\n"
        "\n"
        "https://example.com\n"
        "  # Another comment\n"
        "\n"
        "https://example.org\n"
    )
    configs_captured: list[BatchGenerateConfig] = []

    async def _capture(config: BatchGenerateConfig) -> BatchGenerateResult:
        configs_captured.append(config)
        return _mock_batch_result()

    with patch(_PATCH_TARGET, side_effect=_capture):
        result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].urls == ["https://example.com", "https://example.org"]


def test_generate_batch_url_auto_prefix(tmp_path):
    """generate-batch should auto-prefix https:// for bare domains."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("example.com\nexample.org\n")
    configs_captured: list[BatchGenerateConfig] = []

    async def _capture(config: BatchGenerateConfig) -> BatchGenerateResult:
        configs_captured.append(config)
        return _mock_batch_result()

    with patch(_PATCH_TARGET, side_effect=_capture):
        result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].urls == ["https://example.com", "https://example.org"]


def test_generate_batch_only_comments(tmp_path):
    """File with only comments should be treated as empty."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("# comment 1\n# comment 2\n")

    result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 1
    assert "No URLs found" in result.output


# ── CLI: options ─────────────────────────────────────────────────────────────


def test_generate_batch_concurrency_flag(tmp_path):
    """generate-batch --concurrency should pass through to config."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\n")
    configs_captured: list[BatchGenerateConfig] = []

    async def _capture(config: BatchGenerateConfig) -> BatchGenerateResult:
        configs_captured.append(config)
        return _mock_batch_result(total=1, succeeded=1)

    with patch(_PATCH_TARGET, side_effect=_capture):
        result = runner.invoke(
            app, ["generate-batch", str(url_file), "--concurrency", "5"]
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].concurrency == 5


def test_generate_batch_profile_flag(tmp_path):
    """generate-batch --profile should pass through to config."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\n")
    configs_captured: list[BatchGenerateConfig] = []

    async def _capture(config: BatchGenerateConfig) -> BatchGenerateResult:
        configs_captured.append(config)
        return _mock_batch_result(total=1, succeeded=1)

    with patch(_PATCH_TARGET, side_effect=_capture):
        result = runner.invoke(
            app, ["generate-batch", str(url_file), "--profile", "saas"]
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].profile == ProfileType.saas


def test_generate_batch_model_flag(tmp_path):
    """generate-batch --model should pass through to config."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\n")
    configs_captured: list[BatchGenerateConfig] = []

    async def _capture(config: BatchGenerateConfig) -> BatchGenerateResult:
        configs_captured.append(config)
        return _mock_batch_result(total=1, succeeded=1)

    with patch(_PATCH_TARGET, side_effect=_capture):
        result = runner.invoke(
            app,
            ["generate-batch", str(url_file), "--model", "claude-3-haiku-20240307"],
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].model == "claude-3-haiku-20240307"


def test_generate_batch_output_dir_flag(tmp_path):
    """generate-batch --output-dir should pass through to config."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\n")
    configs_captured: list[BatchGenerateConfig] = []

    async def _capture(config: BatchGenerateConfig) -> BatchGenerateResult:
        configs_captured.append(config)
        return _mock_batch_result(total=1, succeeded=1)

    with patch(_PATCH_TARGET, side_effect=_capture):
        result = runner.invoke(
            app, ["generate-batch", str(url_file), "--output-dir", "/tmp/out"]
        )

    assert result.exit_code == 0
    assert len(configs_captured) == 1
    assert configs_captured[0].output_dir == "/tmp/out"


# ── CLI: error handling ──────────────────────────────────────────────────────


def test_generate_batch_litellm_import_error(tmp_path):
    """generate-batch should show install hint when litellm is not available."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\n")

    import builtins

    original_import = builtins.__import__

    def _mock_import(name, *args, **kwargs):
        if name == "context_cli.core.generate.batch":
            raise ImportError("No module named 'litellm'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_mock_import):
        result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 1
    assert "litellm" in result.output


def test_generate_batch_runtime_error(tmp_path):
    """generate-batch should handle runtime errors gracefully."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\n")

    async def _raise(config: BatchGenerateConfig) -> BatchGenerateResult:
        raise RuntimeError("LLM service unavailable")

    with patch(_PATCH_TARGET, side_effect=_raise):
        result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 1
    assert "LLM service unavailable" in result.output


def test_generate_batch_with_failures(tmp_path):
    """generate-batch should show failure details in Rich output."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com\nhttps://example.org\n")

    async def _partial_fail(config: BatchGenerateConfig) -> BatchGenerateResult:
        return _mock_batch_result(total=2, succeeded=1, failed=1)

    with patch(_PATCH_TARGET, side_effect=_partial_fail):
        result = runner.invoke(app, ["generate-batch", str(url_file)])

    assert result.exit_code == 0
    assert "1/2 succeeded" in result.output
    assert "Connection timeout" in result.output


# ── MCP: generate_batch_tool ─────────────────────────────────────────────────

_mcp_fn = generate_batch_tool.fn if hasattr(generate_batch_tool, "fn") else generate_batch_tool


@pytest.mark.asyncio
async def test_mcp_generate_batch_returns_dict():
    """MCP generate_batch_tool should return a plain dict."""
    with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_batch_result()
        result = await _mcp_fn(
            urls=["https://example.com", "https://example.org"],
        )

    assert isinstance(result, dict)
    assert result["total"] == 2
    assert result["succeeded"] == 2
    assert result["model_used"] == "gpt-4o-mini"
    assert len(result["results"]) == 2


@pytest.mark.asyncio
async def test_mcp_generate_batch_passes_config():
    """MCP generate_batch_tool should pass all params to config."""
    with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_batch_result()
        await _mcp_fn(
            urls=["https://example.com"],
            profile="saas",
            model="gpt-4o",
            output_dir="/tmp/out",
            concurrency=5,
        )

    config = mock_gen.call_args[0][0]
    assert config.urls == ["https://example.com"]
    assert config.profile == ProfileType.saas
    assert config.model == "gpt-4o"
    assert config.output_dir == "/tmp/out"
    assert config.concurrency == 5


@pytest.mark.asyncio
async def test_mcp_generate_batch_default_params():
    """MCP generate_batch_tool should use sensible defaults."""
    with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = _mock_batch_result()
        await _mcp_fn(urls=["https://example.com"])

    config = mock_gen.call_args[0][0]
    assert config.profile == ProfileType.generic
    assert config.model is None
    assert config.output_dir == "./context-output"
    assert config.concurrency == 3
