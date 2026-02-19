"""CSV formatter for Context Lint reports."""

from __future__ import annotations

import csv
import io

from context_cli.core.models import AuditReport, BatchAuditReport, SiteAuditReport


def format_single_report_csv(report: AuditReport) -> str:
    """Format a single-page AuditReport as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["url", "overall_score", "robots_score", "llms_txt_score",
                      "schema_score", "content_score", "content_words"])
    writer.writerow([
        report.url,
        report.overall_score,
        report.robots.score,
        report.llms_txt.score,
        report.schema_org.score,
        report.content.score,
        report.content.word_count,
    ])

    return output.getvalue()


def format_site_report_csv(report: SiteAuditReport) -> str:
    """Format a site-level SiteAuditReport as CSV with per-page rows."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["url", "schema_score", "content_score", "content_words"])

    for page in report.pages:
        writer.writerow([
            page.url,
            page.schema_org.score,
            page.content.score,
            page.content.word_count,
        ])

    # Summary row
    writer.writerow([])
    writer.writerow(["SUMMARY", "overall_score", "robots_score", "llms_txt_score",
                      "schema_avg", "content_avg"])
    writer.writerow([
        report.url,
        report.overall_score,
        report.robots.score,
        report.llms_txt.score,
        report.schema_org.score,
        report.content.score,
    ])

    return output.getvalue()


def format_batch_report_csv(report: BatchAuditReport) -> str:
    """Format a BatchAuditReport as CSV with one row per URL."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["url", "overall_score", "robots_score", "llms_txt_score",
                      "schema_score", "content_score"])
    for r in report.reports:
        writer.writerow([
            r.url, r.overall_score, r.robots.score,
            r.llms_txt.score, r.schema_org.score, r.content.score,
        ])

    return output.getvalue()
