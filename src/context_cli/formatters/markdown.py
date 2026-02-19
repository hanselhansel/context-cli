"""Markdown formatter for AEO audit reports."""

from __future__ import annotations

from context_cli.core.models import AuditReport, BatchAuditReport, SiteAuditReport


def format_single_report_md(report: AuditReport) -> str:
    """Format a single-page AuditReport as a Markdown table."""
    lines = [
        f"# AEO Audit: {report.url}",
        "",
        "| Pillar | Score | Detail |",
        "|--------|------:|--------|",
        f"| Robots.txt AI Access | {report.robots.score} | {report.robots.detail} |",
        f"| llms.txt Presence | {report.llms_txt.score} | {report.llms_txt.detail} |",
        f"| Schema.org JSON-LD | {report.schema_org.score} | {report.schema_org.detail} |",
        f"| Content Density | {report.content.score} | {report.content.detail} |",
        "",
        f"**Overall AEO Score: {report.overall_score}/100**",
    ]

    if report.errors:
        lines.append("")
        lines.append("## Errors")
        for err in report.errors:
            lines.append(f"- {err}")

    return "\n".join(lines) + "\n"


def format_site_report_md(report: SiteAuditReport) -> str:
    """Format a site-level SiteAuditReport as Markdown tables."""
    lines = [
        f"# AEO Site Audit: {report.url}",
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

    lines.extend([
        "",
        f"**Overall AEO Score: {report.overall_score}/100**",
    ])

    if report.errors:
        lines.append("")
        lines.append("## Errors")
        for err in report.errors:
            lines.append(f"- {err}")

    return "\n".join(lines) + "\n"


def format_batch_report_md(report: BatchAuditReport) -> str:
    """Format a BatchAuditReport as a Markdown table."""
    lines = [
        "# Batch AEO Audit Results",
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
