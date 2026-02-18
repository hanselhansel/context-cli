"""Tests for the Typer CLI interface."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from aeo_cli.core.models import (
    AuditReport,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)
from aeo_cli.main import app

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


async def _fake_audit_url(url: str) -> AuditReport:
    """Async mock for audit_url that returns a canned report."""
    return _mock_report()


def test_audit_json_output():
    """--json flag should emit valid JSON with expected top-level keys."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(app, ["audit", "https://example.com", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["url"] == "https://example.com"
    assert data["overall_score"] == 55.0
    assert "robots" in data
    assert "llms_txt" in data
    assert "schema_org" in data
    assert "content" in data


def test_audit_rich_output():
    """Default (Rich table) output should exit cleanly."""
    with patch("aeo_cli.main.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(app, ["audit", "https://example.com"])

    assert result.exit_code == 0
    # The table should include the URL and overall score
    assert "example.com" in result.output
    assert "55.0" in result.output
