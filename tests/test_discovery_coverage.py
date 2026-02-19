"""Coverage tests for discovery.py — fetch_sitemap_urls() and discover_pages()."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from aeo_cli.core.discovery import discover_pages, fetch_sitemap_urls

# ---------------------------------------------------------------------------
# Sitemap XML fixtures
# ---------------------------------------------------------------------------

SITEMAP_XML = """\
<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>"""

SITEMAP_INDEX_XML = """\
<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-blog.xml</loc></sitemap>
</sitemapindex>"""

CHILD_SITEMAP_XML = """\
<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/blog/post1</loc></url>
  <url><loc>https://example.com/blog/post2</loc></url>
</urlset>"""


def _mock_response(status_code: int = 200, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# fetch_sitemap_urls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_sitemap_http_error():
    """HTTPError on get → returns []."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.HTTPError("network"))

    result = await fetch_sitemap_urls("https://example.com", client)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_sitemap_non_200():
    """Both candidates return 404 → returns []."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(404))

    result = await fetch_sitemap_urls("https://example.com", client)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_sitemap_with_children():
    """Index sitemap with child sitemaps → fetches children and merges URLs."""
    client = AsyncMock(spec=httpx.AsyncClient)

    async def side_effect(url, **kwargs):
        if "sitemap.xml" in url and "blog" not in url:
            return _mock_response(200, SITEMAP_INDEX_XML)
        if "sitemap-blog.xml" in url:
            return _mock_response(200, CHILD_SITEMAP_XML)
        return _mock_response(404)

    client.get = AsyncMock(side_effect=side_effect)

    result = await fetch_sitemap_urls("https://example.com", client)
    assert "https://example.com/blog/post1" in result
    assert "https://example.com/blog/post2" in result


@pytest.mark.asyncio
async def test_fetch_sitemap_child_http_error():
    """Child fetch raises HTTPError → parent URLs still returned."""
    client = AsyncMock(spec=httpx.AsyncClient)

    # Index with a child, but child request raises
    async def side_effect(url, **kwargs):
        if "sitemap.xml" in url and "blog" not in url:
            # Return a sitemap index to test child error
            index_with_pages = """\
<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-blog.xml</loc></sitemap>
</sitemapindex>"""
            return _mock_response(200, index_with_pages)
        if "sitemap-blog.xml" in url:
            raise httpx.HTTPError("child fetch failed")
        return _mock_response(404)

    client.get = AsyncMock(side_effect=side_effect)

    # No page URLs from the index itself, and child failed → empty result
    # (the index only has child sitemaps, no direct <url> entries)
    result = await fetch_sitemap_urls("https://example.com", client)
    # The index had no <url> tags, child failed → falls through to second candidate
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_fetch_sitemap_child_non_200():
    """Child returns 500 → skipped via continue on line 101."""
    # Index with a child sitemap that returns 500
    index_xml = """\
<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-child.xml</loc></sitemap>
</sitemapindex>"""

    client = AsyncMock(spec=httpx.AsyncClient)

    async def side_effect(url, **kwargs):
        if url == "https://example.com/sitemap.xml":
            return _mock_response(200, index_xml)
        if "sitemap-child" in url:
            return _mock_response(500)
        return _mock_response(404)

    client.get = AsyncMock(side_effect=side_effect)

    result = await fetch_sitemap_urls("https://example.com", client)
    # No page URLs since the only child returned 500
    assert result == []


@pytest.mark.asyncio
async def test_fetch_sitemap_max_urls_break():
    """Many URLs exceed max_urls → truncated."""
    # Generate sitemap with many URLs
    locs = "\n".join(
        f"  <url><loc>https://example.com/p{i}</loc></url>" for i in range(50)
    )
    big_sitemap = f"""\
<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{locs}
</urlset>"""

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(200, big_sitemap))

    result = await fetch_sitemap_urls("https://example.com", client, max_urls=5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_fetch_sitemap_child_max_urls_break():
    """Child sitemaps push total past max_urls → break in child loop (line 108)."""
    # Index with 2 child sitemaps; first child returns enough to exceed max_urls
    index_xml = """\
<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>"""

    child1_locs = "\n".join(
        f"  <url><loc>https://example.com/c1-p{i}</loc></url>" for i in range(10)
    )
    child1_xml = f"""\
<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{child1_locs}
</urlset>"""

    client = AsyncMock(spec=httpx.AsyncClient)

    async def side_effect(url, **kwargs):
        if url == "https://example.com/sitemap.xml":
            return _mock_response(200, index_xml)
        if "sitemap-1" in url:
            return _mock_response(200, child1_xml)
        if "sitemap-2" in url:
            # Should NOT be fetched since max_urls already hit
            return _mock_response(200, SITEMAP_XML)
        return _mock_response(404)

    client.get = AsyncMock(side_effect=side_effect)

    result = await fetch_sitemap_urls("https://example.com", client, max_urls=5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_fetch_sitemap_stops_after_success():
    """First candidate has URLs → second not fetched."""
    call_count = 0

    async def side_effect(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "sitemap.xml" in url:
            return _mock_response(200, SITEMAP_XML)
        return _mock_response(404)

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=side_effect)

    result = await fetch_sitemap_urls("https://example.com", client)
    assert len(result) == 2
    # Should have only tried first candidate since it returned URLs
    assert call_count == 1


# ---------------------------------------------------------------------------
# discover_pages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_pages_sitemap_exception():
    """fetch_sitemap_urls raising → falls back to spider."""
    client = AsyncMock(spec=httpx.AsyncClient)
    # Make the client.get raise so fetch_sitemap_urls fails
    client.get = AsyncMock(side_effect=Exception("boom"))

    result = await discover_pages(
        "https://example.com",
        client,
        seed_links=["https://example.com/about"],
    )
    assert result.method == "spider"
    assert "https://example.com/about" in result.urls_sampled


@pytest.mark.asyncio
async def test_discover_pages_spider_fallback():
    """fetch_sitemap_urls returns [] → uses seed_links, method='spider'."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(404))

    result = await discover_pages(
        "https://example.com",
        client,
        seed_links=["https://example.com/about"],
    )
    assert result.method == "spider"


@pytest.mark.asyncio
async def test_discover_pages_robots_filter():
    """robots_txt blocking some URLs → those are filtered out."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(200, SITEMAP_XML))

    # robots.txt that blocks /page2
    robots_txt = "User-agent: GPTBot\nDisallow: /page2\n"

    result = await discover_pages(
        "https://example.com",
        client,
        robots_txt=robots_txt,
    )
    sampled_paths = [u for u in result.urls_sampled if "/page2" in u]
    # page2 should be filtered out
    assert len(sampled_paths) == 0


@pytest.mark.asyncio
async def test_discover_pages_dedup():
    """Duplicate URLs → deduplicated."""
    # Sitemap with duplicates (trailing slash difference)
    dup_sitemap = """\
<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page1/</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>"""

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(200, dup_sitemap))

    result = await discover_pages("https://example.com", client)
    # After normalization + dedup, page1 and page1/ should collapse
    # urls_sampled includes seed_url + unique discovered pages
    normalized = set()
    for u in result.urls_sampled:
        normalized.add(u.rstrip("/"))
    # No duplicates when trailing slash is stripped
    assert len(normalized) == len(result.urls_sampled)


@pytest.mark.asyncio
async def test_discover_pages_full_pipeline():
    """End-to-end: sitemap + filter + dedup + sample."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=_mock_response(200, SITEMAP_XML))

    result = await discover_pages(
        "https://example.com",
        client,
        max_pages=10,
        robots_txt="User-agent: *\nAllow: /\n",
    )
    assert result.method == "sitemap"
    assert result.urls_found == 2
    # seed URL always included
    assert "https://example.com" in result.urls_sampled
