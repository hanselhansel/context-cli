"""Tests for the Typer CLI interface."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.main import app

runner = CliRunner()


def _mock_report() -> AuditReport:
    """Build a known AuditReport for CLI output assertions."""
    return AuditReport(
        url="https://example.com",
        overall_score=55.0,
        robots=RobotsReport(found=True, score=25, detail="7/7 AI bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=15, detail="Found"),
        schema_org=SchemaReport(blocks_found=0, score=0, detail="No JSON-LD found"),
        content=ContentReport(word_count=500, score=15, detail="500 words, has headings"),
    )


def _mock_site_report() -> SiteAuditReport:
    """Build a known SiteAuditReport for multi-page CLI output assertions."""
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=68.0,
        robots=RobotsReport(found=True, score=25, detail="7/7 AI bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(
            blocks_found=2, score=13.0, detail="2 JSON-LD blocks across 2 pages"
        ),
        content=ContentReport(
            word_count=700, score=20.0, detail="avg 700 words across 2 pages"
        ),
        discovery=DiscoveryResult(
            method="sitemap", urls_found=50, detail="method=sitemap, found=50, sampled=2"
        ),
        pages_audited=2,
    )


async def _fake_audit_url(url: str, **kwargs) -> AuditReport:
    """Async mock for audit_url that returns a canned report."""
    return _mock_report()


async def _fake_audit_site(url: str, *, max_pages: int = 10, **kwargs) -> SiteAuditReport:
    """Async mock for audit_site that returns a canned site report."""
    return _mock_site_report()


# -- Single-page audit (--single flag) ----------------------------------------


def test_audit_single_json_output():
    """--single --json should emit valid AuditReport JSON."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(app, ["lint", "https://example.com", "--single", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["url"] == "https://example.com"
    assert data["overall_score"] == 55.0
    assert "robots" in data
    assert "llms_txt" in data
    assert "schema_org" in data
    assert "content" in data


def test_audit_single_rich_output():
    """--single flag should produce Rich table output with score."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(app, ["lint", "https://example.com", "--single"])

    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "55.0" in result.output


# -- Multi-page audit (default, no --single) ----------------------------------


def _extract_json(output: str) -> dict:
    """Extract the first JSON object from CLI output (may include Rich progress bar)."""
    start = output.index("{")
    return json.loads(output[start:])


def test_audit_default_multipage_json():
    """Default (no --single) with --json should call audit_site and output SiteAuditReport JSON."""
    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_audit_site):
        result = runner.invoke(app, ["lint", "https://example.com", "--json"])

    assert result.exit_code == 0
    data = _extract_json(result.output)
    assert data["url"] == "https://example.com"
    assert data["domain"] == "example.com"
    assert data["overall_score"] == 68.0
    assert "discovery" in data
    assert "pages" in data
    assert data["pages_audited"] == 2


def test_audit_default_multipage_rich():
    """Default (no --single) should render the site report and exit cleanly."""
    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_audit_site):
        result = runner.invoke(app, ["lint", "https://example.com"])

    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "68.0" in result.output


def test_audit_max_pages_flag():
    """--max-pages should be passed through to audit_site."""
    calls = []

    async def _capture_audit_site(url: str, *, max_pages: int = 10, **kwargs):
        calls.append(max_pages)
        return _mock_site_report()

    with patch("context_cli.cli.audit.audit_site", side_effect=_capture_audit_site):
        result = runner.invoke(app, ["lint", "https://example.com", "--max-pages", "5", "--json"])

    assert result.exit_code == 0
    assert calls == [5]
