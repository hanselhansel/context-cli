"""FastMCP server exposing AEO audit and generate as MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from aeo_cli.core.auditor import audit_site, audit_url
from aeo_cli.core.compare import compare_urls
from aeo_cli.core.history import HistoryDB
from aeo_cli.core.models import (
    AuditReport,
    GenerateConfig,
    ProfileType,
    SiteAuditReport,
)
from aeo_cli.core.recommend import generate_recommendations

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


@mcp.tool
async def generate_batch_tool(
    urls: list[str],
    profile: str = "generic",
    model: str | None = None,
    output_dir: str = "./aeo-output",
    concurrency: int = 3,
) -> dict[str, Any]:
    """Batch generate llms.txt and schema.jsonld for multiple URLs.

    Args:
        urls: List of URLs to generate assets for.
        profile: Industry profile (generic, cpg, saas, ecommerce, blog).
        model: LLM model to use (auto-detected from env if not set).
        output_dir: Directory to write generated files.
        concurrency: Max concurrent generations (default 3).
    """
    from aeo_cli.core.generate.batch import generate_batch as _generate_batch
    from aeo_cli.core.models import BatchGenerateConfig

    config = BatchGenerateConfig(
        urls=urls,
        profile=ProfileType(profile),
        model=model,
        output_dir=output_dir,
        concurrency=concurrency,
    )
    result = await _generate_batch(config)
    return result.model_dump()


@mcp.tool
async def compare(url1: str, url2: str) -> dict[str, Any]:
    """Compare two URLs side-by-side for AI engine optimization readiness.

    Audits both URLs concurrently and returns a comparison report with
    per-pillar score deltas.
    """
    report = await compare_urls(url1, url2)
    return report.model_dump()


@mcp.tool
async def history(url: str, limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve audit history for a URL from the local SQLite database.

    Returns recent audit entries (newest first), each with timestamp and
    per-pillar scores.
    """
    db = HistoryDB()
    try:
        entries = db.list_entries(url, limit=limit)
        return [entry.model_dump() for entry in entries]
    finally:
        db.close()


@mcp.tool
async def recommend(url: str) -> list[dict[str, Any]]:
    """Audit a URL and return actionable recommendations to improve AEO score.

    Runs a single-page audit, then analyzes the results to suggest specific
    improvements sorted by estimated impact.
    """
    report = await audit_url(url)
    recs = generate_recommendations(report)
    return [rec.model_dump() for rec in recs]


@mcp.tool
async def radar(
    prompt: str,
    models: list[str] | None = None,
    brands: list[str] | None = None,
    runs_per_model: int = 1,
) -> dict[str, Any]:
    """Query AI models and analyze what they cite for a given prompt.

    Args:
        prompt: Search query to send to AI models.
        models: LLM models to query (defaults to gpt-4o-mini).
        brands: Brand names to track in responses.
        runs_per_model: Number of runs per model for statistical significance.
    """
    from aeo_cli.core.models import RadarConfig
    from aeo_cli.core.radar.analyzer import build_radar_report
    from aeo_cli.core.radar.query import query_models

    config = RadarConfig(
        prompt=prompt,
        models=models or ["gpt-4o-mini"],
        brands=brands or [],
        runs_per_model=runs_per_model,
    )
    results = await query_models(config)
    report = build_radar_report(config, results)
    return report.model_dump()
