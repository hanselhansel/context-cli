"""Radar command — multi-model citation extraction and brand analysis."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer) -> None:
    """Register the radar command onto the Typer app."""

    @app.command()
    def radar(
        prompt: str = typer.Argument(help="Search prompt to send to AI models"),
        brand: list[str] = typer.Option(
            [], "--brand", "-b", help="Brand name to track (repeatable)"
        ),
        model: list[str] = typer.Option(
            ["gpt-4o-mini"], "--model", "-m", help="LLM model to query (repeatable)"
        ),
        runs: int = typer.Option(
            1, "--runs", "-r", help="Runs per model for statistical significance"
        ),
        json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Query AI models and analyze what they cite and recommend."""
        try:
            from context_cli.core.radar.query import query_models
        except ImportError:
            console.print(
                "[red]Error:[/red] litellm is required for the radar command.\n"
                "Install it with: [bold]pip install aeo-cli\\[generate][/bold]"
            )
            raise SystemExit(1)

        from context_cli.core.models import RadarConfig
        from context_cli.core.radar.analyzer import build_radar_report

        config = RadarConfig(
            prompt=prompt, models=model, brands=brand, runs_per_model=runs
        )

        try:
            with console.status(f"Querying {len(model)} model(s)..."):
                results = asyncio.run(query_models(config))
            report = build_radar_report(config, results)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        if json_output:
            console.print(report.model_dump_json(indent=2))
            return

        # Rich output
        console.print(f"\n[bold]Citation Radar: {report.prompt}[/bold]")
        console.print(f"  Models queried: {len(report.model_results)}")
        console.print(f"  Total citations: {report.total_citations}")

        if report.brand_mentions:
            console.print("\n[bold]Brand Mentions:[/bold]")
            for bm in report.brand_mentions:
                console.print(f"  {bm.brand}: {bm.count}x ({bm.sentiment})")

        if report.domain_breakdown:
            console.print("\n[bold]Source Domains:[/bold]")
            for dc in report.domain_breakdown:
                console.print(f"  {dc.domain} ({dc.category})")
