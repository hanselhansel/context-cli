"""Leaderboard command -- batch-audit URLs and rank by token efficiency."""

from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from context_cli.core.auditor import audit_url
from context_cli.core.batch import parse_url_file
from context_cli.core.models import AuditReport

console = Console()


def register(app: typer.Typer) -> None:
    """Register the leaderboard command onto the Typer app."""

    @app.command("leaderboard")
    def leaderboard(
        source: str = typer.Argument(
            ..., help="Path to .txt/.csv file with URLs, or '-' for stdin"
        ),
        output: str = typer.Option(
            None, "--output", "-o", help="Write leaderboard to file (default: stdout)"
        ),
        waste_threshold: float = typer.Option(
            70.0, "--waste-threshold", help="Max waste %% for RAG Ready (default: 70)"
        ),
        timeout: int = typer.Option(
            15, "--timeout", "-t", help="HTTP timeout per URL (default: 15s)"
        ),
        concurrency: int = typer.Option(
            3, "--concurrency", help="Max concurrent audits (default: 3)"
        ),
        format: str = typer.Option(
            "markdown", "--format", "-f",
            help="Output format: markdown or json (default: markdown)"
        ),
    ) -> None:
        """Batch-audit URLs and rank by token efficiency (lowest waste first)."""
        # Read URLs
        if source == "-":
            raw = sys.stdin.read()
            urls = [
                line.strip()
                for line in raw.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            urls = [u if u.startswith("http") else f"https://{u}" for u in urls]
        else:
            try:
                urls = parse_url_file(source)
            except FileNotFoundError:
                console.print(f"[red]Error:[/red] File not found: {source}")
                raise SystemExit(1)

        if not urls:
            console.print("[yellow]No URLs found.[/yellow]")
            raise SystemExit(1)

        # Run audits with progress bar
        reports: list[AuditReport] = []
        errors: dict[str, str] = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task_id = progress.add_task("Auditing URLs...", total=len(urls))

            async def _audit_all_with_progress() -> None:
                sem = asyncio.Semaphore(concurrency)

                async def _one(url: str) -> None:
                    async with sem:
                        try:
                            r = await audit_url(url, timeout=timeout)
                            reports.append(r)
                        except Exception as e:
                            errors[url] = str(e)
                        finally:
                            progress.advance(task_id)

                tasks = [asyncio.create_task(_one(u)) for u in urls]
                await asyncio.gather(*tasks)

            asyncio.run(_audit_all_with_progress())

        if not reports:
            console.print("[red]All audits failed.[/red]")
            for url, err in errors.items():
                console.print(f"  {url}: {err}")
            raise SystemExit(1)

        # Generate output
        from context_cli.formatters.leaderboard import (
            format_leaderboard_json,
            format_leaderboard_md,
        )

        if format == "json":
            result = format_leaderboard_json(reports, waste_threshold)
        else:
            result = format_leaderboard_md(reports, waste_threshold)

        if output:
            from pathlib import Path

            Path(output).write_text(result)
            console.print(f"[green]Leaderboard saved to:[/green] {output}")
        else:
            console.print(result, end="")

        if errors:
            console.print(f"\n[yellow]{len(errors)} URL(s) failed:[/yellow]")
            for url, err in errors.items():
                console.print(f"  {url}: {err}")
