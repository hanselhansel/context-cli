"""Tests for CSV and Markdown output formatters."""

from __future__ import annotations

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    PageAudit,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.formatters.csv import format_single_report_csv, format_site_report_csv
from context_cli.formatters.markdown import format_single_report_md, format_site_report_md


def _single_report() -> AuditReport:
    return AuditReport(
        url="https://example.com",
        overall_score=55.0,
        robots=RobotsReport(found=True, score=25, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=False, score=0, detail="Not found"),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(word_count=500, score=17, detail="500 words"),
    )


def _site_report() -> SiteAuditReport:
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=68.0,
        robots=RobotsReport(found=True, score=25, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=13, detail="2 blocks"),
        content=ContentReport(word_count=700, score=20, detail="700 words avg"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="50 found"),
        pages=[
            PageAudit(
                url="https://example.com/",
                schema_org=SchemaReport(score=18),
                content=ContentReport(word_count=1000, score=30),
            ),
            PageAudit(
                url="https://example.com/about",
                schema_org=SchemaReport(score=8),
                content=ContentReport(word_count=400, score=10),
            ),
        ],
        pages_audited=2,
    )


# -- CSV formatter tests -------------------------------------------------------


def test_csv_single_report_header():
    """CSV output should have a header row with expected columns."""
    csv_output = format_single_report_csv(_single_report())
    lines = csv_output.strip().split("\n")

    assert len(lines) == 2  # header + data
    assert "url" in lines[0]
    assert "overall_score" in lines[0]
    assert "robots_score" in lines[0]


def test_csv_single_report_values():
    """CSV data row should contain the correct values."""
    csv_output = format_single_report_csv(_single_report())
    lines = csv_output.strip().split("\n")

    assert "https://example.com" in lines[1]
    assert "55.0" in lines[1]
    assert "25" in lines[1]


def test_csv_site_report_has_page_rows():
    """Site CSV should have one row per page plus summary."""
    csv_output = format_site_report_csv(_site_report())

    assert "https://example.com/" in csv_output
    assert "https://example.com/about" in csv_output
    assert "SUMMARY" in csv_output


# -- Markdown formatter tests ---------------------------------------------------


def test_markdown_single_report_structure():
    """Markdown output should contain a heading, table, and overall score."""
    md = format_single_report_md(_single_report())

    assert "# Context Lint:" in md
    assert "| Pillar |" in md
    assert "Robots.txt AI Access" in md
    assert "**Overall Readiness Score: 55.0/100**" in md


def test_markdown_single_report_pillar_values():
    """Markdown table should contain all pillar scores."""
    md = format_single_report_md(_single_report())

    assert "| 25 |" in md or "25" in md
    assert "| 0 |" in md or "Not found" in md
    assert "| 13 |" in md or "1 block" in md
    assert "| 17 |" in md or "500 words" in md


def test_markdown_site_report_structure():
    """Site markdown should contain site-wide and per-page sections."""
    md = format_site_report_md(_site_report())

    assert "# Context Site Lint:" in md
    assert "## Site-Wide Scores" in md
    assert "## Per-Page Breakdown" in md
    assert "**Overall Readiness Score: 68.0/100**" in md


def test_markdown_site_report_pages():
    """Site markdown should list each page in the breakdown table."""
    md = format_site_report_md(_site_report())

    assert "https://example.com/" in md
    assert "https://example.com/about" in md


def test_markdown_single_report_with_errors():
    """Markdown should include an Errors section when errors exist."""
    report = _single_report()
    report.errors = ["Connection timeout"]

    md = format_single_report_md(report)

    assert "## Errors" in md
    assert "Connection timeout" in md


def test_markdown_site_report_with_errors():
    """Site markdown should include an Errors section when errors exist."""
    report = SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25, detail="OK"),
        llms_txt=LlmsTxtReport(found=False, score=0, detail="Not found"),
        schema_org=SchemaReport(blocks_found=0, score=0, detail="None"),
        content=ContentReport(word_count=100, score=5, detail="100 words"),
        discovery=DiscoveryResult(method="spider", urls_found=1, detail="1 found"),
        pages_audited=1,
        errors=["Connection timeout on page 2"],
    )
    md = format_site_report_md(report)
    assert "## Errors" in md
    assert "Connection timeout on page 2" in md
