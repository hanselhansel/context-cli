"""Tests for the page discovery module (sitemap parsing, URL selection, normalisation)."""

from __future__ import annotations

from context_cli.core.discovery import _parse_sitemap_xml, normalize_url, select_diverse_pages

# -- _parse_sitemap_xml --------------------------------------------------------


def test_parse_sitemap_xml_basic():
    """A simple urlset sitemap should return page URLs and no child sitemaps."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/blog/post-1</loc></url>
</urlset>"""
    page_urls, child_urls = _parse_sitemap_xml(xml)
    assert len(page_urls) == 3
    assert child_urls == []
    assert "https://example.com/" in page_urls
    assert "https://example.com/blog/post-1" in page_urls


def test_parse_sitemap_xml_index():
    """A sitemapindex document should return child sitemap URLs, not page URLs."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-posts.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>"""
    page_urls, child_urls = _parse_sitemap_xml(xml)
    assert page_urls == []
    assert len(child_urls) == 2
    assert "https://example.com/sitemap-posts.xml" in child_urls


def test_parse_sitemap_xml_empty():
    """Empty string should return empty lists without raising."""
    page_urls, child_urls = _parse_sitemap_xml("")
    assert page_urls == []
    assert child_urls == []


def test_parse_sitemap_xml_malformed():
    """Malformed XML should return empty lists without raising."""
    page_urls, child_urls = _parse_sitemap_xml("<not valid xml>><>")
    assert page_urls == []
    assert child_urls == []


# -- normalize_url -------------------------------------------------------------


def test_normalize_url_strips_fragment():
    """Fragments (#section) should be removed."""
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_url_strips_trailing_slash():
    """Trailing slashes should be removed (root stays as /)."""
    assert normalize_url("https://example.com/about/") == "https://example.com/about"


def test_normalize_url_lowercases_scheme_and_host():
    """Scheme and host should be lowercased."""
    assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"


def test_normalize_url_root():
    """Root URL should normalize to scheme://host/."""
    assert normalize_url("https://example.com") == "https://example.com/"
    assert normalize_url("https://example.com/") == "https://example.com/"


# -- select_diverse_pages ------------------------------------------------------


def test_select_diverse_pages_includes_seed():
    """The seed URL should always be the first element."""
    urls = [
        "https://example.com/blog/a",
        "https://example.com/about",
        "https://example.com/products/x",
    ]
    seed = "https://example.com/"
    result = select_diverse_pages(urls, seed, max_pages=5)
    assert result[0] == seed


def test_select_diverse_pages_diversity():
    """URLs from different path segments should all appear in the sample."""
    urls = [
        "https://example.com/blog/post-1",
        "https://example.com/blog/post-2",
        "https://example.com/products/widget",
        "https://example.com/products/gadget",
        "https://example.com/about",
        "https://example.com/docs/intro",
    ]
    seed = "https://example.com/"
    result = select_diverse_pages(urls, seed, max_pages=5)

    # Should pick from multiple segments, not just fill up with /blog
    segments = set()
    for u in result[1:]:  # skip seed
        from urllib.parse import urlparse

        path = urlparse(u).path.strip("/")
        seg = path.split("/")[0] if path else ""
        segments.add(seg)

    # With 4 non-seed slots and 4 groups (blog, products, about, docs),
    # we expect at least 3 different segments
    assert len(segments) >= 3


def test_select_diverse_pages_respects_max_pages():
    """Result should never exceed max_pages."""
    urls = [f"https://example.com/page/{i}" for i in range(50)]
    seed = "https://example.com/"
    result = select_diverse_pages(urls, seed, max_pages=5)
    assert len(result) <= 5
    assert result[0] == seed


def test_select_diverse_pages_max_one():
    """max_pages=1 should return only the seed URL."""
    urls = ["https://example.com/a", "https://example.com/b"]
    seed = "https://example.com/"
    result = select_diverse_pages(urls, seed, max_pages=1)
    assert result == [seed]


def test_select_diverse_pages_deduplicates_seed():
    """If seed_url appears in the urls list, it should not be duplicated."""
    seed = "https://example.com/"
    urls = [seed, "https://example.com/about", "https://example.com/blog"]
    result = select_diverse_pages(urls, seed, max_pages=10)
    # seed should appear exactly once
    assert result.count(seed) == 1
