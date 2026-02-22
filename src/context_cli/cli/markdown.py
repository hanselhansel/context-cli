"""CLI command for HTML-to-Markdown conversion."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from context_cli.core.markdown_engine.converter import convert_url_to_markdown

console = Console()


def register(app: typer.Typer) -> None:
    """Register the 'markdown' command on the given Typer app."""

    @app.command()
    def markdown(
        url: str = typer.Argument(help="URL to convert to markdown"),
        stats: bool = typer.Option(
            False, "--stats", "-s", help="Show conversion statistics",
        ),
        output: str | None = typer.Option(
            None, "--output", "-o", help="Write markdown to file",
        ),
    ) -> None:
        """Convert a URL's HTML content to clean, agent-friendly markdown."""
        try:
            md_text, md_stats = asyncio.run(convert_url_to_markdown(url))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

        if output:
            Path(output).write_text(md_text)
            console.print(f"[green]Markdown written to {output}[/green]")
        else:
            console.print(md_text)

        if stats:
            console.print(Panel(
                f"Raw HTML: {md_stats['raw_html_chars']:,} chars"
                f" ({md_stats['raw_tokens']:,} tokens)\n"
                f"Clean MD: {md_stats['clean_md_chars']:,} chars"
                f" ({md_stats['clean_tokens']:,} tokens)\n"
                f"Reduction: {md_stats['reduction_pct']}%",
                title="Conversion Stats",
                border_style="green",
            ))
