"""Check whether a server supports Accept: text/markdown content negotiation."""

from __future__ import annotations

import httpx

from context_cli.core.models import MarkdownAcceptReport


async def check_markdown_accept(
    url: str, client: httpx.AsyncClient
) -> MarkdownAcceptReport:
    """Send a GET with Accept: text/markdown and inspect the response Content-Type."""
    try:
        resp = await client.get(
            url,
            headers={"Accept": "text/markdown"},
            follow_redirects=True,
        )
        ct = resp.headers.get("content-type", "")
        if "text/markdown" in ct or "text/x-markdown" in ct:
            return MarkdownAcceptReport(
                supported=True,
                content_type=ct,
                score=5.0,
                detail=f"Server supports Accept: text/markdown (Content-Type: {ct})",
            )
        return MarkdownAcceptReport(
            supported=False,
            score=0,
            detail="Server does not support Accept: text/markdown",
        )
    except httpx.HTTPError as e:
        return MarkdownAcceptReport(
            supported=False,
            score=0,
            detail=f"Failed to probe Accept: text/markdown: {e}",
        )
