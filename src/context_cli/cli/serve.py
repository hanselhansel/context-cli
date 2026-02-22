"""CLI command for the markdown reverse-proxy server."""

from __future__ import annotations

import typer
from aiohttp import web
from rich.console import Console

from context_cli.core.serve.proxy import create_proxy_app

console = Console()


def register(app: typer.Typer) -> None:
    """Register the ``serve`` command on the given Typer app."""

    @app.command()
    def serve(
        upstream: str = typer.Option(
            ..., "--upstream", "-u", help="Upstream server URL to proxy",
        ),
        port: int = typer.Option(
            8080, "--port", "-p", help="Port to listen on",
        ),
        host: str = typer.Option(
            "0.0.0.0", "--host", "-H", help="Host/interface to bind",
        ),
    ) -> None:
        """Start a reverse proxy that serves HTML as markdown for LLM clients."""
        console.print(
            f"[bold green]Proxy[/bold green] {upstream} -> "
            f"[cyan]{host}:{port}[/cyan]  "
            f"(Accept: text/markdown -> auto-convert)"
        )
        proxy_app = create_proxy_app(upstream)
        web.run_app(proxy_app, host=host, port=port, print=None)
