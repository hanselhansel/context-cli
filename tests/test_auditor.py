"""Tests for auditor pillar checks and scoring logic."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from aeo_cli.core.checks.content import check_content
from aeo_cli.core.checks.robots import check_robots
from aeo_cli.core.checks.schema import check_schema_org
from aeo_cli.core.models import (
    BotAccessResult,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)
from aeo_cli.core.scoring import compute_scores

# -- check_schema_org ----------------------------------------------------------


def test_check_schema_org_with_jsonld():
    """HTML containing a JSON-LD script should yield one parsed block."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Acme", "url": "https://acme.com"}
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    assert report.blocks_found == 1
    assert len(report.schemas) == 1
    assert report.schemas[0].schema_type == "Organization"
    assert "name" in report.schemas[0].properties
    assert "url" in report.schemas[0].properties


def test_check_schema_org_empty_html():
    """Empty HTML should return 0 blocks."""
    report = check_schema_org("")
    assert report.blocks_found == 0
    assert report.schemas == []
    assert report.detail == "No HTML to analyze"


def test_check_schema_org_no_jsonld():
    """HTML without JSON-LD scripts should return 0 blocks."""
    html = "<html><head></head><body><p>Hello</p></body></html>"
    report = check_schema_org(html)
    assert report.blocks_found == 0
    assert report.schemas == []


def test_check_schema_org_multiple_blocks():
    """HTML with two JSON-LD scripts should return 2 blocks."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Organization", "name": "Acme"}
    </script>
    <script type="application/ld+json">
    {"@type": "Article", "headline": "Test"}
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)
    assert report.blocks_found == 2
    types = {s.schema_type for s in report.schemas}
    assert types == {"Organization", "Article"}


# -- check_content -------------------------------------------------------------


def test_check_content_with_markdown():
    """Sample markdown should detect word count, headings, and lists."""
    md = "# Welcome\n\nThis is a sample paragraph with several words.\n\n- item one\n- item two\n"
    report = check_content(md)

    assert report.word_count > 0
    assert report.char_count > 0
    assert report.has_headings is True
    assert report.has_lists is True
    assert report.has_code_blocks is False


def test_check_content_empty_string():
    """Empty markdown should return zero counts and no structure flags."""
    report = check_content("")
    assert report.word_count == 0
    assert report.char_count == 0
    assert report.has_headings is False
    assert report.has_lists is False
    assert report.detail == "No content extracted"


def test_check_content_with_code_blocks():
    """Markdown with code fences should detect code blocks."""
    md = "# Heading\n\n```python\nprint('hello')\n```\n"
    report = check_content(md)
    assert report.has_code_blocks is True
    assert report.has_headings is True


# -- compute_scores ------------------------------------------------------------


def test_compute_scores_full_marks():
    """All bots allowed + llms.txt + 2 schemas + 1500 words + headings + lists -> high score."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in [
        "GPTBot", "ChatGPT-User", "Google-Extended", "ClaudeBot",
        "PerplexityBot", "Amazonbot", "OAI-SearchBot",
    ]]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True, url="https://example.com/llms.txt")
    schema_org = SchemaReport(
        blocks_found=2,
        schemas=[
            SchemaOrgResult(schema_type="Organization", properties=["name"]),
            SchemaOrgResult(schema_type="Article", properties=["headline"]),
        ],
    )
    content = ContentReport(
        word_count=1500,
        has_headings=True,
        has_lists=True,
        has_code_blocks=False,
    )

    robots, llms_txt, schema_org, content, overall = compute_scores(
        robots, llms_txt, schema_org, content
    )

    # Robots: 25 (all 7 bots allowed)
    assert robots.score == 25

    # llms.txt: 10 (revised weight)
    assert llms_txt.score == 10

    # Schema: 8 base + 5 (Article=high-value) + 3 (Organization=standard) = 16
    assert schema_org.score == 16

    # Content: 25 (1500+ words) + 7 (headings) + 5 (lists) = 37
    assert content.score == 37

    # Overall: 25 + 10 + 16 + 37 = 88
    assert overall == 88


def test_compute_scores_nothing_found():
    """No robots, no llms.txt, no schema, no content -> score 0."""
    robots = RobotsReport(found=False)
    llms_txt = LlmsTxtReport(found=False)
    schema_org = SchemaReport()
    content = ContentReport()

    _, _, _, _, overall = compute_scores(robots, llms_txt, schema_org, content)
    assert overall == 0


def test_compute_scores_partial():
    """Partial results should yield proportional scores."""
    # 3 of 7 bots allowed
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="PerplexityBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="Amazonbot", allowed=False, detail="Blocked"),
        BotAccessResult(bot="OAI-SearchBot", allowed=False, detail="Blocked"),
        BotAccessResult(bot="ChatGPT-User", allowed=False, detail="Blocked"),
        BotAccessResult(bot="Google-Extended", allowed=False, detail="Blocked"),
    ]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=False)
    schema_org = SchemaReport(
        blocks_found=1,
        schemas=[SchemaOrgResult(schema_type="WebSite", properties=["name"])],
    )
    content = ContentReport(word_count=500, has_headings=True, has_lists=True)

    robots, llms_txt, schema_org, content, overall = compute_scores(
        robots, llms_txt, schema_org, content
    )

    # Robots: round(25 * 3/7, 1) = 10.7
    assert robots.score == 10.7
    assert llms_txt.score == 0
    # Schema: 8 + 3 (WebSite=standard) = 11
    assert schema_org.score == 11
    # Content: 15 (400+ words) + 7 (headings) + 5 (lists) = 27
    assert content.score == 27
    assert overall == 10.7 + 0 + 11 + 27


# -- check_robots (async, mocked HTTP) ----------------------------------------


@pytest.mark.asyncio
async def test_check_robots_returns_tuple():
    """check_robots should return (RobotsReport, raw_robots_text | None)."""
    robots_txt = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /private\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, raw_text = await check_robots("https://example.com/page", mock_client)

    assert isinstance(report, RobotsReport)
    assert report.found is True
    assert len(report.bots) == 13  # all AI_BOTS checked
    assert raw_text == robots_txt


@pytest.mark.asyncio
async def test_check_robots_not_found():
    """check_robots should handle missing robots.txt gracefully."""
    mock_response = AsyncMock()
    mock_response.status_code = 404

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, raw_text = await check_robots("https://example.com", mock_client)

    assert isinstance(report, RobotsReport)
    assert report.found is False
    assert raw_text is None


@pytest.mark.asyncio
async def test_check_robots_http_error():
    """check_robots should handle HTTP errors without raising."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    report, raw_text = await check_robots("https://example.com", mock_client)

    assert isinstance(report, RobotsReport)
    assert report.found is False
    assert raw_text is None
