"""Tests for the generate CLI command."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from context_cli.core.models import (
    GenerateResult,
    LlmsTxtContent,
    LlmsTxtLink,
    LlmsTxtSection,
    ProfileType,
    SchemaJsonLdOutput,
)
from context_cli.main import app

runner = CliRunner()

# Patch target: generate_assets is lazily imported inside the generate command
# via `from context_cli.core.generate import generate_assets`, so we patch
# at the source module level.
_PATCH_TARGET = "context_cli.core.generate.generate_assets"


def _mock_generate_result() -> GenerateResult:
    """Build a known GenerateResult for CLI output assertions."""
    return GenerateResult(
        url="https://example.com",
        model_used="gpt-4o-mini",
        profile=ProfileType.generic,
        llms_txt=LlmsTxtContent(
            title="Example",
            description="An example website",
            sections=[
                LlmsTxtSection(
                    heading="Docs",
                    links=[
                        LlmsTxtLink(
                            title="Getting Started",
                            url="https://example.com/docs",
                            description="Docs page",
                        )
                    ],
                )
            ],
        ),
        schema_jsonld=SchemaJsonLdOutput(
            schema_type="Organization",
            json_ld={
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Example",
            },
        ),
        llms_txt_path="./context-output/llms.txt",
        schema_jsonld_path="./context-output/schema.jsonld",
    )


async def _fake_generate_assets(config):
    """Async mock for generate_assets."""
    return _mock_generate_result()


def test_generate_basic_invocation():
    """generate command should produce Rich output with file paths."""
    with patch(_PATCH_TARGET, side_effect=_fake_generate_assets):
        result = runner.invoke(app, ["generate", "https://example.com"])

    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "gpt-4o-mini" in result.output
    assert "llms.txt" in result.output
    assert "schema.jsonld" in result.output


def test_generate_json_output():
    """generate --json should output valid JSON."""
    with patch(_PATCH_TARGET, side_effect=_fake_generate_assets):
        result = runner.invoke(app, ["generate", "https://example.com", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["url"] == "https://example.com"
    assert data["model_used"] == "gpt-4o-mini"
    assert "llms_txt" in data
    assert "schema_jsonld" in data


def test_generate_profile_option():
    """generate --profile saas should pass profile through to config."""
    configs = []

    async def _capture_config(config):
        configs.append(config)
        return _mock_generate_result()

    with patch(_PATCH_TARGET, side_effect=_capture_config):
        result = runner.invoke(
            app, ["generate", "https://example.com", "--profile", "saas", "--json"]
        )

    assert result.exit_code == 0
    assert len(configs) == 1
    assert configs[0].profile == ProfileType.saas


def test_generate_model_option():
    """generate --model should pass model through to config."""
    configs = []

    async def _capture_config(config):
        configs.append(config)
        return _mock_generate_result()

    with patch(_PATCH_TARGET, side_effect=_capture_config):
        result = runner.invoke(
            app,
            ["generate", "https://example.com", "--model", "claude-3-haiku-20240307", "--json"],
        )

    assert result.exit_code == 0
    assert len(configs) == 1
    assert configs[0].model == "claude-3-haiku-20240307"


def test_generate_missing_litellm():
    """generate should show install hint when litellm is not available."""
    import builtins

    original_import = builtins.__import__

    def _mock_import(name, *args, **kwargs):
        if name == "context_cli.core.generate":
            raise ImportError("No module named 'litellm'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_mock_import):
        result = runner.invoke(app, ["generate", "https://example.com"])

    assert result.exit_code == 1
    assert "litellm" in result.output or "generate" in result.output


def test_generate_url_auto_prefix():
    """generate should auto-prefix https:// for bare domains."""
    configs = []

    async def _capture_config(config):
        configs.append(config)
        return _mock_generate_result()

    with patch(_PATCH_TARGET, side_effect=_capture_config):
        result = runner.invoke(app, ["generate", "example.com", "--json"])

    assert result.exit_code == 0
    assert len(configs) == 1
    assert configs[0].url == "https://example.com"
