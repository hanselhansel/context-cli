"""Tests for spider-based discovery: link extraction and robots.txt filtering."""

from __future__ import annotations

from context_cli.core.crawler import _extract_internal_links_bs4, _normalize_links
from context_cli.core.discovery import _filter_by_robots

# -- Internal link extraction (BeautifulSoup fallback) -------------------------


def test_extract_internal_links_basic():
    """Should extract same-domain links and resolve relative URLs."""
    html = """
    <html><body>
    <a href="/about">About</a>
    <a href="/blog/post-1">Post</a>
    <a href="https://example.com/contact">Contact</a>
    <a href="https://other.com/external">External</a>
    </body></html>
    """
    links = _extract_internal_links_bs4(html, "https://example.com/")

    assert "https://example.com/about" in links
    assert "https://example.com/blog/post-1" in links
    assert "https://example.com/contact" in links
    assert "https://other.com/external" not in links


def test_extract_internal_links_deduplication():
    """Duplicate links should be deduplicated."""
    html = """
    <html><body>
    <a href="/about">About</a>
    <a href="/about">About Again</a>
    <a href="/about#section">About Section</a>
    </body></html>
    """
    links = _extract_internal_links_bs4(html, "https://example.com/")

    # /about and /about (deduped) — fragment is stripped so /about#section = /about
    about_count = sum(1 for lnk in links if "about" in lnk)
    assert about_count == 1


def test_extract_internal_links_no_links():
    """HTML without links should return empty list."""
    html = "<html><body><p>No links here</p></body></html>"
    links = _extract_internal_links_bs4(html, "https://example.com/")

    assert links == []


# -- Link normalization (crawl4ai format) --------------------------------------


def test_normalize_links_filters_external():
    """External domain links should be filtered out."""
    raw_links = [
        {"href": "/about"},
        {"href": "https://example.com/blog"},
        {"href": "https://other.com/page"},
    ]
    links = _normalize_links(raw_links, "https://example.com/")

    assert "https://example.com/about" in links
    assert "https://example.com/blog" in links
    assert len(links) == 2


def test_normalize_links_empty_href():
    """Entries with empty or missing href should be skipped."""
    raw_links = [
        {"href": ""},
        {"href": "/about"},
        {},
    ]
    links = _normalize_links(raw_links, "https://example.com/")

    assert len(links) == 1
    assert "about" in links[0]


# -- Robots.txt filtering -----------------------------------------------------


def test_filter_by_robots_allows_all():
    """No Disallow rules should allow all URLs through."""
    robots_txt = "User-agent: *\nAllow: /\n"
    urls = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/blog/post",
    ]
    filtered = _filter_by_robots(urls, robots_txt, "https://example.com")

    assert filtered == urls


def test_filter_by_robots_blocks_path():
    """Disallow: /private should filter URLs under /private."""
    robots_txt = "User-agent: GPTBot\nDisallow: /private\n"
    urls = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/private/secret",
        "https://example.com/private/data",
    ]
    filtered = _filter_by_robots(urls, robots_txt, "https://example.com")

    assert "https://example.com/" in filtered
    assert "https://example.com/about" in filtered
    assert "https://example.com/private/secret" not in filtered
    assert "https://example.com/private/data" not in filtered


def test_filter_by_robots_empty_robots():
    """Empty robots.txt should allow everything."""
    filtered = _filter_by_robots(
        ["https://example.com/a", "https://example.com/b"],
        "",
        "https://example.com",
    )

    assert len(filtered) == 2
