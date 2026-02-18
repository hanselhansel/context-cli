"""AEO-CLI — Agentic Engine Optimization auditor CLI."""

from __future__ import annotations

import asyncio
import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from aeo_cli.core.auditor import audit_site, audit_url
from aeo_cli.core.models import (
    AuditReport,
    GenerateConfig,
    OutputFormat,
    ProfileType,
    SiteAuditReport,
)
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
        # Backwards compat: --quiet uses threshold 50 unless --fail-under overrides
        threshold = fail_under if fail_under is not None else 50
        _audit_quiet(url, single, max_pages, threshold, fail_on_blocked_bots)
        return

    # Normal flow
    report = _run_audit(url, single, max_pages)
    _render_output(report, format, verbose, single)
    _write_github_step_summary(report, fail_under)

    if fail_under is not None or fail_on_blocked_bots:
        _check_exit_conditions(report, fail_under, fail_on_blocked_bots)


def _run_audit(
    url: str, single: bool, max_pages: int,
) -> AuditReport | SiteAuditReport:
    """Execute the audit and return the report."""
    if single:
        with console.status(f"Auditing {url}..."):
            return asyncio.run(audit_url(url))

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

        report = asyncio.run(
            audit_site(url, max_pages=max_pages, progress_callback=on_progress)
        )
        progress.update(task_id, description="Done", completed=max_pages)
    return report


def _render_output(
    report: AuditReport | SiteAuditReport,
    format: OutputFormat | None,
    verbose: bool,
    single: bool,
) -> None:
    """Render the audit report in the requested format."""
    if format == OutputFormat.json:
        console.print(report.model_dump_json(indent=2))
        return
    if format == OutputFormat.csv:
        if isinstance(report, SiteAuditReport):
            console.print(format_site_report_csv(report), end="")
        else:
            console.print(format_single_report_csv(report), end="")
        return
    if format == OutputFormat.markdown:
        if isinstance(report, SiteAuditReport):
            console.print(format_site_report_md(report), end="")
        else:
            console.print(format_single_report_md(report), end="")
        return

    # Rich output
    if isinstance(report, SiteAuditReport):
        _render_site_report(report)
        return

    # Single-page Rich table
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


def _check_exit_conditions(
    report: AuditReport | SiteAuditReport,
    fail_under: float | None,
    fail_on_blocked_bots: bool,
) -> None:
    """Check CI exit conditions and raise SystemExit if thresholds are breached."""
    # Bot blocking takes priority over score failure (exit 2 before exit 1)
    if fail_on_blocked_bots and report.robots.found:
        if any(not b.allowed for b in report.robots.bots):
            raise SystemExit(2)
    if fail_under is not None and report.overall_score < fail_under:
        raise SystemExit(1)


def _write_github_step_summary(
    report: AuditReport | SiteAuditReport, fail_under: float | None,
) -> None:
    """Write CI summary to $GITHUB_STEP_SUMMARY if running in GitHub Actions."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    from aeo_cli.formatters.ci_summary import format_ci_summary

    md = format_ci_summary(report, fail_under=fail_under)
    with open(summary_path, "a") as f:
        f.write(md)


def _audit_quiet(
    url: str,
    single: bool,
    max_pages: int,
    threshold: float = 50,
    fail_on_blocked_bots: bool = False,
) -> None:
    """Run audit silently — exit based on threshold and bot access."""
    report: AuditReport | SiteAuditReport
    if single:
        report = asyncio.run(audit_url(url))
    else:
        report = asyncio.run(audit_site(url, max_pages=max_pages))

    if fail_on_blocked_bots and report.robots.found:
        if any(not b.allowed for b in report.robots.bots):
            raise SystemExit(2)
    raise SystemExit(0 if report.overall_score >= threshold else 1)


@app.command()
def generate(
    url: str = typer.Argument(help="URL to generate llms.txt and schema.jsonld for"),
    profile: ProfileType = typer.Option(
        ProfileType.generic, "--profile", "-p", help="Industry profile for prompt tuning"
    ),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model to use (auto-detected if not set)"
    ),
    output_dir: str = typer.Option(
        "./aeo-output", "--output-dir", "-o", help="Directory to write generated files"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Generate llms.txt and schema.jsonld for a URL using LLM analysis."""
    if not url.startswith("http"):
        url = f"https://{url}"

    try:
        from aeo_cli.core.generate import generate_assets
    except ImportError:
        console.print(
            "[red]Error:[/red] litellm is required for the generate command.\n"
            "Install it with: [bold]pip install aeo-cli\\[generate][/bold]"
        )
        raise SystemExit(1)

    config = GenerateConfig(url=url, profile=profile, model=model, output_dir=output_dir)

    try:
        with console.status(f"Generating assets for {url}..."):
            result = asyncio.run(generate_assets(config))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    if json_output:
        console.print(result.model_dump_json(indent=2))
        return

    # Rich output
    console.print(f"\n[bold green]Generated AEO assets for {result.url}[/bold green]")
    console.print(f"  [bold]Model:[/bold] {result.model_used}")
    console.print(f"  [bold]Profile:[/bold] {result.profile.value}")
    if result.llms_txt_path:
        console.print(f"  [bold]llms.txt:[/bold] {result.llms_txt_path}")
    if result.schema_jsonld_path:
        console.print(f"  [bold]schema.jsonld:[/bold] {result.schema_jsonld_path}")
    if result.errors:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for err in result.errors:
            console.print(f"  • {err}")


@app.command()
def mcp() -> None:
    """Start the AEO-CLI MCP server (stdio transport)."""
    from aeo_cli.server import mcp as mcp_server

    mcp_server.run(transport="stdio")
