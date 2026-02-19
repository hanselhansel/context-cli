"""Tests for GitHub Step Summary file integration (_write_github_step_summary)."""

from __future__ import annotations

import os
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


def _mock_report(score: float = 55.0) -> AuditReport:
    """Build a mock AuditReport."""
    return AuditReport(
        url="https://example.com",
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="7/7 bots allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=0, score=0, detail="No JSON-LD"),
        content=ContentReport(word_count=500, score=20, detail="500 words"),
    )


async def _fake_audit_url(url: str, **kwargs) -> AuditReport:
    return _mock_report()


def test_writes_to_file_when_env_set(tmp_path):
    """Should write summary markdown to the file specified by GITHUB_STEP_SUMMARY."""
    summary_file = tmp_path / "summary.md"

    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url),
        patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}),
    ):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single"]
        )

    assert result.exit_code == 0
    content = summary_file.read_text()
    assert "Context Lint" in content
    assert "55.0/100" in content


def test_skips_when_env_unset(tmp_path):
    """Should not create any file when GITHUB_STEP_SUMMARY is not set."""
    summary_file = tmp_path / "summary.md"

    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url),
        patch.dict(os.environ, {}, clear=False),
    ):
        # Make sure GITHUB_STEP_SUMMARY is not set
        os.environ.pop("GITHUB_STEP_SUMMARY", None)
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single"]
        )

    assert result.exit_code == 0
    assert not summary_file.exists()


def test_appends_not_overwrites(tmp_path):
    """Should append to the summary file, not overwrite existing content."""
    summary_file = tmp_path / "summary.md"
    summary_file.write_text("# Existing content\n\n")

    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url),
        patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}),
    ):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single"]
        )

    assert result.exit_code == 0
    content = summary_file.read_text()
    # Both the existing content and the new summary should be present
    assert "# Existing content" in content
    assert "Context Lint" in content
