"""Tests for HTML report formatter."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

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
from context_cli.formatters.html import format_single_report_html, format_site_report_html
from context_cli.main import app

runner = CliRunner()


def _single_report(score: float = 72.5) -> AuditReport:
    """Build a known AuditReport for HTML tests."""
    return AuditReport(
        url="https://example.com",
        overall_score=score,
        robots=RobotsReport(found=True, score=25.0, detail="7/7 AI bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="Found at /llms.txt"),
        schema_org=SchemaReport(blocks_found=2, score=20.0, detail="2 JSON-LD blocks"),
        content=ContentReport(word_count=800, score=17.5, detail="800 words, has headings"),
    )


def _site_report() -> SiteAuditReport:
    """Build a known SiteAuditReport for HTML tests."""
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=68.0,
        robots=RobotsReport(found=True, score=25.0, detail="7/7 AI bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=13.0, detail="2 blocks avg"),
        content=ContentReport(word_count=700, score=20.0, detail="700 words avg"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="50 found"),
        pages=[
            PageAudit(
                url="https://example.com/",
                schema_org=SchemaReport(score=18.0),
                content=ContentReport(word_count=1000, score=30.0),
            ),
            PageAudit(
                url="https://example.com/about",
                schema_org=SchemaReport(score=8.0),
                content=ContentReport(word_count=400, score=10.0),
            ),
        ],
        pages_audited=2,
    )


# -- format_single_report_html tests ------------------------------------------


def test_single_html_is_valid_html5():
    """HTML output should be a complete HTML5 document."""
    html = format_single_report_html(_single_report())
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "<html" in html
    assert "</html>" in html
    assert "<head>" in html
    assert "<body>" in html


def test_single_html_contains_score():
    """HTML should display the overall score value."""
    html = format_single_report_html(_single_report())
    assert "72.5" in html


def test_single_html_contains_all_pillar_names():
    """HTML should contain names for all four pillars."""
    html = format_single_report_html(_single_report())
    assert "Robots" in html
    assert "llms.txt" in html
    assert "Schema" in html
    assert "Content" in html


def test_single_html_contains_pillar_details():
    """HTML should contain pillar detail strings."""
    html = format_single_report_html(_single_report())
    assert "7/7 AI bots allowed" in html
    assert "Found at /llms.txt" in html
    assert "2 JSON-LD blocks" in html
    assert "800 words" in html


def test_single_html_contains_url():
    """HTML should contain the audited URL."""
    html = format_single_report_html(_single_report())
    assert "https://example.com" in html


def test_single_html_is_self_contained():
    """HTML should not contain external stylesheet or script links."""
    html = format_single_report_html(_single_report())
    # No external CSS links
    assert 'rel="stylesheet"' not in html
    # No external scripts
    assert "<script src=" not in html
    # Should have inline style
    assert "<style>" in html


def test_single_html_has_inline_css():
    """HTML should contain inline CSS for styling."""
    html = format_single_report_html(_single_report())
    assert "<style>" in html
    assert "</style>" in html


# -- Score color threshold tests -----------------------------------------------


def test_score_color_green_high():
    """Score >= 80 should use green color."""
    html = format_single_report_html(_single_report(score=85.0))
    # The score gauge should contain a green color indicator
    assert "#0cce6b" in html or "green" in html.lower()


def test_score_color_yellow_medium():
    """Score >= 50 and < 80 should use yellow/orange color."""
    html = format_single_report_html(_single_report(score=65.0))
    assert "#ffa400" in html or "orange" in html.lower()


def test_score_color_red_low():
    """Score < 50 should use red color."""
    html = format_single_report_html(_single_report(score=30.0))
    assert "#ff4e42" in html or "red" in html.lower()


# -- format_site_report_html tests ---------------------------------------------


def test_site_html_is_valid_html5():
    """Site HTML should be a complete HTML5 document."""
    html = format_site_report_html(_site_report())
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "<html" in html
    assert "</html>" in html


def test_site_html_contains_score():
    """Site HTML should display the overall score."""
    html = format_site_report_html(_site_report())
    assert "68" in html


def test_site_html_contains_domain():
    """Site HTML should display the domain."""
    html = format_site_report_html(_site_report())
    assert "example.com" in html


def test_site_html_contains_page_urls():
    """Site HTML should list individual page URLs."""
    html = format_site_report_html(_site_report())
    assert "https://example.com/" in html
    assert "https://example.com/about" in html


def test_site_html_contains_pillar_names():
    """Site HTML should contain all pillar names."""
    html = format_site_report_html(_site_report())
    assert "Robots" in html
    assert "llms.txt" in html
    assert "Schema" in html
    assert "Content" in html


def test_site_html_is_self_contained():
    """Site HTML should be self-contained (no external deps)."""
    html = format_site_report_html(_site_report())
    assert 'rel="stylesheet"' not in html
    assert "<script src=" not in html
    assert "<style>" in html


def test_site_html_contains_discovery_info():
    """Site HTML should show discovery method info."""
    html = format_site_report_html(_site_report())
    assert "sitemap" in html.lower() or "50 found" in html


def test_site_html_contains_pages_audited():
    """Site HTML should show number of pages audited."""
    html = format_site_report_html(_site_report())
    assert "2" in html


# -- Responsive layout test ----------------------------------------------------


def test_html_has_viewport_meta():
    """HTML should have a viewport meta tag for responsive layout."""
    html = format_single_report_html(_single_report())
    assert "viewport" in html


# -- Error display test --------------------------------------------------------


def test_single_html_with_errors():
    """HTML should display errors when present."""
    report = _single_report()
    report.errors = ["Connection timeout", "DNS resolution failed"]
    html = format_single_report_html(report)
    assert "Connection timeout" in html
    assert "DNS resolution failed" in html


def test_site_html_with_errors():
    """Site HTML should display errors when present."""
    report = _site_report()
    report.errors = ["Page /blog failed to load"]
    html = format_site_report_html(report)
    assert "Page /blog failed to load" in html


# -- Edge cases ----------------------------------------------------------------


def test_single_html_zero_score():
    """HTML should handle zero score correctly."""
    report = AuditReport(
        url="https://empty.com",
        overall_score=0.0,
        robots=RobotsReport(found=False, score=0.0, detail="Not found"),
        llms_txt=LlmsTxtReport(found=False, score=0.0, detail="Not found"),
        schema_org=SchemaReport(blocks_found=0, score=0.0, detail="None"),
        content=ContentReport(word_count=0, score=0.0, detail="No content"),
    )
    html = format_single_report_html(report)
    assert "<!DOCTYPE html>" in html
    assert "0" in html


def test_single_html_perfect_score():
    """HTML should handle perfect 100 score correctly."""
    html = format_single_report_html(_single_report(score=100.0))
    assert "100" in html


def test_site_html_no_pages():
    """Site HTML should handle empty pages list."""
    report = SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=35.0,
        robots=RobotsReport(found=True, score=25.0, detail="OK"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="Found"),
        schema_org=SchemaReport(blocks_found=0, score=0.0, detail="None"),
        content=ContentReport(word_count=0, score=0.0, detail="None"),
        discovery=DiscoveryResult(method="spider", urls_found=0, detail="0 found"),
        pages_audited=0,
    )
    html = format_site_report_html(report)
    assert "<!DOCTYPE html>" in html


def test_html_escapes_special_characters():
    """HTML should properly escape special characters in URLs and details."""
    report = AuditReport(
        url="https://example.com/page?q=1&b=2",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25.0, detail='Rule: Disallow <script>'),
        llms_txt=LlmsTxtReport(found=False, score=0.0, detail="Not found"),
        schema_org=SchemaReport(blocks_found=0, score=0.0, detail="None"),
        content=ContentReport(word_count=100, score=25.0, detail="100 words"),
    )
    html = format_single_report_html(report)
    # Should escape angle brackets in detail
    assert "<script>" not in html
    assert "&lt;script&gt;" in html or "script" in html


# -- CLI --format html integration tests --------------------------------------


def test_cli_format_html_single(tmp_path, monkeypatch):
    """--single --format html should create an HTML file."""
    monkeypatch.chdir(tmp_path)

    async def _fake_audit(url, **kwargs):
        return _single_report()

    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--format", "html"]
        )

    assert result.exit_code == 0
    assert "HTML report saved" in result.output or ".html" in result.output


def test_cli_format_html_site(tmp_path, monkeypatch):
    """--format html for site report should create an HTML file."""
    monkeypatch.chdir(tmp_path)

    async def _fake_audit(*a, **kw):
        return _site_report()

    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_audit):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--format", "html"]
        )

    assert result.exit_code == 0
    assert "HTML report saved" in result.output or ".html" in result.output
