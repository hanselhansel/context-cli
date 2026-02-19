"""Pillar 2: llms.txt presence checking."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from context_cli.core.models import LlmsTxtReport


async def _probe_file(
    base: str, paths: list[str], client: httpx.AsyncClient
) -> str | None:
    """Probe a list of URL paths, returning the first that has non-empty content."""
    for path in paths:
        probe_url = base + path
        try:
            resp = await client.get(probe_url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.text.strip()) > 0:
                return probe_url
        except httpx.HTTPError:
            continue
    return None


async def check_llms_txt(url: str, client: httpx.AsyncClient) -> LlmsTxtReport:
    """Probe /llms.txt, /.well-known/llms.txt, /llms-full.txt, /.well-known/llms-full.txt."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    llms_url = await _probe_file(base, ["/llms.txt", "/.well-known/llms.txt"], client)
    full_url = await _probe_file(
        base, ["/llms-full.txt", "/.well-known/llms-full.txt"], client
    )

    found = llms_url is not None
    full_found = full_url is not None

    # Build detail string
    parts: list[str] = []
    if found:
        parts.append(f"llms.txt at {llms_url}")
    if full_found:
        parts.append(f"llms-full.txt at {full_url}")

    if parts:
        detail = "Found: " + ", ".join(parts)
    else:
        detail = "llms.txt not found"

    return LlmsTxtReport(
        found=found,
        url=llms_url,
        llms_full_found=full_found,
        llms_full_url=full_url,
        detail=detail,
    )
