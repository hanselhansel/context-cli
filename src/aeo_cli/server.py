"""FastMCP server exposing AEO audit as an MCP tool."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from aeo_cli.core.auditor import audit_site, audit_url
from aeo_cli.core.models import AuditReport, SiteAuditReport

mcp = FastMCP(
    name="aeo-cli",
    instructions=(
        "AEO-CLI audits URLs for AI crawler readiness, checking robots.txt, "
        "llms.txt, Schema.org structured data, and content density. "
        "By default it discovers and audits multiple pages across the site."
    ),
)


@mcp.tool
async def audit(url: str, single_page: bool = False, max_pages: int = 10) -> dict[str, Any]:
    """Audit a URL for AI engine optimization readiness.

    By default discovers and audits up to max_pages pages across the site.
    Set single_page=True to audit only the given URL.
    """
    report: AuditReport | SiteAuditReport
    if single_page:
        report = await audit_url(url)
    else:
        report = await audit_site(url, max_pages=max_pages)
    return report.model_dump()
