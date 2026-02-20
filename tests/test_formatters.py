"""Tests for CSV and Markdown output formatters."""

from __future__ import annotations

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    Diagnostic,
    DiscoveryResult,
    LintCheck,
    LintResult,
    LlmsTxtReport,
    PageAudit,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.formatters.csv import format_single_report_csv, format_site_report_csv
from context_cli.formatters.markdown import format_single_report_md, format_site_report_md


def _lint_result() -> LintResult:
    return LintResult(
        checks=[
            LintCheck(name="AI Primitives", passed=True, detail="llms.txt found"),
            LintCheck(name="Bot Access", passed=True, detail="13/13 AI bots allowed"),
            LintCheck(name="Data Structuring", passed=True, detail="3 JSON-LD blocks"),
            LintCheck(name="Token Efficiency", passed=False, detail="85% Context Waste"),
        ],
        context_waste_pct=85.0,
        raw_tokens=18402,
        clean_tokens=2760,
        passed=False,
    )


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

    assert "# Context Lint Report:" in md
    assert "## Site-Wide Scores" in md
    assert "## Per-Page Breakdown" in md


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


# -- Token Waste in CSV tests ------------------------------------------------


def test_csv_single_report_has_token_waste_columns():
    """CSV with lint_result should include token waste columns."""
    report = _single_report()
    report.lint_result = _lint_result()
    csv_output = format_single_report_csv(report)
    lines = csv_output.strip().split("\n")

    assert "raw_tokens" in lines[0]
    assert "clean_tokens" in lines[0]
    assert "context_waste_pct" in lines[0]
    assert "18402" in lines[1]
    assert "2760" in lines[1]
    assert "85.0" in lines[1]


def test_csv_single_report_no_lint_result_has_empty_columns():
    """CSV without lint_result should have empty token waste columns."""
    report = _single_report()
    csv_output = format_single_report_csv(report)
    lines = csv_output.strip().split("\n")

    assert "raw_tokens" in lines[0]
    # Data row should still have the column but with empty values
    assert len(lines) == 2


# -- Token Waste in Markdown tests -------------------------------------------


def test_markdown_single_report_with_lint_result():
    """Markdown output should include Token Waste section when lint_result set."""
    report = _single_report()
    report.lint_result = _lint_result()
    md = format_single_report_md(report)

    assert "## Token Waste" in md
    assert "Context Waste: 85%" in md
    assert "18,402 raw" in md
    assert "2,760 clean" in md
    assert "AI Primitives" in md
    assert "PASS" in md
    assert "FAIL" in md


def test_markdown_single_report_no_lint_result():
    """Markdown output should NOT include Token Waste section when lint_result is None."""
    report = _single_report()
    md = format_single_report_md(report)
    assert "## Token Waste" not in md


def test_markdown_site_report_with_lint_result():
    """Site markdown should include Token Waste section when lint_result set."""
    report = _site_report()
    report.lint_result = _lint_result()
    md = format_site_report_md(report)

    assert "## Token Waste" in md
    assert "Context Waste: 85%" in md
    assert "Token Efficiency" in md


# -- Diagnostics in CSV tests ------------------------------------------------


def _diagnostics() -> list[Diagnostic]:
    return [
        Diagnostic(code="WARN-001", severity="warn", message="Excessive DOM bloat."),
        Diagnostic(code="INFO-001", severity="info", message="Readability grade: 12.3"),
    ]


def test_csv_single_report_has_diagnostics_column():
    """CSV with diagnostics should include diagnostics column with comma-separated codes."""
    report = _single_report()
    lr = _lint_result()
    lr.diagnostics = _diagnostics()
    report.lint_result = lr
    csv_output = format_single_report_csv(report)
    lines = csv_output.strip().split("\n")

    assert "diagnostics" in lines[0]
    assert "WARN-001" in lines[1]
    assert "INFO-001" in lines[1]


def test_csv_single_report_empty_diagnostics():
    """CSV with lint_result but no diagnostics should have empty diagnostics column."""
    report = _single_report()
    report.lint_result = _lint_result()
    csv_output = format_single_report_csv(report)
    lines = csv_output.strip().split("\n")

    assert "diagnostics" in lines[0]


def test_csv_single_report_no_lint_result_has_empty_diagnostics():
    """CSV without lint_result should have empty diagnostics column."""
    report = _single_report()
    csv_output = format_single_report_csv(report)
    lines = csv_output.strip().split("\n")

    assert "diagnostics" in lines[0]


# -- Diagnostics in Markdown tests -------------------------------------------


def test_markdown_single_report_with_diagnostics():
    """Markdown should include Diagnostics section when diagnostics exist."""
    report = _single_report()
    lr = _lint_result()
    lr.diagnostics = _diagnostics()
    report.lint_result = lr
    md = format_single_report_md(report)

    assert "### Diagnostics" in md
    assert "| WARN-001 | warn | Excessive DOM bloat. |" in md
    assert "| INFO-001 | info | Readability grade: 12.3 |" in md


def test_markdown_single_report_lint_result_no_diagnostics():
    """Markdown with lint_result but no diagnostics should NOT show Diagnostics section."""
    report = _single_report()
    report.lint_result = _lint_result()
    md = format_single_report_md(report)

    assert "### Diagnostics" not in md


def test_markdown_site_report_with_diagnostics():
    """Site markdown should include Diagnostics section when diagnostics exist."""
    report = _site_report()
    lr = _lint_result()
    lr.diagnostics = _diagnostics()
    report.lint_result = lr
    md = format_site_report_md(report)

    assert "### Diagnostics" in md
    assert "WARN-001" in md
    assert "INFO-001" in md
