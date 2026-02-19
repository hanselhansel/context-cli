"""Generate command — LLM-powered llms.txt and schema.jsonld generation."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from aeo_cli.core.models import GenerateConfig, ProfileType

console = Console()


def register(app: typer.Typer) -> None:
    """Register the generate command onto the Typer app."""

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
