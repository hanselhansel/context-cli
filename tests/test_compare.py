"""Tests for the compare command — core logic, formatter, and CLI."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from context_cli.core.compare import build_compare_report, compare_urls
from context_cli.core.models import (
    AuditReport,
    CompareReport,
    ContentReport,
    LlmsTxtReport,
    PillarDelta,
    RobotsReport,
    SchemaReport,
)
from context_cli.formatters.compare import render_compare
from context_cli.main import app

runner = CliRunner()

# ── Helpers ──────────────────────────────────────────────────────────────────

_URL_A = "https://alpha.example.com"
_URL_B = "https://beta.example.com"


def _report(url: str, overall: float, robots: float, llms: float,
            schema: float, content: float) -> AuditReport:
    return AuditReport(
        url=url,
        overall_score=overall,
        robots=RobotsReport(found=True, score=robots, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=llms, detail="ok"),
        schema_org=SchemaReport(score=schema, detail="ok"),
        content=ContentReport(score=content, detail="ok"),
    )


def _high_report() -> AuditReport:
    return _report(_URL_A, 80.0, 25.0, 10.0, 20.0, 25.0)


def _low_report() -> AuditReport:
    return _report(_URL_B, 40.0, 10.0, 0.0, 10.0, 20.0)


# ── build_compare_report ────────────────────────────────────────────────────


def test_build_compare_report_basic():
    """build_compare_report produces correct overall delta and pillar deltas."""
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())

    assert isinstance(result, CompareReport)
    assert result.url_a == _URL_A
    assert result.url_b == _URL_B
    assert result.score_a == 80.0
    assert result.score_b == 40.0
    assert result.delta == 40.0


def test_build_compare_report_pillar_count():
    """Should have exactly 4 pillar deltas."""
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    assert len(result.pillars) == 4


def test_build_compare_report_pillar_names():
    """Pillar names should be robots, llms_txt, schema_org, content."""
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    names = {p.pillar for p in result.pillars}
    assert names == {"robots", "llms_txt", "schema_org", "content"}


def test_build_compare_report_robots_delta():
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    robots = next(p for p in result.pillars if p.pillar == "robots")
    assert robots.score_a == 25.0
    assert robots.score_b == 10.0
    assert robots.delta == 15.0
    assert robots.max_score == 25


def test_build_compare_report_llms_delta():
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    llms = next(p for p in result.pillars if p.pillar == "llms_txt")
    assert llms.delta == 10.0


def test_build_compare_report_equal_scores():
    """When both reports have the same score, delta should be 0."""
    a = _report(_URL_A, 50.0, 12.5, 5.0, 12.5, 20.0)
    b = _report(_URL_B, 50.0, 12.5, 5.0, 12.5, 20.0)
    result = build_compare_report(_URL_A, _URL_B, a, b)
    assert result.delta == 0.0
    for p in result.pillars:
        assert p.delta == 0.0


def test_build_compare_report_b_wins():
    """When URL B scores higher, overall delta should be negative."""
    result = build_compare_report(_URL_A, _URL_B, _low_report(), _high_report())
    assert result.delta < 0


def test_build_compare_report_includes_full_reports():
    """CompareReport should include the full audit reports."""
    a = _high_report()
    b = _low_report()
    result = build_compare_report(_URL_A, _URL_B, a, b)
    assert result.report_a.url == _URL_A
    assert result.report_b.url == _URL_B


# ── compare_urls ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.core.compare.audit_url", new_callable=AsyncMock)
async def test_compare_urls_calls_both(mock_audit):
    """compare_urls should call audit_url twice, once per URL."""
    mock_audit.side_effect = [_high_report(), _low_report()]
    result = await compare_urls(_URL_A, _URL_B)

    assert mock_audit.call_count == 2
    assert isinstance(result, CompareReport)
    assert result.url_a == _URL_A
    assert result.url_b == _URL_B


@pytest.mark.asyncio
@patch("context_cli.core.compare.audit_url", new_callable=AsyncMock)
async def test_compare_urls_passes_timeout(mock_audit):
    """compare_urls should forward timeout to audit_url."""
    mock_audit.return_value = _high_report()
    await compare_urls(_URL_A, _URL_B, timeout=30)

    for call in mock_audit.call_args_list:
        assert call.kwargs["timeout"] == 30


@pytest.mark.asyncio
@patch("context_cli.core.compare.audit_url", new_callable=AsyncMock)
async def test_compare_urls_passes_bots(mock_audit):
    """compare_urls should forward bots to audit_url."""
    mock_audit.return_value = _high_report()
    await compare_urls(_URL_A, _URL_B, bots=["TestBot"])

    for call in mock_audit.call_args_list:
        assert call.kwargs["bots"] == ["TestBot"]


# ── render_compare ──────────────────────────────────────────────────────────


def _capture_compare(report: CompareReport) -> str:
    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=120)
    render_compare(report, con)
    return buf.getvalue()


def test_render_compare_shows_urls():
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    text = _capture_compare(result)
    assert "alpha.example.com" in text
    assert "beta.example.com" in text


def test_render_compare_shows_pillar_names():
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    text = _capture_compare(result)
    assert "Robots.txt" in text
    assert "llms.txt" in text
    assert "Schema.org" in text
    assert "Content" in text


def test_render_compare_shows_overall():
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    text = _capture_compare(result)
    assert "Overall" in text
    assert "80" in text
    assert "40" in text


def test_render_compare_winner_a():
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    text = _capture_compare(result)
    assert "Winner" in text
    assert "alpha" in text


def test_render_compare_winner_b():
    result = build_compare_report(_URL_A, _URL_B, _low_report(), _high_report())
    text = _capture_compare(result)
    assert "Winner" in text
    assert "beta" in text


def test_render_compare_tie():
    a = _report(_URL_A, 50.0, 12.5, 5.0, 12.5, 20.0)
    b = _report(_URL_B, 50.0, 12.5, 5.0, 12.5, 20.0)
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare(result)
    assert "Tie" in text


# ── CLI integration ─────────────────────────────────────────────────────────


@patch("context_cli.cli.compare.compare_urls", new_callable=AsyncMock)
def test_cli_compare_rich_output(mock_compare):
    """CLI compare renders Rich table output by default."""
    mock_compare.return_value = build_compare_report(
        _URL_A, _URL_B, _high_report(), _low_report(),
    )
    result = runner.invoke(app, ["compare", _URL_A, _URL_B])
    assert result.exit_code == 0
    assert "Overall" in result.output


@patch("context_cli.cli.compare.compare_urls", new_callable=AsyncMock)
def test_cli_compare_json_output(mock_compare):
    """CLI compare --json produces valid JSON."""
    mock_compare.return_value = build_compare_report(
        _URL_A, _URL_B, _high_report(), _low_report(),
    )
    result = runner.invoke(app, ["compare", _URL_A, _URL_B, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["url_a"] == _URL_A
    assert data["url_b"] == _URL_B
    assert "pillars" in data


@patch("context_cli.cli.compare.compare_urls", new_callable=AsyncMock)
def test_cli_compare_timeout_flag(mock_compare):
    """CLI compare --timeout passes through to compare_urls."""
    mock_compare.return_value = build_compare_report(
        _URL_A, _URL_B, _high_report(), _low_report(),
    )
    runner.invoke(app, ["compare", _URL_A, _URL_B, "-t", "30", "--json"])
    _, kwargs = mock_compare.call_args
    assert kwargs["timeout"] == 30


@patch("context_cli.cli.compare.compare_urls", new_callable=AsyncMock)
def test_cli_compare_bots_flag(mock_compare):
    """CLI compare --bots passes through as list."""
    mock_compare.return_value = build_compare_report(
        _URL_A, _URL_B, _high_report(), _low_report(),
    )
    runner.invoke(app, ["compare", _URL_A, _URL_B, "--bots", "BotA,BotB", "--json"])
    _, kwargs = mock_compare.call_args
    assert kwargs["bots"] == ["BotA", "BotB"]


@patch("context_cli.cli.compare.compare_urls", new_callable=AsyncMock)
def test_cli_compare_no_bots_passes_none(mock_compare):
    """CLI compare without --bots passes bots=None."""
    mock_compare.return_value = build_compare_report(
        _URL_A, _URL_B, _high_report(), _low_report(),
    )
    runner.invoke(app, ["compare", _URL_A, _URL_B, "--json"])
    _, kwargs = mock_compare.call_args
    assert kwargs["bots"] is None


# ── Model serialization ─────────────────────────────────────────────────────


def test_compare_report_model_dump():
    """CompareReport should be serializable via model_dump."""
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    data = result.model_dump()
    assert data["url_a"] == _URL_A
    assert len(data["pillars"]) == 4


def test_pillar_delta_model():
    """PillarDelta fields should be correct."""
    pd = PillarDelta(
        pillar="robots", score_a=25, score_b=10, delta=15, max_score=25,
    )
    assert pd.pillar == "robots"
    assert pd.delta == 15


# ── Token waste comparison tests ────────────────────────────────────────────


def test_render_compare_shows_token_waste_when_both_have_lint():
    """Compare table should show Token Waste row when both reports have lint_result."""
    from context_cli.core.models import LintCheck, LintResult
    a = _high_report()
    b = _low_report()
    a.lint_result = LintResult(
        checks=[LintCheck(name="Token Efficiency", passed=False, detail="85%")],
        context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500, passed=False,
    )
    b.lint_result = LintResult(
        checks=[LintCheck(name="Token Efficiency", passed=True, detail="42%")],
        context_waste_pct=42.0, raw_tokens=10000, clean_tokens=5800, passed=True,
    )
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare(result)
    assert "Token Waste" in text
    assert "85%" in text
    assert "42%" in text


def test_render_compare_no_token_waste_without_lint():
    """Compare table should NOT show Token Waste row when lint_result is missing."""
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    text = _capture_compare(result)
    assert "Token Waste" not in text


def test_render_compare_no_token_waste_when_only_one_has_lint():
    """Compare table should NOT show Token Waste row when only one report has lint_result."""
    from context_cli.core.models import LintCheck, LintResult
    a = _high_report()
    a.lint_result = LintResult(
        checks=[LintCheck(name="Token Efficiency", passed=False, detail="85%")],
        context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500, passed=False,
    )
    b = _low_report()  # No lint_result
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare(result)
    assert "Token Waste" not in text


def test_render_compare_token_waste_equal():
    """Compare should show 0% delta when both have same waste percentage."""
    from context_cli.core.models import LintResult
    a = _high_report()
    b = _low_report()
    a.lint_result = LintResult(
        checks=[], context_waste_pct=50.0, raw_tokens=5000, clean_tokens=2500, passed=True,
    )
    b.lint_result = LintResult(
        checks=[], context_waste_pct=50.0, raw_tokens=5000, clean_tokens=2500, passed=True,
    )
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare(result)
    assert "Token Waste" in text
    assert "0%" in text


def test_render_compare_token_waste_a_less_waste():
    """Compare should show green negative delta when A has less waste than B."""
    from context_cli.core.models import LintResult
    a = _high_report()
    b = _low_report()
    a.lint_result = LintResult(
        checks=[], context_waste_pct=30.0, raw_tokens=10000, clean_tokens=7000, passed=True,
    )
    b.lint_result = LintResult(
        checks=[], context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500, passed=False,
    )
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare(result)
    assert "Token Waste" in text
    # A has 30%, B has 85%, delta is -55 (A has less waste = green)
    assert "30%" in text
    assert "85%" in text


# ── Diagnostics in compare output ──────────────────────────────────────────


def _capture_compare_plain(report: CompareReport) -> str:
    buf = StringIO()
    con = Console(file=buf, no_color=True, width=120)
    render_compare(report, con)
    return buf.getvalue()


def test_render_compare_diagnostics_both_urls():
    """Compare should show diagnostics for both URLs when both have them."""
    from context_cli.core.models import Diagnostic, LintCheck, LintResult
    a = _high_report()
    b = _low_report()
    a.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500, passed=False,
        diagnostics=[
            Diagnostic(code="WARN-001", severity="warn", message="Excessive DOM bloat."),
        ],
    )
    b.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=42.0, raw_tokens=10000, clean_tokens=5800, passed=True,
        diagnostics=[
            Diagnostic(code="INFO-001", severity="info", message="Readability grade: 12.3"),
        ],
    )
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare_plain(result)
    assert "Diagnostics" in text
    assert "alpha.example.com" in text
    assert "beta.example.com" in text
    assert "WARN-001" in text
    assert "INFO-001" in text


def test_render_compare_diagnostics_one_url_only():
    """Compare should show diagnostics only for the URL that has them."""
    from context_cli.core.models import Diagnostic, LintCheck, LintResult
    a = _high_report()
    b = _low_report()
    a.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500, passed=False,
        diagnostics=[
            Diagnostic(code="WARN-001", severity="warn", message="DOM bloat"),
        ],
    )
    b.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=42.0, raw_tokens=10000, clean_tokens=5800, passed=True,
    )
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare_plain(result)
    assert "WARN-001" in text
    assert "Diagnostics" in text


def test_render_compare_no_diagnostics_without_lint():
    """Compare should not show diagnostics when no lint_result."""
    result = build_compare_report(_URL_A, _URL_B, _high_report(), _low_report())
    text = _capture_compare_plain(result)
    assert "Diagnostics:" not in text


def test_render_compare_diagnostics_error_severity():
    """Compare diagnostics should render error severity."""
    from context_cli.core.models import Diagnostic, LintCheck, LintResult
    a = _high_report()
    a.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=85.0, raw_tokens=10000, clean_tokens=1500, passed=False,
        diagnostics=[
            Diagnostic(code="ERR-001", severity="error", message="Critical issue"),
            Diagnostic(code="WARN-001", severity="warn", message="Minor issue"),
            Diagnostic(code="INFO-001", severity="info", message="Informational"),
        ],
    )
    b = _low_report()
    result = build_compare_report(_URL_A, _URL_B, a, b)
    text = _capture_compare_plain(result)
    assert "ERR-001" in text
    assert "WARN-001" in text
    assert "INFO-001" in text
