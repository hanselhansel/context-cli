"""GitHub Step Summary formatter for AEO audit reports."""

from __future__ import annotations

from aeo_cli.core.models import AuditReport, SiteAuditReport


def _format_header(report: AuditReport | SiteAuditReport, fail_under: float | None) -> str:
    """Format the summary header with PASS/FAIL badge."""
    score = report.overall_score
    if fail_under is not None:
        status = "PASS ✅" if score >= fail_under else "FAIL ❌"
    else:
        status = "PASS ✅" if score >= 50 else "FAIL ❌"
    url = report.url
    return f"## AEO Audit: {url}\n\n**Score: {score}/100** — {status}\n"


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


def format_ci_summary(
    report: AuditReport | SiteAuditReport,
    *,
    fail_under: float | None = None,
) -> str:
    """Format a complete GitHub Step Summary markdown string."""
    parts = [
        _format_header(report, fail_under),
        _format_pillar_table(report),
        _format_bot_table(report),
    ]
    if isinstance(report, SiteAuditReport):
        parts.append(_format_page_breakdown(report))
    return "\n".join(parts) + "\n"
