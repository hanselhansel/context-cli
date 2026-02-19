"""Generate command — LLM-powered llms.txt and schema.jsonld generation."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from context_cli.core.models import BatchGenerateConfig, GenerateConfig, ProfileType

console = Console()


def register(app: typer.Typer) -> None:
    """Register the generate and generate-batch commands onto the Typer app."""

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
            from context_cli.core.generate import generate_assets
        except ImportError:
            console.print(
                "[red]Error:[/red] litellm is required for the generate command.\n"
                "Install it with: [bold]pip install aeo-cli\\[generate][/bold]"
            )
            raise SystemExit(1)

        config = GenerateConfig(
            url=url, profile=profile, model=model, output_dir=output_dir
        )

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

    @app.command("generate-batch")
    def generate_batch_cmd(
        file: str = typer.Argument(help="File with URLs (one per line, .txt or .csv)"),
        profile: ProfileType = typer.Option(
            ProfileType.generic, "--profile", "-p", help="Industry profile for prompt tuning"
        ),
        model: str = typer.Option(
            None, "--model", "-m", help="LLM model to use (auto-detected if not set)"
        ),
        output_dir: str = typer.Option(
            "./aeo-output", "--output-dir", "-o", help="Directory to write generated files"
        ),
        concurrency: int = typer.Option(
            3, "--concurrency", "-c", help="Max concurrent generations"
        ),
        json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
    ) -> None:
        """Batch generate llms.txt and schema.jsonld for multiple URLs."""
        # Validate file exists
        file_path = Path(file)
        if not file_path.is_file():
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise SystemExit(1)

        # Parse URLs from file
        urls: list[str] = []
        for line in file_path.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                if not stripped.startswith("http"):
                    stripped = f"https://{stripped}"
                urls.append(stripped)

        if not urls:
            console.print("[red]Error:[/red] No URLs found in file")
            raise SystemExit(1)

        try:
            from context_cli.core.generate.batch import generate_batch
        except ImportError:
            console.print(
                "[red]Error:[/red] litellm is required for the generate-batch command.\n"
                "Install it with: [bold]pip install aeo-cli\\[generate][/bold]"
            )
            raise SystemExit(1)

        config = BatchGenerateConfig(
            urls=urls,
            profile=profile,
            model=model,
            output_dir=output_dir,
            concurrency=concurrency,
        )

        try:
            with console.status(f"Batch generating assets for {len(urls)} URLs..."):
                result = asyncio.run(generate_batch(config))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        if json_output:
            console.print(result.model_dump_json(indent=2))
            return

        # Rich summary output
        console.print(
            f"\n[bold green]Batch generation complete[/bold green] — "
            f"{result.succeeded}/{result.total} succeeded"
        )
        console.print(f"  [bold]Model:[/bold] {result.model_used}")
        console.print(f"  [bold]Profile:[/bold] {result.profile.value}")
        console.print(f"  [bold]Output:[/bold] {result.output_dir}")

        for pr in result.results:
            if pr.success:
                console.print(f"  [green]✓[/green] {pr.url}")
            else:
                console.print(f"  [red]✗[/red] {pr.url}: {pr.error}")
