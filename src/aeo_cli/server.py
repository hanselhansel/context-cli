"""FastMCP server exposing AEO audit as an MCP tool."""

from __future__ import annotations

from fastmcp import FastMCP

from aeo_cli.core.auditor import audit_url

mcp = FastMCP(
    name="aeo-cli",
    instructions=(
        "AEO-CLI audits URLs for AI crawler readiness, checking robots.txt, "
        "llms.txt, Schema.org structured data, and content density."
    ),
)


@mcp.tool
async def audit(url: str) -> dict:
    """Audit a URL for AI engine optimization readiness.

    Returns an AEO score (0-100) with detailed pillar breakdowns
    for robots.txt, llms.txt, Schema.org, and content density.
    """
    report = await audit_url(url)
    return report.model_dump()
