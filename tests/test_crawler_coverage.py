"""Coverage tests for crawler.py — link filtering, markdown compat, extract_pages()."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aeo_cli.core.crawler import (
    CrawlResult,
    _extract_internal_links_bs4,
    _normalize_links,
    extract_page,
    extract_pages,
)

# ---------------------------------------------------------------------------
# _extract_internal_links_bs4
# ---------------------------------------------------------------------------


def test_bs4_links_non_http_scheme():
    """mailto: and javascript: links should be filtered out."""
    html = """
    <html><body>
      <a href="mailto:x@y.com">Email</a>
      <a href="javascript:void(0)">Click</a>
      <a href="https://example.com/ok">OK</a>
    </body></html>
    """
    links = _extract_internal_links_bs4(html, "https://example.com")
    assert links == ["https://example.com/ok"]


# ---------------------------------------------------------------------------
# _normalize_links
# ---------------------------------------------------------------------------


def test_normalize_links_cross_domain():
    """Cross-domain links should be filtered out."""
    raw = [
        {"href": "https://other.com/page"},
        {"href": "https://example.com/local"},
    ]
    result = _normalize_links(raw, "https://example.com")
    assert result == ["https://example.com/local"]


def test_normalize_links_non_http_scheme():
    """Non-HTTP schemes (mailto, javascript, ftp) should be filtered out."""
    raw = [
        {"href": "mailto:user@example.com"},
        {"href": "javascript:void(0)"},
        {"href": "ftp://example.com/file"},
        {"href": "https://example.com/valid"},
    ]
    result = _normalize_links(raw, "https://example.com")
    assert result == ["https://example.com/valid"]


# ---------------------------------------------------------------------------
# extract_page — markdown compat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_page_markdown_object_compat():
    """When result.markdown has .raw_markdown attr, it should be used."""
    mock_md = MagicMock()
    mock_md.raw_markdown = "# Hello from raw"
    # Ensure hasattr(md, "raw_markdown") is True
    type(mock_md).raw_markdown = "# Hello from raw"

    mock_result = MagicMock()
    mock_result.markdown = mock_md
    mock_result.html = "<html><body>hi</body></html>"
    mock_result.success = True
    mock_result.links = {"internal": []}

    mock_crawler = AsyncMock()
    mock_crawler.arun = AsyncMock(return_value=mock_result)
    mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
    mock_crawler.__aexit__ = AsyncMock(return_value=False)

    with patch("crawl4ai.AsyncWebCrawler", return_value=mock_crawler):
        result = await extract_page("https://example.com")

    assert result.success is True
    assert result.markdown == "# Hello from raw"


@pytest.mark.asyncio
async def test_extract_page_markdown_non_string():
    """When result.markdown is None with no raw_markdown, md becomes ''."""
    mock_result = MagicMock()
    mock_result.markdown = None
    mock_result.html = "<html></html>"
    mock_result.success = True
    mock_result.links = {"internal": []}
    # Ensure hasattr(None, "raw_markdown") is False — it is by default

    mock_crawler = AsyncMock()
    mock_crawler.arun = AsyncMock(return_value=mock_result)
    mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
    mock_crawler.__aexit__ = AsyncMock(return_value=False)

    with patch("crawl4ai.AsyncWebCrawler", return_value=mock_crawler):
        result = await extract_page("https://example.com")

    assert result.markdown == ""


@pytest.mark.asyncio
async def test_extract_page_bs4_fallback_links():
    """When result.links is not a dict, fall back to BS4 extraction."""
    mock_result = MagicMock()
    mock_result.markdown = "page content"
    mock_result.html = '<html><body><a href="/about">About</a></body></html>'
    mock_result.success = True
    # links is a list, not a dict → triggers fallback
    mock_result.links = []

    mock_crawler = AsyncMock()
    mock_crawler.arun = AsyncMock(return_value=mock_result)
    mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
    mock_crawler.__aexit__ = AsyncMock(return_value=False)

    with patch("crawl4ai.AsyncWebCrawler", return_value=mock_crawler):
        result = await extract_page("https://example.com")

    assert result.internal_links is not None
    assert "https://example.com/about" in result.internal_links


@pytest.mark.asyncio
async def test_extract_page_link_exception_silent():
    """When link extraction raises, it should be silently caught."""

    class BadResult:
        html = "<html></html>"
        markdown = "hello"
        success = True

        @property
        def links(self):
            raise RuntimeError("link error")

    mock_crawler = AsyncMock()
    mock_crawler.arun = AsyncMock(return_value=BadResult())
    mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
    mock_crawler.__aexit__ = AsyncMock(return_value=False)

    with patch("crawl4ai.AsyncWebCrawler", return_value=mock_crawler):
        result = await extract_page("https://example.com")

    # Should succeed despite link error
    assert result.success is True
    assert result.internal_links is None


# ---------------------------------------------------------------------------
# extract_pages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("aeo_cli.core.crawler.extract_page", new_callable=AsyncMock)
async def test_extract_pages_basic(mock_ep):
    """Two URLs → two results in order."""
    mock_ep.side_effect = [
        CrawlResult(url="https://a.com", html="<a>", markdown="a", success=True),
        CrawlResult(url="https://b.com", html="<b>", markdown="b", success=True),
    ]
    results = await extract_pages(["https://a.com", "https://b.com"], delay_seconds=0)
    assert len(results) == 2
    assert results[0].url == "https://a.com"
    assert results[1].url == "https://b.com"


@pytest.mark.asyncio
@patch("aeo_cli.core.crawler.extract_page", new_callable=AsyncMock)
async def test_extract_pages_timeout(mock_ep):
    """When extract_page hangs, timeout → CrawlResult(success=False)."""

    async def hang(*args, **kwargs):
        await asyncio.sleep(100)

    mock_ep.side_effect = hang
    results = await extract_pages(
        ["https://slow.com"], delay_seconds=0, per_page_timeout=0.01
    )
    assert len(results) == 1
    assert results[0].success is False
    assert "Timed out" in (results[0].error or "")


@pytest.mark.asyncio
@patch("aeo_cli.core.crawler.extract_page", new_callable=AsyncMock)
async def test_extract_pages_exception(mock_ep):
    """When extract_page raises, → CrawlResult(success=False)."""
    mock_ep.side_effect = RuntimeError("kaboom")
    results = await extract_pages(["https://bad.com"], delay_seconds=0)
    assert len(results) == 1
    assert results[0].success is False
    assert "kaboom" in (results[0].error or "")


@pytest.mark.asyncio
@patch("aeo_cli.core.crawler.extract_page", new_callable=AsyncMock)
async def test_extract_pages_preserves_order(mock_ep):
    """Three URLs → results match input order regardless of completion time."""
    mock_ep.side_effect = [
        CrawlResult(url="https://1.com", html="", markdown="", success=True),
        CrawlResult(url="https://2.com", html="", markdown="", success=True),
        CrawlResult(url="https://3.com", html="", markdown="", success=True),
    ]
    urls = ["https://1.com", "https://2.com", "https://3.com"]
    results = await extract_pages(urls, delay_seconds=0)
    assert [r.url for r in results] == urls
