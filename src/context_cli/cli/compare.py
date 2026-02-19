"""Compare command — side-by-side readiness comparison of two URLs."""

from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console

from context_cli.core.compare import compare_urls
from context_cli.formatters.compare import render_compare


def register(app: typer.Typer) -> None:
    """Register the compare command onto the Typer app."""
    app.command(name="compare")(compare_command)


def compare_command(
    url_a: str = typer.Argument(help="First URL to audit"),
    url_b: str = typer.Argument(help="Second URL to audit"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    timeout: int = typer.Option(15, "--timeout", "-t", help="HTTP timeout in seconds"),
    bots: str | None = typer.Option(None, "--bots", help="Comma-separated bot names"),
) -> None:
    """Compare Readiness Scores of two URLs side-by-side."""
    bots_list = [b.strip() for b in bots.split(",")] if bots else None
    report = asyncio.run(compare_urls(url_a, url_b, timeout=timeout, bots=bots_list))

    if json_output:
        typer.echo(json.dumps(report.model_dump(), indent=2))
    else:
        console = Console()
        render_compare(report, console)
