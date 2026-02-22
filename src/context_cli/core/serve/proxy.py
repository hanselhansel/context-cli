"""Reverse proxy server — serves HTML as markdown for LLM clients.

When an incoming request includes ``Accept: text/markdown``, the proxy fetches the
upstream page, converts the HTML to clean markdown via the markdown engine, and
returns it with ``Content-Type: text/markdown; charset=utf-8``.  All other requests
are passed through unchanged.
"""

from __future__ import annotations

import httpx
from aiohttp import web

from context_cli.core.markdown_engine import convert_html_to_markdown

_MARKDOWN_CONTENT_TYPE = "text/markdown; charset=utf-8"
_SOURCE_HEADER = "X-Content-Source"
_SOURCE_VALUE = "markdown-proxy"
_HOP_BY_HOP = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
})


def _wants_markdown(request: web.Request) -> bool:
    """Return True if the client indicated it accepts text/markdown."""
    accept = request.headers.get("Accept", "")
    return "text/markdown" in accept


def _is_html(content_type: str) -> bool:
    """Return True if the content-type header indicates HTML."""
    return "text/html" in content_type


def _build_upstream_url(upstream: str, path: str, query_string: str) -> str:
    """Construct the full upstream URL from base, path, and query string."""
    url = upstream.rstrip("/") + path
    if query_string:
        url += "?" + query_string
    return url


def _filter_headers(
    headers: httpx.Headers,
) -> dict[str, str]:
    """Filter hop-by-hop headers from the upstream response."""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in _HOP_BY_HOP
    }


async def _proxy_handler(request: web.Request) -> web.Response:
    """Handle a single proxied request."""
    upstream: str = request.app["upstream"]
    url = _build_upstream_url(upstream, request.path, request.query_string)

    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True,
        ) as client:
            upstream_resp = await client.get(
                url,
                headers={"User-Agent": "ContextCLI-Proxy/1.0"},
            )
    except (httpx.TimeoutException, httpx.ConnectError):
        return web.Response(status=502, text="Bad Gateway: upstream unavailable")

    content_type = upstream_resp.headers.get("content-type", "")
    body = upstream_resp.content
    headers = _filter_headers(upstream_resp.headers)

    if _wants_markdown(request) and _is_html(content_type):
        md_text = convert_html_to_markdown(upstream_resp.text)
        # Remove upstream content-type; we set our own via content_type=
        headers.pop("Content-Type", None)
        headers.pop("content-type", None)
        headers[_SOURCE_HEADER] = _SOURCE_VALUE
        return web.Response(
            status=upstream_resp.status_code,
            text=md_text,
            content_type="text/markdown",
            charset="utf-8",
            headers=headers,
        )

    return web.Response(
        status=upstream_resp.status_code,
        body=body,
        headers=headers,
    )


def create_proxy_app(upstream: str) -> web.Application:
    """Create an aiohttp application that proxies to *upstream*.

    Args:
        upstream: The base URL of the upstream server (e.g. ``http://localhost:3000``).

    Returns:
        A configured :class:`aiohttp.web.Application`.
    """
    app = web.Application()
    app["upstream"] = upstream
    app.router.add_route("*", "/{path_info:.*}", _proxy_handler)
    return app


def run_proxy(
    upstream: str,
    port: int = 8080,
    host: str = "0.0.0.0",
) -> None:
    """Start the markdown reverse-proxy server.

    Args:
        upstream: The base URL of the upstream server.
        port: Port to listen on (default 8080).
        host: Host/interface to bind (default ``0.0.0.0``).
    """
    app = create_proxy_app(upstream)
    web.run_app(app, host=host, port=port)
