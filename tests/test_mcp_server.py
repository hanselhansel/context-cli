"""Tests for the FastMCP server audit tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from context_cli.core.models import (
    AgentReadinessReport,
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
from context_cli.server import (
    agent_readiness_audit,
    audit,
    convert_to_markdown,
    generate,
    generate_agents_md_tool,
)

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


# -- Generate MCP tool --------------------------------------------------------

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


# -- Agent Readiness Audit MCP tool -------------------------------------------

_agent_readiness_fn = (
    agent_readiness_audit.fn
    if hasattr(agent_readiness_audit, "fn")
    else agent_readiness_audit
)


def _mock_report_with_agent_readiness() -> AuditReport:
    ar = AgentReadinessReport(score=12, detail="4/6 checks passed")
    return AuditReport(
        url="https://example.com",
        overall_score=67.0,
        robots=RobotsReport(found=True, score=25),
        llms_txt=LlmsTxtReport(found=True, score=10),
        schema_org=SchemaReport(blocks_found=2, score=15),
        content=ContentReport(word_count=600, score=17),
        agent_readiness=ar,
    )


def _mock_report_without_agent_readiness() -> AuditReport:
    return AuditReport(
        url="https://example.com",
        overall_score=55.0,
        robots=RobotsReport(found=True, score=25),
        llms_txt=LlmsTxtReport(found=False, score=0),
        schema_org=SchemaReport(blocks_found=1, score=13),
        content=ContentReport(word_count=500, score=17),
        agent_readiness=None,
    )


@pytest.mark.asyncio
async def test_agent_readiness_audit_with_data():
    """agent_readiness_audit returns agent_readiness model_dump when present."""
    with patch("context_cli.server.audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_report_with_agent_readiness()

        result = await _agent_readiness_fn("https://example.com")

        mock_audit.assert_called_once_with("https://example.com")
        assert isinstance(result, dict)
        assert result["score"] == 12
        assert result["detail"] == "4/6 checks passed"
        assert "agents_md" in result
        assert "markdown_accept" in result
        assert "mcp_endpoint" in result
        assert "semantic_html" in result
        assert "x402" in result
        assert "nlweb" in result


@pytest.mark.asyncio
async def test_agent_readiness_audit_without_data():
    """agent_readiness_audit returns error dict when agent_readiness is None."""
    with patch("context_cli.server.audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_report_without_agent_readiness()

        result = await _agent_readiness_fn("https://example.com")

        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "Agent readiness data not available"


@pytest.mark.asyncio
async def test_agent_readiness_audit_returns_dict():
    """agent_readiness_audit always returns a plain dict."""
    with patch("context_cli.server.audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_report_with_agent_readiness()

        result = await _agent_readiness_fn("https://example.com")

        assert isinstance(result, dict)
        # Should NOT be a Pydantic model
        assert not hasattr(result, "model_dump")


@pytest.mark.asyncio
async def test_agent_readiness_audit_sub_reports_structure():
    """agent_readiness_audit result contains all sub-report fields."""
    with patch("context_cli.server.audit_url", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _mock_report_with_agent_readiness()

        result = await _agent_readiness_fn("https://example.com")

        # Verify sub-report structure
        assert "found" in result["agents_md"]
        assert "supported" in result["markdown_accept"]
        assert "found" in result["mcp_endpoint"]
        assert "has_main" in result["semantic_html"]
        assert "found" in result["x402"]
        assert "found" in result["nlweb"]


# -- Convert to Markdown MCP tool ---------------------------------------------

_convert_to_markdown_fn = (
    convert_to_markdown.fn
    if hasattr(convert_to_markdown, "fn")
    else convert_to_markdown
)


@pytest.mark.asyncio
async def test_convert_to_markdown_success():
    """convert_to_markdown returns markdown text and stats on success."""
    mock_md = "# Hello World\n\nSome content here.\n"
    mock_stats: dict[str, float | int] = {
        "raw_html_chars": 500,
        "clean_md_chars": 40,
        "raw_tokens": 125,
        "clean_tokens": 10,
        "reduction_pct": 92.0,
    }
    with patch(
        "context_cli.core.markdown_engine.converter.convert_url_to_markdown",
        new_callable=AsyncMock,
    ) as mock_convert:
        mock_convert.return_value = (mock_md, mock_stats)

        result = await _convert_to_markdown_fn("https://example.com")

        mock_convert.assert_called_once_with("https://example.com")
        assert isinstance(result, dict)
        assert result["markdown"] == mock_md
        assert result["stats"] == mock_stats


@pytest.mark.asyncio
async def test_convert_to_markdown_stats_fields():
    """convert_to_markdown result stats contain all expected fields."""
    mock_md = "# Test\n"
    mock_stats: dict[str, float | int] = {
        "raw_html_chars": 1000,
        "clean_md_chars": 50,
        "raw_tokens": 250,
        "clean_tokens": 12,
        "reduction_pct": 95.2,
    }
    with patch(
        "context_cli.core.markdown_engine.converter.convert_url_to_markdown",
        new_callable=AsyncMock,
    ) as mock_convert:
        mock_convert.return_value = (mock_md, mock_stats)

        result = await _convert_to_markdown_fn("https://example.com")

        stats = result["stats"]
        assert "raw_html_chars" in stats
        assert "clean_md_chars" in stats
        assert "raw_tokens" in stats
        assert "clean_tokens" in stats
        assert "reduction_pct" in stats


@pytest.mark.asyncio
async def test_convert_to_markdown_empty_page():
    """convert_to_markdown handles empty markdown result."""
    mock_md = ""
    mock_stats: dict[str, float | int] = {
        "raw_html_chars": 100,
        "clean_md_chars": 0,
        "raw_tokens": 25,
        "clean_tokens": 0,
        "reduction_pct": 100.0,
    }
    with patch(
        "context_cli.core.markdown_engine.converter.convert_url_to_markdown",
        new_callable=AsyncMock,
    ) as mock_convert:
        mock_convert.return_value = (mock_md, mock_stats)

        result = await _convert_to_markdown_fn("https://example.com")

        assert result["markdown"] == ""
        assert result["stats"]["clean_md_chars"] == 0


@pytest.mark.asyncio
async def test_convert_to_markdown_propagates_error():
    """convert_to_markdown propagates HTTP errors from the converter."""
    with patch(
        "context_cli.core.markdown_engine.converter.convert_url_to_markdown",
        new_callable=AsyncMock,
    ) as mock_convert:
        mock_convert.side_effect = Exception("HTTP 404 Not Found")

        with pytest.raises(Exception, match="HTTP 404 Not Found"):
            await _convert_to_markdown_fn("https://example.com/missing")


# -- Generate AGENTS.md MCP tool ----------------------------------------------

_generate_agents_md_fn = (
    generate_agents_md_tool.fn
    if hasattr(generate_agents_md_tool, "fn")
    else generate_agents_md_tool
)


@pytest.fixture()
def _mock_agents_md_module():
    """Inject a fake agents_md module into sys.modules for the test duration."""
    import sys
    import types

    mock_fn = AsyncMock()
    mod = types.ModuleType("context_cli.core.generate.agents_md")
    mod.generate_agents_md = mock_fn  # type: ignore[attr-defined]
    sys.modules["context_cli.core.generate.agents_md"] = mod
    yield mock_fn
    sys.modules.pop("context_cli.core.generate.agents_md", None)


@pytest.mark.asyncio
async def test_generate_agents_md_tool_success(_mock_agents_md_module: AsyncMock):
    """generate_agents_md_tool returns content and url on success."""
    mock_gen = _mock_agents_md_module
    mock_content = "# AGENTS.md\n\n## Endpoints\n- /api/search\n"
    mock_gen.return_value = mock_content

    result = await _generate_agents_md_fn("https://example.com")

    mock_gen.assert_called_once_with("https://example.com")
    assert isinstance(result, dict)
    assert result["content"] == mock_content
    assert result["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_generate_agents_md_tool_returns_dict(
    _mock_agents_md_module: AsyncMock,
):
    """generate_agents_md_tool always returns a plain dict."""
    mock_gen = _mock_agents_md_module
    mock_gen.return_value = "# AGENTS.md\n"

    result = await _generate_agents_md_fn("https://example.com")

    assert isinstance(result, dict)
    assert "content" in result
    assert "url" in result


@pytest.mark.asyncio
async def test_generate_agents_md_tool_propagates_error(
    _mock_agents_md_module: AsyncMock,
):
    """generate_agents_md_tool propagates errors from the generator."""
    mock_gen = _mock_agents_md_module
    mock_gen.side_effect = RuntimeError("LLM API key not configured")

    with pytest.raises(RuntimeError, match="LLM API key not configured"):
        await _generate_agents_md_fn("https://example.com")


@pytest.mark.asyncio
async def test_generate_agents_md_tool_preserves_url(
    _mock_agents_md_module: AsyncMock,
):
    """generate_agents_md_tool returns the original URL in the response."""
    mock_gen = _mock_agents_md_module
    test_url = "https://my-site.io/about"
    mock_gen.return_value = "# AGENTS.md for my-site.io\n"

    result = await _generate_agents_md_fn(test_url)

    assert result["url"] == test_url
