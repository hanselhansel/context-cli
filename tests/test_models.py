"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    LintCheck,
    LintResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)


def _make_report() -> AuditReport:
    """Build a complete AuditReport for reuse across tests."""
    return AuditReport(
        url="https://example.com",
        overall_score=72.5,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
                BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked by robots.txt"),
            ],
            score=12.5,
            detail="1/2 AI bots allowed",
        ),
        llms_txt=LlmsTxtReport(
            found=True,
            url="https://example.com/llms.txt",
            score=15,
            detail="Found at https://example.com/llms.txt",
        ),
        schema_org=SchemaReport(
            blocks_found=1,
            schemas=[SchemaOrgResult(schema_type="Organization", properties=["name", "url"])],
            score=15,
            detail="1 JSON-LD block(s) found",
        ),
        content=ContentReport(
            word_count=1200,
            char_count=7200,
            has_headings=True,
            has_lists=True,
            has_code_blocks=False,
            score=28,
            detail="1200 words, has headings, has lists",
        ),
        errors=["Some non-fatal warning"],
    )


def test_audit_report_instantiation():
    """AuditReport should accept all pillar sub-reports."""
    report = _make_report()

    assert report.url == "https://example.com"
    assert report.overall_score == 72.5
    assert report.robots.found is True
    assert len(report.robots.bots) == 2
    assert report.llms_txt.found is True
    assert report.schema_org.blocks_found == 1
    assert report.content.word_count == 1200
    assert report.errors == ["Some non-fatal warning"]


def test_json_roundtrip():
    """model_dump_json -> model_validate_json should produce an equal model."""
    original = _make_report()
    json_str = original.model_dump_json()
    restored = AuditReport.model_validate_json(json_str)

    assert restored == original
    assert restored.robots.bots[0].bot == "GPTBot"
    assert restored.schema_org.schemas[0].schema_type == "Organization"


def test_default_values():
    """Unset optional / default fields should have correct defaults."""
    robots = RobotsReport(found=False)
    assert robots.bots == []
    assert robots.score == 0
    assert robots.detail == ""

    llms = LlmsTxtReport(found=False)
    assert llms.url is None
    assert llms.score == 0

    schema = SchemaReport()
    assert schema.blocks_found == 0
    assert schema.schemas == []
    assert schema.score == 0

    content = ContentReport()
    assert content.word_count == 0
    assert content.char_count == 0
    assert content.has_headings is False
    assert content.has_lists is False
    assert content.has_code_blocks is False
    assert content.score == 0


# ── Token waste fields on ContentReport ──────────────────────────────────────


def test_content_report_token_defaults():
    """New token fields should default to zero."""
    content = ContentReport()
    assert content.raw_html_chars == 0
    assert content.clean_markdown_chars == 0
    assert content.estimated_raw_tokens == 0
    assert content.estimated_clean_tokens == 0
    assert content.context_waste_pct == 0.0


def test_content_report_token_fields():
    """ContentReport with token fields should round-trip correctly."""
    content = ContentReport(
        word_count=500,
        raw_html_chars=20000,
        clean_markdown_chars=5000,
        estimated_raw_tokens=5000,
        estimated_clean_tokens=1250,
        context_waste_pct=75.0,
    )
    assert content.raw_html_chars == 20000
    assert content.clean_markdown_chars == 5000
    assert content.estimated_raw_tokens == 5000
    assert content.estimated_clean_tokens == 1250
    assert content.context_waste_pct == 75.0

    # JSON round-trip
    data = content.model_dump()
    restored = ContentReport(**data)
    assert restored.raw_html_chars == 20000
    assert restored.context_waste_pct == 75.0


def test_content_report_waste_pct_bounds():
    """context_waste_pct should enforce ge=0 and le=100."""
    with pytest.raises(ValidationError):
        ContentReport(context_waste_pct=-1.0)

    with pytest.raises(ValidationError):
        ContentReport(context_waste_pct=101.0)

    # Boundary values should be valid
    content_zero = ContentReport(context_waste_pct=0.0)
    assert content_zero.context_waste_pct == 0.0
    content_max = ContentReport(context_waste_pct=100.0)
    assert content_max.context_waste_pct == 100.0


# ── LintCheck and LintResult models ─────────────────────────────────────────


def test_lint_check_instantiation():
    """LintCheck should hold name, passed, and detail."""
    check = LintCheck(name="Bot Access", passed=True, detail="All bots allowed")
    assert check.name == "Bot Access"
    assert check.passed is True
    assert check.detail == "All bots allowed"


def test_lint_check_default_detail():
    """LintCheck detail defaults to empty string."""
    check = LintCheck(name="Test", passed=False)
    assert check.detail == ""


def test_lint_result_defaults():
    """LintResult defaults should be sensible."""
    result = LintResult()
    assert result.checks == []
    assert result.context_waste_pct == 0.0
    assert result.raw_tokens == 0
    assert result.clean_tokens == 0
    assert result.passed is True


def test_lint_result_with_checks():
    """LintResult with mixed pass/fail checks."""
    checks = [
        LintCheck(name="A", passed=True),
        LintCheck(name="B", passed=False, detail="missing"),
    ]
    result = LintResult(
        checks=checks,
        context_waste_pct=65.0,
        raw_tokens=5000,
        clean_tokens=1750,
        passed=False,
    )
    assert len(result.checks) == 2
    assert result.passed is False
    assert result.context_waste_pct == 65.0
    assert result.raw_tokens == 5000
    assert result.clean_tokens == 1750


def test_lint_result_json_roundtrip():
    """LintResult should survive JSON serialization."""
    checks = [LintCheck(name="Test", passed=True, detail="OK")]
    original = LintResult(checks=checks, context_waste_pct=42.5, raw_tokens=100, clean_tokens=58)
    json_str = original.model_dump_json()
    restored = LintResult.model_validate_json(json_str)
    assert restored == original


# ── AuditReport with lint_result ─────────────────────────────────────────────


def test_audit_report_lint_result_default_none():
    """AuditReport.lint_result defaults to None."""
    report = _make_report()
    assert report.lint_result is None


def test_audit_report_with_lint_result():
    """AuditReport should accept a LintResult."""
    lint = LintResult(
        checks=[LintCheck(name="AI Primitives", passed=True, detail="llms.txt found")],
        context_waste_pct=40.0,
        raw_tokens=2000,
        clean_tokens=1200,
        passed=True,
    )
    report = AuditReport(
        url="https://example.com",
        robots=RobotsReport(found=True),
        llms_txt=LlmsTxtReport(found=True),
        schema_org=SchemaReport(),
        content=ContentReport(),
        lint_result=lint,
    )
    assert report.lint_result is not None
    assert report.lint_result.passed is True
    assert report.lint_result.context_waste_pct == 40.0


def test_audit_report_lint_result_json_roundtrip():
    """AuditReport with lint_result should survive JSON round-trip."""
    lint = LintResult(
        checks=[
            LintCheck(name="A", passed=True),
            LintCheck(name="B", passed=False, detail="fail"),
        ],
        context_waste_pct=55.0,
        passed=False,
    )
    report = AuditReport(
        url="https://example.com",
        robots=RobotsReport(found=True),
        llms_txt=LlmsTxtReport(found=True),
        schema_org=SchemaReport(),
        content=ContentReport(),
        lint_result=lint,
    )
    json_str = report.model_dump_json()
    restored = AuditReport.model_validate_json(json_str)
    assert restored.lint_result is not None
    assert restored.lint_result.passed is False
    assert len(restored.lint_result.checks) == 2
