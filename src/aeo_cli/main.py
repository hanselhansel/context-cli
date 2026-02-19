"""AEO-CLI — Agentic Engine Optimization auditor CLI."""

from __future__ import annotations

import asyncio
import os

import typer
from rich.console import Console
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
from aeo_cli.formatters.csv import (
    format_single_report_csv,
    format_site_report_csv,
)
from aeo_cli.formatters.markdown import (
    format_single_report_md,
    format_site_report_md,
)
from aeo_cli.formatters.verbose import (
    render_verbose_single,
    render_verbose_site,
)
from aeo_cli.formatters.verbose import (
    score_color as _score_color_impl,
)

app = typer.Typer(help="AEO-CLI: Audit URLs for AI crawler readiness and get a 0-100 AEO score.")
console = Console()

def _score_color(score: float, pillar: str) -> Text:
    """Return a Rich Text with the score colored by threshold (green/yellow/red)."""
    return _score_color_impl(score, pillar)


def _render_site_report(report: SiteAuditReport) -> None:
    """Render a multi-page site audit report using Rich."""
    from aeo_cli.formatters.rich_output import render_site_report

    render_site_report(report, console)


@app.command()
def audit(
    url: str = typer.Argument(None, help="URL to audit for AI crawler readiness"),
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
    timeout: int = typer.Option(
        15, "--timeout", "-t", help="HTTP timeout in seconds (default: 15)"
    ),
    file: str = typer.Option(
        None, "--file", "-F", help="Path to .txt or .csv file with URLs (one per line)"
    ),
    concurrency: int = typer.Option(
        3, "--concurrency", help="Max concurrent audits in batch mode (default: 3)"
    ),
    bots: str = typer.Option(
        None, "--bots", help="Comma-separated custom AI bot list (overrides defaults)"
    ),
) -> None:
    """Run an AEO audit on a URL and display the results."""
    # --json flag is a shortcut for --format json
    if json_output and format is None:
        format = OutputFormat.json

    # Parse --bots into a list
    bots_list = [b.strip() for b in bots.split(",")] if bots else None

    # Batch mode: --file flag
    if file:
        _run_batch_mode(file, format, single, max_pages, timeout, concurrency, bots=bots_list)
        return

    if not url:
        console.print("[red]Error:[/red] Provide a URL argument or use --file for batch mode.")
        raise SystemExit(1)

    if not url.startswith("http"):
        url = f"https://{url}"

    if quiet:
        # Backwards compat: --quiet uses threshold 50 unless --fail-under overrides
        threshold = fail_under if fail_under is not None else 50
        _audit_quiet(
            url, single, max_pages, threshold, fail_on_blocked_bots, timeout, bots=bots_list
        )
        return  # pragma: no cover — _audit_quiet always raises SystemExit

    # Normal flow
    report = _run_audit(url, single, max_pages, timeout, bots=bots_list)
    _render_output(report, format, verbose, single)
    _write_github_step_summary(report, fail_under)

    if fail_under is not None or fail_on_blocked_bots:
        _check_exit_conditions(report, fail_under, fail_on_blocked_bots)


def _run_audit(
    url: str,
    single: bool,
    max_pages: int,
    timeout: int = 15,
    *,
    bots: list[str] | None = None,
) -> AuditReport | SiteAuditReport:
    """Execute the audit and return the report."""
    if single:
        with console.status(f"Auditing {url}..."):
            return asyncio.run(audit_url(url, timeout=timeout, bots=bots))

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
            audit_site(url, max_pages=max_pages, timeout=timeout,
                       progress_callback=on_progress, bots=bots)
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
        if verbose:
            render_verbose_site(report, console)
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
        render_verbose_single(report, console)

    if report.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  • {err}")


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
    timeout: int = 15,
    *,
    bots: list[str] | None = None,
) -> None:
    """Run audit silently — exit based on threshold and bot access."""
    report: AuditReport | SiteAuditReport
    if single:
        report = asyncio.run(audit_url(url, timeout=timeout, bots=bots))
    else:
        report = asyncio.run(audit_site(url, max_pages=max_pages, timeout=timeout, bots=bots))

    if fail_on_blocked_bots and report.robots.found:
        if any(not b.allowed for b in report.robots.bots):
            raise SystemExit(2)
    raise SystemExit(0 if report.overall_score >= threshold else 1)


def _run_batch_mode(
    file: str,
    format: OutputFormat | None,
    single: bool,
    max_pages: int,
    timeout: int,
    concurrency: int,
    *,
    bots: list[str] | None = None,
) -> None:
    """Execute batch audit from a URL file and render results."""
    from aeo_cli.core.batch import parse_url_file, run_batch_audit

    try:
        urls = parse_url_file(file)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise SystemExit(1)

    if not urls:
        console.print("[yellow]Warning:[/yellow] No URLs found in file.")
        return

    with console.status(f"Running batch audit on {len(urls)} URLs..."):
        batch_report = asyncio.run(
            run_batch_audit(
                urls, single=single, max_pages=max_pages,
                timeout=timeout, concurrency=concurrency, bots=bots,
            )
        )

    if format == OutputFormat.json:
        console.print(batch_report.model_dump_json(indent=2))
        return
    if format == OutputFormat.csv:
        from aeo_cli.formatters.csv import format_batch_report_csv

        console.print(format_batch_report_csv(batch_report), end="")
        return
    if format == OutputFormat.markdown:
        from aeo_cli.formatters.markdown import format_batch_report_md

        console.print(format_batch_report_md(batch_report), end="")
        return

    from aeo_cli.formatters.rich_output import render_batch_rich

    render_batch_rich(batch_report, console)


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
