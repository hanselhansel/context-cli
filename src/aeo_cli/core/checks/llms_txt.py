"""Pillar 2: llms.txt presence checking."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from aeo_cli.core.models import LlmsTxtReport


async def check_llms_txt(url: str, client: httpx.AsyncClient) -> LlmsTxtReport:
    """Probe /llms.txt and /.well-known/llms.txt."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    paths = ["/llms.txt", "/.well-known/llms.txt"]

    for path in paths:
        probe_url = base + path
        try:
            resp = await client.get(probe_url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.text.strip()) > 0:
                return LlmsTxtReport(
                    found=True,
                    url=probe_url,
                    detail=f"Found at {probe_url}",
                )
        except httpx.HTTPError:
            continue

    return LlmsTxtReport(found=False, detail="llms.txt not found")
