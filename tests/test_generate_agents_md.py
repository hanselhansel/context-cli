"""Tests for AGENTS.md generator module."""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest

from context_cli.core.generate.agents_md import (
    _build_agents_md,
    _build_error_agents_md,
    _extract_site_info,
    generate_agents_md,
)

SAMPLE_HTML = """\
<html>
<head>
    <title>Example Site</title>
    <meta name="description" content="An example website for testing.">
</head>
<body>
    <h1>Welcome</h1>
    <h2>About Us</h2>
    <h3>Team</h3>
    <a href="/about">About</a>
    <a href="/contact">Contact</a>
    <a href="https://external.com/foo">External</a>
</body>
</html>
"""


class TestExtractSiteInfo:
    """Tests for _extract_site_info."""

    def test_extracts_title(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        assert info["title"] == "Example Site"

    def test_extracts_description(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        assert info["description"] == "An example website for testing."

    def test_extracts_internal_links(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        links = info["links"]
        assert isinstance(links, list)
        assert "/about" in links
        assert "/contact" in links

    def test_excludes_external_links(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        links = info["links"]
        assert isinstance(links, list)
        assert "https://external.com/foo" not in links

    def test_extracts_domain(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com/page")
        assert info["domain"] == "example.com"

    def test_extracts_headings(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        headings = info["headings"]
        assert isinstance(headings, list)
        assert "Welcome" in headings
        assert "About Us" in headings
        assert "Team" in headings

    def test_no_title(self) -> None:
        html = "<html><body><p>Hello</p></body></html>"
        info = _extract_site_info(html, "https://example.com")
        assert info["title"] == ""

    def test_no_description(self) -> None:
        html = "<html><head><title>T</title></head></html>"
        info = _extract_site_info(html, "https://example.com")
        assert info["description"] == ""

    def test_deduplicates_links(self) -> None:
        html = '<html><body><a href="/a">A</a><a href="/a">A again</a></body></html>'
        info = _extract_site_info(html, "https://example.com")
        links = info["links"]
        assert isinstance(links, list)
        assert links.count("/a") == 1


class TestBuildAgentsMd:
    """Tests for _build_agents_md."""

    def test_contains_header(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert content.startswith("# AGENTS.md\n")

    def test_contains_domain(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert "**Domain**: example.com" in content

    def test_contains_allowed_actions(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert "## Allowed Actions" in content
        assert "Browse public pages" in content

    def test_contains_rate_limits(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert "## Rate Limits" in content
        assert "1 request per second" in content

    def test_contains_endpoints(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert "## Endpoints" in content
        assert "- /about" in content

    def test_no_links_shows_homepage(self) -> None:
        info: dict[str, str | list[str]] = {
            "domain": "empty.com",
            "title": "",
            "description": "",
            "links": [],
            "headings": [],
        }
        content = _build_agents_md(info)
        assert "- / (homepage)" in content

    def test_contains_data_formats(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert "## Data Formats" in content
        assert "text/html" in content

    def test_contains_authentication_section(self) -> None:
        info = _extract_site_info(SAMPLE_HTML, "https://example.com")
        content = _build_agents_md(info)
        assert "## Authentication" in content
        assert "None" in content


class TestBuildErrorAgentsMd:
    """Tests for _build_error_agents_md."""

    def test_contains_error_note(self) -> None:
        content = _build_error_agents_md("fail.com", "Connection refused")
        assert "Could not fetch site" in content
        assert "Connection refused" in content

    def test_contains_domain(self) -> None:
        content = _build_error_agents_md("fail.com", "timeout")
        assert "fail.com" in content


class TestGenerateAgentsMd:
    """Tests for generate_agents_md (async, mocked HTTP)."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self) -> None:
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, text=SAMPLE_HTML)
        )
        with patch(
            "context_cli.core.generate.agents_md.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ):
            result = await generate_agents_md("https://example.com")

        assert "# AGENTS.md" in result
        assert "example.com" in result

    @pytest.mark.asyncio
    async def test_fetch_error_returns_error_agents_md(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(handler)
        with patch(
            "context_cli.core.generate.agents_md.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ):
            result = await generate_agents_md("https://fail.example.com")

        assert "# AGENTS.md" in result
        assert "Could not fetch site" in result

    @pytest.mark.asyncio
    async def test_output_path_writes_file(self, tmp_path: object) -> None:
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)
        out = str(tmp_path / "AGENTS.md")
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, text=SAMPLE_HTML)
        )
        with patch(
            "context_cli.core.generate.agents_md.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ):
            result = await generate_agents_md(
                "https://example.com", output_path=out
            )

        assert os.path.exists(out)
        with open(out) as f:
            assert f.read() == result

    @pytest.mark.asyncio
    async def test_output_path_on_error_writes_file(
        self, tmp_path: object,
    ) -> None:
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)
        out = str(tmp_path / "subdir" / "AGENTS.md")

        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        transport = httpx.MockTransport(handler)
        with patch(
            "context_cli.core.generate.agents_md.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ):
            result = await generate_agents_md(
                "https://fail.com", output_path=out
            )

        assert os.path.exists(out)
        with open(out) as f:
            assert f.read() == result

    @pytest.mark.asyncio
    async def test_http_error_status(self) -> None:
        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, text="Server Error")
        )
        with patch(
            "context_cli.core.generate.agents_md.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ):
            result = await generate_agents_md("https://broken.com")

        assert "Could not fetch site" in result
