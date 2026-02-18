"""Tests for the compiler — render functions and generate_assets orchestrator."""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, patch

from aeo_cli.core.crawler import CrawlResult
from aeo_cli.core.generate.compiler import (
    generate_assets,
    render_llms_txt,
    render_schema_jsonld,
)
from aeo_cli.core.models import (
    GenerateConfig,
    LlmsTxtContent,
    LlmsTxtLink,
    LlmsTxtSection,
    ProfileType,
    SchemaJsonLdOutput,
)


class TestRenderLlmsTxt:
    def test_basic_format(self):
        content = LlmsTxtContent(
            title="Example Corp",
            description="The leading example provider.",
            sections=[
                LlmsTxtSection(
                    heading="Docs",
                    links=[
                        LlmsTxtLink(
                            title="Guide",
                            url="https://example.com/guide",
                            description="Getting started",
                        )
                    ],
                )
            ],
        )
        result = render_llms_txt(content)
        assert result.startswith("# Example Corp\n")
        assert "> The leading example provider." in result
        assert "## Docs" in result
        assert "- [Guide](https://example.com/guide): Getting started" in result

    def test_link_without_description(self):
        content = LlmsTxtContent(
            title="Test",
            description="Test site",
            sections=[
                LlmsTxtSection(
                    heading="Links",
                    links=[
                        LlmsTxtLink(title="Home", url="https://example.com")
                    ],
                )
            ],
        )
        result = render_llms_txt(content)
        assert "- [Home](https://example.com)" in result
        # No trailing colon when no description
        assert "- [Home](https://example.com):" not in result

    def test_empty_sections(self):
        content = LlmsTxtContent(
            title="Minimal",
            description="Minimal site",
            sections=[],
        )
        result = render_llms_txt(content)
        assert result == "# Minimal\n> Minimal site\n"

    def test_multiple_sections(self):
        content = LlmsTxtContent(
            title="Multi",
            description="Multi-section site",
            sections=[
                LlmsTxtSection(heading="Docs", links=[]),
                LlmsTxtSection(heading="API", links=[]),
            ],
        )
        result = render_llms_txt(content)
        assert "## Docs" in result
        assert "## API" in result

    def test_ends_with_newline(self):
        content = LlmsTxtContent(
            title="Test",
            description="Test",
            sections=[],
        )
        assert render_llms_txt(content).endswith("\n")


class TestRenderSchemaJsonld:
    def test_basic_format(self):
        output = SchemaJsonLdOutput(
            schema_type="Organization",
            json_ld={
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Example Corp",
            },
        )
        result = render_schema_jsonld(output)
        parsed = json.loads(result)
        assert parsed["@type"] == "Organization"
        assert parsed["name"] == "Example Corp"

    def test_pretty_printed(self):
        output = SchemaJsonLdOutput(
            schema_type="Product",
            json_ld={"@type": "Product", "name": "Widget"},
        )
        result = render_schema_jsonld(output)
        # Pretty-printed means multiple lines
        assert "\n" in result

    def test_ends_with_newline(self):
        output = SchemaJsonLdOutput(
            schema_type="X",
            json_ld={"@type": "X"},
        )
        assert render_schema_jsonld(output).endswith("\n")


class TestGenerateAssets:
    async def test_full_pipeline_mocked(self, tmp_path):
        mock_crawl = CrawlResult(
            url="https://example.com",
            html="<html></html>",
            markdown="# Example\nWelcome to Example Corp.",
            success=True,
            internal_links=["https://example.com/about"],
        )

        llms_response = {
            "title": "Example Corp",
            "description": "The leading example provider.",
            "sections": [
                {
                    "heading": "About",
                    "links": [
                        {
                            "title": "About Us",
                            "url": "https://example.com/about",
                            "description": "Learn more",
                        }
                    ],
                }
            ],
        }
        schema_response = {
            "schema_type": "Organization",
            "json_ld": {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Example Corp",
                "url": "https://example.com",
            },
        }

        call_count = 0

        async def mock_call_llm(messages, model, response_model):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return llms_response
            return schema_response

        config = GenerateConfig(
            url="https://example.com",
            profile=ProfileType.generic,
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        with (
            patch(
                "aeo_cli.core.crawler.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "aeo_cli.core.generate.llm.call_llm_structured",
                side_effect=mock_call_llm,
            ),
        ):
            result = await generate_assets(config)

        assert result.url == "https://example.com"
        assert result.model_used == "gpt-4o-mini"
        assert result.profile == ProfileType.generic
        assert result.llms_txt.title == "Example Corp"
        assert result.schema_jsonld.schema_type == "Organization"

        # Files written
        assert os.path.exists(result.llms_txt_path)
        assert os.path.exists(result.schema_jsonld_path)

        with open(result.llms_txt_path) as f:
            assert "# Example Corp" in f.read()
        with open(result.schema_jsonld_path) as f:
            data = json.load(f)
            assert data["@type"] == "Organization"

    async def test_crawl_failure_raises(self):
        mock_crawl = CrawlResult(
            url="https://bad.com",
            html="",
            markdown="",
            success=False,
            error="Connection refused",
        )
        config = GenerateConfig(url="https://bad.com", model="gpt-4o-mini")

        with patch(
            "aeo_cli.core.crawler.extract_page",
            new_callable=AsyncMock,
            return_value=mock_crawl,
        ):
            import pytest

            with pytest.raises(RuntimeError, match="Failed to crawl"):
                await generate_assets(config)

    async def test_auto_detects_model(self, tmp_path):
        mock_crawl = CrawlResult(
            url="https://example.com",
            html="<html></html>",
            markdown="# Test",
            success=True,
        )

        async def mock_call_llm(messages, model, response_model):
            if response_model.__name__ == "LlmsTxtContent":
                return {"title": "T", "description": "D", "sections": []}
            return {
                "schema_type": "Organization",
                "json_ld": {"@type": "Organization"},
            }

        config = GenerateConfig(
            url="https://example.com",
            output_dir=str(tmp_path),
        )  # model=None → auto-detect

        with (
            patch(
                "aeo_cli.core.crawler.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "aeo_cli.core.generate.llm.call_llm_structured",
                side_effect=mock_call_llm,
            ),
            patch(
                "aeo_cli.core.generate.llm.detect_model",
                return_value="gpt-4o-mini",
            ),
        ):
            result = await generate_assets(config)
            assert result.model_used == "gpt-4o-mini"
