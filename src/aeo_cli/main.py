"""AEO-CLI — Agentic Engine Optimization auditor CLI."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from aeo_cli.core.auditor import audit_site, audit_url
from aeo_cli.core.models import AuditReport, OutputFormat, SiteAuditReport
from aeo_cli.formatters.csv import format_single_report_csv, format_site_report_csv
from aeo_cli.formatters.markdown import format_single_report_md, format_site_report_md

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


def _overall_color(score: float) -> str:
    """Return a Rich color string for an overall 0-100 score."""
    if score >= 70:
        return "green"
    elif score >= 40:
        return "yellow"
    return "red"


def _render_site_report(report: SiteAuditReport) -> None:
    """Render a multi-page site audit report using Rich."""
    # Header panel
    header_lines = [
        f"[bold]Domain:[/bold] {report.domain}",
        f"[bold]Discovery:[/bold] {report.discovery.method} — {report.discovery.detail}",
        f"[bold]Pages audited:[/bold] {report.pages_audited}"
        + (f"  ([red]{report.pages_failed} failed[/red])" if report.pages_failed else ""),
    ]
    console.print(Panel("\n".join(header_lines), title=f"AEO Site Audit: {report.url}"))

    # Site-wide scores table (robots + llms.txt — same across site)
    site_table = Table(title="Site-Wide Scores")
    site_table.add_column("Pillar", style="bold")
    site_table.add_column("Score", justify="right")
    site_table.add_column("Detail")
    site_table.add_row(
        "Robots.txt AI Access",
        _score_color(report.robots.score, "robots"),
        report.robots.detail,
    )
    site_table.add_row(
        "llms.txt Presence",
        _score_color(report.llms_txt.score, "llms_txt"),
        report.llms_txt.detail,
    )
    console.print(site_table)

    # Aggregate per-page scores (schema + content averaged)
    agg_table = Table(title="Aggregate Page Scores")
    agg_table.add_column("Pillar", style="bold")
    agg_table.add_column("Avg Score", justify="right")
    agg_table.add_column("Detail")
    agg_table.add_row(
        "Schema.org JSON-LD",
        _score_color(report.schema_org.score, "schema_org"),
        report.schema_org.detail,
    )
    agg_table.add_row(
        "Content Density",
        _score_color(report.content.score, "content"),
        report.content.detail,
    )
    console.print(agg_table)

    # Per-page breakdown
    if report.pages:
        page_table = Table(title="Per-Page Breakdown")
        page_table.add_column("URL", max_width=60)
        page_table.add_column("Schema", justify="right")
        page_table.add_column("Content", justify="right")
        page_table.add_column("Total", justify="right")
        for page in report.pages:
            total = page.schema_org.score + page.content.score
            page_table.add_row(
                page.url,
                _score_color(page.schema_org.score, "schema_org"),
                _score_color(page.content.score, "content"),
                Text(f"{total}", style=_overall_color(total)),
            )
        console.print(page_table)

    # Overall score
    color = _overall_color(report.overall_score)
    console.print(
        f"\n[bold]Overall AEO Score:[/bold] [{color}]{report.overall_score}/100[/{color}]"
    )

    # Errors
    if report.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  • {err}")


@app.command()
def audit(
    url: str = typer.Argument(help="URL to audit for AI crawler readiness"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON instead of Rich table"),
    format: OutputFormat = typer.Option(
        None, "--format", "-f", help="Output format: json, csv, or markdown"
    ),
    single: bool = typer.Option(
        False, "--single", help="Single-page audit only (skip multi-page discovery)"
    ),
    max_pages: int = typer.Option(
        10, "--max-pages", "-n", help="Max pages to audit in multi-page mode"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed per-pillar breakdown with explanations"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress output, exit code 0 if score >= 50, else 1"
    ),
    fail_under: float = typer.Option(
        None, "--fail-under", help="Exit code 1 if overall score is below this threshold (0-100)"
    ),
    fail_on_blocked_bots: bool = typer.Option(
        False,
        "--fail-on-blocked-bots",
        help="Exit code 2 if any AI bot is blocked by robots.txt",
    ),
) -> None:
    """Run an AEO audit on a URL and display the results."""
    if not url.startswith("http"):
        url = f"https://{url}"

    # --json flag is a shortcut for --format json
    if json_output and format is None:
        format = OutputFormat.json

    if quiet:
        _audit_quiet(url, single, max_pages)
        return

    if single:
        _audit_single(url, format, verbose)
    else:
        _audit_site(url, format, max_pages, verbose)


def _audit_single(url: str, format: OutputFormat | None, verbose: bool = False) -> None:
    """Run a single-page audit."""
    with console.status(f"Auditing {url}..."):
        report = asyncio.run(audit_url(url))

    if format == OutputFormat.json:
        console.print(report.model_dump_json(indent=2))
        return
    if format == OutputFormat.csv:
        console.print(format_single_report_csv(report), end="")
        return
    if format == OutputFormat.markdown:
        console.print(format_single_report_md(report), end="")
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

    if verbose:
        _render_verbose(report)

    if report.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  • {err}")


def _render_verbose(report) -> None:
    """Render a detailed verbose breakdown with scoring explanations in Rich panels."""
    console.print()
    console.print("[bold]Scoring Methodology:[/bold] Content (40pts) + Robots (25pts) "
                  "+ Schema (25pts) + llms.txt (10pts) = 100pts max")

    # Robots detail
    robots_lines = [f"[bold]Robots.txt AI Bot Access[/bold] — Score: {report.robots.score}/25"]
    if report.robots.found and report.robots.bots:
        for bot in report.robots.bots:
            status = "[green]Allowed[/green]" if bot.allowed else "[red]Blocked[/red]"
            robots_lines.append(f"  {bot.bot}: {status}")
    else:
        robots_lines.append("  robots.txt not found or inaccessible")
    console.print(Panel("\n".join(robots_lines), title="Robots.txt Detail", border_style="blue"))

    # llms.txt detail
    llms_info = f"Score: {report.llms_txt.score}/10"
    if report.llms_txt.found:
        llms_info += f"\n  Found at: {report.llms_txt.url}"
    else:
        llms_info += "\n  Not found at /llms.txt or /.well-known/llms.txt"
    console.print(Panel(
        f"[bold]llms.txt[/bold] — {llms_info}",
        title="llms.txt Detail", border_style="blue",
    ))

    # Schema detail
    schema_lines = [f"[bold]Schema.org JSON-LD[/bold] — Score: {report.schema_org.score}/25"]
    schema_lines.append(f"  Blocks found: {report.schema_org.blocks_found}")
    for s in report.schema_org.schemas:
        schema_lines.append(f"  @type: {s.schema_type} ({len(s.properties)} properties)")
    console.print(Panel("\n".join(schema_lines), title="Schema.org Detail", border_style="blue"))

    # Content detail
    content_lines = [
        f"[bold]Content Density[/bold] — Score: {report.content.score}/40",
        f"  Word count: {report.content.word_count}",
        f"  Headings: {'Yes' if report.content.has_headings else 'No'} (+7 if present)",
        f"  Lists: {'Yes' if report.content.has_lists else 'No'} (+5 if present)",
        f"  Code blocks: {'Yes' if report.content.has_code_blocks else 'No'} (+3 if present)",
    ]
    console.print(Panel("\n".join(content_lines), title="Content Detail", border_style="blue"))


def _audit_site(
    url: str, format: OutputFormat | None, max_pages: int, verbose: bool = False,
) -> None:
    """Run a multi-page site audit with progress display."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"Discovering pages on {url}...", total=max_pages)

        def on_progress(msg: str) -> None:
            progress.update(task_id, description=msg, advance=1)

        report = asyncio.run(audit_site(url, max_pages=max_pages, progress_callback=on_progress))
        progress.update(task_id, description="Done", completed=max_pages)

    if format == OutputFormat.json:
        console.print(report.model_dump_json(indent=2))
        return
    if format == OutputFormat.csv:
        console.print(format_site_report_csv(report), end="")
        return
    if format == OutputFormat.markdown:
        console.print(format_site_report_md(report), end="")
        return

    _render_site_report(report)


def _audit_quiet(url: str, single: bool, max_pages: int) -> None:
    """Run audit silently — exit 0 if score >= 50, else exit 1."""
    report: AuditReport | SiteAuditReport
    if single:
        report = asyncio.run(audit_url(url))
    else:
        report = asyncio.run(audit_site(url, max_pages=max_pages))
    score = report.overall_score

    raise SystemExit(0 if score >= 50 else 1)


@app.command()
def mcp() -> None:
    """Start the AEO-CLI MCP server (stdio transport)."""
    from aeo_cli.server import mcp as mcp_server

    mcp_server.run(transport="stdio")
