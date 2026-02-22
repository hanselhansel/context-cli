"""Agent readiness sub-check: MCP endpoint detection at /.well-known/mcp.json."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from context_cli.core.models import McpEndpointReport


async def check_mcp_endpoint(url: str, client: httpx.AsyncClient) -> McpEndpointReport:
    """Probe /.well-known/mcp.json and report MCP endpoint availability."""
    parsed = urlparse(url)
    mcp_url = f"{parsed.scheme}://{parsed.netloc}/.well-known/mcp.json"

    try:
        resp = await client.get(mcp_url, follow_redirects=True)
        if resp.status_code != 200:
            return McpEndpointReport(
                found=False,
                detail=f"MCP endpoint returned HTTP {resp.status_code}",
            )

        try:
            data = resp.json()
        except Exception:
            return McpEndpointReport(
                found=True,
                url=mcp_url,
                score=1.0,
                detail="MCP endpoint found but contains invalid JSON",
            )

        tools_count = None
        if isinstance(data, dict) and isinstance(data.get("tools"), list):
            tools_count = len(data["tools"])

        return McpEndpointReport(
            found=True,
            url=mcp_url,
            tools_count=tools_count,
            score=4.0,
            detail=f"MCP endpoint found with {tools_count} tool(s)"
            if tools_count is not None
            else "MCP endpoint found",
        )

    except httpx.HTTPError as exc:
        return McpEndpointReport(
            found=False, detail=f"Failed to probe MCP endpoint: {exc}"
        )
