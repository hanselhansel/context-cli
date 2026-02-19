"""Watch command — continuous monitoring with periodic audits."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table

from context_cli.core.auditor import audit_url
from context_cli.core.history import HistoryDB
from context_cli.core.models import AuditReport
from context_cli.core.regression import detect_regression

console = Console()


def _save_to_history(report: AuditReport) -> None:
    """Save report to history and check for regression."""
    db = HistoryDB()
    try:
        previous = db.get_latest_report(report.url)
        db.save(report)
        console.print("[green]  Saved to history.[/green]")
        if previous is not None:
            result = detect_regression(report, previous)
            if result.has_regression:
                console.print(
                    f"  [bold red]Regression:[/bold red] "
                    f"score dropped {abs(result.delta):.1f} points "
                    f"({result.previous_score:.0f} -> {result.current_score:.0f})"
                )
    except Exception as exc:
        console.print(f"  [yellow]History save error:[/yellow] {exc}")
    finally:
        db.close()


def _render_report(report: AuditReport, json_output: bool) -> None:
    """Render a single audit report (Rich table or JSON)."""
    if json_output:
        console.print(report.model_dump_json(indent=2))
        return

    table = Table(title=f"AEO Audit: {report.url}")
    table.add_column("Pillar", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Detail")

    table.add_row("Robots.txt AI Access", f"{report.robots.score:.1f}/25", report.robots.detail)
    table.add_row("llms.txt Presence", f"{report.llms_txt.score:.1f}/10", report.llms_txt.detail)
    schema_detail = report.schema_org.detail
    table.add_row("Schema.org JSON-LD", f"{report.schema_org.score:.1f}/25", schema_detail)
    table.add_row("Content Density", f"{report.content.score:.1f}/40", report.content.detail)

    console.print(table)
    console.print(f"  [bold]Overall:[/bold] [cyan]{report.overall_score:.1f}/100[/cyan]")


def register(app: typer.Typer) -> None:
    """Register the watch command onto the Typer app."""
    app.command(name="watch")(watch_command)


def watch_command(
    url: str = typer.Argument(help="URL to monitor continuously"),
    interval: int = typer.Option(
        3600, "--interval", "-i", help="Seconds between audits (default: 3600)"
    ),
    single: bool = typer.Option(
        False, "--single", help="Single-page audit only"
    ),
    max_pages: int = typer.Option(
        10, "--max-pages", "-n", help="Max pages for multi-page mode"
    ),
    timeout: int = typer.Option(
        15, "--timeout", "-t", help="HTTP timeout in seconds"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output JSON instead of Rich table"
    ),
    save: bool = typer.Option(
        False, "--save", help="Save each audit to history"
    ),
    fail_under: float = typer.Option(
        None, "--fail-under", help="Exit with error if score drops below threshold"
    ),
    bots: str = typer.Option(
        None, "--bots", help="Comma-separated custom AI bot list"
    ),
) -> None:
    """Continuously monitor a URL with periodic AEO audits."""
    if not url.startswith("http"):
        url = f"https://{url}"

    bots_list = [b.strip() for b in bots.split(",")] if bots else None

    console.print(f"[bold]Watching[/bold] {url} every {interval}s")
    console.print("Press Ctrl+C to stop.\n")

    run_count = 0
    try:
        while True:
            run_count += 1
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            console.print(f"[bold cyan]Run #{run_count}[/bold cyan] — {timestamp}")

            report = asyncio.run(audit_url(url, timeout=timeout, bots=bots_list))

            _render_report(report, json_output)

            if save:
                _save_to_history(report)

            if fail_under is not None and report.overall_score < fail_under:
                console.print(
                    f"\n[bold red]Score {report.overall_score:.1f} "
                    f"< --fail-under {fail_under}[/bold red]"
                )
                raise SystemExit(1)

            console.print()
            time.sleep(interval)

    except KeyboardInterrupt:
        s = "s" if run_count != 1 else ""
        console.print(f"\n[bold]Stopped[/bold] after {run_count} run{s}.")
