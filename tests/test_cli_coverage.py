"""Coverage tests for main.py CLI branches — targets all uncovered lines."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from aeo_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    DiscoveryResult,
    GenerateResult,
    LlmsTxtContent,
    LlmsTxtReport,
    PageAudit,
    ProfileType,
    RobotsReport,
    SchemaJsonLdOutput,
    SchemaOrgResult,
    SchemaReport,
    SiteAuditReport,
)
from aeo_cli.main import app

runner = CliRunner()

_PATCH_GENERATE = "aeo_cli.core.generate.generate_assets"


# ── Mock factories ───────────────────────────────────────────────────────────


def _report(score: float = 55.0, **overrides) -> AuditReport:
    defaults = dict(
        url="https://example.com",
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(word_count=500, score=17, detail="500 words"),
    )
    defaults.update(overrides)
    return AuditReport(**defaults)


def _site_report(score: float = 68.0, **overrides) -> SiteAuditReport:
    defaults = dict(
        url="https://example.com",
        domain="example.com",
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=13, detail="2 blocks"),
        content=ContentReport(word_count=700, score=20, detail="700 words"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="50 found"),
        pages_audited=2,
    )
    defaults.update(overrides)
    return SiteAuditReport(**defaults)


def _gen_result(**overrides) -> GenerateResult:
    defaults = dict(
        url="https://example.com",
        model_used="gpt-4o-mini",
        profile=ProfileType.generic,
        llms_txt=LlmsTxtContent(title="Test", description="Test site", sections=[]),
        schema_jsonld=SchemaJsonLdOutput(schema_type="Organization", json_ld={}),
        llms_txt_path="./out/llms.txt",
        schema_jsonld_path="./out/schema.jsonld",
    )
    defaults.update(overrides)
    return GenerateResult(**defaults)


# ── _overall_color() — lines 54, 57 ─────────────────────────────────────────


def test_site_report_green_score():
    """Site report score >= 70 triggers _overall_color green (line 54)."""
    report = _site_report(score=75.0)

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0
    assert "75.0" in result.output


def test_site_report_red_score():
    """Site report score < 40 triggers _overall_color red (line 57)."""
    report = _site_report(score=20.0)

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0
    assert "20.0" in result.output


# ── _render_site_report() pages table — lines 107-120 ───────────────────────


def test_site_report_with_pages():
    """Site report with per-page breakdown (lines 106-120)."""
    pages = [
        PageAudit(
            url="https://example.com/",
            schema_org=SchemaReport(score=13, detail="1 block"),
            content=ContentReport(word_count=500, score=17, detail="500 words"),
        ),
        PageAudit(
            url="https://example.com/about",
            schema_org=SchemaReport(score=8, detail="1 block"),
            content=ContentReport(word_count=200, score=8, detail="200 words"),
        ),
    ]
    report = _site_report(pages=pages)

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0
    assert "example.com/about" in result.output


# ── _render_site_report() errors — lines 130-132 ────────────────────────────


def test_site_report_with_errors():
    """Site report errors section (lines 129-132)."""
    report = _site_report(errors=["Timeout on page 3"])

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0
    assert "Timeout" in result.output


# ── Quiet mode multi-page — lines 175, 353, 356-357 ─────────────────────────


def test_quiet_multipage_pass():
    """--quiet without --single, score >= 50 → exit 0 (lines 175, 353)."""
    report = _site_report(score=60.0)

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com", "--quiet"])
    assert result.exit_code == 0


def test_quiet_multipage_fail():
    """--quiet without --single, score < 50 → exit 1."""
    report = _site_report(score=30.0)

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com", "--quiet"])
    assert result.exit_code == 1


def test_quiet_blocked_bots():
    """--quiet --fail-on-blocked-bots with blocked bot → exit 2 (lines 356-357)."""
    bots = [BotAccessResult(bot="GPTBot", allowed=False, detail="Blocked")]
    report = _site_report(
        score=60.0,
        robots=RobotsReport(found=True, bots=bots, score=0, detail="blocked"),
    )

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--quiet", "--fail-on-blocked-bots"]
        )
    assert result.exit_code == 2


# ── Format branches — lines 224-228, 231 ────────────────────────────────────


def test_audit_csv_single():
    """--single --format csv produces CSV (line 227)."""

    async def _fake(url):
        return _report()

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--format", "csv"]
        )
    assert result.exit_code == 0
    assert "url" in result.output


def test_audit_csv_site():
    """--format csv for site report (lines 224-225)."""

    async def _fake(*a, **kw):
        return _site_report()

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--format", "csv"]
        )
    assert result.exit_code == 0


def test_audit_markdown_single():
    """--single --format markdown (line 233)."""

    async def _fake(url):
        return _report()

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--format", "markdown"]
        )
    assert result.exit_code == 0
    assert "AEO Audit" in result.output


def test_audit_markdown_site():
    """--format markdown for site report (line 231)."""

    async def _fake(*a, **kw):
        return _site_report()

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--format", "markdown"]
        )
    assert result.exit_code == 0
    assert "AEO" in result.output


# ── Verbose mode — lines 268-310 ────────────────────────────────────────────


def test_verbose_robots_not_found():
    """Verbose with robots.found=False (line 281)."""
    report = _report(robots=RobotsReport(found=False, score=0, detail="not found"))

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--verbose"]
        )
    assert result.exit_code == 0
    assert "inaccessible" in result.output


def test_verbose_llms_not_found():
    """Verbose with llms_txt.found=False (line 289)."""
    report = _report(llms_txt=LlmsTxtReport(found=False, score=0, detail="Not found"))

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--verbose"]
        )
    assert result.exit_code == 0
    assert "Not found at" in result.output


def test_verbose_with_bots():
    """Verbose with bot list (lines 276-279)."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked"),
    ]
    report = _report(robots=RobotsReport(found=True, bots=bots, score=15, detail="5/7"))

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--verbose"]
        )
    assert result.exit_code == 0
    assert "GPTBot" in result.output


def test_verbose_llms_found():
    """Verbose with llms_txt.found=True shows URL (line 287)."""
    report = _report(
        llms_txt=LlmsTxtReport(
            found=True, score=10, url="https://example.com/llms.txt", detail="Found"
        )
    )

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--verbose"]
        )
    assert result.exit_code == 0
    assert "Found at" in result.output


def test_verbose_schema_detail():
    """Verbose with schema types (lines 296-300)."""
    report = _report(
        schema_org=SchemaReport(
            blocks_found=1,
            score=13,
            schemas=[SchemaOrgResult(schema_type="Organization", properties=["name", "url"])],
            detail="1 block",
        )
    )

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--verbose"]
        )
    assert result.exit_code == 0
    assert "Organization" in result.output


def test_verbose_content_detail():
    """Verbose content breakdown (lines 303-310)."""
    report = _report(
        content=ContentReport(
            word_count=500,
            score=17,
            has_headings=True,
            has_lists=True,
            has_code_blocks=True,
            detail="500 words",
        )
    )

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--verbose"]
        )
    assert result.exit_code == 0
    assert "Word count" in result.output or "500" in result.output


# ── Single page errors — lines 262-265 ──────────────────────────────────────


def test_single_page_with_errors():
    """Single-page rich output shows errors section (lines 262-265)."""
    report = _report(errors=["Crawl failed"])

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com", "--single"])
    assert result.exit_code == 0
    assert "Crawl failed" in result.output


# ── Generate command — lines 393-395, 410-412 ───────────────────────────────


def test_generate_runtime_error():
    """Generate catches RuntimeError → exit 1 (lines 393-395)."""
    with patch(
        _PATCH_GENERATE,
        new_callable=AsyncMock,
        side_effect=RuntimeError("API error"),
    ):
        result = runner.invoke(app, ["generate", "https://example.com"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_generate_warnings():
    """Generate shows warnings when result.errors populated (lines 410-412)."""
    result_obj = _gen_result(errors=["Schema might be incomplete"])

    with patch(
        _PATCH_GENERATE,
        new_callable=AsyncMock,
        return_value=result_obj,
    ):
        result = runner.invoke(app, ["generate", "https://example.com"])
    assert result.exit_code == 0
    assert "Warnings" in result.output or "Schema might be incomplete" in result.output


# ── MCP command — lines 418-420 ──────────────────────────────────────────────


def test_mcp_command():
    """mcp command calls mcp_server.run(transport='stdio') (lines 418-420)."""
    import aeo_cli.server

    with patch.object(aeo_cli.server, "mcp") as mock_mcp:
        mock_mcp.run = MagicMock()
        result = runner.invoke(app, ["mcp"])
    mock_mcp.run.assert_called_once_with(transport="stdio")
    assert result.exit_code == 0


# ── Progress callback — line 204 ────────────────────────────────────────────


def test_site_audit_progress_callback():
    """Site audit in Rich mode invokes progress_callback (line 204)."""
    report = _site_report()

    async def _fake(url, *, max_pages=10, progress_callback=None, **kw):
        if progress_callback:
            progress_callback("Discovering pages...")
            progress_callback("Crawling page 2/3...")
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0


# ── pages_failed — line 67 ──────────────────────────────────────────────────


def test_site_report_pages_failed():
    """Site report with pages_failed renders the failed count (line 67)."""
    report = _site_report(pages_failed=2)

    async def _fake(*a, **kw):
        return report

    with patch("aeo_cli.main.audit_site", side_effect=_fake):
        result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0
    assert "failed" in result.output


# ── _check_exit_conditions — lines 182-183, 320-324 ─────────────────────────


def test_fail_under_triggers_exit():
    """--fail-under with score below threshold → exit 1 (lines 183, 323-324)."""

    async def _fake(url):
        return _report(score=30.0)

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--fail-under", "50"]
        )
    assert result.exit_code == 1


def test_fail_on_blocked_bots_nonquiet():
    """--fail-on-blocked-bots in non-quiet mode → exit 2 (lines 183, 320-322)."""
    bots = [BotAccessResult(bot="GPTBot", allowed=False, detail="Blocked")]
    report = _report(
        score=60.0,
        robots=RobotsReport(found=True, bots=bots, score=0, detail="blocked"),
    )

    async def _fake(url):
        return report

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--fail-on-blocked-bots"]
        )
    assert result.exit_code == 2


# ── _write_github_step_summary — lines 334-338 ──────────────────────────────


def test_github_step_summary(tmp_path):
    """GITHUB_STEP_SUMMARY env var triggers CI summary write (lines 334-338)."""
    summary_file = tmp_path / "summary.md"

    async def _fake(url):
        return _report(score=55.0)

    env = {**os.environ, "GITHUB_STEP_SUMMARY": str(summary_file)}
    with patch("aeo_cli.main.audit_url", side_effect=_fake), \
         patch.dict(os.environ, env, clear=True):
        result = runner.invoke(app, ["audit", "https://example.com", "--single"])
    assert result.exit_code == 0
    assert summary_file.exists()
    assert "AEO" in summary_file.read_text()


# ── _audit_quiet single — line 351 ──────────────────────────────────────────


def test_quiet_single_pass():
    """--quiet --single with score >= 50 → exit 0 (line 351)."""

    async def _fake(url):
        return _report(score=60.0)

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--quiet"]
        )
    assert result.exit_code == 0


def test_quiet_single_fail():
    """--quiet --single with score < 50 → exit 1."""

    async def _fake(url):
        return _report(score=30.0)

    with patch("aeo_cli.main.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "https://example.com", "--single", "--quiet"]
        )
    assert result.exit_code == 1
