"""Coverage tests for audit_url(), audit_site(), and _audit_site_inner()."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from aeo_cli.core.auditor import _audit_site_inner, audit_site, audit_url
from aeo_cli.core.crawler import CrawlResult
from aeo_cli.core.models import (
    BotAccessResult,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEED = "https://example.com"


def _make_robots(found: bool = True) -> tuple[RobotsReport, str | None]:
    bots = [BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed")]
    return (
        RobotsReport(found=found, bots=bots, detail="1/1 AI bots allowed"),
        "User-agent: *\nAllow: /",
    )


def _make_llms() -> LlmsTxtReport:
    return LlmsTxtReport(found=True, url=f"{_SEED}/llms.txt", detail="Found")


def _make_crawl(success: bool = True, error: str | None = None) -> CrawlResult:
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


# ── audit_url() ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_robots_exception(mock_robots, mock_llms, mock_crawl):
    """When check_robots raises, errors should contain 'Robots check failed'."""
    mock_robots.side_effect = RuntimeError("boom")
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()

    report = await audit_url(_SEED)

    assert any("Robots check failed" in e for e in report.errors)
    assert report.robots.found is False


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_llms_txt_exception(mock_robots, mock_llms, mock_crawl):
    """When check_llms_txt raises, fallback LlmsTxtReport is used."""
    mock_robots.return_value = _make_robots()
    mock_llms.side_effect = RuntimeError("boom")
    mock_crawl.return_value = _make_crawl()

    report = await audit_url(_SEED)

    assert any("llms.txt check failed" in e for e in report.errors)
    assert report.llms_txt.found is False


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_crawl_exception(mock_robots, mock_llms, mock_crawl):
    """When extract_page raises, 'Crawl failed' should appear in errors."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.side_effect = RuntimeError("boom")

    report = await audit_url(_SEED)

    assert any("Crawl failed" in e for e in report.errors)


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_crawl_not_successful(mock_robots, mock_llms, mock_crawl):
    """A CrawlResult with success=False should append 'Crawl error: ...'."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl(success=False, error="timeout")

    report = await audit_url(_SEED)

    assert any("Crawl error: timeout" in e for e in report.errors)


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_url_happy_path(mock_robots, mock_llms, mock_crawl):
    """All pillars succeed → complete report with scores > 0."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()

    report = await audit_url(_SEED)

    assert report.errors == []
    assert report.overall_score > 0
    assert report.robots.score > 0
    assert report.llms_txt.score > 0
    assert report.content.score > 0


# ── audit_site() timeout ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_site_timeout():
    """When _audit_site_inner takes too long, audit_site returns a timeout report."""

    async def slow_inner(*args, **kwargs):
        await asyncio.sleep(10)

    with (
        patch("aeo_cli.core.auditor._audit_site_inner", side_effect=slow_inner),
        patch("aeo_cli.core.auditor.SITE_AUDIT_TIMEOUT", 0.01),
    ):
        report = await audit_site(_SEED)

    assert report.discovery.method == "timeout"
    assert any("timed out" in e.lower() for e in report.errors)


@pytest.mark.asyncio
async def test_audit_site_progress_callback():
    """When progress_callback is provided, it should be called."""
    progress_msgs: list[str] = []

    async def fake_inner(*args, **kwargs):
        # Call the progress function (6th arg)
        progress_fn = args[5]
        progress_fn("test progress")
        return SiteAuditReport(
            url=_SEED,
            domain="example.com",
            overall_score=0,
            robots=RobotsReport(found=False),
            llms_txt=LlmsTxtReport(found=False),
            schema_org=SchemaReport(),
            content=ContentReport(),
            discovery=DiscoveryResult(method="sitemap"),
        )

    with patch("aeo_cli.core.auditor._audit_site_inner", side_effect=fake_inner):
        await audit_site(_SEED, progress_callback=progress_msgs.append)

    assert "test progress" in progress_msgs


# ── _audit_site_inner() ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_happy_path(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """Full pipeline: seed + 1 additional page → 2 PageAudits."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap",
        urls_found=2,
        urls_sampled=[_SEED, f"{_SEED}/about"],
    )
    mock_batch.return_value = [
        CrawlResult(
            url=f"{_SEED}/about",
            html="<html><body>About</body></html>",
            markdown="About page " + "word " * 100,
            success=True,
        )
    ]

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    assert isinstance(report, SiteAuditReport)
    assert len(report.pages) == 2
    assert report.errors == []


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_robots_exception(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """check_robots raising → fallback RobotsReport(found=False)."""
    mock_robots.side_effect = RuntimeError("boom")
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED]
    )

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    assert report.robots.found is False
    assert any("Robots check failed" in e for e in report.errors)


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_llms_exception(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """check_llms_txt raising → fallback LlmsTxtReport(found=False)."""
    mock_robots.return_value = _make_robots()
    mock_llms.side_effect = RuntimeError("boom")
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED]
    )

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    assert report.llms_txt.found is False
    assert any("llms.txt check failed" in e for e in report.errors)


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_seed_crawl_exception(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """extract_page raising → 'Seed crawl failed' in errors."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.side_effect = RuntimeError("boom")
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED]
    )

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    assert any("Seed crawl failed" in e for e in report.errors)


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_seed_crawl_failed(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """extract_page returns success=False → error appended, no PageAudit for seed."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = CrawlResult(
        url=_SEED, html="", markdown="", success=False, error="connection reset"
    )
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED]
    )

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    assert any("Seed crawl error" in e for e in report.errors)
    # No PageAudit for the failed seed
    assert not any(p.url == _SEED and not p.errors for p in report.pages)


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_batch_failed_pages(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """A failed CrawlResult in batch → PageAudit with errors."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap",
        urls_sampled=[_SEED, f"{_SEED}/broken"],
    )
    mock_batch.return_value = [
        CrawlResult(
            url=f"{_SEED}/broken",
            html="",
            markdown="",
            success=False,
            error="500 Internal Server Error",
        )
    ]

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    broken_pages = [p for p in report.pages if p.url == f"{_SEED}/broken"]
    assert len(broken_pages) == 1
    assert broken_pages[0].errors


@pytest.mark.asyncio
@patch("aeo_cli.core.auditor.extract_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.discover_pages", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.extract_page", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_llms_txt", new_callable=AsyncMock)
@patch("aeo_cli.core.auditor.check_robots", new_callable=AsyncMock)
async def test_audit_site_inner_no_remaining_urls(
    mock_robots, mock_llms, mock_crawl, mock_discover, mock_batch
):
    """discover_pages returns only seed_url → extract_pages NOT called."""
    mock_robots.return_value = _make_robots()
    mock_llms.return_value = _make_llms()
    mock_crawl.return_value = _make_crawl()
    mock_discover.return_value = DiscoveryResult(
        method="sitemap", urls_sampled=[_SEED]
    )

    errors: list[str] = []
    report = await _audit_site_inner(_SEED, "example.com", 10, 0.0, errors, lambda _: None)

    mock_batch.assert_not_called()
    assert len(report.pages) == 1
