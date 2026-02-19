"""MCP server command — starts the FastMCP stdio server."""

from __future__ import annotations

import typer


def register(app: typer.Typer) -> None:
    """Register the mcp command onto the Typer app."""

    @app.command()
    def mcp() -> None:
        """Start the AEO-CLI MCP server (stdio transport)."""
        from context_cli.server import mcp as mcp_server

        mcp_server.run(transport="stdio")
