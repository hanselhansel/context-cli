"""Tests for verbose CLI output."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from aeo_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)
from aeo_cli.main import app

runner = CliRunner()


def _verbose_report() -> AuditReport:
    return AuditReport(
        url="https://example.com",
        overall_score=65.0,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked"),
            ],
            score=12.5,
            detail="1/2 allowed",
        ),
        llms_txt=LlmsTxtReport(
            found=True,
            url="https://example.com/llms.txt",
            score=10,
            detail="Found",
        ),
        schema_org=SchemaReport(
            blocks_found=1,
            schemas=[SchemaOrgResult(schema_type="Organization", properties=["name", "url"])],
            score=13,
            detail="1 block",
        ),
        content=ContentReport(
            word_count=800,
            has_headings=True,
            has_lists=True,
            has_code_blocks=False,
            score=32,
            detail="800 words",
        ),
    )


async def _fake_audit(url: str) -> AuditReport:
    return _verbose_report()


def test_verbose_shows_bot_details():
    """--verbose should show per-bot allowed/blocked status."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert result.exit_code == 0
    assert "GPTBot" in result.output
    assert "ClaudeBot" in result.output


def test_verbose_shows_schema_types():
    """--verbose should show @type for each JSON-LD block."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert "Organization" in result.output


def test_verbose_shows_content_details():
    """--verbose should show word count and structure flags."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert "800" in result.output
    assert "Headings" in result.output


def test_verbose_shows_scoring_methodology():
    """--verbose should include the scoring methodology line."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single", "--verbose"])

    assert "Scoring Methodology" in result.output


def test_non_verbose_omits_panels():
    """Without --verbose, the detailed panels should not appear."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit):
        result = runner.invoke(app, ["audit", "https://example.com", "--single"])

    assert "Scoring Methodology" not in result.output
