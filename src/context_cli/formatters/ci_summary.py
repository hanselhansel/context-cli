"""GitHub Step Summary formatter for Context Lint reports."""

from __future__ import annotations

from context_cli.core.models import AuditReport, SiteAuditReport


def _waste_status(waste_pct: float) -> str:
    """Return PASS/WARN/FAIL status for token waste percentage."""
    if waste_pct <= 30:
        return "PASS ✅"
    if waste_pct <= 70:
        return "WARN ⚠️"
    return "FAIL ❌"


def _format_header(report: AuditReport | SiteAuditReport, fail_under: float | None) -> str:
    """Format the summary header with PASS/FAIL badge."""
    score = report.overall_score
    if fail_under is not None:
        status = "PASS ✅" if score >= fail_under else "FAIL ❌"
    else:
        status = "PASS ✅" if score >= 50 else "FAIL ❌"
    url = report.url
    lines = [f"## Context Lint: {url}", ""]
    # Token Waste hero metric (when lint_result is available)
    if hasattr(report, "lint_result") and report.lint_result is not None:
        waste_pct = report.lint_result.context_waste_pct
        waste_stat = _waste_status(waste_pct)
        lines.append(f"**Token Waste: {waste_pct:.0f}%** — {waste_stat}")
    lines.append(f"**Score: {score}/100** — {status}")
    lines.append("")
    return "\n".join(lines)


def _format_pillar_table(report: AuditReport | SiteAuditReport) -> str:
    """Format pillar scores as a markdown table."""
    lines = [
        "| Pillar | Score | Max | Detail |",
        "|--------|------:|----:|--------|",
        f"| Robots.txt AI Access | {report.robots.score} | 25 | {report.robots.detail} |",
        f"| llms.txt Presence | {report.llms_txt.score} | 10 | {report.llms_txt.detail} |",
        f"| Schema.org JSON-LD | {report.schema_org.score} | 25 | {report.schema_org.detail} |",
        f"| Content Density | {report.content.score} | 40 | {report.content.detail} |",
    ]
    return "\n".join(lines) + "\n"


def _format_bot_table(report: AuditReport | SiteAuditReport) -> str:
    """Format bot access as a markdown table. Only if robots data has bots."""
    if not report.robots.found or not report.robots.bots:
        return ""
    lines = [
        "\n### Bot Access",
        "",
        "| Bot | Status |",
        "|-----|--------|",
    ]
    for bot in report.robots.bots:
        status = "✅ Allowed" if bot.allowed else "❌ Blocked"
        lines.append(f"| {bot.bot} | {status} |")
    return "\n".join(lines) + "\n"


def _format_page_breakdown(report: SiteAuditReport) -> str:
    """Format per-page breakdown for site audits. Empty string for single-page."""
    if not hasattr(report, "pages") or not report.pages:
        return ""
    lines = [
        "\n### Per-Page Breakdown",
        "",
        "| URL | Schema | Content | Total |",
        "|-----|-------:|--------:|------:|",
    ]
    for page in report.pages:
        total = page.schema_org.score + page.content.score
        lines.append(
            f"| {page.url} | {page.schema_org.score} | {page.content.score} | {total} |"
        )
    return "\n".join(lines) + "\n"


def _format_diagnostics(report: AuditReport | SiteAuditReport) -> str:
    """Format diagnostics as a markdown section for CI summary."""
    if not hasattr(report, "lint_result") or report.lint_result is None:
        return ""
    lr = report.lint_result
    if not lr.diagnostics:
        return ""
    lines = ["\n### Diagnostics", ""]
    for d in lr.diagnostics:
        lines.append(f"- **{d.code}** ({d.severity}): {d.message}")
    return "\n".join(lines) + "\n"


def _format_lint_results(report: AuditReport | SiteAuditReport) -> str:
    """Format token waste lint results as a markdown section."""
    if not hasattr(report, "lint_result") or report.lint_result is None:
        return ""
    lr = report.lint_result
    lines = [
        f"\n**Token Waste: {lr.context_waste_pct:.0f}%**"
        f" ({lr.raw_tokens:,} raw → {lr.clean_tokens:,} clean tokens)\n",
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
    ]
    for check in lr.checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"| {check.name} | {status} | {check.detail} |")
    return "\n".join(lines) + "\n"


def format_ci_summary(
    report: AuditReport | SiteAuditReport,
    *,
    fail_under: float | None = None,
) -> str:
    """Format a complete GitHub Step Summary markdown string."""
    parts = [
        _format_header(report, fail_under),
        _format_pillar_table(report),
        _format_lint_results(report),
        _format_diagnostics(report),
        _format_bot_table(report),
    ]
    if isinstance(report, SiteAuditReport):
        parts.append(_format_page_breakdown(report))
    return "\n".join(parts) + "\n"
