"""Rich console renderers for lint reports (linter-style aesthetic)."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from context_cli.core.models import (
    AuditReport,
    BatchAuditReport,
    LintResult,
    SiteAuditReport,
)
from context_cli.formatters.verbose import overall_color, score_color

# ── Linter-style helpers ────────────────────────────────────────────────────


def _check_status_markup(severity: str, passed: bool) -> str:
    """Return Rich markup for a lint check status badge."""
    if severity == "warn":
        return "[yellow][WARN][/yellow]"
    if passed:
        return "[green][PASS][/green]"
    return "[red][FAIL][/red]"


def _render_lint_checks(lr: LintResult, console: Console) -> None:
    """Render the pass/warn/fail lint checks in linter style."""
    for check in lr.checks:
        status = _check_status_markup(check.severity, check.passed)
        console.print(f"  {status} {check.name:<20s} {check.detail}")


def _render_token_analysis(lr: LintResult, console: Console) -> None:
    """Render the token analysis section in linter style."""
    dash_line = "\u2500" * 41
    console.print(f"\n  \u2500\u2500 Token Analysis {dash_line}")
    console.print(f"  Raw HTML tokens:  {lr.raw_tokens:>10,}")
    console.print(f"  Clean MD tokens:  {lr.clean_tokens:>10,}")
    waste_color = (
        "green" if lr.context_waste_pct < 30
        else ("yellow" if lr.context_waste_pct < 70 else "red")
    )
    wasted = lr.raw_tokens - lr.clean_tokens
    waste_suffix = f"  ({wasted:,} wasted tokens)" if lr.raw_tokens > 0 else ""
    console.print(
        f"  Context Waste:    "
        f"[{waste_color}]{lr.context_waste_pct:>9.1f}%[/{waste_color}]"
        f"{waste_suffix}"
    )


def _render_verdict(lr: LintResult, console: Console) -> None:
    """Render a RESULT verdict line summarizing pass/fail/warn counts."""
    passed = sum(1 for c in lr.checks if c.severity != "warn" and c.passed)
    failed = sum(1 for c in lr.checks if c.severity != "warn" and not c.passed)
    warned = sum(1 for c in lr.checks if c.severity == "warn")

    parts = [
        f"[green]{passed} passed[/green]",
        f"[red]{failed} failed[/red]",
    ]
    if warned:
        parts.append(f"[yellow]{warned} warning{'s' if warned != 1 else ''}[/yellow]")

    console.print(f"\n  [bold]RESULT:[/bold] {', '.join(parts)}")


def _render_diagnostics(lr: LintResult, console: Console) -> None:
    """Render the diagnostics section in linter style."""
    if not lr.diagnostics:
        return

    dash_line = "\u2500" * 43
    console.print(f"\n  \u2500\u2500 Diagnostics {dash_line}")
    for d in lr.diagnostics:
        color = (
            "red" if d.severity == "error"
            else ("yellow" if d.severity == "warn" else "cyan")
        )
        console.print(f"  [{color}]{d.code}[/{color}]  {d.message}")

    errors = sum(1 for d in lr.diagnostics if d.severity == "error")
    warns = sum(1 for d in lr.diagnostics if d.severity == "warn")
    console.print(
        f"\n  {warns} warning{'s' if warns != 1 else ''},"
        f" {errors} error{'s' if errors != 1 else ''}"
    )


# ── Single-page linter output ──────────────────────────────────────────────


def render_single_report(report: AuditReport, console: Console) -> None:
    """Render a single-page audit report in linter style."""
    console.print(f"\n  [bold]LINT[/bold]  {report.url}\n")

    if report.lint_result:
        lr = report.lint_result
        _render_lint_checks(lr, console)
        _render_token_analysis(lr, console)
        _render_diagnostics(lr, console)
        _render_verdict(lr, console)

    if report.errors:
        console.print("[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  \u2022 {err}")


# ── Site-level linter output ───────────────────────────────────────────────


def render_site_report(report: SiteAuditReport, console: Console) -> None:
    """Render a multi-page site audit report using Rich."""
    header_lines = [
        f"[bold]Domain:[/bold] {report.domain}",
        f"[bold]Discovery:[/bold] {report.discovery.method} \u2014 {report.discovery.detail}",
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

    # Linter-style lint result display
    if report.lint_result:
        lr = report.lint_result
        console.print()
        _render_lint_checks(lr, console)
        _render_token_analysis(lr, console)
        _render_diagnostics(lr, console)
        _render_verdict(lr, console)

    if report.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in report.errors:
            console.print(f"  \u2022 {err}")


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
            console.print(f"  \u2022 {url}: {err}")
