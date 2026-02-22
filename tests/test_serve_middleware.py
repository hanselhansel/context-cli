"""Tests for ASGI and WSGI markdown middleware."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — minimal ASGI / WSGI apps for testing
# ---------------------------------------------------------------------------

async def _html_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """Minimal ASGI app that returns HTML."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html; charset=utf-8"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"<html><body><h1>Hello</h1><p>World</p></body></html>",
        }
    )


async def _html_chunked_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns HTML in multiple chunks."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html"],
            ],
        }
    )
    # First chunk
    await send(
        {
            "type": "http.response.body",
            "body": b"<html><body><h1>Hel",
            "more_body": True,
        }
    )
    # Second chunk
    await send(
        {
            "type": "http.response.body",
            "body": b"lo</h1><p>World</p></body></html>",
            "more_body": False,
        }
    )


async def _json_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns JSON."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b'{"key": "value"}',
        }
    )


async def _plain_text_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns plain text."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/plain"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"Just plain text",
        }
    )


async def _html_404_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns HTML with 404 status."""
    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                [b"content-type", b"text/html"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"<html><body><h1>Not Found</h1></body></html>",
        }
    )


async def _empty_body_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns HTML with empty body."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"",
        }
    )


async def _no_content_type_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns response without content-type header."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"no content type",
        }
    )


async def _html_multi_header_asgi_app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI app that returns HTML with multiple headers."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html; charset=utf-8"],
                [b"x-custom", b"value"],
                [b"cache-control", b"no-cache"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"<html><body><p>Test</p></body></html>",
        }
    )


def _wsgi_html_app(environ: dict, start_response: Any) -> list[bytes]:
    """Minimal WSGI app returning HTML."""
    start_response(
        "200 OK",
        [("Content-Type", "text/html; charset=utf-8")],
    )
    return [b"<html><body><h1>Hello</h1><p>World</p></body></html>"]


def _wsgi_json_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app returning JSON."""
    start_response(
        "200 OK",
        [("Content-Type", "application/json")],
    )
    return [b'{"key": "value"}']


def _wsgi_plain_text_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app returning plain text."""
    start_response(
        "200 OK",
        [("Content-Type", "text/plain")],
    )
    return [b"Just plain text"]


def _wsgi_html_404_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app returning 404 HTML."""
    start_response(
        "404 Not Found",
        [("Content-Type", "text/html")],
    )
    return [b"<html><body><h1>Not Found</h1></body></html>"]


def _wsgi_empty_body_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app returning empty body HTML."""
    start_response(
        "200 OK",
        [("Content-Type", "text/html")],
    )
    return [b""]


def _wsgi_chunked_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app returning HTML in multiple chunks."""
    start_response(
        "200 OK",
        [("Content-Type", "text/html")],
    )
    return [
        b"<html><body><h1>Hel",
        b"lo</h1><p>World</p></body></html>",
    ]


def _wsgi_no_content_type_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app with no content-type header."""
    start_response("200 OK", [])
    return [b"no content type"]


def _wsgi_multi_header_app(environ: dict, start_response: Any) -> list[bytes]:
    """WSGI app with multiple response headers."""
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("X-Custom", "value"),
            ("Cache-Control", "no-cache"),
        ],
    )
    return [b"<html><body><p>Test</p></body></html>"]


# ---------------------------------------------------------------------------
# ASGI Middleware Helpers
# ---------------------------------------------------------------------------

def _make_http_scope(
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict:
    """Create a minimal ASGI HTTP scope."""
    return {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers or [],
    }


def _make_ws_scope() -> dict:
    """Create a minimal ASGI WebSocket scope."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [],
    }


def _make_lifespan_scope() -> dict:
    """Create a minimal ASGI lifespan scope."""
    return {
        "type": "lifespan",
    }


async def _collect_asgi_response(
    app: Any,
    scope: dict,
) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    """Run an ASGI app and collect the response.

    Returns (status, headers, body).
    """
    status = 0
    headers: list[tuple[bytes, bytes]] = []
    body_parts: list[bytes] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b""}

    async def send(message: dict) -> None:
        nonlocal status, headers
        if message["type"] == "http.response.start":
            status = message["status"]
            headers = [
                (bytes(h[0]), bytes(h[1])) for h in message.get("headers", [])
            ]
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))

    await app(scope, receive, send)
    return status, headers, b"".join(body_parts)


# ---------------------------------------------------------------------------
# WSGI Middleware Helpers
# ---------------------------------------------------------------------------

def _make_wsgi_environ(
    accept: str | None = None,
) -> dict:
    """Create a minimal WSGI environ dict."""
    environ: dict[str, Any] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.url_scheme": "http",
    }
    if accept is not None:
        environ["HTTP_ACCEPT"] = accept
    return environ


def _collect_wsgi_response(
    app: Any,
    environ: dict,
) -> tuple[str, list[tuple[str, str]], bytes]:
    """Run a WSGI app and collect the response.

    Returns (status, headers, body).
    """
    captured_status = ""
    captured_headers: list[tuple[str, str]] = []

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        nonlocal captured_status, captured_headers
        captured_status = status
        captured_headers = headers

    body_parts = list(app(environ, start_response))
    return captured_status, captured_headers, b"".join(body_parts)


# ===========================================================================
# ASGI Middleware Tests
# ===========================================================================


class TestMarkdownASGIMiddleware:
    """Tests for MarkdownASGIMiddleware."""

    @pytest.mark.asyncio
    async def test_converts_html_to_markdown_when_accept_header_present(self) -> None:
        """HTML response is converted to markdown when Accept: text/markdown."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n\nWorld\n",
        ) as mock_convert:
            status, headers, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_called_once()
        assert status == 200
        assert body == b"# Hello\n\nWorld\n"

    @pytest.mark.asyncio
    async def test_sets_content_type_to_text_markdown(self) -> None:
        """Response Content-Type is set to text/markdown; charset=utf-8."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ):
            _, headers, _ = await _collect_asgi_response(app, scope)

        header_dict = {k: v for k, v in headers}
        assert header_dict[b"content-type"] == b"text/markdown; charset=utf-8"

    @pytest.mark.asyncio
    async def test_adds_x_content_source_header(self) -> None:
        """Response has X-Content-Source: markdown-middleware header."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ):
            _, headers, _ = await _collect_asgi_response(app, scope)

        header_dict = {k: v for k, v in headers}
        assert header_dict[b"x-content-source"] == b"markdown-middleware"

    @pytest.mark.asyncio
    async def test_passthrough_when_no_accept_markdown(self) -> None:
        """HTML is passed through unchanged when no Accept: text/markdown."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/html")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            status, headers, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_not_called()
        assert status == 200
        assert b"<html>" in body

    @pytest.mark.asyncio
    async def test_passthrough_for_websocket_scope(self) -> None:
        """WebSocket scopes are passed through without interception."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        ws_messages: list[dict] = []

        async def ws_app(scope: dict, receive: Any, send: Any) -> None:
            ws_messages.append({"scope": scope})

        app = MarkdownASGIMiddleware(ws_app)
        scope = _make_ws_scope()

        await app(scope, MagicMock(), MagicMock())
        assert len(ws_messages) == 1

    @pytest.mark.asyncio
    async def test_passthrough_for_lifespan_scope(self) -> None:
        """Lifespan scopes are passed through without interception."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        lifespan_messages: list[dict] = []

        async def lifespan_app(scope: dict, receive: Any, send: Any) -> None:
            lifespan_messages.append({"scope": scope})

        app = MarkdownASGIMiddleware(lifespan_app)
        scope = _make_lifespan_scope()

        await app(scope, MagicMock(), MagicMock())
        assert len(lifespan_messages) == 1

    @pytest.mark.asyncio
    async def test_passthrough_for_json_response(self) -> None:
        """JSON responses are passed through unchanged."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_json_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            status, headers, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_not_called()
        assert body == b'{"key": "value"}'

    @pytest.mark.asyncio
    async def test_passthrough_for_plain_text_response(self) -> None:
        """Plain text responses are passed through unchanged."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_plain_text_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            status, _, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_not_called()
        assert body == b"Just plain text"

    @pytest.mark.asyncio
    async def test_preserves_status_code(self) -> None:
        """Non-200 status codes are preserved in converted response."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_404_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Not Found\n",
        ):
            status, _, body = await _collect_asgi_response(app, scope)

        assert status == 404
        assert body == b"# Not Found\n"

    @pytest.mark.asyncio
    async def test_handles_empty_body(self) -> None:
        """Empty HTML body results in empty markdown."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_empty_body_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="",
        ):
            status, _, body = await _collect_asgi_response(app, scope)

        assert status == 200
        assert body == b""

    @pytest.mark.asyncio
    async def test_buffers_streaming_chunks(self) -> None:
        """Multiple body chunks are buffered and converted together."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_chunked_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n\nWorld\n",
        ) as mock_convert:
            status, _, body = await _collect_asgi_response(app, scope)

        # The full HTML should have been passed to the converter
        call_args = mock_convert.call_args[0][0]
        assert "<h1>Hello</h1>" in call_args
        assert body == b"# Hello\n\nWorld\n"

    @pytest.mark.asyncio
    async def test_accept_markdown_among_multiple_types(self) -> None:
        """Accept header with multiple types including text/markdown triggers conversion."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/html, text/markdown, application/json")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ) as mock_convert:
            status, _, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_called_once()
        assert body == b"# Hello\n"

    @pytest.mark.asyncio
    async def test_no_accept_header_passes_through(self) -> None:
        """Request with no Accept header passes through unchanged."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_asgi_app)
        scope = _make_http_scope(headers=[])

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            status, _, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_not_called()
        assert b"<html>" in body

    @pytest.mark.asyncio
    async def test_preserves_non_content_type_headers(self) -> None:
        """Non-content-type response headers are preserved (except content-length)."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_html_multi_header_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="Test\n",
        ):
            _, headers, _ = await _collect_asgi_response(app, scope)

        header_dict = {k: v for k, v in headers}
        assert header_dict[b"x-custom"] == b"value"
        assert header_dict[b"cache-control"] == b"no-cache"

    @pytest.mark.asyncio
    async def test_no_content_type_passthrough(self) -> None:
        """Response with no content-type header passes through."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        app = MarkdownASGIMiddleware(_no_content_type_asgi_app)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            _, _, body = await _collect_asgi_response(app, scope)

        mock_convert.assert_not_called()
        assert body == b"no content type"

    @pytest.mark.asyncio
    async def test_content_length_updated_after_conversion(self) -> None:
        """Content-Length header reflects the markdown body size, not original."""
        from context_cli.core.serve.middleware import MarkdownASGIMiddleware

        async def app_with_content_length(
            scope: dict, receive: Any, send: Any,
        ) -> None:
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/html"],
                    [b"content-length", b"999"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": b"<html><body><p>Hello</p></body></html>",
            })

        mw = MarkdownASGIMiddleware(app_with_content_length)
        scope = _make_http_scope(
            headers=[(b"accept", b"text/markdown")],
        )

        md_text = "Hello\n"
        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value=md_text,
        ):
            _, headers, body = await _collect_asgi_response(mw, scope)

        header_dict = {k: v for k, v in headers}
        assert header_dict[b"content-length"] == str(len(md_text.encode())).encode()


# ===========================================================================
# WSGI Middleware Tests
# ===========================================================================


class TestMarkdownWSGIMiddleware:
    """Tests for MarkdownWSGIMiddleware."""

    def test_converts_html_to_markdown_when_accept_header_present(self) -> None:
        """HTML response is converted to markdown when Accept: text/markdown."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n\nWorld\n",
        ) as mock_convert:
            status, headers, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_called_once()
        assert body == b"# Hello\n\nWorld\n"

    def test_sets_content_type_to_text_markdown(self) -> None:
        """Response Content-Type is set to text/markdown; charset=utf-8."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ):
            _, headers, _ = _collect_wsgi_response(app, environ)

        header_dict = {k: v for k, v in headers}
        assert header_dict["Content-Type"] == "text/markdown; charset=utf-8"

    def test_adds_x_content_source_header(self) -> None:
        """Response has X-Content-Source: markdown-middleware header."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ):
            _, headers, _ = _collect_wsgi_response(app, environ)

        header_dict = {k: v for k, v in headers}
        assert header_dict["X-Content-Source"] == "markdown-middleware"

    def test_passthrough_when_no_accept_markdown(self) -> None:
        """HTML is passed through unchanged when no Accept: text/markdown."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ(accept="text/html")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            status, headers, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_not_called()
        assert b"<html>" in body

    def test_passthrough_for_json_response(self) -> None:
        """JSON responses are passed through unchanged."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_json_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            _, _, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_not_called()
        assert body == b'{"key": "value"}'

    def test_passthrough_for_plain_text_response(self) -> None:
        """Plain text responses are passed through unchanged."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_plain_text_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            _, _, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_not_called()
        assert body == b"Just plain text"

    def test_preserves_status_code(self) -> None:
        """Non-200 status codes are preserved."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_404_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Not Found\n",
        ):
            status, _, body = _collect_wsgi_response(app, environ)

        assert status == "404 Not Found"
        assert body == b"# Not Found\n"

    def test_handles_empty_body(self) -> None:
        """Empty HTML body results in empty markdown."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_empty_body_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="",
        ):
            status, _, body = _collect_wsgi_response(app, environ)

        assert body == b""

    def test_buffers_chunked_response(self) -> None:
        """Multiple response chunks are buffered and converted together."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_chunked_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n\nWorld\n",
        ) as mock_convert:
            _, _, body = _collect_wsgi_response(app, environ)

        call_args = mock_convert.call_args[0][0]
        assert "<h1>Hello</h1>" in call_args
        assert body == b"# Hello\n\nWorld\n"

    def test_no_accept_header_passes_through(self) -> None:
        """Request with no Accept header passes through unchanged."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ()  # No accept header

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            _, _, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_not_called()
        assert b"<html>" in body

    def test_accept_markdown_among_multiple_types(self) -> None:
        """Accept header with multiple types including text/markdown triggers conversion."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ(
            accept="text/html, text/markdown, application/json",
        )

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ) as mock_convert:
            _, _, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_called_once()
        assert body == b"# Hello\n"

    def test_no_content_type_passthrough(self) -> None:
        """Response with no content-type header passes through."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_no_content_type_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
        ) as mock_convert:
            _, _, body = _collect_wsgi_response(app, environ)

        mock_convert.assert_not_called()
        assert body == b"no content type"

    def test_preserves_non_content_type_headers(self) -> None:
        """Non-content-type response headers are preserved (except content-length)."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_multi_header_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="Test\n",
        ):
            _, headers, _ = _collect_wsgi_response(app, environ)

        header_dict = {k: v for k, v in headers}
        assert header_dict["X-Custom"] == "value"
        assert header_dict["Cache-Control"] == "no-cache"

    def test_content_length_updated_after_conversion(self) -> None:
        """Content-Length header reflects the markdown body size."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        def app_with_cl(environ: dict, start_response: Any) -> list[bytes]:
            start_response(
                "200 OK",
                [
                    ("Content-Type", "text/html"),
                    ("Content-Length", "999"),
                ],
            )
            return [b"<html><body><p>Hello</p></body></html>"]

        mw = MarkdownWSGIMiddleware(app_with_cl)
        environ = _make_wsgi_environ(accept="text/markdown")

        md_text = "Hello\n"
        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value=md_text,
        ):
            _, headers, body = _collect_wsgi_response(mw, environ)

        header_dict = {k: v for k, v in headers}
        assert header_dict["Content-Length"] == str(len(md_text.encode()))

    def test_start_response_called_with_correct_args(self) -> None:
        """start_response is called with status and headers list."""
        from context_cli.core.serve.middleware import MarkdownWSGIMiddleware

        app = MarkdownWSGIMiddleware(_wsgi_html_app)
        environ = _make_wsgi_environ(accept="text/markdown")

        captured_calls: list[tuple[str, list[tuple[str, str]]]] = []

        def mock_start_response(
            status: str, headers: list[tuple[str, str]],
        ) -> None:
            captured_calls.append((status, headers))

        with patch(
            "context_cli.core.serve.middleware.convert_html_to_markdown",
            return_value="# Hello\n",
        ):
            list(app(environ, mock_start_response))

        assert len(captured_calls) == 1
        assert captured_calls[0][0] == "200 OK"
        header_names = [h[0] for h in captured_calls[0][1]]
        assert "Content-Type" in header_names
        assert "X-Content-Source" in header_names
