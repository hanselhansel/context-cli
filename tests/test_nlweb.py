"""Tests for NLWeb support detection check."""

from __future__ import annotations

import httpx
import pytest

from context_cli.core.checks.nlweb import check_nlweb

NLWEB_SCHEMA_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "NLWebEndpoint",
    "name": "Search",
    "url": "https://example.com/nlweb"
}
</script>
</head><body></body></html>
"""

NLWEB_ACTION_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "potentialAction": {
        "@type": "NLSearchAction",
        "target": "https://example.com/search?q={query}"
    }
}
</script>
</head><body></body></html>
"""

NO_NLWEB_HTML = """
<html><head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Example"
}
</script>
</head><body></body></html>
"""


def _make_client(handler):
    """Create an httpx.AsyncClient with a mock transport."""
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_nlweb_full_score():
    """Test well-known found + schema extensions → score=1."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "/.well-known/nlweb" in str(request.url):
            return httpx.Response(200, text='{"endpoint": "https://example.com/nlweb"}')
        return httpx.Response(200)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html=NLWEB_SCHEMA_HTML)

    assert report.found is True
    assert report.well_known_found is True
    assert report.schema_extensions is True
    assert report.score == 1.0
    assert "/.well-known/nlweb found" in report.detail
    assert "NLWeb schema extensions found" in report.detail


@pytest.mark.asyncio
async def test_nlweb_well_known_only():
    """Test well-known found only → score=0.5."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "/.well-known/nlweb" in str(request.url):
            return httpx.Response(200, text="{}")
        return httpx.Response(200)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html=NO_NLWEB_HTML)

    assert report.found is True
    assert report.well_known_found is True
    assert report.schema_extensions is False
    assert report.score == 0.5
    assert "/.well-known/nlweb found" in report.detail


@pytest.mark.asyncio
async def test_nlweb_schema_only():
    """Test schema extensions only → score=0.5."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html=NLWEB_ACTION_HTML)

    assert report.found is True
    assert report.well_known_found is False
    assert report.schema_extensions is True
    assert report.score == 0.5
    assert "NLWeb schema extensions found" in report.detail


@pytest.mark.asyncio
async def test_nlweb_not_found():
    """Test no NLWeb support → score=0."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html=NO_NLWEB_HTML)

    assert report.found is False
    assert report.well_known_found is False
    assert report.schema_extensions is False
    assert report.score == 0
    assert "No NLWeb support detected" in report.detail


@pytest.mark.asyncio
async def test_nlweb_network_error():
    """Test network error for well-known returns safe default (no crash)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client)

    assert report.found is False
    assert report.well_known_found is False
    assert report.score == 0
    assert "No NLWeb support detected" in report.detail


@pytest.mark.asyncio
async def test_nlweb_empty_html():
    """Test empty HTML with 404 well-known → score=0."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html="")

    assert report.found is False
    assert report.score == 0
    assert "No NLWeb support detected" in report.detail


@pytest.mark.asyncio
async def test_nlweb_invalid_jsonld():
    """Test invalid JSON-LD is skipped gracefully."""
    html = """
    <html><head>
    <script type="application/ld+json">NOT VALID JSON</script>
    </head><body></body></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html=html)

    assert report.found is False
    assert report.score == 0


@pytest.mark.asyncio
async def test_nlweb_non_dict_jsonld_items():
    """Test JSON-LD with non-dict items in array is skipped."""
    html = """
    <html><head>
    <script type="application/ld+json">
    ["just a string", 42, null]
    </script>
    </head><body></body></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _make_client(handler) as client:
        report = await check_nlweb("https://example.com", client, html=html)

    assert report.found is False
    assert report.score == 0
