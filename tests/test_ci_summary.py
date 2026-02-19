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
    assert "## AEO Audit: https://example.com" in md
    assert "**Score: 55.0/100**" in md


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
    """PASS/FAIL status should render correctly based on threshold."""
    # Default threshold (50) — score 55 → PASS
    report_pass = _mock_report(score=55.0)
    md_pass = format_ci_summary(report_pass)
    assert "PASS" in md_pass

    # Default threshold (50) — score 30 → FAIL
    report_fail = _mock_report(score=30.0)
    md_fail = format_ci_summary(report_fail)
    assert "FAIL" in md_fail

    # Custom threshold — score 55 but threshold 70 → FAIL
    md_custom = format_ci_summary(report_pass, fail_under=70)
    assert "FAIL" in md_custom


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
