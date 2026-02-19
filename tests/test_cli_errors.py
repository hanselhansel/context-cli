"""Tests for CLI error output handling."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)
from context_cli.main import app

runner = CliRunner()


def _error_report(url: str) -> AuditReport:
    """Build an AuditReport with errors for testing error display."""
    return AuditReport(
        url=url,
        overall_score=0,
        robots=RobotsReport(found=False, detail="Check failed"),
        llms_txt=LlmsTxtReport(found=False, detail="Check failed"),
        schema_org=SchemaReport(detail="No HTML to analyze"),
        content=ContentReport(detail="No content extracted"),
        errors=["Crawl failed: Connection refused", "DNS resolution failed"],
    )


async def _fake_audit_url_error(url: str, **kwargs) -> AuditReport:
    return _error_report(url)


async def _fake_audit_url_exception(url: str, **kwargs) -> AuditReport:
    raise RuntimeError("Unexpected crash")


def test_cli_displays_errors():
    """CLI should display errors from the audit report."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_error):
        result = runner.invoke(app, ["lint", "https://unreachable.test", "--single"])

    assert result.exit_code == 0
    assert "Crawl failed" in result.output or "Error" in result.output


def test_cli_json_includes_errors():
    """JSON output should include the errors list."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_error):
        result = runner.invoke(app, ["lint", "https://unreachable.test", "--single", "--json"])

    assert result.exit_code == 0
    assert "Crawl failed" in result.output
    assert "DNS resolution failed" in result.output


def test_cli_auto_adds_https():
    """CLI should auto-prepend https:// to URLs without a scheme."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_error) as mock:
        runner.invoke(app, ["lint", "example.com", "--single"])

    # The mock should have been called with https://example.com
    mock.assert_called_once()
    call_url = mock.call_args[0][0]
    assert call_url == "https://example.com"


def test_cli_zero_score_display():
    """A zero-score result should still render without crashing."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_error):
        result = runner.invoke(app, ["lint", "https://empty.test", "--single"])

    assert result.exit_code == 0
    assert "0" in result.output
