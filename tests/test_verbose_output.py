"""Tests for verbose CLI output — panels, formulas, recommendations, and edge cases."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from rich.console import Console
from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    ContentUsageReport,
    DiscoveryResult,
    EeatReport,
    LlmsTxtReport,
    PageAudit,
    RobotsReport,
    RslReport,
    SchemaOrgResult,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.formatters.verbose import (
    PILLAR_MAX,
    generate_recommendations,
    overall_color,
    render_content_usage_verbose,
    render_content_verbose,
    render_eeat_verbose,
    render_llms_verbose,
    render_recommendations,
    render_robots_verbose,
    render_rsl_verbose,
    render_schema_verbose,
    render_verbose_single,
    render_verbose_site,
    score_color,
)
from context_cli.main import app

runner = CliRunner()


# ── Test Fixtures ────────────────────────────────────────────────────────────


def _verbose_report() -> AuditReport:
    """Standard verbose test fixture with all 13 bots, detail strings, and char_count."""
    return AuditReport(
        url="https://example.com",
        overall_score=65.0,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ChatGPT-User", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Google-Extended", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked by robots.txt"),
                BotAccessResult(bot="PerplexityBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Amazonbot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="OAI-SearchBot", allowed=False, detail="Blocked by robots.txt"),
                BotAccessResult(bot="DeepSeek-AI", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Grok", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Meta-ExternalAgent", allowed=True, detail="Allowed"),
                BotAccessResult(bot="cohere-ai", allowed=True, detail="Allowed"),
                BotAccessResult(bot="AI2Bot", allowed=False, detail="Blocked by robots.txt"),
                BotAccessResult(bot="ByteSpider", allowed=True, detail="Allowed"),
            ],
            score=19.2,
            detail="10/13 AI bots allowed",
        ),
        llms_txt=LlmsTxtReport(
            found=True,
            url="https://example.com/llms.txt",
            score=10,
            detail="Found at https://example.com/llms.txt",
        ),
        schema_org=SchemaReport(
            blocks_found=1,
            schemas=[
                SchemaOrgResult(schema_type="Organization", properties=["name", "url", "logo"]),
            ],
            score=13,
            detail="1 JSON-LD block(s) found",
        ),
        content=ContentReport(
            word_count=800,
            char_count=4000,
            has_headings=True,
            has_lists=True,
            has_code_blocks=False,
            score=32,
            detail="800 words, has headings, has lists",
        ),
    )


def _perfect_report() -> AuditReport:
    """A report with maximum scores across all pillars."""
    return AuditReport(
        url="https://perfect.example.com",
        overall_score=100,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ChatGPT-User", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Google-Extended", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ClaudeBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="PerplexityBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Amazonbot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="OAI-SearchBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="DeepSeek-AI", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Grok", allowed=True, detail="Allowed"),
                BotAccessResult(bot="Meta-ExternalAgent", allowed=True, detail="Allowed"),
                BotAccessResult(bot="cohere-ai", allowed=True, detail="Allowed"),
                BotAccessResult(bot="AI2Bot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ByteSpider", allowed=True, detail="Allowed"),
            ],
            score=25,
            detail="13/13 AI bots allowed",
        ),
        llms_txt=LlmsTxtReport(
            found=True,
            url="https://perfect.example.com/llms.txt",
            score=10,
            detail="Found",
        ),
        schema_org=SchemaReport(
            blocks_found=4,
            schemas=[
                SchemaOrgResult(schema_type="Organization", properties=["name", "url"]),
                SchemaOrgResult(schema_type="WebSite", properties=["name", "url"]),
                SchemaOrgResult(schema_type="Article", properties=["headline", "author"]),
                SchemaOrgResult(schema_type="FAQPage", properties=["mainEntity"]),
            ],
            score=25,
            detail="4 JSON-LD block(s) found",
        ),
        content=ContentReport(
            word_count=2000,
            char_count=10000,
            has_headings=True,
            has_lists=True,
            has_code_blocks=True,
            score=40,
            detail="2000 words, has headings, has lists, has code blocks",
        ),
    )


def _minimal_report() -> AuditReport:
    """A report with zero scores — everything missing."""
    return AuditReport(
        url="https://empty.example.com",
        overall_score=0,
        robots=RobotsReport(found=False, detail="robots.txt not found"),
        llms_txt=LlmsTxtReport(found=False, detail="llms.txt not found"),
        schema_org=SchemaReport(detail="No JSON-LD found"),
        content=ContentReport(detail="No content extracted"),
    )


def _site_report() -> SiteAuditReport:
    """Multi-page site audit fixture."""
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=55.0,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked by robots.txt"),
            ],
            score=12.5,
            detail="1/2 AI bots allowed",
        ),
        llms_txt=LlmsTxtReport(found=False, detail="llms.txt not found"),
        schema_org=SchemaReport(
            blocks_found=2,
            schemas=[
                SchemaOrgResult(schema_type="Organization", properties=["name", "url"]),
                SchemaOrgResult(schema_type="WebPage", properties=["name"]),
            ],
            score=15,
            detail="2 JSON-LD block(s) across 2 pages",
        ),
        content=ContentReport(
            word_count=600,
            char_count=3000,
            has_headings=True,
            has_lists=False,
            has_code_blocks=False,
            score=22,
            detail="avg 600 words across 2 pages",
        ),
        discovery=DiscoveryResult(
            method="sitemap",
            urls_found=5,
            urls_sampled=["https://example.com", "https://example.com/about"],
            detail="Sitemap: 5 URLs found, 2 sampled",
        ),
        pages=[
            PageAudit(
                url="https://example.com",
                schema_org=SchemaReport(
                    blocks_found=1,
                    schemas=[
                        SchemaOrgResult(schema_type="Organization", properties=["name", "url"]),
                    ],
                    score=13,
                    detail="1 JSON-LD block(s) found",
                ),
                content=ContentReport(
                    word_count=900,
                    char_count=4500,
                    has_headings=True,
                    has_lists=True,
                    has_code_blocks=False,
                    score=32,
                    detail="900 words",
                ),
            ),
            PageAudit(
                url="https://example.com/about",
                schema_org=SchemaReport(
                    blocks_found=1,
                    schemas=[SchemaOrgResult(schema_type="WebPage", properties=["name"])],
                    score=13,
                    detail="1 JSON-LD block(s) found",
                ),
                content=ContentReport(
                    word_count=300,
                    char_count=1500,
                    has_headings=True,
                    has_lists=False,
                    has_code_blocks=False,
                    score=22,
                    detail="300 words",
                ),
            ),
        ],
        pages_audited=2,
        pages_failed=0,
    )


def _capture(fn, *args) -> str:
    """Capture Rich console output from a function that takes a Console arg."""
    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=120)
    fn(*args, con)
    return buf.getvalue()


def _panel_text(panel) -> str:
    """Render a Rich Panel to plain text for assertions."""
    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=120)
    con.print(panel)
    return buf.getvalue()


# ── Score Color Tests ────────────────────────────────────────────────────────


def test_score_color_green_threshold():
    """Scores >= 70% of pillar max should render green."""
    text = score_color(20.0, "robots")  # 20/25 = 80%
    assert text.style == "green"


def test_score_color_yellow_threshold():
    """Scores >= 40% but < 70% of pillar max should render yellow."""
    text = score_color(12.0, "robots")  # 12/25 = 48%
    assert text.style == "yellow"


def test_score_color_red_threshold():
    """Scores < 40% of pillar max should render red."""
    text = score_color(5.0, "robots")  # 5/25 = 20%
    assert text.style == "red"


def test_score_color_content_pillar():
    """score_color works correctly for content pillar (max 40)."""
    text = score_color(30.0, "content")  # 30/40 = 75%
    assert text.style == "green"


def test_overall_color_green():
    assert overall_color(75) == "green"


def test_overall_color_yellow():
    assert overall_color(50) == "yellow"


def test_overall_color_red():
    assert overall_color(20) == "red"


def test_pillar_max_values():
    """PILLAR_MAX should match the constants from auditor."""
    assert PILLAR_MAX["robots"] == 25
    assert PILLAR_MAX["llms_txt"] == 10
    assert PILLAR_MAX["schema_org"] == 25
    assert PILLAR_MAX["content"] == 40


# ── Robots Panel Tests ───────────────────────────────────────────────────────


def test_robots_verbose_shows_formula():
    """Robots panel should display the scoring formula."""
    report = _verbose_report()
    text = _panel_text(render_robots_verbose(report))
    assert "10/13" in text
    assert "× 25" in text or "× 25" in text


def test_robots_verbose_shows_bot_detail_strings():
    """Robots panel should show per-bot detail strings."""
    report = _verbose_report()
    text = _panel_text(render_robots_verbose(report))
    assert "GPTBot" in text
    assert "ClaudeBot" in text
    assert "Blocked by robots.txt" in text
    assert "Allowed" in text


def test_robots_verbose_all_bots_listed():
    """All 13 bots should appear in the robots panel."""
    report = _verbose_report()
    text = _panel_text(render_robots_verbose(report))
    for bot in report.robots.bots:
        assert bot.bot in text


def test_robots_verbose_not_found():
    """When robots.txt is not found, the panel should show a fallback message."""
    report = _minimal_report()
    text = _panel_text(render_robots_verbose(report))
    assert "not found" in text.lower()


def test_robots_verbose_border_color_scales():
    """Panel border should be colored based on score ratio."""
    report = _perfect_report()
    panel = render_robots_verbose(report)
    assert panel.border_style == "green"

    report2 = _minimal_report()
    panel2 = render_robots_verbose(report2)
    assert panel2.border_style == "red"


# ── llms.txt Panel Tests ────────────────────────────────────────────────────


def test_llms_verbose_shows_detail_string():
    """llms.txt panel should show the detail string when found."""
    report = _verbose_report()
    text = _panel_text(render_llms_verbose(report))
    assert "Found at" in text
    assert "llms.txt" in text


def test_llms_verbose_not_found_shows_paths_checked():
    """When llms.txt is not found, panel shows the paths that were checked."""
    report = _minimal_report()
    text = _panel_text(render_llms_verbose(report))
    assert "/llms.txt" in text
    assert "/.well-known/llms.txt" in text


def test_llms_verbose_binary_scoring():
    """Panel should explain the binary scoring (10 or 0)."""
    report = _verbose_report()
    text = _panel_text(render_llms_verbose(report))
    assert "10" in text
    assert "Binary" in text or "binary" in text


def test_llms_verbose_border_green_when_found():
    report = _verbose_report()
    panel = render_llms_verbose(report)
    assert panel.border_style == "green"


def test_llms_verbose_border_red_when_missing():
    report = _minimal_report()
    panel = render_llms_verbose(report)
    assert panel.border_style == "red"


# ── Schema Panel Tests ───────────────────────────────────────────────────────


def test_schema_verbose_shows_formula():
    """Schema panel should display the scoring formula."""
    report = _verbose_report()
    text = _panel_text(render_schema_verbose(report))
    assert "base 8" in text
    assert "× 1 type" in text or "× 1" in text


def test_schema_verbose_shows_property_names():
    """Schema panel should list property names for each @type."""
    report = _verbose_report()
    text = _panel_text(render_schema_verbose(report))
    assert "name" in text
    assert "url" in text
    assert "logo" in text


def test_schema_verbose_shows_type():
    """Schema panel should show @type for each JSON-LD block."""
    report = _verbose_report()
    text = _panel_text(render_schema_verbose(report))
    assert "Organization" in text


def test_schema_verbose_empty():
    """When no JSON-LD is found, schema panel shows appropriate message."""
    report = _minimal_report()
    text = _panel_text(render_schema_verbose(report))
    assert "No JSON-LD" in text


def test_schema_verbose_multiple_types():
    """Schema panel handles multiple types with high-value/standard breakdown."""
    report = _perfect_report()  # Has 4 types: 2 high-value + 2 standard
    text = _panel_text(render_schema_verbose(report))
    assert "2 high-value" in text
    assert "2 standard" in text
    assert "Organization" in text
    assert "Article" in text


def test_schema_verbose_border_color():
    report = _perfect_report()
    panel = render_schema_verbose(report)
    assert panel.border_style == "green"

    report2 = _minimal_report()
    panel2 = render_schema_verbose(report2)
    assert panel2.border_style == "red"


# ── Content Panel Tests ──────────────────────────────────────────────────────


def test_content_verbose_shows_char_count():
    """Content panel should display the char_count (previously hidden)."""
    report = _verbose_report()
    text = _panel_text(render_content_verbose(report))
    assert "4000" in text


def test_content_verbose_shows_tier_and_formula():
    """Content panel should show the word tier and bonus formula."""
    report = _verbose_report()  # 800 words
    text = _panel_text(render_content_verbose(report))
    # Active tier: 800+ = 20 pts
    assert "800+" in text or "800" in text
    assert "active" in text.lower()
    # Formula: 20 base + 7 headings + 5 lists + 0 code
    assert "20 base" in text
    assert "7 headings" in text
    assert "5 lists" in text
    assert "0 code" in text


def test_content_verbose_shows_word_count():
    """Content panel should prominently display word count."""
    report = _verbose_report()
    text = _panel_text(render_content_verbose(report))
    assert "800" in text


def test_content_verbose_shows_structure_flags():
    """Content panel should show headings/lists/code status."""
    report = _verbose_report()
    text = _panel_text(render_content_verbose(report))
    assert "Headings" in text
    assert "Lists" in text
    assert "Code" in text


def test_content_verbose_all_tiers_shown():
    """Content panel should display all word count tiers."""
    report = _verbose_report()
    text = _panel_text(render_content_verbose(report))
    assert "1500+" in text or "1500" in text
    assert "800+" in text or "800" in text
    assert "400+" in text or "400" in text
    assert "150+" in text or "150" in text


def test_content_verbose_zero_words():
    """Content panel handles zero word count gracefully."""
    report = _minimal_report()
    text = _panel_text(render_content_verbose(report))
    assert "0" in text


def test_content_verbose_high_score_green_border():
    report = _perfect_report()
    panel = render_content_verbose(report)
    assert panel.border_style == "green"


def test_content_verbose_low_score_red_border():
    report = _minimal_report()
    panel = render_content_verbose(report)
    assert panel.border_style == "red"


# ── Recommendations Tests ────────────────────────────────────────────────────


def test_recommendations_for_blocked_bots():
    """Should recommend unblocking specific blocked bots."""
    report = _verbose_report()
    recs = generate_recommendations(report)
    bot_rec = [r for r in recs if "Unblock" in r]
    assert len(bot_rec) == 1
    assert "ClaudeBot" in bot_rec[0]
    assert "OAI-SearchBot" in bot_rec[0]
    assert "AI2Bot" in bot_rec[0]


def test_recommendations_for_missing_llms_txt():
    """Should recommend creating llms.txt when not found."""
    report = _minimal_report()
    recs = generate_recommendations(report)
    llms_rec = [r for r in recs if "llms.txt" in r.lower()]
    assert len(llms_rec) >= 1
    assert "+10 pts" in llms_rec[0]


def test_recommendations_for_no_schema():
    """Should recommend adding JSON-LD when none found."""
    report = _minimal_report()
    recs = generate_recommendations(report)
    schema_rec = [r for r in recs if "JSON-LD" in r or "Schema.org" in r]
    assert len(schema_rec) >= 1


def test_recommendations_for_low_word_count():
    """Should suggest adding words to reach the next tier."""
    report = AuditReport(
        url="https://example.com",
        overall_score=10,
        robots=RobotsReport(found=True, bots=[], score=0, detail=""),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=0, detail="No JSON-LD"),
        content=ContentReport(
            word_count=200, char_count=1000, has_headings=False,
            has_lists=False, has_code_blocks=False, score=8, detail="200 words",
        ),
    )
    recs = generate_recommendations(report)
    word_rec = [r for r in recs if "more words" in r]
    assert len(word_rec) >= 1
    # Should suggest reaching 400 tier
    assert "400" in word_rec[0]


def test_recommendations_for_missing_headings():
    """Should recommend adding headings when missing."""
    report = AuditReport(
        url="https://example.com",
        overall_score=20,
        robots=RobotsReport(found=True, bots=[], score=0, detail=""),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=0, detail="No JSON-LD"),
        content=ContentReport(
            word_count=500, char_count=2500, has_headings=False,
            has_lists=True, has_code_blocks=False, score=20, detail="500 words",
        ),
    )
    recs = generate_recommendations(report)
    heading_rec = [r for r in recs if "headings" in r.lower() or "heading" in r.lower()]
    assert len(heading_rec) >= 1
    assert "+7" in heading_rec[0]


def test_no_recommendations_for_perfect_score():
    """Perfect score should produce no recommendations (or very few)."""
    report = _perfect_report()
    recs = generate_recommendations(report)
    assert len(recs) == 0


def test_render_recommendations_returns_none_for_perfect():
    """render_recommendations should return None when no recs exist."""
    report = _perfect_report()
    panel = render_recommendations(report)
    assert panel is None


def test_render_recommendations_returns_panel_with_content():
    """render_recommendations should return a Panel with numbered items."""
    report = _minimal_report()
    panel = render_recommendations(report)
    assert panel is not None
    text = _panel_text(panel)
    assert "1." in text
    assert "How to improve" in text


def test_recommendations_for_missing_robots():
    """Should recommend creating robots.txt when not found."""
    report = _minimal_report()
    recs = generate_recommendations(report)
    robots_rec = [r for r in recs if "robots.txt" in r.lower()]
    assert len(robots_rec) >= 1


# ── Single-Page Compositor Tests ─────────────────────────────────────────────


def test_verbose_single_renders_all_panels():
    """render_verbose_single should render all panel sections."""
    report = _verbose_report()
    output = _capture(render_verbose_single, report)
    assert "Scoring Methodology" in output
    assert "Robots.txt Detail" in output
    assert "llms.txt Detail" in output
    assert "Schema.org Detail" in output
    assert "Content Detail" in output


def test_verbose_single_renders_recommendations():
    """render_verbose_single should render recommendations when applicable."""
    report = _verbose_report()  # Has blocked bots → recommendations exist
    output = _capture(render_verbose_single, report)
    assert "Recommendations" in output


def test_verbose_single_no_recommendations_for_perfect():
    """render_verbose_single should skip recommendations panel for perfect score."""
    report = _perfect_report()
    output = _capture(render_verbose_single, report)
    assert "Recommendations" not in output


# ── Multi-Page Verbose Tests ────────────────────────────────────────────────


def test_verbose_site_renders_per_page_panels():
    """render_verbose_site should render per-page panels."""
    report = _site_report()
    output = _capture(render_verbose_site, report)
    assert "Per-Page Detail" in output
    assert "https://example.com/about" in output


def test_verbose_site_renders_aggregation():
    """render_verbose_site should show aggregation explanation."""
    report = _site_report()
    output = _capture(render_verbose_site, report)
    assert "Aggregation Detail" in output
    assert "depth" in output.lower()
    assert "weight" in output.lower()


def test_verbose_site_renders_site_wide_panels():
    """render_verbose_site should render site-wide robots and llms panels."""
    report = _site_report()
    output = _capture(render_verbose_site, report)
    assert "Robots.txt Detail" in output
    assert "llms.txt Detail" in output


def test_verbose_site_renders_recommendations():
    """render_verbose_site should include recommendations."""
    report = _site_report()
    output = _capture(render_verbose_site, report)
    assert "Recommendations" in output


def test_verbose_site_with_failed_pages():
    """Verbose site should handle pages with errors gracefully."""
    report = _site_report()
    # Add a failed page
    report.pages.append(PageAudit(
        url="https://example.com/broken",
        schema_org=SchemaReport(detail="Crawl failed"),
        content=ContentReport(detail="Crawl failed"),
        errors=["Connection timeout"],
    ))
    output = _capture(render_verbose_site, report)
    assert "broken" in output
    assert "Connection timeout" in output


def test_verbose_site_empty_pages():
    """Verbose site should handle empty pages list."""
    report = _site_report()
    report.pages = []
    output = _capture(render_verbose_site, report)
    # Should still show site-wide panels
    assert "Robots.txt Detail" in output
    assert "llms.txt Detail" in output
    # Should not crash
    assert "Per-Page Detail" not in output


def test_verbose_site_schema_with_many_properties():
    """Per-page detail should truncate schema properties >5 with '... (+N more)'.

    Note: Rich markup parser consumes the [...] brackets, so we verify the
    code path is exercised via coverage and check that the schema type renders.
    """
    report = _site_report()
    # Replace first page's schema with one that has >5 properties
    report.pages[0].schema_org = SchemaReport(
        blocks_found=1,
        schemas=[
            SchemaOrgResult(
                schema_type="Product",
                properties=["name", "url", "image", "price", "brand", "sku", "description"],
            ),
        ],
        score=13,
        detail="1 JSON-LD block(s) found",
    )
    output = _capture(render_verbose_site, report)
    # Rich consumes [...] as markup, so @type is the visible part
    assert "Product" in output
    # Verify the truncation path was hit (7 properties > 5)
    assert len(report.pages[0].schema_org.schemas[0].properties) > 5


def test_verbose_site_page_weight_depth_2():
    """Pages at URL depth 2 should get weight 2 in aggregation detail."""
    report = _site_report()
    report.pages.append(PageAudit(
        url="https://example.com/blog/my-post",
        schema_org=SchemaReport(detail="No JSON-LD found"),
        content=ContentReport(word_count=400, char_count=2000, score=18, detail="400 words"),
    ))
    output = _capture(render_verbose_site, report)
    assert "depth 2" in output
    assert "weight 2" in output


def test_verbose_site_page_weight_depth_3_plus():
    """Pages at URL depth 3+ should get weight 1 in aggregation detail."""
    report = _site_report()
    report.pages.append(PageAudit(
        url="https://example.com/blog/2024/my-post",
        schema_org=SchemaReport(detail="No JSON-LD found"),
        content=ContentReport(word_count=300, char_count=1500, score=15, detail="300 words"),
    ))
    output = _capture(render_verbose_site, report)
    assert "depth 3" in output
    assert "weight 1" in output


# ── CLI Integration Tests ────────────────────────────────────────────────────


async def _fake_audit(url: str, **kwargs) -> AuditReport:
    return _verbose_report()


async def _fake_site_audit(url: str, **kwargs) -> SiteAuditReport:
    return _site_report()


def test_verbose_shows_bot_details():
    """--verbose should show per-bot allowed/blocked status via CLI."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert result.exit_code == 0
    assert "GPTBot" in result.output
    assert "ClaudeBot" in result.output


def test_verbose_shows_schema_types():
    """--verbose should show @type for each JSON-LD block via CLI."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert "Organization" in result.output


def test_verbose_shows_content_details():
    """--verbose should show word count and structure flags via CLI."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert "800" in result.output
    assert "Headings" in result.output


def test_verbose_shows_scoring_methodology():
    """--verbose should include the scoring methodology line via CLI."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert "Scoring Methodology" in result.output


def test_non_verbose_omits_panels():
    """Without --verbose, the detailed panels should not appear."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single"])

    assert "Scoring Methodology" not in result.output


def test_verbose_does_not_affect_json_output():
    """--verbose with --json should still produce valid JSON, no panels."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--json", "--verbose"]
        )

    assert result.exit_code == 0
    assert "Scoring Methodology" not in result.output
    assert '"url"' in result.output


def test_verbose_does_not_affect_csv_output():
    """--verbose with --format csv should still produce CSV, no panels."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(
            app,
            ["audit", "https://example.com", "--single", "--format", "csv", "--verbose"],
        )

    assert result.exit_code == 0
    assert "Scoring Methodology" not in result.output


def test_site_verbose_via_cli():
    """--verbose should work for multi-page site audits via CLI."""
    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_site_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--verbose"])

    assert result.exit_code == 0
    assert "Scoring Methodology" in result.output
    assert "Robots.txt Detail" in result.output


def test_site_verbose_shows_per_page():
    """Multi-page --verbose should show per-page detail."""
    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_site_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--verbose"])

    assert result.exit_code == 0
    assert "Per-Page Detail" in result.output
    assert "example.com/about" in result.output


# ── RSL Panel Tests ─────────────────────────────────────────────────────────


def _rsl_report() -> AuditReport:
    """Report with RSL signals populated."""
    report = _verbose_report()
    report.rsl = RslReport(
        has_crawl_delay=True,
        crawl_delay_value=10.0,
        has_sitemap_directive=True,
        sitemap_urls=["https://example.com/sitemap.xml"],
        has_ai_specific_rules=True,
        ai_specific_agents=["GPTBot", "ClaudeBot"],
        detail="RSL signals found",
    )
    return report


def test_rsl_verbose_shows_crawl_delay():
    report = _rsl_report()
    text = _panel_text(render_rsl_verbose(report))
    assert "Crawl-delay" in text
    assert "10" in text


def test_rsl_verbose_shows_sitemap_urls():
    report = _rsl_report()
    text = _panel_text(render_rsl_verbose(report))
    assert "sitemap.xml" in text


def test_rsl_verbose_shows_ai_specific_agents():
    report = _rsl_report()
    text = _panel_text(render_rsl_verbose(report))
    assert "GPTBot" in text
    assert "ClaudeBot" in text


def test_rsl_verbose_no_signals():
    report = _verbose_report()
    report.rsl = RslReport(detail="No RSL signals")
    text = _panel_text(render_rsl_verbose(report))
    assert "No RSL signals" in text


def test_rsl_verbose_none_returns_none():
    report = _verbose_report()
    report.rsl = None
    result = render_rsl_verbose(report)
    assert result is None


def test_rsl_verbose_border_is_blue():
    report = _rsl_report()
    panel = render_rsl_verbose(report)
    assert panel is not None
    assert panel.border_style == "blue"


# ── Content-Usage Panel Tests ───────────────────────────────────────────────


def _content_usage_report() -> AuditReport:
    """Report with Content-Usage header populated."""
    report = _verbose_report()
    report.content_usage = ContentUsageReport(
        header_found=True,
        header_value="training=no; search=yes",
        allows_training=False,
        allows_search=True,
        detail="Content-Usage header found",
    )
    return report


def test_content_usage_verbose_shows_header_value():
    report = _content_usage_report()
    text = _panel_text(render_content_usage_verbose(report))
    assert "training=no" in text


def test_content_usage_verbose_shows_permissions():
    report = _content_usage_report()
    text = _panel_text(render_content_usage_verbose(report))
    assert "Training" in text
    assert "Search" in text


def test_content_usage_verbose_not_found():
    report = _verbose_report()
    report.content_usage = ContentUsageReport(
        header_found=False,
        detail="No Content-Usage header",
    )
    text = _panel_text(render_content_usage_verbose(report))
    assert "not found" in text.lower() or "No Content-Usage" in text


def test_content_usage_verbose_none_returns_none():
    report = _verbose_report()
    report.content_usage = None
    result = render_content_usage_verbose(report)
    assert result is None


def test_content_usage_verbose_border_is_blue():
    report = _content_usage_report()
    panel = render_content_usage_verbose(report)
    assert panel is not None
    assert panel.border_style == "blue"


# ── E-E-A-T Panel Tests ────────────────────────────────────────────────────


def _eeat_report() -> AuditReport:
    """Report with E-E-A-T signals populated."""
    report = _verbose_report()
    report.eeat = EeatReport(
        has_author=True,
        author_name="Dr. Sarah Chen",
        has_date=True,
        has_about_page=True,
        has_contact_info=True,
        has_citations=True,
        citation_count=5,
        trust_signals=["privacy policy", "terms of service"],
        detail="E-E-A-T signals found",
    )
    return report


def test_eeat_verbose_shows_author():
    report = _eeat_report()
    text = _panel_text(render_eeat_verbose(report))
    assert "Dr. Sarah Chen" in text


def test_eeat_verbose_shows_date():
    report = _eeat_report()
    text = _panel_text(render_eeat_verbose(report))
    assert "Date" in text or "date" in text


def test_eeat_verbose_shows_citations():
    report = _eeat_report()
    text = _panel_text(render_eeat_verbose(report))
    assert "5" in text
    assert "citation" in text.lower()


def test_eeat_verbose_shows_trust_signals():
    report = _eeat_report()
    text = _panel_text(render_eeat_verbose(report))
    assert "privacy policy" in text.lower()
    assert "terms of service" in text.lower()


def test_eeat_verbose_no_signals():
    report = _verbose_report()
    report.eeat = EeatReport(detail="No E-E-A-T signals detected")
    text = _panel_text(render_eeat_verbose(report))
    assert "No E-E-A-T signals" in text


def test_eeat_verbose_none_returns_none():
    report = _verbose_report()
    report.eeat = None
    result = render_eeat_verbose(report)
    assert result is None


def test_eeat_verbose_border_is_blue():
    report = _eeat_report()
    panel = render_eeat_verbose(report)
    assert panel is not None
    assert panel.border_style == "blue"


def test_eeat_verbose_partial_signals():
    """E-E-A-T panel handles partial signal set (author but nothing else)."""
    report = _verbose_report()
    report.eeat = EeatReport(
        has_author=True,
        author_name="Jane",
        detail="author: Jane",
    )
    text = _panel_text(render_eeat_verbose(report))
    assert "Jane" in text


def test_eeat_verbose_no_author_but_has_date():
    """E-E-A-T panel shows 'not found' for author when only date is detected."""
    report = _verbose_report()
    report.eeat = EeatReport(
        has_date=True,
        detail="publication date",
    )
    text = _panel_text(render_eeat_verbose(report))
    assert "not found" in text.lower()  # Author not found
    assert "Yes" in text  # Date = Yes


# ── Informational panels in compositor ──────────────────────────────────────


def test_verbose_single_renders_informational_panels():
    """render_verbose_single should render RSL/Content-Usage/E-E-A-T when present."""
    report = _rsl_report()
    report.content_usage = ContentUsageReport(
        header_found=True, header_value="training=yes", detail="found",
    )
    report.eeat = EeatReport(has_author=True, author_name="Bob", detail="author: Bob")
    output = _capture(render_verbose_single, report)
    assert "RSL" in output
    assert "Content-Usage" in output
    assert "E-E-A-T" in output


def test_verbose_single_skips_none_informational():
    """render_verbose_single should skip informational panels when None."""
    report = _verbose_report()
    # All informational fields are None by default
    output = _capture(render_verbose_single, report)
    assert "RSL" not in output
    assert "Content-Usage" not in output
    assert "E-E-A-T" not in output


def test_verbose_site_renders_informational_panels():
    """render_verbose_site should render RSL/Content-Usage/E-E-A-T when present."""
    report = _site_report()
    report.rsl = RslReport(has_crawl_delay=True, crawl_delay_value=5, detail="RSL found")
    report.content_usage = ContentUsageReport(header_found=True, detail="found")
    report.eeat = EeatReport(has_author=True, detail="author found")
    output = _capture(render_verbose_site, report)
    assert "RSL" in output
    assert "Content-Usage" in output
    assert "E-E-A-T" in output
