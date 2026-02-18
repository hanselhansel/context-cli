"""AEO-CLI — Agentic Engine Optimization auditor CLI."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from aeo_cli.core.auditor import audit_url

app = typer.Typer(help="AEO-CLI: Audit URLs for AI crawler readiness and get a 0-100 AEO score.")
console = Console()

# Pillar max scores for color thresholds
_PILLAR_MAX = {
    "robots": 25,
    "llms_txt": 10,
    "schema_org": 25,
    "content": 40,
}


def _score_color(score: float, pillar: str) -> Text:
    """Return a Rich Text with the score colored by threshold (green/yellow/red)."""
    max_pts = _PILLAR_MAX[pillar]
    ratio = score / max_pts if max_pts else 0
    if ratio >= 0.7:
        color = "green"
    elif ratio >= 0.4:
        color = "yellow"
    else:
        color = "red"
    return Text(f"{score}", style=color)


@app.command()
def audit(
    url: str = typer.Argument(help="URL to audit for AI crawler readiness"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON instead of Rich table"),
) -> None:
    """Run an AEO audit on a URL and display the results."""
    if not url.startswith("http"):
        url = f"https://{url}"

    with console.status(f"Auditing {url}..."):
        report = asyncio.run(audit_url(url))

    if json_output:
        console.print(report.model_dump_json(indent=2))
        return

    # Build Rich table
    table = Table(title=f"AEO Audit: {report.url}")
    table.add_column("Pillar", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Detail")

    rows = [
        ("Robots.txt AI Access", report.robots.score, "robots", report.robots.detail),
        ("llms.txt Presence", report.llms_txt.score, "llms_txt", report.llms_txt.detail),
        ("Schema.org JSON-LD", report.schema_org.score, "schema_org", report.schema_org.detail),
        ("Content Density", report.content.score, "content", report.content.detail),
    ]
    for label, score, pillar, detail in rows:
        table.add_row(label, _score_color(score, pillar), detail)

    console.print(table)
    console.print(f"\n[bold]Overall AEO Score:[/bold] [cyan]{report.overall_score}/100[/cyan]")

    if report.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  • {err}")


@app.command()
def mcp() -> None:
    """Start the AEO-CLI MCP server (stdio transport)."""
    from aeo_cli.server import mcp as mcp_server

    mcp_server.run(transport="stdio")
