"""Benchmark command — Share-of-Recommendation tracking across AI models."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from context_cli.core.models import BenchmarkConfig, BenchmarkReport

console = Console()


def _run_benchmark(config: BenchmarkConfig) -> BenchmarkReport:
    """Run the full benchmark pipeline: dispatch -> judge -> compute report.

    Separated for easy mocking in tests.
    """
    from context_cli.core.benchmark.dispatcher import dispatch_queries
    from context_cli.core.benchmark.judge import judge_all
    from context_cli.core.benchmark.metrics import compute_report

    results = asyncio.run(dispatch_queries(config))
    judged = asyncio.run(judge_all(results, config.brand, config.competitors))
    return compute_report(config, judged)


def register(app: typer.Typer) -> None:
    """Register the benchmark command onto the Typer app."""

    @app.command()
    def benchmark(
        prompts_file: str = typer.Argument(help="Path to prompts file (CSV or text, one per line)"),
        brand: str = typer.Option(..., "--brand", "-b", help="Target brand to track"),
        competitor: list[str] = typer.Option(
            [], "--competitor", "-c", help="Competitor brand (repeatable)"
        ),
        model: list[str] = typer.Option(
            ["gpt-4o-mini"], "--model", "-m", help="LLM model to query (repeatable)"
        ),
        runs: int = typer.Option(3, "--runs", "-r", help="Runs per model per prompt"),
        yes: bool = typer.Option(False, "--yes", "-y", help="Skip cost confirmation"),
        json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Run a Share-of-Recommendation benchmark across AI models."""
        # Validate prompts file exists
        file_path = Path(prompts_file)
        if not file_path.is_file():
            console.print(f"[red]Error:[/red] File not found: {prompts_file}")
            raise SystemExit(1)

        # Load prompts
        try:
            from context_cli.core.benchmark.loader import load_prompts
        except ImportError:
            console.print(
                "[red]Error:[/red] litellm is required for the benchmark command.\n"
                "Install it with: [bold]pip install context-cli\\[generate][/bold]"
            )
            raise SystemExit(1)

        try:
            entries = load_prompts(str(file_path))
        except ImportError:
            console.print(
                "[red]Error:[/red] litellm is required for the benchmark command.\n"
                "Install it with: [bold]pip install context-cli\\[generate][/bold]"
            )
            raise SystemExit(1)

        if not entries:
            console.print("[red]Error:[/red] No prompts found in file")
            raise SystemExit(1)

        # Build config
        config = BenchmarkConfig(
            prompts=entries,
            brand=brand,
            competitors=competitor,
            models=model,
            runs_per_model=runs,
        )

        # Estimate cost
        from context_cli.core.benchmark.cost import estimate_benchmark_cost, format_cost

        estimated = estimate_benchmark_cost(config)
        cost_str = format_cost(estimated)

        # Cost confirmation
        if not yes:
            console.print(
                f"\n[bold]Benchmark plan:[/bold] {len(entries)} prompts x "
                f"{len(model)} model(s) x {runs} runs"
            )
            console.print(f"[bold]Estimated cost:[/bold] {cost_str}")
            confirm = typer.confirm("Proceed?")
            if not confirm:
                console.print("[yellow]Aborted.[/yellow]")
                raise SystemExit(1)

        # Run benchmark
        try:
            with console.status("Running benchmark..."):
                report = _run_benchmark(config)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        # Output
        if json_output:
            console.print(report.model_dump_json(indent=2))
            return

        # Rich output
        console.print(f"\n[bold]Benchmark Report: {report.config.brand}[/bold]")
        console.print(f"  Competitors: {', '.join(report.config.competitors)}")
        console.print(f"  Total queries: {report.total_queries}")
        console.print(f"  Estimated cost: {cost_str}")
        console.print(
            f"\n  [bold]Overall mention rate:[/bold] "
            f"{report.overall_mention_rate:.0%}"
        )
        console.print(
            f"  [bold]Overall recommendation rate:[/bold] "
            f"{report.overall_recommendation_rate:.0%}"
        )

        # Per-model summaries
        if report.model_summaries:
            console.print("\n[bold]Per-Model Summary:[/bold]")
            for ms in report.model_summaries:
                console.print(
                    f"  {ms.model}: mention={ms.mention_rate:.0%} "
                    f"recommend={ms.recommendation_rate:.0%}"
                )

        # Per-prompt results
        unique_prompts = sorted({r.prompt.prompt for r in report.results if not r.error})
        if unique_prompts:
            console.print("\n[bold]Prompts Evaluated:[/bold]")
            for p in unique_prompts:
                console.print(f"  {p[:60]}")
