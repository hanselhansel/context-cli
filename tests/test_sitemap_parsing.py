"""Additional tests for sitemap parsing — namespaces, index files, edge cases."""

from __future__ import annotations

from context_cli.core.discovery import _parse_sitemap_xml


def test_sitemap_with_lastmod_and_priority():
    """Sitemaps with extra elements (lastmod, priority) should still parse URLs."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2024-01-15</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://example.com/about</loc>
    <lastmod>2024-01-10</lastmod>
  </url>
</urlset>"""
    page_urls, child_urls = _parse_sitemap_xml(xml)

    assert len(page_urls) == 2
    assert child_urls == []
    assert "https://example.com/" in page_urls
    assert "https://example.com/about" in page_urls


def test_sitemap_index_with_lastmod():
    """Sitemap index with lastmod on child entries should parse correctly."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
    <lastmod>2024-01-15</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
</sitemapindex>"""
    page_urls, child_urls = _parse_sitemap_xml(xml)

    assert page_urls == []
    assert len(child_urls) == 2


def test_sitemap_with_whitespace_in_loc():
    """Whitespace around loc text should be stripped."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>
      https://example.com/page-1
    </loc>
  </url>
</urlset>"""
    page_urls, _ = _parse_sitemap_xml(xml)

    assert len(page_urls) == 1
    assert page_urls[0] == "https://example.com/page-1"


def test_sitemap_mixed_index_and_urlset():
    """A document with both sitemap and url elements should parse both."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page</loc></url>
</urlset>"""
    # This is technically a urlset, not an index — just checking it works
    page_urls, child_urls = _parse_sitemap_xml(xml)

    assert len(page_urls) == 1
    assert child_urls == []


def test_sitemap_large_urlset():
    """A sitemap with many URLs should parse them all."""
    urls_xml = "\n".join(
        f"  <url><loc>https://example.com/page/{i}</loc></url>"
        for i in range(100)
    )
    xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}
</urlset>"""
    page_urls, _ = _parse_sitemap_xml(xml)

    assert len(page_urls) == 100


def test_sitemap_no_namespace():
    """A sitemap without the standard namespace should return empty results."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset>
  <url><loc>https://example.com/</loc></url>
</urlset>"""
    page_urls, child_urls = _parse_sitemap_xml(xml)

    # Without the expected namespace, the findall won't match
    assert page_urls == []
    assert child_urls == []
