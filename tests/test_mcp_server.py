"""Tests for the FastMCP server audit tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    DiscoveryResult,
    GenerateResult,
    LlmsTxtContent,
    LlmsTxtLink,
    LlmsTxtReport,
    LlmsTxtSection,
    ProfileType,
    RobotsReport,
    SchemaJsonLdOutput,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.server import audit, generate

# FastMCP 2.x wraps @mcp.tool functions in a FunctionTool object.
# The underlying async function is accessible via .fn
_audit_fn = audit.fn if hasattr(audit, "fn") else audit


def _mock_single_report() -> AuditReport:
    return AuditReport(
        url="https://example.com",
        overall_score=55.0,
        robots=RobotsReport(found=True, score=25, detail="7/7 AI bots allowed"),
        llms_txt=LlmsTxtReport(found=False, score=0),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(word_count=500, score=17, detail="500 words"),
    )


def _mock_site_report() -> SiteAuditReport:
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=68.0,
        robots=RobotsReport(found=True, score=25),
        llms_txt=LlmsTxtReport(found=True, score=10),
        schema_org=SchemaReport(blocks_found=2, score=13),
        content=ContentReport(word_count=700, score=20),
        discovery=DiscoveryResult(method="sitemap", urls_found=50),
        pages_audited=3,
    )


@pytest.mark.asyncio
async def test_audit_tool_single_page():
    """MCP audit tool with single_page=True should call audit_url."""
    with patch("context_cli.server.audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_single_report()

        result = await _audit_fn("https://example.com", single_page=True)

        mock_audit.assert_called_once_with("https://example.com")
        assert result["url"] == "https://example.com"
        assert result["overall_score"] == 55.0
        assert "robots" in result
        assert "content" in result


@pytest.mark.asyncio
async def test_audit_tool_site_audit():
    """MCP audit tool with default params should call audit_site."""
    with patch("context_cli.server.audit_site", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_site_report()

        result = await _audit_fn("https://example.com")

        mock_audit.assert_called_once_with("https://example.com", max_pages=10)
        assert result["domain"] == "example.com"
        assert result["overall_score"] == 68.0
        assert "discovery" in result


@pytest.mark.asyncio
async def test_audit_tool_custom_max_pages():
    """MCP audit tool should pass max_pages to audit_site."""
    with patch("context_cli.server.audit_site", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_site_report()

        await _audit_fn("https://example.com", max_pages=5)

        mock_audit.assert_called_once_with("https://example.com", max_pages=5)


@pytest.mark.asyncio
async def test_audit_tool_returns_dict():
    """MCP audit tool should return a plain dict (not Pydantic model)."""
    with patch("context_cli.server.audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_single_report()

        result = await _audit_fn("https://example.com", single_page=True)

        assert isinstance(result, dict)


# ── Generate MCP tool ────────────────────────────────────────────────────────

_generate_fn = generate.fn if hasattr(generate, "fn") else generate


def _mock_generate_result() -> GenerateResult:
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
                    links=[LlmsTxtLink(title="Docs", url="https://example.com/docs")],
                )
            ],
        ),
        schema_jsonld=SchemaJsonLdOutput(
            schema_type="Organization",
            json_ld={"@context": "https://schema.org", "@type": "Organization"},
        ),
        llms_txt_path="./context-output/llms.txt",
        schema_jsonld_path="./context-output/schema.jsonld",
    )


@pytest.mark.asyncio
async def test_generate_tool_returns_dict():
    """MCP generate tool should return a plain dict."""
    with patch(
        "context_cli.core.generate.generate_assets", new_callable=AsyncMock
    ) as mock_gen:
        mock_gen.return_value = _mock_generate_result()
        result = await _generate_fn("https://example.com")

        assert isinstance(result, dict)
        assert result["url"] == "https://example.com"
        assert result["model_used"] == "gpt-4o-mini"
        assert "llms_txt" in result
        assert "schema_jsonld" in result
