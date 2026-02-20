"""Markdown formatter for Context Lint reports."""

from __future__ import annotations

from context_cli.core.models import AuditReport, BatchAuditReport, SiteAuditReport


def _format_token_waste_md(report: AuditReport | SiteAuditReport) -> list[str]:
    """Format token waste section for markdown output."""
    if not hasattr(report, "lint_result") or report.lint_result is None:
        return []
    lr = report.lint_result
    lines = [
        "",
        "## Token Waste",
        "",
        f"**Context Waste: {lr.context_waste_pct:.0f}%**"
        f" ({lr.raw_tokens:,} raw → {lr.clean_tokens:,} clean tokens)",
        "",
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
    ]
    for check in lr.checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"| {check.name} | {status} | {check.detail} |")

    if lr.diagnostics:
        lines.extend([
            "",
            "### Diagnostics",
            "",
            "| Code | Severity | Message |",
            "|------|----------|---------|",
        ])
        for d in lr.diagnostics:
            lines.append(f"| {d.code} | {d.severity} | {d.message} |")

    return lines


def format_single_report_md(report: AuditReport) -> str:
    """Format a single-page AuditReport as a Markdown table."""
    lines = [
        f"# Context Lint: {report.url}",
        "",
        "| Pillar | Score | Detail |",
        "|--------|------:|--------|",
        f"| Robots.txt AI Access | {report.robots.score} | {report.robots.detail} |",
        f"| llms.txt Presence | {report.llms_txt.score} | {report.llms_txt.detail} |",
        f"| Schema.org JSON-LD | {report.schema_org.score} | {report.schema_org.detail} |",
        f"| Content Density | {report.content.score} | {report.content.detail} |",
    ]

    lines.extend(_format_token_waste_md(report))

    if report.errors:
        lines.append("")
        lines.append("## Errors")
        for err in report.errors:
            lines.append(f"- {err}")

    return "\n".join(lines) + "\n"


def format_site_report_md(report: SiteAuditReport) -> str:
    """Format a site-level SiteAuditReport as Markdown tables."""
    lines = [
        f"# Context Lint Report: {report.url}",
        "",
        f"**Domain:** {report.domain}  ",
        f"**Discovery:** {report.discovery.method} — {report.discovery.detail}  ",
        f"**Pages audited:** {report.pages_audited}",
        "",
        "## Site-Wide Scores",
        "",
        "| Pillar | Score | Detail |",
        "|--------|------:|--------|",
        f"| Robots.txt AI Access | {report.robots.score} | {report.robots.detail} |",
        f"| llms.txt Presence | {report.llms_txt.score} | {report.llms_txt.detail} |",
        "",
        "## Aggregate Page Scores",
        "",
        "| Pillar | Avg Score | Detail |",
        "|--------|----------:|--------|",
        f"| Schema.org JSON-LD | {report.schema_org.score} | {report.schema_org.detail} |",
        f"| Content Density | {report.content.score} | {report.content.detail} |",
    ]

    if report.pages:
        lines.extend([
            "",
            "## Per-Page Breakdown",
            "",
            "| URL | Schema | Content | Total |",
            "|-----|-------:|--------:|------:|",
        ])
        for page in report.pages:
            total = page.schema_org.score + page.content.score
            lines.append(
                f"| {page.url} | {page.schema_org.score} | {page.content.score} | {total} |"
            )

    lines.extend(_format_token_waste_md(report))

    if report.errors:
        lines.append("")
        lines.append("## Errors")
        for err in report.errors:
            lines.append(f"- {err}")

    return "\n".join(lines) + "\n"


def format_batch_report_md(report: BatchAuditReport) -> str:
    """Format a BatchAuditReport as a Markdown table."""
    lines = [
        "# Batch Context Lint Results",
        "",
        "| URL | Score | Robots | llms.txt | Schema | Content |",
        "|-----|-------|--------|----------|--------|---------|",
    ]
    for r in report.reports:
        lines.append(
            f"| {r.url} | {r.overall_score} | {r.robots.score} | "
            f"{r.llms_txt.score} | {r.schema_org.score} | {r.content.score} |"
        )
    if report.errors:
        lines.extend(["", "## Errors", ""])
        for url, err in report.errors.items():
            lines.append(f"- **{url}**: {err}")

    return "\n".join(lines) + "\n"
