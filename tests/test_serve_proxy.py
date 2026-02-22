"""Comprehensive tests for the markdown reverse-proxy server."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from context_cli.core.serve.proxy import (
    _SOURCE_HEADER,
    _SOURCE_VALUE,
    _build_upstream_url,
    _filter_headers,
    _is_html,
    _wants_markdown,
    create_proxy_app,
    run_proxy,
)

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

SIMPLE_HTML = "<html><body><h1>Hello</h1><p>World</p></body></html>"


@pytest.fixture
def proxy_app():
    """Create a proxy app pointing at a dummy upstream."""
    return create_proxy_app("http://upstream.test")


@pytest.fixture
async def proxy_client(proxy_app):
    """Create an aiohttp test client for the proxy app."""
    server = TestServer(proxy_app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


def _make_httpx_response(
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    text: str = "",
    content: bytes | None = None,
) -> MagicMock:
    """Build a mock httpx.Response with the given attributes."""
    resp = MagicMock()
    resp.status_code = status_code
    _headers = headers or {}
    resp.headers = httpx.Headers(_headers)
    resp.text = text
    resp.content = content if content is not None else text.encode()
    return resp


# ---------------------------------------------------------------------------
# Unit tests: _wants_markdown
# ---------------------------------------------------------------------------


class TestWantsMarkdown:
    """Tests for the _wants_markdown helper."""

    def test_accept_text_markdown(self):
        """Request with Accept: text/markdown returns True."""
        req = MagicMock()
        req.headers = {"Accept": "text/markdown"}
        assert _wants_markdown(req) is True

    def test_accept_with_quality(self):
        """Accept header with quality factor still matches."""
        req = MagicMock()
        req.headers = {"Accept": "text/markdown;q=0.9, text/html"}
        assert _wants_markdown(req) is True

    def test_accept_html_only(self):
        """Request wanting only HTML returns False."""
        req = MagicMock()
        req.headers = {"Accept": "text/html"}
        assert _wants_markdown(req) is False

    def test_no_accept_header(self):
        """Missing Accept header returns False."""
        req = MagicMock()
        req.headers = {}
        assert _wants_markdown(req) is False

    def test_accept_wildcard(self):
        """Wildcard does not count as text/markdown."""
        req = MagicMock()
        req.headers = {"Accept": "*/*"}
        assert _wants_markdown(req) is False


# ---------------------------------------------------------------------------
# Unit tests: _is_html
# ---------------------------------------------------------------------------


class TestIsHtml:
    """Tests for the _is_html helper."""

    def test_text_html(self):
        assert _is_html("text/html") is True

    def test_text_html_charset(self):
        assert _is_html("text/html; charset=utf-8") is True

    def test_application_json(self):
        assert _is_html("application/json") is False

    def test_empty_string(self):
        assert _is_html("") is False

    def test_image_png(self):
        assert _is_html("image/png") is False


# ---------------------------------------------------------------------------
# Unit tests: _build_upstream_url
# ---------------------------------------------------------------------------


class TestBuildUpstreamUrl:
    """Tests for the _build_upstream_url helper."""

    def test_simple_path(self):
        result = _build_upstream_url("http://example.com", "/page", "")
        assert result == "http://example.com/page"

    def test_with_query_string(self):
        result = _build_upstream_url("http://example.com", "/search", "q=hello")
        assert result == "http://example.com/search?q=hello"

    def test_trailing_slash_on_upstream(self):
        result = _build_upstream_url("http://example.com/", "/page", "")
        assert result == "http://example.com/page"

    def test_root_path(self):
        result = _build_upstream_url("http://example.com", "/", "")
        assert result == "http://example.com/"

    def test_empty_path(self):
        result = _build_upstream_url("http://example.com", "", "")
        assert result == "http://example.com"


# ---------------------------------------------------------------------------
# Unit tests: _filter_headers
# ---------------------------------------------------------------------------


class TestFilterHeaders:
    """Tests for the _filter_headers helper."""

    def test_removes_hop_by_hop(self):
        headers = httpx.Headers({
            "Content-Type": "text/html",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
        })
        filtered = _filter_headers(headers)
        assert "Content-Type" in filtered or "content-type" in filtered
        assert "transfer-encoding" not in {k.lower() for k in filtered}
        assert "connection" not in {k.lower() for k in filtered}

    def test_preserves_custom_headers(self):
        headers = httpx.Headers({
            "X-Custom": "value",
            "Content-Type": "text/html",
        })
        filtered = _filter_headers(headers)
        assert filtered.get("X-Custom") == "value" or filtered.get("x-custom") == "value"

    def test_removes_content_encoding(self):
        headers = httpx.Headers({"Content-Encoding": "gzip"})
        filtered = _filter_headers(headers)
        assert "content-encoding" not in {k.lower() for k in filtered}

    def test_empty_headers(self):
        headers = httpx.Headers({})
        filtered = _filter_headers(headers)
        assert filtered == {}


# ---------------------------------------------------------------------------
# Integration tests: proxy handler via test client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_markdown_response_for_html_upstream(proxy_client):
    """Accept: text/markdown + HTML upstream -> markdown conversion."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html; charset=utf-8"},
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/page", headers={"Accept": "text/markdown"},
        )

    assert resp.status == 200
    assert "text/markdown" in resp.headers.get("Content-Type", "")
    assert resp.headers.get(_SOURCE_HEADER) == _SOURCE_VALUE
    body = await resp.text()
    # Markdown output should contain the heading text
    assert "Hello" in body


@pytest.mark.asyncio
async def test_passthrough_when_no_accept_markdown(proxy_client):
    """Without Accept: text/markdown, HTML is passed through unchanged."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html"},
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/page", headers={"Accept": "text/html"})

    assert resp.status == 200
    body = await resp.read()
    assert body == SIMPLE_HTML.encode()
    assert _SOURCE_HEADER not in resp.headers


@pytest.mark.asyncio
async def test_passthrough_json_even_with_accept_markdown(proxy_client):
    """JSON upstream is passed through even when Accept: text/markdown is set."""
    json_body = '{"key": "value"}'
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "application/json"},
        text=json_body,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/api/data", headers={"Accept": "text/markdown"},
        )

    assert resp.status == 200
    body = await resp.text()
    assert '"key"' in body
    assert _SOURCE_HEADER not in resp.headers


@pytest.mark.asyncio
async def test_passthrough_image_binary(proxy_client):
    """Binary image upstream is passed through unchanged."""
    image_bytes = b"\x89PNG\r\n\x1a\nfakepng"
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "image/png"},
        text="",
        content=image_bytes,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/image.png")

    assert resp.status == 200
    body = await resp.read()
    assert body == image_bytes


@pytest.mark.asyncio
async def test_upstream_timeout_returns_502(proxy_client):
    """Upstream timeout -> 502 Bad Gateway."""
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=httpx.TimeoutException("timed out"),
        )
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/slow-page")

    assert resp.status == 502
    body = await resp.text()
    assert "Bad Gateway" in body


@pytest.mark.asyncio
async def test_upstream_connection_error_returns_502(proxy_client):
    """Upstream connection refused -> 502 Bad Gateway."""
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused"),
        )
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/down")

    assert resp.status == 502


@pytest.mark.asyncio
async def test_x_content_source_header_present(proxy_client):
    """Markdown responses include the X-Content-Source header."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html"},
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/", headers={"Accept": "text/markdown"})

    assert resp.headers[_SOURCE_HEADER] == _SOURCE_VALUE


@pytest.mark.asyncio
async def test_x_content_source_absent_for_passthrough(proxy_client):
    """Pass-through responses do NOT include X-Content-Source."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html"},
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/", headers={"Accept": "text/html"})

    assert _SOURCE_HEADER not in resp.headers


@pytest.mark.asyncio
async def test_upstream_status_preserved(proxy_client):
    """Upstream 404 status code is forwarded to client."""
    mock_resp = _make_httpx_response(
        status_code=404,
        headers={"Content-Type": "text/html"},
        text="<html><body>Not Found</body></html>",
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/missing")

    assert resp.status == 404


@pytest.mark.asyncio
async def test_upstream_500_with_markdown_accept(proxy_client):
    """Upstream 500 with Accept: text/markdown still converts to markdown."""
    mock_resp = _make_httpx_response(
        status_code=500,
        headers={"Content-Type": "text/html"},
        text="<html><body><h1>Server Error</h1></body></html>",
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/error", headers={"Accept": "text/markdown"},
        )

    assert resp.status == 500
    body = await resp.text()
    assert "Server Error" in body
    assert resp.headers.get(_SOURCE_HEADER) == _SOURCE_VALUE


@pytest.mark.asyncio
async def test_empty_html_upstream(proxy_client):
    """Empty HTML body with Accept: text/markdown returns empty markdown."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html"},
        text="",
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/empty", headers={"Accept": "text/markdown"},
        )

    assert resp.status == 200
    body = await resp.text()
    assert body.strip() == ""


@pytest.mark.asyncio
async def test_multiple_paths_proxied(proxy_client):
    """Different paths are forwarded to different upstream URLs."""
    calls = []

    async def capture_get(url, **kwargs):
        calls.append(url)
        return _make_httpx_response(
            headers={"Content-Type": "text/html"},
            text=f"<html><body>{url}</body></html>",
        )

    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=capture_get)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        await proxy_client.get("/page-a")
        await proxy_client.get("/page-b")
        await proxy_client.get("/deep/nested/path")

    assert len(calls) == 3
    assert calls[0] == "http://upstream.test/page-a"
    assert calls[1] == "http://upstream.test/page-b"
    assert calls[2] == "http://upstream.test/deep/nested/path"


@pytest.mark.asyncio
async def test_query_string_forwarded(proxy_client):
    """Query strings are forwarded to the upstream."""
    captured_url = []

    async def capture_get(url, **kwargs):
        captured_url.append(url)
        return _make_httpx_response(
            headers={"Content-Type": "text/html"},
            text=SIMPLE_HTML,
        )

    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=capture_get)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        await proxy_client.get("/search?q=hello&page=2")

    assert captured_url[0] == "http://upstream.test/search?q=hello&page=2"


@pytest.mark.asyncio
async def test_custom_upstream_headers_preserved(proxy_client):
    """Custom upstream response headers are forwarded to the client."""
    mock_resp = _make_httpx_response(
        headers={
            "Content-Type": "text/html",
            "X-Custom-Header": "custom-value",
            "X-Request-Id": "abc-123",
        },
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/page")

    assert resp.headers.get("X-Custom-Header") == "custom-value"
    assert resp.headers.get("X-Request-Id") == "abc-123"


@pytest.mark.asyncio
async def test_content_type_overridden_for_markdown(proxy_client):
    """Content-Type is replaced with text/markdown for converted responses."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html; charset=utf-8"},
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/page", headers={"Accept": "text/markdown"},
        )

    ct = resp.headers.get("Content-Type", "")
    assert "text/markdown" in ct
    assert "charset=utf-8" in ct


# ---------------------------------------------------------------------------
# create_proxy_app tests
# ---------------------------------------------------------------------------


class TestCreateProxyApp:
    """Tests for the create_proxy_app factory."""

    def test_returns_aiohttp_app(self):
        """Factory returns an aiohttp web.Application."""
        app = create_proxy_app("http://example.com")
        assert isinstance(app, web.Application)

    def test_stores_upstream_in_app(self):
        """The upstream URL is stored in the app dict."""
        app = create_proxy_app("http://my-upstream:3000")
        assert app["upstream"] == "http://my-upstream:3000"

    def test_has_catch_all_route(self):
        """App has a catch-all route registered."""
        app = create_proxy_app("http://example.com")
        # The app should have at least one route resource
        resources = list(app.router.resources())
        assert len(resources) >= 1


# ---------------------------------------------------------------------------
# run_proxy tests
# ---------------------------------------------------------------------------


class TestRunProxy:
    """Tests for the run_proxy convenience function."""

    def test_run_proxy_calls_run_app(self):
        """run_proxy calls aiohttp.web.run_app with correct parameters."""
        with patch("context_cli.core.serve.proxy.web.run_app") as mock_run:
            with patch(
                "context_cli.core.serve.proxy.create_proxy_app",
            ) as mock_create:
                mock_app = MagicMock()
                mock_create.return_value = mock_app
                run_proxy("http://example.com", port=9090, host="127.0.0.1")

            mock_create.assert_called_once_with("http://example.com")
            mock_run.assert_called_once_with(mock_app, host="127.0.0.1", port=9090)

    def test_run_proxy_default_args(self):
        """run_proxy uses default host and port when not specified."""
        with patch("context_cli.core.serve.proxy.web.run_app"):
            with patch(
                "context_cli.core.serve.proxy.create_proxy_app",
            ) as mock_create:
                mock_create.return_value = MagicMock()
                run_proxy("http://example.com")

            mock_create.assert_called_once_with("http://example.com")


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


class TestServeCliCommand:
    """Tests for the CLI serve command registration."""

    def test_register_adds_serve_command(self):
        """register() adds a 'serve' command to the Typer app."""
        import typer

        from context_cli.cli.serve import register

        test_app = typer.Typer()
        register(test_app)

        # Check that a command named 'serve' was registered
        command_names = [
            cmd.name or cmd.callback.__name__
            for cmd in test_app.registered_commands
        ]
        assert "serve" in command_names

    def test_serve_command_has_upstream_option(self):
        """The serve command requires --upstream."""
        import typer
        from typer.testing import CliRunner

        from context_cli.cli.serve import register

        test_app = typer.Typer()
        register(test_app)
        runner = CliRunner()

        # Without --upstream, should fail
        result = runner.invoke(test_app, [])
        assert result.exit_code != 0

    def test_serve_command_invokes_run_app(self):
        """The serve command starts the proxy with correct args."""
        import typer
        from typer.testing import CliRunner

        from context_cli.cli.serve import register

        test_app = typer.Typer()
        register(test_app)
        runner = CliRunner()

        with patch("context_cli.cli.serve.create_proxy_app") as mock_create:
            with patch("context_cli.cli.serve.web.run_app") as mock_run:
                mock_create.return_value = MagicMock()
                runner.invoke(
                    test_app,
                    ["--upstream", "http://localhost:3000"],
                )

            mock_create.assert_called_once_with("http://localhost:3000")
            mock_run.assert_called_once()

    def test_serve_command_custom_port_and_host(self):
        """The serve command passes custom port and host."""
        import typer
        from typer.testing import CliRunner

        from context_cli.cli.serve import register

        test_app = typer.Typer()
        register(test_app)
        runner = CliRunner()

        with patch("context_cli.cli.serve.create_proxy_app") as mock_create:
            with patch("context_cli.cli.serve.web.run_app") as mock_run:
                mock_create.return_value = MagicMock()
                runner.invoke(
                    test_app,
                    [
                        "--upstream", "http://localhost:3000",
                        "--port", "9999",
                        "--host", "127.0.0.1",
                    ],
                )

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs["host"] == "127.0.0.1"
            assert call_kwargs.kwargs["port"] == 9999


@pytest.mark.asyncio
async def test_root_path_proxied(proxy_client):
    """Root path '/' is proxied correctly."""
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html"},
        text=SIMPLE_HTML,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get("/")

    assert resp.status == 200


@pytest.mark.asyncio
async def test_markdown_conversion_strips_scripts(proxy_client):
    """Markdown conversion strips script tags from output."""
    html_with_script = (
        "<html><body>"
        "<script>alert('xss')</script>"
        "<h1>Clean Content</h1>"
        "</body></html>"
    )
    mock_resp = _make_httpx_response(
        headers={"Content-Type": "text/html"},
        text=html_with_script,
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/page", headers={"Accept": "text/markdown"},
        )

    body = await resp.text()
    assert "alert" not in body
    assert "Clean Content" in body


@pytest.mark.asyncio
async def test_upstream_empty_content_type(proxy_client):
    """Empty Content-Type from upstream -> passthrough (not HTML)."""
    mock_resp = _make_httpx_response(
        headers={},
        text="raw data",
    )
    with patch("context_cli.core.serve.proxy.httpx.AsyncClient") as mock_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client_instance

        resp = await proxy_client.get(
            "/raw", headers={"Accept": "text/markdown"},
        )

    # Should passthrough because content-type is not HTML
    assert _SOURCE_HEADER not in resp.headers
