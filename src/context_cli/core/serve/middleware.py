"""ASGI and WSGI middleware — converts HTML to Markdown on ``Accept: text/markdown``."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from context_cli.core.markdown_engine import convert_html_to_markdown

# Type aliases for ASGI
ASGIApp = Callable[..., Any]
Scope = dict[str, Any]
Receive = Callable[..., Any]
Send = Callable[..., Any]

_MARKDOWN_CONTENT_TYPE = b"text/markdown; charset=utf-8"
_SOURCE_HEADER = (b"x-content-source", b"markdown-middleware")


def _wants_markdown(headers: list[tuple[bytes, bytes]]) -> bool:
    """Return True if request Accept header includes text/markdown."""
    for name, value in headers:
        if name.lower() == b"accept" and b"text/markdown" in value:
            return True
    return False


def _is_html_content_type(headers: list[list[bytes] | tuple[bytes, bytes]]) -> bool:
    """Return True if response Content-Type starts with text/html."""
    for pair in headers:
        name = pair[0] if isinstance(pair, (list, tuple)) else b""
        value = pair[1] if isinstance(pair, (list, tuple)) else b""
        if name.lower() == b"content-type" and b"text/html" in value:
            return True
    return False


def _rebuild_headers(
    original: list[list[bytes] | tuple[bytes, bytes]],
    md_body: bytes,
) -> list[list[bytes]]:
    """Rebuild response headers: replace Content-Type, update Content-Length, add source."""
    new_headers: list[list[bytes]] = []
    for pair in original:
        name = bytes(pair[0]).lower()
        if name == b"content-type":
            new_headers.append([b"content-type", _MARKDOWN_CONTENT_TYPE])
        elif name == b"content-length":
            new_headers.append(
                [b"content-length", str(len(md_body)).encode()]
            )
        else:
            new_headers.append([bytes(pair[0]), bytes(pair[1])])
    new_headers.append(list(_SOURCE_HEADER))
    return new_headers


class MarkdownASGIMiddleware:
    """ASGI middleware — converts HTML to Markdown when Accept: text/markdown."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send,
    ) -> None:
        """Handle an ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_headers: list[tuple[bytes, bytes]] = [
            (bytes(h[0]), bytes(h[1])) for h in scope.get("headers", [])
        ]

        if not _wants_markdown(request_headers):
            await self.app(scope, receive, send)
            return

        start_message: dict[str, Any] = {}
        body_parts: list[bytes] = []

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal start_message

            if message["type"] == "http.response.start":
                start_message = message
                return  # Defer sending until we know the full body

            if message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))
                more = message.get("more_body", False)
                if more:
                    return  # Keep buffering

                # Full body received — decide whether to convert.
                orig_headers = start_message.get("headers", [])

                if not _is_html_content_type(orig_headers):
                    # Not HTML — flush everything unchanged.
                    await send(start_message)
                    await send({
                        "type": "http.response.body",
                        "body": b"".join(body_parts),
                    })
                    return

                # Convert HTML → Markdown
                full_html = b"".join(body_parts).decode("utf-8", errors="replace")
                md_text = convert_html_to_markdown(full_html)
                md_bytes = md_text.encode("utf-8")

                new_headers = _rebuild_headers(orig_headers, md_bytes)
                await send({
                    "type": "http.response.start",
                    "status": start_message["status"],
                    "headers": new_headers,
                })
                await send({
                    "type": "http.response.body",
                    "body": md_bytes,
                })

        await self.app(scope, receive, send_wrapper)


class MarkdownWSGIMiddleware:
    """WSGI middleware — converts HTML to Markdown when Accept: text/markdown."""

    def __init__(self, app: Callable[..., Iterable[bytes]]) -> None:
        self.app = app

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> Iterable[bytes]:
        """Handle a WSGI request."""
        accept = environ.get("HTTP_ACCEPT", "")
        if "text/markdown" not in accept:
            return self.app(environ, start_response)

        # Capture the upstream response.
        captured_status = ""
        captured_headers: list[tuple[str, str]] = []

        def capture_start_response(
            status: str, headers: list[tuple[str, str]],
        ) -> None:
            nonlocal captured_status, captured_headers
            captured_status = status
            captured_headers = headers

        response_iter = self.app(environ, capture_start_response)
        body = b"".join(response_iter)

        # Check if the response is HTML.
        is_html = any(
            name.lower() == "content-type" and "text/html" in value
            for name, value in captured_headers
        )

        if not is_html:
            start_response(captured_status, captured_headers)
            return [body]

        # Convert HTML → Markdown
        html_text = body.decode("utf-8", errors="replace")
        md_text = convert_html_to_markdown(html_text)
        md_bytes = md_text.encode("utf-8")

        new_headers: list[tuple[str, str]] = []
        for name, value in captured_headers:
            lower_name = name.lower()
            if lower_name == "content-type":
                new_headers.append(
                    ("Content-Type", "text/markdown; charset=utf-8")
                )
            elif lower_name == "content-length":
                new_headers.append(
                    ("Content-Length", str(len(md_bytes)))
                )
            else:
                new_headers.append((name, value))
        new_headers.append(("X-Content-Source", "markdown-middleware"))

        start_response(captured_status, new_headers)
        return [md_bytes]
