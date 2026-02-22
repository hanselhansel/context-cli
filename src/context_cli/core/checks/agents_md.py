"""Check for AGENTS.md presence at well-known paths."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from context_cli.core.models import AgentsMdReport

PROBE_PATHS: list[str] = [
    "/agents.md",
    "/AGENTS.md",
    "/.well-known/agents.md",
]

DEFAULT_TIMEOUT: int = 15


async def check_agents_md(url: str, client: httpx.AsyncClient) -> AgentsMdReport:
    """Probe for AGENTS.md at standard paths, return on first hit."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    for path in PROBE_PATHS:
        probe_url = f"{base}{path}"
        try:
            resp = await client.get(probe_url, follow_redirects=True)
            if resp.status_code != 200:
                continue
            ct = resp.headers.get("content-type", "")
            if "text" not in ct:
                continue
            return AgentsMdReport(
                found=True,
                url=probe_url,
                score=5.0,
                detail=f"AGENTS.md found at {probe_url}",
            )
        except httpx.HTTPError:
            continue

    return AgentsMdReport(
        found=False,
        score=0,
        detail="No AGENTS.md found",
    )
