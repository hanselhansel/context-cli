"""Tests for CI/CD features: --fail-under, --fail-on-blocked-bots, exit codes."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.main import app

runner = CliRunner()


def _mock_report(
    score: float = 55.0, bots_allowed: bool = True,
) -> AuditReport:
    """Build a mock AuditReport with configurable score and bot access."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=bots_allowed, detail="test"),
        BotAccessResult(bot="ClaudeBot", allowed=bots_allowed, detail="test"),
    ]
    return AuditReport(
        url="https://example.com",
        overall_score=score,
        robots=RobotsReport(found=True, bots=bots, score=25 if bots_allowed else 10, detail="test"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=0, score=0, detail="No JSON-LD found"),
        content=ContentReport(word_count=500, score=15, detail="500 words"),
    )


def _mock_site_report(score: float = 68.0) -> SiteAuditReport:
    """Build a mock SiteAuditReport with configurable score."""
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="7/7 bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=13.0, detail="2 JSON-LD blocks"),
        content=ContentReport(word_count=700, score=20.0, detail="avg 700 words"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="method=sitemap"),
        pages_audited=2,
    )


async def _fake_audit_url(url: str, **kwargs) -> AuditReport:
    return _mock_report()


async def _fake_audit_url_low(url: str, **kwargs) -> AuditReport:
    return _mock_report(score=30.0)


async def _fake_audit_url_blocked(url: str, **kwargs) -> AuditReport:
    return _mock_report(score=55.0, bots_allowed=False)


async def _fake_audit_url_low_blocked(url: str, **kwargs) -> AuditReport:
    return _mock_report(score=30.0, bots_allowed=False)


async def _fake_audit_site(url: str, *, max_pages: int = 10, **kwargs) -> SiteAuditReport:
    return _mock_site_report()


async def _fake_audit_site_low(url: str, *, max_pages: int = 10, **kwargs) -> SiteAuditReport:
    return _mock_site_report(score=40.0)


# -- --fail-under tests -------------------------------------------------------


def test_fail_under_exits_1_below_threshold():
    """--fail-under exits 1 when score is below the threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single", "--fail-under", "70"]
        )
    assert result.exit_code == 1


def test_fail_under_exits_0_above_threshold():
    """--fail-under exits 0 when score is at or above the threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single", "--fail-under", "50"]
        )
    assert result.exit_code == 0


def test_quiet_backwards_compat_default_threshold():
    """--quiet without --fail-under uses default threshold of 50."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        # score=55, threshold=50 → exit 0
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single", "--quiet"]
        )
    assert result.exit_code == 0

    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_low):
        # score=30, threshold=50 → exit 1
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single", "--quiet"]
        )
    assert result.exit_code == 1


def test_fail_under_with_json_outputs_before_exit():
    """--fail-under with --json should still output JSON before exiting."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--json", "--fail-under", "70"],
        )
    assert result.exit_code == 1
    # JSON should still be present in the output
    data = json.loads(result.output)
    assert data["overall_score"] == 55.0


def test_fail_under_with_markdown():
    """--fail-under with --format markdown should still output markdown before exiting."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--format", "markdown", "--fail-under", "70",
            ],
        )
    assert result.exit_code == 1
    assert "Context Lint" in result.output


# -- --fail-on-blocked-bots tests ---------------------------------------------


def test_fail_on_blocked_bots_exits_2():
    """--fail-on-blocked-bots exits 2 when bots are blocked."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_blocked):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--fail-on-blocked-bots"],
        )
    assert result.exit_code == 2


def test_blocked_bots_priority_over_score_failure():
    """Blocked bots (exit 2) takes priority over score failure (exit 1)."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_low_blocked):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--fail-under", "70", "--fail-on-blocked-bots",
            ],
        )
    # Should be 2 (blocked bots), not 1 (score below threshold)
    assert result.exit_code == 2


# -- Site audit with --fail-under ----------------------------------------------


def test_fail_under_with_site_audit():
    """--fail-under works with multi-page site audit."""
    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_audit_site_low):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--json", "--fail-under", "60"],
        )
    assert result.exit_code == 1
