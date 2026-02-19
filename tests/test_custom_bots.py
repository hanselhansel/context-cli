"""Tests for --bots custom bot list feature.

Validates that a custom bot list can be threaded through:
check_robots() -> audit_url() -> audit_site() -> batch -> CLI.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from context_cli.core.checks.robots import AI_BOTS, check_robots
from context_cli.main import app

runner = CliRunner()

# ── check_robots with custom bots ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_robots_custom_bots():
    """check_robots with a custom bot list should only check those bots."""
    robots_txt = "User-agent: *\nAllow: /\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, _ = await check_robots(
        "https://example.com", mock_client, bots=["MyBot", "TestBot"]
    )

    assert len(report.bots) == 2
    assert report.bots[0].bot == "MyBot"
    assert report.bots[1].bot == "TestBot"
    assert "2/2" in report.detail


@pytest.mark.asyncio
async def test_check_robots_default_bots_unchanged():
    """check_robots without bots param should use all default AI_BOTS."""
    robots_txt = "User-agent: *\nAllow: /\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, _ = await check_robots("https://example.com", mock_client)

    assert len(report.bots) == len(AI_BOTS)


@pytest.mark.asyncio
async def test_check_robots_single_custom_bot_blocked():
    """Custom bot list with one blocked bot."""
    robots_txt = "User-agent: OnlyBot\nDisallow: /\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, _ = await check_robots(
        "https://example.com", mock_client, bots=["OnlyBot"]
    )

    assert len(report.bots) == 1
    assert report.bots[0].allowed is False
    assert "0/1" in report.detail


# ── audit_url with custom bots ───────────────────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_passes_bots(mock_robots, mock_llms, mock_crawl):
    """audit_url should forward bots param to check_robots."""
    from context_cli.core.auditor import audit_url
    from context_cli.core.models import LlmsTxtReport, RobotsReport

    mock_robots.return_value = (
        RobotsReport(found=True, detail="1/1 AI bots allowed"),
        "",
    )
    mock_llms.return_value = LlmsTxtReport(found=False, detail="Not found")
    mock_crawl.return_value = AsyncMock(
        success=False, html="", markdown="", error="test"
    )

    custom = ["CustomBot"]
    await audit_url("https://example.com", bots=custom)

    # check_robots should have been called with bots=custom
    _, kwargs = mock_robots.call_args
    assert kwargs.get("bots") == custom


# ── audit_site with custom bots ──────────────────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("context_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("context_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("context_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_passes_bots(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_pages
):
    """audit_site should forward bots param to check_robots."""
    from context_cli.core.auditor import audit_site
    from context_cli.core.models import DiscoveryResult, LlmsTxtReport, RobotsReport

    mock_robots.return_value = (
        RobotsReport(found=True, detail="1/1 AI bots allowed"),
        "",
    )
    mock_llms.return_value = LlmsTxtReport(found=False, detail="Not found")
    mock_crawl.return_value = AsyncMock(
        success=False, html="", markdown="", error="test", internal_links=[]
    )
    mock_discover.return_value = DiscoveryResult(
        method="test", urls_sampled=[], detail="test"
    )
    mock_pages.return_value = []

    custom = ["SiteBot"]
    await audit_site("https://example.com", bots=custom)

    _, kwargs = mock_robots.call_args
    assert kwargs.get("bots") == custom


# ── batch with custom bots ───────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.core.batch.audit_url", new_callable=AsyncMock)
async def test_batch_audit_passes_bots(mock_audit_url):
    """run_batch_audit should forward bots to audit_url."""
    from context_cli.core.batch import run_batch_audit
    from context_cli.core.models import (
        AuditReport,
        ContentReport,
        LlmsTxtReport,
        RobotsReport,
        SchemaReport,
    )

    mock_audit_url.return_value = AuditReport(
        url="https://example.com",
        overall_score=50,
        robots=RobotsReport(found=True, detail="ok"),
        llms_txt=LlmsTxtReport(found=False, detail="nope"),
        schema_org=SchemaReport(detail="none"),
        content=ContentReport(detail="ok"),
    )

    custom = ["BatchBot"]
    await run_batch_audit(
        ["https://example.com"], single=True, bots=custom
    )

    _, kwargs = mock_audit_url.call_args
    assert kwargs.get("bots") == custom


# ── CLI --bots flag ──────────────────────────────────────────────────────────


@patch("context_cli.cli.audit._run_audit")
def test_cli_bots_flag_parsed(mock_run_audit):
    """CLI --bots flag should parse comma-separated string into a list."""
    from context_cli.core.models import (
        AuditReport,
        ContentReport,
        LlmsTxtReport,
        RobotsReport,
        SchemaReport,
    )

    mock_run_audit.return_value = AuditReport(
        url="https://example.com",
        overall_score=50,
        robots=RobotsReport(found=True, detail="ok"),
        llms_txt=LlmsTxtReport(found=False, detail="nope"),
        schema_org=SchemaReport(detail="none"),
        content=ContentReport(detail="ok"),
    )

    result = runner.invoke(app, ["lint", "https://example.com", "--bots", "BotA,BotB"])
    assert result.exit_code == 0

    _, kwargs = mock_run_audit.call_args
    assert kwargs.get("bots") == ["BotA", "BotB"]


@patch("context_cli.cli.audit._run_audit")
def test_cli_no_bots_flag_passes_none(mock_run_audit):
    """Without --bots flag, bots=None should be passed."""
    from context_cli.core.models import (
        AuditReport,
        ContentReport,
        LlmsTxtReport,
        RobotsReport,
        SchemaReport,
    )

    mock_run_audit.return_value = AuditReport(
        url="https://example.com",
        overall_score=50,
        robots=RobotsReport(found=True, detail="ok"),
        llms_txt=LlmsTxtReport(found=False, detail="nope"),
        schema_org=SchemaReport(detail="none"),
        content=ContentReport(detail="ok"),
    )

    result = runner.invoke(app, ["lint", "https://example.com"])
    assert result.exit_code == 0

    _, kwargs = mock_run_audit.call_args
    assert kwargs.get("bots") is None
