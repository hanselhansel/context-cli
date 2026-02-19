"""Tests for Pydantic data models."""

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
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
