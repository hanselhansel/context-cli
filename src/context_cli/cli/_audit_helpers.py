"""Extracted helper functions for the lint command."""

from __future__ import annotations

import asyncio
import os

from rich.console import Console

from context_cli.core.models import (
    AuditReport,
    OutputFormat,
    SiteAuditReport,
)


def _save_to_history(
    report: AuditReport, con: Console, threshold: float = 5.0,
) -> None:
    """Save report to history and check for regression against previous audit."""
    import context_cli.cli.audit as _audit_mod

    db = _audit_mod.HistoryDB()
    try:
        previous = db.get_latest_report(report.url)
        db.save(report)
        con.print("[green]Saved to history.[/green]")

        if previous is not None:
            result = _audit_mod.detect_regression(
                report, previous, threshold=threshold,
            )
            if result.has_regression:
                con.print(
                    f"[bold red]Regression detected:[/bold red] "
                    f"score dropped {abs(result.delta):.1f} points "
                    f"({result.previous_score:.0f} -> "
                    f"{result.current_score:.0f})"
                )
    except Exception as exc:
        con.print(f"[yellow]History save error:[/yellow] {exc}")
    finally:
        db.close()


def _send_webhook(
    webhook_url: str,
    report: AuditReport | SiteAuditReport,
    *,
    console: Console,
) -> None:
    """Send audit results to a webhook URL (best-effort, never crashes)."""
    from context_cli.core.webhook import build_webhook_payload, send_webhook

    try:
        payload = build_webhook_payload(report)
        success = asyncio.run(send_webhook(webhook_url, payload))
        if success:
            console.print("[green]Webhook delivered successfully.[/green]")
        else:
            console.print(
                "[yellow]Webhook delivery failed (non-2xx response).[/yellow]"
            )
    except Exception as exc:
        console.print(f"[yellow]Webhook error:[/yellow] {exc}")


def _handle_save_baseline(
    report: AuditReport, path_str: str, *, console: Console,
) -> None:
    """Save audit scores as a baseline JSON file."""
    from pathlib import Path

    from context_cli.core.ci.baseline import save_baseline

    try:
        save_baseline(report, Path(path_str))
        console.print(f"[green]Baseline saved to:[/green] {path_str}")
    except Exception as exc:
        console.print(f"[yellow]Baseline save error:[/yellow] {exc}")


def _handle_baseline_compare(
    report: AuditReport,
    path_str: str,
    threshold: float,
    con: Console,
) -> None:
    """Compare audit against a saved baseline and exit 1 on regression."""
    from pathlib import Path

    from context_cli.core.ci.baseline import compare_baseline, load_baseline

    try:
        baseline = load_baseline(Path(path_str))
    except FileNotFoundError:
        con.print(f"[red]Error:[/red] Baseline file not found: {path_str}")
        raise SystemExit(1)

    result = compare_baseline(report, baseline, threshold=threshold)

    if result.passed:
        con.print(
            "[green]Baseline comparison passed:[/green] No regressions detected."
        )
    else:
        con.print(
            "[bold red]Baseline comparison failed"
            " \u2014 regressions detected:[/bold red]"
        )
        for reg in result.regressions:
            con.print(
                f"  [red]{reg.pillar}:[/red] "
                f"{reg.previous_score:.1f} -> {reg.current_score:.1f} "
                f"(delta: {reg.delta:+.1f})"
            )
        raise SystemExit(1)


def _check_pillar_thresholds(
    report: AuditReport | SiteAuditReport,
    robots_min: float | None,
    schema_min: float | None,
    content_min: float | None,
    llms_min: float | None,
    overall_min: float | None,
    *,
    console: Console,
    max_context_waste: float | None = None,
    require_llms_txt: bool = False,
    require_bot_access: bool = False,
) -> None:
    """Check per-pillar thresholds and exit 1 if any fail."""
    has_any = any(
        v is not None
        for v in (
            robots_min, schema_min, content_min, llms_min,
            overall_min, max_context_waste,
        )
    ) or require_llms_txt or require_bot_access
    if not has_any:
        return

    from context_cli.core.ci.thresholds import check_thresholds
    from context_cli.core.models import PillarThresholds

    thresholds = PillarThresholds(
        robots_min=robots_min,
        schema_min=schema_min,
        content_min=content_min,
        llms_min=llms_min,
        overall_min=overall_min,
        max_context_waste=max_context_waste,
        require_llms_txt=require_llms_txt,
        require_bot_access=require_bot_access,
    )
    result = check_thresholds(report, thresholds)
    if not result.passed:
        console.print("\n[bold red]Pillar threshold failures:[/bold red]")
        for failure in result.failures:
            console.print(
                f"  [red]FAIL[/red] {failure.pillar}: "
                f"{failure.actual:.1f} < {failure.minimum:.1f} (minimum)"
            )
        raise SystemExit(1)


def _check_exit_conditions(
    report: AuditReport | SiteAuditReport,
    fail_under: float | None,
    fail_on_blocked_bots: bool,
) -> None:
    """Check CI exit conditions and raise SystemExit if breached."""
    if fail_on_blocked_bots and report.robots.found:
        if any(not b.allowed for b in report.robots.bots):
            raise SystemExit(2)
    if fail_under is not None and report.overall_score < fail_under:
        raise SystemExit(1)


def _write_github_step_summary(
    report: AuditReport | SiteAuditReport,
    fail_under: float | None,
) -> None:
    """Write CI summary to $GITHUB_STEP_SUMMARY if in GitHub Actions."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    from context_cli.formatters.ci_summary import format_ci_summary

    md = format_ci_summary(report, fail_under=fail_under)
    with open(summary_path, "a") as f:
        f.write(md)


def _audit_quiet(
    url: str,
    single: bool,
    max_pages: int,
    threshold: float = 50,
    fail_on_blocked_bots: bool = False,
    timeout: int = 15,
    *,
    bots: list[str] | None = None,
) -> None:
    """Run audit silently \u2014 exit based on threshold and bot access."""
    import context_cli.cli.audit as _audit_mod

    report: AuditReport | SiteAuditReport
    if single:
        report = asyncio.run(
            _audit_mod.audit_url(url, timeout=timeout, bots=bots),
        )
    else:
        report = asyncio.run(
            _audit_mod.audit_site(
                url, max_pages=max_pages, timeout=timeout, bots=bots,
            )
        )

    if fail_on_blocked_bots and report.robots.found:
        if any(not b.allowed for b in report.robots.bots):
            raise SystemExit(2)
    raise SystemExit(0 if report.overall_score >= threshold else 1)


def _run_batch_mode(
    file: str,
    format: OutputFormat | None,
    single: bool,
    max_pages: int,
    timeout: int,
    concurrency: int,
    *,
    bots: list[str] | None = None,
    console: Console,
) -> None:
    """Execute batch audit from a URL file and render results."""
    from context_cli.core.batch import parse_url_file, run_batch_audit

    try:
        urls = parse_url_file(file)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise SystemExit(1)

    if not urls:
        console.print("[yellow]Warning:[/yellow] No URLs found in file.")
        return

    with console.status(f"Running batch audit on {len(urls)} URLs..."):
        batch_report = asyncio.run(
            run_batch_audit(
                urls, single=single, max_pages=max_pages,
                timeout=timeout, concurrency=concurrency, bots=bots,
            )
        )

    if format == OutputFormat.json:
        console.print(batch_report.model_dump_json(indent=2))
        return
    if format == OutputFormat.csv:
        from context_cli.formatters.csv import format_batch_report_csv

        console.print(format_batch_report_csv(batch_report), end="")
        return
    if format == OutputFormat.markdown:
        from context_cli.formatters.markdown import format_batch_report_md

        console.print(format_batch_report_md(batch_report), end="")
        return

    from context_cli.formatters.rich_output import render_batch_rich

    render_batch_rich(batch_report, console)
