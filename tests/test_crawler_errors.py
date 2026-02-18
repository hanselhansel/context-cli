"""Tests for crawler error handling (timeout, DNS failure, SSL error)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aeo_cli.core.crawler import extract_page


@pytest.mark.asyncio
async def test_crawl4ai_import_error():
    """If crawl4ai is not installed, extract_page should return a failed CrawlResult."""
    with patch.dict("sys.modules", {"crawl4ai": None}):
        with patch("aeo_cli.core.crawler.AsyncWebCrawler", side_effect=ImportError("No module")):
            pass
    # Simulate import failure by patching the import inside extract_page
    with patch("builtins.__import__", side_effect=ImportError("No module named 'crawl4ai'")):
        result = await extract_page("https://example.com")

    assert result.success is False
    assert result.error is not None
    assert "crawl4ai" in result.error.lower() or "module" in result.error.lower()


@pytest.mark.asyncio
async def test_crawler_generic_exception():
    """A generic exception during crawl should be captured, not raised."""
    with patch("aeo_cli.core.crawler.AsyncWebCrawler") as mock_cls:
        mock_crawler = AsyncMock()
        mock_crawler.arun.side_effect = RuntimeError("Browser crashed")
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await extract_page("https://example.com")

    assert result.success is False
    assert "Browser crashed" in result.error


@pytest.mark.asyncio
async def test_crawler_returns_failed_result():
    """crawl4ai returning success=False should propagate to CrawlResult."""
    mock_result = MagicMock()
    mock_result.success = False
    mock_result.html = ""
    mock_result.markdown = ""
    mock_result.links = {}

    with patch("aeo_cli.core.crawler.AsyncWebCrawler") as mock_cls:
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await extract_page("https://example.com")

    assert result.success is False


@pytest.mark.asyncio
async def test_crawler_successful_extraction():
    """A successful crawl should return HTML, markdown, and internal links."""
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.html = "<html><body>Hello</body></html>"
    mock_result.markdown = "Hello"
    mock_result.links = {
        "internal": [{"href": "/about"}, {"href": "/blog"}],
        "external": [{"href": "https://other.com"}],
    }

    with patch("aeo_cli.core.crawler.AsyncWebCrawler") as mock_cls:
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await extract_page("https://example.com")

    assert result.success is True
    assert result.html == "<html><body>Hello</body></html>"
    assert result.markdown == "Hello"
    assert result.internal_links is not None
    assert len(result.internal_links) == 2
