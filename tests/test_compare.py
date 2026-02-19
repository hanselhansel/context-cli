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
