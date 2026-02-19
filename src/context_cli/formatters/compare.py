"""Rich table formatter for compare command output."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from context_cli.core.models import CompareReport

# Friendly pillar names for display
_PILLAR_NAMES: dict[str, str] = {
    "robots": "Robots.txt",
    "llms_txt": "llms.txt",
    "schema_org": "Schema.org",
    "content": "Content",
}


def _delta_text(delta: float) -> str:
    """Format a delta value with color and +/- sign."""
    if delta > 0:
        return f"[green]+{delta}[/green]"
    if delta < 0:
        return f"[red]{delta}[/red]"
    return "[dim]0[/dim]"


def render_compare(report: CompareReport, console: Console) -> None:
    """Render a compare report as a Rich table."""
    table = Table(title="Readiness Score Comparison", show_header=True, header_style="bold")
    table.add_column("Pillar", style="bold")
    table.add_column(report.url_a, justify="right")
    table.add_column(report.url_b, justify="right")
    table.add_column("Delta", justify="right")

    for p in report.pillars:
        name = _PILLAR_NAMES.get(p.pillar, p.pillar)
        table.add_row(
            f"{name} (/{p.max_score:.0f})",
            f"{p.score_a}",
            f"{p.score_b}",
            _delta_text(p.delta),
        )

    # Overall row
    table.add_section()
    table.add_row(
        "[bold]Overall (/100)[/bold]",
        f"[bold]{report.score_a}[/bold]",
        f"[bold]{report.score_b}[/bold]",
        _delta_text(report.delta),
    )

    console.print(table)

    # Winner summary
    if report.delta > 0:
        console.print(f"\n[green]Winner: {report.url_a}[/green] (by {report.delta} pts)")
    elif report.delta < 0:
        console.print(f"\n[green]Winner: {report.url_b}[/green] (by {-report.delta} pts)")
    else:
        console.print("\n[yellow]Tie — both URLs scored identically[/yellow]")
