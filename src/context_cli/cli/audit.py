"""Lint command — single-page, multi-page, batch, and CI modes."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from context_cli.cli._audit_helpers import (
    _audit_quiet,
    _check_exit_conditions,
    _check_pillar_thresholds,
    _handle_baseline_compare,
    _handle_save_baseline,
    _run_batch_mode,
    _save_to_history,
    _send_webhook,
    _write_github_step_summary,
)
from context_cli.core.auditor import audit_site, audit_url
from context_cli.core.config import load_config
from context_cli.core.history import HistoryDB  # noqa: F401 — re-export for test patching
from context_cli.core.models import (
    AuditReport,
    OutputFormat,
    SiteAuditReport,
)
from context_cli.core.regression import (
    detect_regression,  # noqa: F401 — re-export for test patching
)
from context_cli.formatters.csv import (
    format_single_report_csv,
    format_site_report_csv,
)
from context_cli.formatters.markdown import (
    format_single_report_md,
    format_site_report_md,
)
from context_cli.formatters.verbose import (
    render_verbose_single,
    render_verbose_site,
)
from context_cli.formatters.verbose_panels import score_color as _score_color_impl

console = Console()


def _score_color(score: float, pillar: str) -> Text:
    """Return a Rich Text with the score colored by threshold."""
    return _score_color_impl(score, pillar)


def register(app: typer.Typer) -> None:
    """Register the lint command onto the Typer app."""

    @app.command("lint")
    def audit(
        url: str = typer.Argument(None, help="URL to lint for LLM readiness"),
        json_output: bool = typer.Option(
            False, "--json", help="Output raw JSON instead of Rich table"
        ),
        format: OutputFormat = typer.Option(
            None, "--format", "-f", help="Output format: json, csv, or markdown"
        ),
        single: bool = typer.Option(
            False, "--single", help="Single-page audit only (skip multi-page discovery)"
        ),
        max_pages: int = typer.Option(
            10, "--max-pages", "-n", help="Max pages to audit in multi-page mode"
        ),
        verbose: bool = typer.Option(
            False, "--verbose", "-v",
            help="Show detailed per-pillar breakdown with explanations",
        ),
        quiet: bool = typer.Option(
            False, "--quiet", "-q",
            help="Suppress output, exit code 0 if score >= 50, else 1",
        ),
        fail_under: float = typer.Option(
            None, "--fail-under",
            help="Exit code 1 if overall score is below this threshold (0-100)",
        ),
        fail_on_blocked_bots: bool = typer.Option(
            False, "--fail-on-blocked-bots",
            help="Exit code 2 if any AI bot is blocked by robots.txt",
        ),
        timeout: int = typer.Option(
            15, "--timeout", "-t", help="HTTP timeout in seconds (default: 15)"
        ),
        file: str = typer.Option(
            None, "--file", "-F",
            help="Path to .txt or .csv file with URLs (one per line)",
        ),
        concurrency: int = typer.Option(
            3, "--concurrency", help="Max concurrent audits in batch mode (default: 3)"
        ),
        bots: str = typer.Option(
            None, "--bots", help="Comma-separated custom AI bot list (overrides defaults)"
        ),
        save: bool = typer.Option(
            False, "--save",
            help="Save audit results to local history (~/.context-cli/history.db)",
        ),
        regression_threshold: float = typer.Option(
            5.0, "--regression-threshold",
            help="Score drop threshold to flag as regression (default: 5 points)",
        ),
        webhook: str = typer.Option(
            None, "--webhook",
            help="Webhook URL to POST audit results to (Slack/Discord/custom)",
        ),
        robots_min: float = typer.Option(
            None, "--robots-min",
            help="Minimum robots.txt pillar score (exit 1 if below)",
        ),
        schema_min: float = typer.Option(
            None, "--schema-min",
            help="Minimum schema.org pillar score (exit 1 if below)",
        ),
        content_min: float = typer.Option(
            None, "--content-min",
            help="Minimum content density pillar score (exit 1 if below)",
        ),
        llms_min: float = typer.Option(
            None, "--llms-min",
            help="Minimum llms.txt pillar score (exit 1 if below)",
        ),
        overall_min: float = typer.Option(
            None, "--overall-min",
            help="Minimum overall Readiness Score (exit 1 if below)",
        ),
        save_baseline: str = typer.Option(
            None, "--save-baseline",
            help="Save audit scores as a JSON baseline file at this path",
        ),
        baseline: str = typer.Option(
            None, "--baseline",
            help="Compare audit against a saved baseline file (exit 1 on regression)",
        ),
        max_context_waste: float = typer.Option(
            None, "--max-context-waste",
            help="Maximum acceptable context waste %% (exit 1 if exceeded)",
        ),
        require_llms_txt: bool = typer.Option(
            False, "--require-llms-txt",
            help="Fail if llms.txt is not present",
        ),
        require_bot_access: bool = typer.Option(
            False, "--require-bot-access",
            help="Fail if any AI bot is blocked",
        ),
    ) -> None:
        """Run a Context Lint on a URL and display the results."""
        # Load config file defaults
        cfg = load_config()

        # Apply config defaults (CLI flags override when explicitly set)
        effective_timeout = cfg.timeout if timeout == 15 else timeout
        effective_max_pages = cfg.max_pages if max_pages == 10 else max_pages
        effective_save = save or cfg.save
        effective_verbose = verbose or cfg.verbose
        effective_single = single or cfg.single
        effective_threshold = (
            cfg.regression_threshold if regression_threshold == 5.0 else regression_threshold
        )

        # --json flag is a shortcut for --format json
        if json_output and format is None:
            format = OutputFormat.json

        # Apply config format if no CLI format specified
        if format is None and cfg.format is not None:
            try:
                format = OutputFormat(cfg.format)
            except ValueError:
                pass

        # Parse --bots into a list (CLI overrides config)
        if bots:
            bots_list: list[str] | None = [b.strip() for b in bots.split(",")]
        elif cfg.bots:
            bots_list = cfg.bots
        else:
            bots_list = None

        # Batch mode: --file flag
        if file:
            _run_batch_mode(
                file, format, effective_single, effective_max_pages,
                effective_timeout, concurrency,
                bots=bots_list, console=console,
            )
            return

        if not url:
            console.print(
                "[red]Error:[/red] Provide a URL argument or use --file for batch mode."
            )
            raise SystemExit(1)

        if not url.startswith("http"):
            url = f"https://{url}"

        if quiet:
            threshold_val = fail_under if fail_under is not None else 50
            _audit_quiet(
                url, effective_single, effective_max_pages, threshold_val,
                fail_on_blocked_bots, effective_timeout, bots=bots_list,
            )
            return  # pragma: no cover — _audit_quiet always raises SystemExit

        # Normal flow
        report = _run_audit(
            url, effective_single, effective_max_pages, effective_timeout, bots=bots_list,
        )
        _render_output(report, format, effective_verbose, effective_single)

        if webhook:
            _send_webhook(webhook, report, console=console)

        if effective_save:
            if isinstance(report, AuditReport):
                _save_to_history(report, console, threshold=effective_threshold)
            else:
                console.print(
                    "[yellow]Note:[/yellow] --save stores single-page audits only. "
                    "Use --single for history tracking."
                )

        # Baseline save/compare (only for single-page AuditReport)
        if save_baseline and isinstance(report, AuditReport):
            _handle_save_baseline(report, save_baseline, console=console)

        if baseline and isinstance(report, AuditReport):
            _handle_baseline_compare(
                report, baseline, effective_threshold, console,
            )

        _write_github_step_summary(report, fail_under)

        # Per-pillar threshold checking
        _check_pillar_thresholds(
            report, robots_min, schema_min, content_min, llms_min, overall_min,
            console=console,
            max_context_waste=max_context_waste,
            require_llms_txt=require_llms_txt,
            require_bot_access=require_bot_access,
        )

        if fail_under is not None or fail_on_blocked_bots:
            _check_exit_conditions(report, fail_under, fail_on_blocked_bots)


def _run_audit(
    url: str,
    single: bool,
    max_pages: int,
    timeout: int = 15,
    *,
    bots: list[str] | None = None,
) -> AuditReport | SiteAuditReport:
    """Execute the audit and return the report."""
    if single:
        with console.status(f"Auditing {url}..."):
            return asyncio.run(audit_url(url, timeout=timeout, bots=bots))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"Discovering pages on {url}...", total=max_pages)

        def on_progress(msg: str) -> None:
            progress.update(task_id, description=msg, advance=1)

        report = asyncio.run(
            audit_site(
                url, max_pages=max_pages, timeout=timeout,
                progress_callback=on_progress, bots=bots,
            )
        )
        progress.update(task_id, description="Done", completed=max_pages)
    return report


def _render_output(
    report: AuditReport | SiteAuditReport,
    format: OutputFormat | None,
    verbose: bool,
    single: bool,
) -> None:
    """Render the audit report in the requested format."""
    if format == OutputFormat.json:
        console.print(report.model_dump_json(indent=2))
        return
    if format == OutputFormat.csv:
        if isinstance(report, SiteAuditReport):
            console.print(format_site_report_csv(report), end="")
        else:
            console.print(format_single_report_csv(report), end="")
        return
    if format == OutputFormat.markdown:
        if isinstance(report, SiteAuditReport):
            console.print(format_site_report_md(report), end="")
        else:
            console.print(format_single_report_md(report), end="")
        return
    if format == OutputFormat.html:
        from pathlib import Path

        from context_cli.formatters.html import (
            format_single_report_html,
            format_site_report_html,
        )

        if isinstance(report, SiteAuditReport):
            html_str = format_site_report_html(report)
        else:
            html_str = format_single_report_html(report)
        slug = report.url.replace("https://", "").replace("http://", "").replace("/", "_")
        filename = f"context-report-{slug}.html"
        Path(filename).write_text(html_str)
        console.print(f"[green]HTML report saved to:[/green] {filename}")
        return

    # Rich output
    if isinstance(report, SiteAuditReport):
        from context_cli.formatters.rich_output import render_site_report

        render_site_report(report, console)
        if verbose:
            render_verbose_site(report, console)
        return

    # Single-page output — linter style when lint_result available, fallback to table
    if report.lint_result:
        from context_cli.formatters.rich_output import render_single_report

        render_single_report(report, console)
    else:
        table = Table(title=f"Context Lint: {report.url}")
        table.add_column("Pillar", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Detail")

        rows = [
            ("Robots.txt AI Access", report.robots.score, "robots", report.robots.detail),
            ("llms.txt Presence", report.llms_txt.score, "llms_txt", report.llms_txt.detail),
            (
                "Schema.org JSON-LD",
                report.schema_org.score, "schema_org", report.schema_org.detail,
            ),
            ("Content Density", report.content.score, "content", report.content.detail),
        ]
        for label, score, pillar, detail in rows:
            table.add_row(label, _score_color(score, pillar), detail)

        console.print(table)
        console.print(
            f"\n[bold]Overall Readiness Score:[/bold]"
            f" [cyan]{report.overall_score}/100[/cyan]"
        )

        if report.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for err in report.errors:
                console.print(f"  \u2022 {err}")

    if verbose:
        render_verbose_single(report, console)
