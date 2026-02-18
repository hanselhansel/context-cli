"""FastMCP server exposing AEO audit and generate as MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from aeo_cli.core.auditor import audit_site, audit_url
from aeo_cli.core.models import AuditReport, GenerateConfig, ProfileType, SiteAuditReport

mcp = FastMCP(
    name="aeo-cli",
    instructions=(
        "AEO-CLI audits URLs for AI crawler readiness, checking robots.txt, "
        "llms.txt, Schema.org structured data, and content density. "
        "By default it discovers and audits multiple pages across the site. "
        "It can also generate llms.txt and schema.jsonld files using LLM analysis."
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


@mcp.tool
async def generate(
    url: str,
    profile: str = "generic",
    model: str | None = None,
    output_dir: str = "./aeo-output",
) -> dict[str, Any]:
    """Generate llms.txt and schema.jsonld for a URL using LLM analysis.

    Args:
        url: URL to generate assets for.
        profile: Industry profile (generic, cpg, saas, ecommerce, blog).
        model: LLM model to use (auto-detected from env if not set).
        output_dir: Directory to write generated files.
    """
    from aeo_cli.core.generate import generate_assets

    config = GenerateConfig(
        url=url,
        profile=ProfileType(profile),
        model=model,
        output_dir=output_dir,
    )
    result = await generate_assets(config)
    return result.model_dump()
