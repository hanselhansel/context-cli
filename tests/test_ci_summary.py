"""Tests for the GitHub Step Summary formatter (ci_summary.py)."""

from __future__ import annotations

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    PageAudit,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.formatters.ci_summary import format_ci_summary


def _mock_report(score: float = 55.0) -> AuditReport:
    """Build a mock AuditReport."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked"),
    ]
    return AuditReport(
        url="https://example.com",
        overall_score=score,
        robots=RobotsReport(found=True, bots=bots, score=15, detail="5/7 bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=1, score=12, detail="1 JSON-LD block"),
        content=ContentReport(word_count=500, score=18, detail="500 words"),
    )


def _mock_site_report() -> SiteAuditReport:
    """Build a mock SiteAuditReport with pages."""
    pages = [
        PageAudit(
            url="https://example.com/page1",
            schema_org=SchemaReport(blocks_found=1, score=10, detail="1 block"),
            content=ContentReport(word_count=400, score=15, detail="400 words"),
        ),
        PageAudit(
            url="https://example.com/page2",
            schema_org=SchemaReport(blocks_found=0, score=0, detail="No JSON-LD"),
            content=ContentReport(word_count=800, score=25, detail="800 words"),
        ),
    ]
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=68.0,
        robots=RobotsReport(found=True, score=25, detail="7/7 bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=1, score=10, detail="1 JSON-LD block avg"),
        content=ContentReport(word_count=600, score=20, detail="avg 600 words"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="method=sitemap"),
        pages=pages,
        pages_audited=2,
    )


def test_summary_contains_heading_with_score():
    """Summary should include the URL heading and score."""
    report = _mock_report(score=55.0)
    md = format_ci_summary(report)
    assert "## Context Lint: https://example.com" in md


def test_summary_contains_pillar_table():
    """Summary should include the pillar scores table."""
    report = _mock_report()
    md = format_ci_summary(report)
    assert "| Pillar | Score | Max | Detail |" in md
    assert "Robots.txt AI Access" in md
    assert "llms.txt Presence" in md
    assert "Schema.org JSON-LD" in md
    assert "Content Density" in md


def test_pass_fail_status_rendering():
    """PASS/FAIL status logic still works for CI exit code (not displayed in output)."""
    from context_cli.core.models import LintCheck, LintResult
    # With lint_result → Token Waste hero metric shows PASS/FAIL
    report_pass = _mock_report(score=55.0)
    report_pass.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=20.0, raw_tokens=100, clean_tokens=80,
    )
    md_pass = format_ci_summary(report_pass)
    assert "PASS" in md_pass

    # With high waste → FAIL in Token Waste hero metric
    report_fail = _mock_report(score=30.0)
    report_fail.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500,
    )
    md_fail = format_ci_summary(report_fail)
    assert "FAIL" in md_fail

    # Custom fail_under threshold — covers the fail_under is not None branch
    md_custom = format_ci_summary(report_pass, fail_under=70)
    assert "Context Lint" in md_custom


def test_bot_access_table():
    """Summary should include bot access table with allowed/blocked status."""
    report = _mock_report()
    md = format_ci_summary(report)
    assert "### Bot Access" in md
    assert "GPTBot" in md
    assert "ClaudeBot" in md
    assert "Allowed" in md
    assert "Blocked" in md


def test_site_audit_page_breakdown():
    """Site audit summary should include per-page breakdown."""
    report = _mock_site_report()
    md = format_ci_summary(report)
    assert "### Per-Page Breakdown" in md
    assert "https://example.com/page1" in md
    assert "https://example.com/page2" in md


def test_page_breakdown_empty_pages():
    """_format_page_breakdown with empty pages returns empty string."""
    from context_cli.formatters.ci_summary import _format_page_breakdown

    report = SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25, detail="OK"),
        llms_txt=LlmsTxtReport(found=False, score=0, detail="Not found"),
        schema_org=SchemaReport(detail="None"),
        content=ContentReport(detail="None"),
        discovery=DiscoveryResult(method="sitemap", detail="0 found"),
        pages=[],
        pages_audited=0,
    )
    result = _format_page_breakdown(report)
    assert result == ""


# -- Token Waste in CI Summary tests ------------------------------------------


def _lint_result():  # noqa: ANN202
    from context_cli.core.models import LintCheck, LintResult
    return LintResult(
        checks=[
            LintCheck(name="AI Primitives", passed=True, detail="llms.txt found"),
            LintCheck(name="Bot Access", passed=True, detail="13/13 AI bots allowed"),
            LintCheck(name="Token Efficiency", passed=False, detail="85% Context Waste"),
        ],
        context_waste_pct=85.0,
        raw_tokens=18402,
        clean_tokens=2760,
        passed=False,
    )


def test_ci_summary_includes_token_waste():
    """CI summary should include token waste section when lint_result is set."""
    report = _mock_report()
    report.lint_result = _lint_result()
    md = format_ci_summary(report)

    assert "Token Waste: 85%" in md
    assert "18,402 raw" in md
    assert "2,760 clean" in md
    assert "| AI Primitives | PASS |" in md
    assert "| Token Efficiency | FAIL |" in md


def test_ci_summary_no_token_waste_without_lint_result():
    """CI summary should NOT include token waste when lint_result is None."""
    report = _mock_report()
    md = format_ci_summary(report)
    assert "Token Waste" not in md


def test_ci_summary_lint_results_empty_string_when_none():
    """_format_lint_results returns empty string when lint_result is None."""
    from context_cli.formatters.ci_summary import _format_lint_results
    report = _mock_report()
    assert _format_lint_results(report) == ""


# -- Diagnostics in CI Summary tests ------------------------------------------


def test_ci_summary_includes_diagnostics():
    """CI summary should include diagnostics section when diagnostics exist."""
    from context_cli.core.models import Diagnostic
    report = _mock_report()
    lr = _lint_result()
    lr.diagnostics = [
        Diagnostic(code="WARN-001", severity="warn", message="Excessive DOM bloat."),
        Diagnostic(code="INFO-001", severity="info", message="Readability grade: 12.3"),
    ]
    report.lint_result = lr
    md = format_ci_summary(report)

    assert "### Diagnostics" in md
    assert "**WARN-001** (warn): Excessive DOM bloat." in md
    assert "**INFO-001** (info): Readability grade: 12.3" in md


def test_ci_summary_no_diagnostics_without_lint_result():
    """CI summary should NOT include diagnostics when lint_result is None."""
    report = _mock_report()
    md = format_ci_summary(report)
    assert "### Diagnostics" not in md


def test_ci_summary_no_diagnostics_when_empty():
    """CI summary should NOT include diagnostics when diagnostics list is empty."""
    report = _mock_report()
    report.lint_result = _lint_result()
    md = format_ci_summary(report)
    assert "### Diagnostics" not in md


def test_ci_summary_diagnostics_empty_string_when_none():
    """_format_diagnostics returns empty string when lint_result is None."""
    from context_cli.formatters.ci_summary import _format_diagnostics
    report = _mock_report()
    assert _format_diagnostics(report) == ""


def test_ci_summary_diagnostics_empty_string_when_no_diagnostics():
    """_format_diagnostics returns empty string when diagnostics list is empty."""
    from context_cli.formatters.ci_summary import _format_diagnostics
    report = _mock_report()
    report.lint_result = _lint_result()
    assert _format_diagnostics(report) == ""


# -- Token Waste Hero Metric in Header tests -----------------------------------


def test_ci_summary_header_shows_token_waste_hero_metric():
    """Header should show Token Waste hero metric when lint_result is available."""
    report = _mock_report()
    report.lint_result = _lint_result()
    md = format_ci_summary(report)
    # Token Waste hero metric should appear before the score line
    assert "**Token Waste: 85%** — FAIL" in md


def test_ci_summary_header_no_waste_without_lint_result():
    """Header should NOT show Token Waste line when lint_result is None."""
    report = _mock_report()
    md = format_ci_summary(report)
    lines = md.split("\n")
    header_lines = [line for line in lines if "Token Waste" in line and "**Token Waste" in line]
    # The header should NOT contain a Token Waste hero metric line
    assert len(header_lines) == 0


def test_ci_summary_waste_status_pass():
    """_waste_status should return PASS for <= 30%."""
    from context_cli.formatters.ci_summary import _waste_status
    assert "PASS" in _waste_status(0)
    assert "PASS" in _waste_status(30)


def test_ci_summary_waste_status_warn():
    """_waste_status should return WARN for 31-70%."""
    from context_cli.formatters.ci_summary import _waste_status
    assert "WARN" in _waste_status(31)
    assert "WARN" in _waste_status(50)
    assert "WARN" in _waste_status(70)


def test_ci_summary_waste_status_fail():
    """_waste_status should return FAIL for > 70%."""
    from context_cli.formatters.ci_summary import _waste_status
    assert "FAIL" in _waste_status(71)
    assert "FAIL" in _waste_status(100)


def test_ci_summary_header_waste_warn():
    """Header should show WARN for waste between 31-70%."""
    from context_cli.core.models import LintCheck, LintResult
    report = _mock_report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=50.0,
        raw_tokens=1000,
        clean_tokens=500,
    )
    md = format_ci_summary(report)
    assert "**Token Waste: 50%** — WARN" in md


def test_ci_summary_header_waste_pass():
    """Header should show PASS for waste <= 30%."""
    from context_cli.core.models import LintCheck, LintResult
    report = _mock_report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=20.0,
        raw_tokens=100,
        clean_tokens=80,
    )
    md = format_ci_summary(report)
    assert "**Token Waste: 20%** — PASS" in md
