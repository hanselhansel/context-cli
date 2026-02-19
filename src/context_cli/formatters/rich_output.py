"""Rich console renderers for site-level and batch audit reports."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from context_cli.core.models import BatchAuditReport, SiteAuditReport
from context_cli.formatters.verbose import overall_color, score_color


def render_site_report(report: SiteAuditReport, console: Console) -> None:
    """Render a multi-page site audit report using Rich."""
    header_lines = [
        f"[bold]Domain:[/bold] {report.domain}",
        f"[bold]Discovery:[/bold] {report.discovery.method} — {report.discovery.detail}",
        f"[bold]Pages audited:[/bold] {report.pages_audited}"
        + (f"  ([red]{report.pages_failed} failed[/red])" if report.pages_failed else ""),
    ]
    console.print(Panel("\n".join(header_lines), title=f"Context Lint Report: {report.url}"))

    site_table = Table(title="Site-Wide Scores")
    site_table.add_column("Pillar", style="bold")
    site_table.add_column("Score", justify="right")
    site_table.add_column("Detail")
    site_table.add_row(
        "Robots.txt AI Access",
        score_color(report.robots.score, "robots"),
        report.robots.detail,
    )
    site_table.add_row(
        "llms.txt Presence",
        score_color(report.llms_txt.score, "llms_txt"),
        report.llms_txt.detail,
    )
    console.print(site_table)

    agg_table = Table(title="Aggregate Page Scores")
    agg_table.add_column("Pillar", style="bold")
    agg_table.add_column("Avg Score", justify="right")
    agg_table.add_column("Detail")
    agg_table.add_row(
        "Schema.org JSON-LD",
        score_color(report.schema_org.score, "schema_org"),
        report.schema_org.detail,
    )
    agg_table.add_row(
        "Content Density",
        score_color(report.content.score, "content"),
        report.content.detail,
    )
    console.print(agg_table)

    if report.pages:
        page_table = Table(title="Per-Page Breakdown")
        page_table.add_column("URL", max_width=60)
        page_table.add_column("Schema", justify="right")
        page_table.add_column("Content", justify="right")
        page_table.add_column("Total", justify="right")
        for page in report.pages:
            total = page.schema_org.score + page.content.score
            page_table.add_row(
                page.url,
                score_color(page.schema_org.score, "schema_org"),
                score_color(page.content.score, "content"),
                Text(f"{total}", style=overall_color(total)),
            )
        console.print(page_table)

    color = overall_color(report.overall_score)
    console.print(
        f"\n[bold]Overall Readiness Score:[/bold] [{color}]{report.overall_score}/100[/{color}]"
    )

    if report.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  • {err}")


def render_batch_rich(batch_report: BatchAuditReport, console: Console) -> None:
    """Render batch audit results as a Rich summary table."""
    table = Table(title=f"Batch Context Lint ({len(batch_report.reports)} URLs)")
    table.add_column("URL", max_width=50)
    table.add_column("Score", justify="right")
    table.add_column("Robots", justify="right")
    table.add_column("llms.txt", justify="right")
    table.add_column("Schema", justify="right")
    table.add_column("Content", justify="right")

    for report in batch_report.reports:
        color = overall_color(report.overall_score)
        table.add_row(
            report.url,
            Text(f"{report.overall_score}", style=color),
            f"{report.robots.score}",
            f"{report.llms_txt.score}",
            f"{report.schema_org.score}",
            f"{report.content.score}",
        )

    console.print(table)

    if batch_report.errors:
        console.print("\n[bold red]Failed URLs:[/bold red]")
        for url, err in batch_report.errors.items():
            console.print(f"  • {url}: {err}")
