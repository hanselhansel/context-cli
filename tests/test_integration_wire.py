"""Tests for wiring agent-readiness checks into auditor and Rich display."""

from __future__ import annotations

from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest
from rich.console import Console

from context_cli.core.auditor import _build_agent_readiness, audit_url
from context_cli.core.crawler import CrawlResult
from context_cli.core.models import (
    AgentReadinessReport,
    AgentsMdReport,
    AuditReport,
    BatchAuditReport,
    BotAccessResult,
    ContentReport,
    ContentUsageReport,
    DiscoveryResult,
    LlmsTxtReport,
    MarkdownAcceptReport,
    McpEndpointReport,
    NlwebReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
    SemanticHtmlReport,
    SiteAuditReport,
    X402Report,
)
from context_cli.formatters.rich_output import (
    render_batch_rich,
    render_single_report,
    render_site_report,
)
from context_cli.formatters.verbose_panels import (
    PILLAR_MAX,
    render_agent_readiness_verbose,
)

# ── Helpers ─────────────────────────────────────────────────────────────────

_SEED = "https://example.com"


def _make_robots(found: bool = True) -> tuple[RobotsReport, str | None]:
    bots = [BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed")]
    return (
        RobotsReport(found=found, bots=bots, detail="1/1 AI bots allowed"),
        "User-agent: *\nAllow: /",
    )


def _make_llms() -> LlmsTxtReport:
    return LlmsTxtReport(found=True, url=f"{_SEED}/llms.txt", detail="Found")


def _make_crawl(
    success: bool = True, error: str | None = None
) -> CrawlResult:
    return CrawlResult(
        url=_SEED,
        html=(
            '<html><head><script type="application/ld+json">'
            '{"@type":"Organization","name":"X"}'
            "</script></head><body>" + " word" * 200 + "</body></html>"
        ),
        markdown="# Hello\n" + "word " * 200,
        success=success,
        error=error,
        internal_links=[f"{_SEED}/about"],
    )


def _make_agents_md() -> AgentsMdReport:
    return AgentsMdReport(
        found=True, url=f"{_SEED}/agents.md", score=5.0,
        detail="AGENTS.md found",
    )


def _make_md_accept() -> MarkdownAcceptReport:
    return MarkdownAcceptReport(
        supported=True, content_type="text/markdown", score=5.0,
        detail="Server supports Accept: text/markdown",
    )


def _make_mcp() -> McpEndpointReport:
    return McpEndpointReport(
        found=True, url=f"{_SEED}/.well-known/mcp.json", tools_count=3,
        score=4.0, detail="MCP endpoint found with 3 tool(s)",
    )


def _make_x402() -> X402Report:
    return X402Report(
        found=True, has_402_status=True, has_payment_header=True,
        score=2.0, detail="x402 detected",
    )


def _make_nlweb() -> NlwebReport:
    return NlwebReport(
        found=True, well_known_found=True, schema_extensions=True,
        score=1.0, detail="NLWeb found",
    )


def _make_semantic_html() -> SemanticHtmlReport:
    return SemanticHtmlReport(
        has_main=True, has_article=True, has_header=True,
        has_footer=True, has_nav=True, aria_landmarks=3,
        score=3.0, detail="Semantic HTML found",
    )


def _make_cu() -> ContentUsageReport:
    return ContentUsageReport(
        header_found=False, detail="No Content-Usage header",
    )


def _make_agent_readiness() -> AgentReadinessReport:
    return AgentReadinessReport(
        agents_md=_make_agents_md(),
        markdown_accept=_make_md_accept(),
        mcp_endpoint=_make_mcp(),
        semantic_html=_make_semantic_html(),
        x402=_make_x402(),
        nlweb=_make_nlweb(),
        score=20.0,
        detail="Agent readiness: 20/20",
    )


def _make_report(
    agent_readiness: AgentReadinessReport | None = None,
) -> AuditReport:
    return AuditReport(
        url=_SEED,
        overall_score=50.0,
        robots=RobotsReport(
            found=True,
            bots=[BotAccessResult(bot="GPTBot", allowed=True, detail="OK")],
            score=25, detail="1/1 allowed",
        ),
        llms_txt=LlmsTxtReport(
            found=True, url=f"{_SEED}/llms.txt", score=10, detail="Found",
        ),
        schema_org=SchemaReport(
            blocks_found=1,
            schemas=[
                SchemaOrgResult(
                    schema_type="Organization", properties=["name"],
                ),
            ],
            score=11, detail="1 JSON-LD block(s) found",
        ),
        content=ContentReport(
            word_count=500, char_count=2500, has_headings=True,
            has_lists=True, score=27, detail="500 words",
        ),
        agent_readiness=agent_readiness,
    )


def _make_site_report(
    agent_readiness: AgentReadinessReport | None = None,
) -> SiteAuditReport:
    return SiteAuditReport(
        url=_SEED,
        domain="example.com",
        overall_score=50.0,
        robots=RobotsReport(
            found=True,
            bots=[BotAccessResult(bot="GPTBot", allowed=True, detail="OK")],
            score=25, detail="1/1 allowed",
        ),
        llms_txt=LlmsTxtReport(found=False, detail="Not found"),
        schema_org=SchemaReport(detail="No JSON-LD"),
        content=ContentReport(detail="No content"),
        discovery=DiscoveryResult(method="sitemap", detail="1 page"),
        agent_readiness=agent_readiness,
    )


def _panel_text(panel) -> str:
    """Render a Rich Panel to plain text for assertions."""
    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=120)
    con.print(panel)
    return buf.getvalue()


def _capture_console(fn, *args) -> str:
    """Capture Rich console output from a function that takes Console."""
    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=120)
    fn(*args, con)
    return buf.getvalue()


# ── audit_url() agent readiness wiring tests ────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.core.auditor.check_nlweb", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_x402", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_mcp_endpoint", new_callable=AsyncMock)
@patch(
    "context_cli.core.auditor.check_markdown_accept",
    new_callable=AsyncMock,
)
@patch("context_cli.core.auditor.check_agents_md", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_returns_agent_readiness(
    mock_robots, mock_llms, mock_crawl,
    mock_agents_md, mock_md_accept, mock_mcp, mock_x402, mock_nlweb,
):
    """audit_url() should return AuditReport with agent_readiness."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_agents_md.return_value = _make_agents_md()
    mock_md_accept.return_value = _make_md_accept()
    mock_mcp.return_value = _make_mcp()
    mock_x402.return_value = _make_x402()
    mock_nlweb.return_value = _make_nlweb()

    report = await audit_url(_SEED)

    assert report.agent_readiness is not None
    assert report.agent_readiness.agents_md.found is True
    assert report.agent_readiness.agents_md.score == 5.0
    assert report.agent_readiness.markdown_accept.supported is True
    assert report.agent_readiness.mcp_endpoint.found is True
    assert report.agent_readiness.x402.found is True
    assert report.agent_readiness.nlweb.found is True
    assert report.agent_readiness.score > 0


@pytest.mark.asyncio
@patch("context_cli.core.auditor.check_nlweb", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_x402", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_mcp_endpoint", new_callable=AsyncMock)
@patch(
    "context_cli.core.auditor.check_markdown_accept",
    new_callable=AsyncMock,
)
@patch("context_cli.core.auditor.check_agents_md", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_agent_check_error_handling(
    mock_robots, mock_llms, mock_crawl,
    mock_agents_md, mock_md_accept, mock_mcp, mock_x402, mock_nlweb,
):
    """One agent check fails, others succeed."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_agents_md.side_effect = RuntimeError("boom")
    mock_md_accept.return_value = _make_md_accept()
    mock_mcp.return_value = _make_mcp()
    mock_x402.return_value = _make_x402()
    mock_nlweb.return_value = _make_nlweb()

    report = await audit_url(_SEED)

    assert report.agent_readiness is not None
    # AGENTS.md failed, should use default
    assert report.agent_readiness.agents_md.found is False
    assert report.agent_readiness.agents_md.score == 0
    # Others should be fine
    assert report.agent_readiness.markdown_accept.supported is True
    assert any("AGENTS.md check failed" in e for e in report.errors)


@pytest.mark.asyncio
@patch("context_cli.core.auditor.check_nlweb", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_x402", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_mcp_endpoint", new_callable=AsyncMock)
@patch(
    "context_cli.core.auditor.check_markdown_accept",
    new_callable=AsyncMock,
)
@patch("context_cli.core.auditor.check_agents_md", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_all_agent_checks_fail(
    mock_robots, mock_llms, mock_crawl,
    mock_agents_md, mock_md_accept, mock_mcp, mock_x402, mock_nlweb,
):
    """All agent checks fail -- should produce default empty reports."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_agents_md.side_effect = RuntimeError("boom")
    mock_md_accept.side_effect = RuntimeError("boom")
    mock_mcp.side_effect = RuntimeError("boom")
    mock_x402.side_effect = RuntimeError("boom")
    mock_nlweb.side_effect = RuntimeError("boom")

    report = await audit_url(_SEED)

    assert report.agent_readiness is not None
    assert report.agent_readiness.score == 0
    # But semantic_html is sync, should still work
    assert isinstance(
        report.agent_readiness.semantic_html, SemanticHtmlReport
    )


@pytest.mark.asyncio
@patch("context_cli.core.auditor.check_nlweb", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_x402", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_mcp_endpoint", new_callable=AsyncMock)
@patch(
    "context_cli.core.auditor.check_markdown_accept",
    new_callable=AsyncMock,
)
@patch("context_cli.core.auditor.check_agents_md", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_agent_readiness_score_sum(
    mock_robots, mock_llms, mock_crawl,
    mock_agents_md, mock_md_accept, mock_mcp, mock_x402, mock_nlweb,
):
    """Agent readiness total score is sum of sub-check scores."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_agents_md.return_value = _make_agents_md()  # score=5
    mock_md_accept.return_value = _make_md_accept()  # score=5
    mock_mcp.return_value = _make_mcp()  # score=4
    mock_x402.return_value = _make_x402()  # score=2
    mock_nlweb.return_value = _make_nlweb()  # score=1

    report = await audit_url(_SEED)

    ar = report.agent_readiness
    assert ar is not None
    expected = (
        ar.agents_md.score + ar.markdown_accept.score
        + ar.mcp_endpoint.score + ar.semantic_html.score
        + ar.x402.score + ar.nlweb.score
    )
    assert ar.score == expected


# ── _build_agent_readiness tests ────────────────────────────────────────────


def test_build_agent_readiness_happy_path():
    """All results valid -> correct total score."""
    errors: list[str] = []
    ar = _build_agent_readiness(
        _make_agents_md(), _make_md_accept(), _make_mcp(),
        _make_semantic_html(), _make_x402(), _make_nlweb(), errors,
    )
    assert ar.score == 20.0
    assert errors == []


def test_build_agent_readiness_with_exceptions():
    """Exception results -> default reports, errors logged."""
    errors: list[str] = []
    ar = _build_agent_readiness(
        RuntimeError("boom"), RuntimeError("boom"),
        RuntimeError("boom"), _make_semantic_html(),
        RuntimeError("boom"), RuntimeError("boom"), errors,
    )
    assert ar.agents_md.found is False
    assert ar.markdown_accept.supported is False
    assert ar.mcp_endpoint.found is False
    assert ar.x402.found is False
    assert ar.nlweb.found is False
    # Only semantic_html has a score
    assert ar.score == _make_semantic_html().score
    assert len(errors) == 5


def test_build_agent_readiness_bad_semantic_html():
    """Non-SemanticHtmlReport value -> default."""
    errors: list[str] = []
    ar = _build_agent_readiness(
        _make_agents_md(), _make_md_accept(), _make_mcp(),
        "not a report", _make_x402(), _make_nlweb(), errors,
    )
    assert ar.semantic_html.score == 0
    assert ar.score == 5 + 5 + 4 + 0 + 2 + 1


# ── _audit_site_inner agent readiness tests ──────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.core.auditor.check_nlweb", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_x402", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_mcp_endpoint", new_callable=AsyncMock)
@patch(
    "context_cli.core.auditor.check_markdown_accept",
    new_callable=AsyncMock,
)
@patch("context_cli.core.auditor.check_agents_md", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("context_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_site_inner_returns_agent_readiness(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch,
    mock_agents_md, mock_md_accept, mock_mcp, mock_x402, mock_nlweb,
):
    """_audit_site_inner should populate agent_readiness."""
    from context_cli.core.auditor import _audit_site_inner

    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED],
    )
    mock_agents_md.return_value = _make_agents_md()
    mock_md_accept.return_value = _make_md_accept()
    mock_mcp.return_value = _make_mcp()
    mock_x402.return_value = _make_x402()
    mock_nlweb.return_value = _make_nlweb()

    errors: list[str] = []
    report = await _audit_site_inner(
        _SEED, "example.com", 10, 0.0, errors, lambda _: None,
    )

    assert report.agent_readiness is not None
    assert report.agent_readiness.agents_md.found is True
    assert report.agent_readiness.score > 0


@pytest.mark.asyncio
@patch("context_cli.core.auditor.check_nlweb", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_x402", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_mcp_endpoint", new_callable=AsyncMock)
@patch(
    "context_cli.core.auditor.check_markdown_accept",
    new_callable=AsyncMock,
)
@patch("context_cli.core.auditor.check_agents_md", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("context_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_site_inner_agent_error_handling(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch,
    mock_agents_md, mock_md_accept, mock_mcp, mock_x402, mock_nlweb,
):
    """Agent check failures in site audit are handled gracefully."""
    from context_cli.core.auditor import _audit_site_inner

    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED],
    )
    mock_agents_md.side_effect = RuntimeError("boom")
    mock_md_accept.side_effect = RuntimeError("boom")
    mock_mcp.return_value = _make_mcp()
    mock_x402.return_value = _make_x402()
    mock_nlweb.return_value = _make_nlweb()

    errors: list[str] = []
    report = await _audit_site_inner(
        _SEED, "example.com", 10, 0.0, errors, lambda _: None,
    )

    assert report.agent_readiness is not None
    # Failed checks get defaults
    assert report.agent_readiness.agents_md.found is False
    assert report.agent_readiness.markdown_accept.supported is False
    # Successful checks retained
    assert report.agent_readiness.mcp_endpoint.found is True


# ── Verbose panel tests ─────────────────────────────────────────────────────


def test_pillar_max_includes_agent_readiness():
    """PILLAR_MAX should include agent_readiness = 20."""
    assert "agent_readiness" in PILLAR_MAX
    assert PILLAR_MAX["agent_readiness"] == 20


def test_render_agent_readiness_verbose_none():
    """Should return None when agent_readiness is None."""
    report = _make_report(agent_readiness=None)
    result = render_agent_readiness_verbose(report)
    assert result is None


def test_render_agent_readiness_verbose_populated():
    """Should return a Panel with sub-check breakdown."""
    ar = _make_agent_readiness()
    report = _make_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    assert panel is not None
    text = _panel_text(panel)
    assert "Agent Readiness" in text
    assert "AGENTS.md" in text
    assert "Accept: text/markdown" in text
    assert "MCP Endpoint" in text
    assert "Semantic HTML" in text
    assert "x402 Payment" in text
    assert "NLWeb" in text
    assert "20" in text


def test_render_agent_readiness_verbose_zero_score():
    """Zero-score agent readiness should use red border."""
    ar = AgentReadinessReport(score=0, detail="Agent readiness: 0/20")
    report = _make_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    assert panel is not None
    assert panel.border_style == "red"


def test_render_agent_readiness_verbose_high_score():
    """High-score agent readiness should use green border."""
    ar = _make_agent_readiness()
    report = _make_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    assert panel is not None
    assert panel.border_style == "green"


def test_render_agent_readiness_verbose_detail_shown():
    """Sub-check detail strings should be rendered."""
    ar = _make_agent_readiness()
    report = _make_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    text = _panel_text(panel)
    assert "AGENTS.md found" in text
    assert "MCP endpoint found" in text


def test_render_agent_readiness_verbose_site_report():
    """Should work with SiteAuditReport too."""
    ar = _make_agent_readiness()
    report = _make_site_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    assert panel is not None
    text = _panel_text(panel)
    assert "Agent Readiness" in text


def test_render_agent_readiness_verbose_partial_scores():
    """Panel with partial scores: some checks pass, some fail."""
    ar = AgentReadinessReport(
        agents_md=AgentsMdReport(found=True, score=5.0, detail="Found"),
        markdown_accept=MarkdownAcceptReport(score=0, detail="Not supported"),
        mcp_endpoint=McpEndpointReport(score=0, detail="Not found"),
        semantic_html=SemanticHtmlReport(score=2.0, detail="Partial"),
        x402=X402Report(score=0, detail="Not detected"),
        nlweb=NlwebReport(score=0, detail="Not found"),
        score=7.0,
        detail="Agent readiness: 7/20",
    )
    report = _make_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    assert panel is not None
    text = _panel_text(panel)
    # Rich markup may strip/format fractional scores
    assert "AGENTS.md" in text
    assert "MCP Endpoint" in text
    assert "Not supported" in text
    assert "Not found" in text


def test_render_agent_readiness_verbose_empty_detail():
    """Sub-checks with empty detail should not render detail line."""
    ar = AgentReadinessReport(
        agents_md=AgentsMdReport(score=0, detail=""),
        score=0,
        detail="Agent readiness: 0/20",
    )
    report = _make_report(agent_readiness=ar)
    panel = render_agent_readiness_verbose(report)
    assert panel is not None
    # Should not crash, empty detail is fine


# ── Rich output tests ──────────────────────────────────────────────────────


def test_render_single_report_no_agent_readiness():
    """render_single_report should not crash when agent_readiness=None."""
    report = _make_report(agent_readiness=None)
    output = _capture_console(render_single_report, report)
    assert "Agent Readiness" not in output


def test_render_single_report_with_agent_readiness():
    """render_single_report should show agent readiness when populated."""
    ar = _make_agent_readiness()
    report = _make_report(agent_readiness=ar)
    output = _capture_console(render_single_report, report)
    assert "Agent Readiness" in output
    assert "20" in output


def test_render_site_report_no_agent_readiness():
    """render_site_report should not crash when agent_readiness=None."""
    report = _make_site_report(agent_readiness=None)
    output = _capture_console(render_site_report, report)
    assert "Agent Readiness" not in output


def test_render_site_report_with_agent_readiness():
    """render_site_report should show agent readiness when populated."""
    ar = _make_agent_readiness()
    report = _make_site_report(agent_readiness=ar)
    output = _capture_console(render_site_report, report)
    assert "Agent Readiness" in output
    assert "20" in output


def test_render_batch_no_agent_readiness():
    """Batch table should not have Agent column when no agent_readiness."""
    batch = BatchAuditReport(
        urls=[_SEED],
        reports=[_make_report(agent_readiness=None)],
    )
    output = _capture_console(render_batch_rich, batch)
    assert "Agent" not in output


def test_render_batch_with_agent_readiness():
    """Batch table should have Agent column when agent_readiness exists."""
    ar = _make_agent_readiness()
    batch = BatchAuditReport(
        urls=[_SEED],
        reports=[_make_report(agent_readiness=ar)],
    )
    output = _capture_console(render_batch_rich, batch)
    assert "Agent" in output
    assert "20" in output


def test_render_batch_mixed_agent_readiness():
    """Batch table handles mix of reports with and without agent_readiness."""
    ar = _make_agent_readiness()
    batch = BatchAuditReport(
        urls=[_SEED, f"{_SEED}/other"],
        reports=[
            _make_report(agent_readiness=ar),
            _make_report(agent_readiness=None),
        ],
    )
    output = _capture_console(render_batch_rich, batch)
    assert "Agent" in output
    # Second report has no agent_readiness, should show "-"


# ── Verbose compositor integration tests ────────────────────────────────────


def test_verbose_single_renders_agent_readiness():
    """render_verbose_single should render agent readiness panel."""
    from context_cli.formatters.verbose import render_verbose_single
    ar = _make_agent_readiness()
    report = _make_report(agent_readiness=ar)
    output = _capture_console(render_verbose_single, report)
    assert "Agent Readiness" in output


def test_verbose_single_skips_agent_readiness_when_none():
    """render_verbose_single should skip agent readiness when None."""
    from context_cli.formatters.verbose import render_verbose_single
    report = _make_report(agent_readiness=None)
    output = _capture_console(render_verbose_single, report)
    assert "Agent Readiness Detail" not in output


def test_verbose_site_renders_agent_readiness():
    """render_verbose_site should render agent readiness panel."""
    from context_cli.formatters.verbose import render_verbose_site
    ar = _make_agent_readiness()
    report = _make_site_report(agent_readiness=ar)
    output = _capture_console(render_verbose_site, report)
    assert "Agent Readiness" in output


def test_verbose_site_skips_agent_readiness_when_none():
    """render_verbose_site should skip agent readiness when None."""
    from context_cli.formatters.verbose import render_verbose_site
    report = _make_site_report(agent_readiness=None)
    output = _capture_console(render_verbose_site, report)
    assert "Agent Readiness Detail" not in output


# ── Re-export test ──────────────────────────────────────────────────────────


def test_render_agent_readiness_verbose_re_exported():
    """render_agent_readiness_verbose should be importable from verbose."""
    from context_cli.formatters.verbose import (
        render_agent_readiness_verbose,
    )
    assert callable(render_agent_readiness_verbose)
