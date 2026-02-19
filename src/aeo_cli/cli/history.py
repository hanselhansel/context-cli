"""History command — view and manage audit history."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from aeo_cli.core.history import HistoryDB


def register(app: typer.Typer) -> None:
    """Register the history command onto the Typer app."""
    app.command(name="history")(history_command)


def history_command(
    url: str = typer.Argument(help="URL to look up in audit history"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max entries to show"),
    show: int | None = typer.Option(
        None, "--show", help="Show full report for a specific entry ID"
    ),
    delete: bool = typer.Option(False, "--delete", help="Delete all history for this URL"),
) -> None:
    """View or manage audit history for a URL."""
    console = Console()
    db = HistoryDB()
    try:
        if delete:
            count = db.delete_url(url)
            if count:
                console.print(f"Deleted {count} history entries for {url}")
            else:
                console.print(f"No history found for {url}")
            return

        if show is not None:
            report = db.get_report(show)
            if report is None:
                console.print(f"Entry #{show} not found.")
                return
            if json_output:
                console.print(report.model_dump_json(indent=2))
            else:
                console.print(report.model_dump_json(indent=2))
            return

        entries = db.list_entries(url, limit=limit)
        if not entries:
            console.print(f"No history found for {url}")
            return

        if json_output:
            console.print(json.dumps([e.model_dump() for e in entries], indent=2))
            return

        table = Table(title=f"Audit History: {url}")
        table.add_column("ID", justify="right")
        table.add_column("Timestamp")
        table.add_column("Overall", justify="right")
        table.add_column("Robots", justify="right")
        table.add_column("llms.txt", justify="right")
        table.add_column("Schema", justify="right")
        table.add_column("Content", justify="right")

        for entry in entries:
            table.add_row(
                str(entry.id),
                entry.timestamp[:19],
                f"{entry.overall_score:.1f}",
                f"{entry.robots_score:.1f}",
                f"{entry.llms_txt_score:.1f}",
                f"{entry.schema_org_score:.1f}",
                f"{entry.content_score:.1f}",
            )

        console.print(table)
    finally:
        db.close()
