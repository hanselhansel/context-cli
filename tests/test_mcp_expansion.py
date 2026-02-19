"""Tests for expanded MCP server tools: compare, history, recommend."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_cli.core.models import (
    AuditReport,
    CompareReport,
    ContentReport,
    LlmsTxtReport,
    PillarDelta,
    Recommendation,
    RobotsReport,
    SchemaReport,
)
from context_cli.server import compare, history, recommend

# FastMCP 2.x wraps @mcp.tool functions in a FunctionTool object.
_compare_fn = compare.fn if hasattr(compare, "fn") else compare
_history_fn = history.fn if hasattr(history, "fn") else history
_recommend_fn = recommend.fn if hasattr(recommend, "fn") else recommend


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_report(url: str = "https://example.com", score: float = 55.0) -> AuditReport:
    return AuditReport(
        url=url,
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="ok"),
        llms_txt=LlmsTxtReport(found=False, score=0),
        schema_org=SchemaReport(blocks_found=1, score=13),
        content=ContentReport(word_count=500, score=17),
    )


def _mock_compare_report() -> CompareReport:
    return CompareReport(
        url_a="https://a.example.com",
        url_b="https://b.example.com",
        score_a=80.0,
        score_b=50.0,
        delta=30.0,
        pillars=[
            PillarDelta(pillar="robots", score_a=25, score_b=15, delta=10, max_score=25),
            PillarDelta(pillar="llms_txt", score_a=10, score_b=0, delta=10, max_score=10),
            PillarDelta(pillar="schema_org", score_a=20, score_b=15, delta=5, max_score=25),
            PillarDelta(pillar="content", score_a=25, score_b=20, delta=5, max_score=40),
        ],
        report_a=_mock_report("https://a.example.com", 80.0),
        report_b=_mock_report("https://b.example.com", 50.0),
    )


# ── Compare MCP tool ────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.server.compare_urls", new_callable=AsyncMock)
async def test_compare_tool_returns_dict(mock_compare):
    """MCP compare tool should return a dict (CompareReport-like)."""
    mock_compare.return_value = _mock_compare_report()
    result = await _compare_fn("https://a.example.com", "https://b.example.com")

    assert isinstance(result, dict)
    assert result["url_a"] == "https://a.example.com"
    assert result["url_b"] == "https://b.example.com"
    assert result["delta"] == 30.0
    assert "pillars" in result


@pytest.mark.asyncio
@patch("context_cli.server.compare_urls", new_callable=AsyncMock)
async def test_compare_tool_calls_compare_urls(mock_compare):
    """MCP compare tool should call compare_urls with both URLs."""
    mock_compare.return_value = _mock_compare_report()
    await _compare_fn("https://a.example.com", "https://b.example.com")
    mock_compare.assert_called_once_with("https://a.example.com", "https://b.example.com")


@pytest.mark.asyncio
@patch("context_cli.server.compare_urls", new_callable=AsyncMock)
async def test_compare_tool_includes_pillar_deltas(mock_compare):
    """MCP compare tool result should include pillar deltas."""
    mock_compare.return_value = _mock_compare_report()
    result = await _compare_fn("https://a.example.com", "https://b.example.com")
    assert len(result["pillars"]) == 4
    pillar_names = {p["pillar"] for p in result["pillars"]}
    assert pillar_names == {"robots", "llms_txt", "schema_org", "content"}


# ── History MCP tool ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_history_tool_returns_list(tmp_path):
    """MCP history tool should return a list of entries."""
    with patch("context_cli.server.HistoryDB") as MockDB:
        mock_db = MagicMock()
        mock_db.list_entries.return_value = []
        MockDB.return_value = mock_db

        result = await _history_fn("https://example.com")

        assert isinstance(result, list)
        assert result == []


@pytest.mark.asyncio
async def test_history_tool_passes_limit():
    """MCP history tool should pass limit param to list_entries."""
    with patch("context_cli.server.HistoryDB") as MockDB:
        mock_db = MagicMock()
        mock_db.list_entries.return_value = []
        MockDB.return_value = mock_db

        await _history_fn("https://example.com", limit=5)

        mock_db.list_entries.assert_called_once_with("https://example.com", limit=5)


@pytest.mark.asyncio
async def test_history_tool_returns_serialized_entries():
    """MCP history tool should return entries as dicts."""
    from context_cli.core.history import HistoryEntry

    entries = [
        HistoryEntry(
            id=1,
            url="https://example.com",
            timestamp="2026-01-01T00:00:00Z",
            overall_score=55.0,
            robots_score=25.0,
            llms_txt_score=0.0,
            schema_org_score=13.0,
            content_score=17.0,
        ),
    ]
    with patch("context_cli.server.HistoryDB") as MockDB:
        mock_db = MagicMock()
        mock_db.list_entries.return_value = entries
        MockDB.return_value = mock_db

        result = await _history_fn("https://example.com")

        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["overall_score"] == 55.0


@pytest.mark.asyncio
async def test_history_tool_default_limit():
    """MCP history tool should default to limit=10."""
    with patch("context_cli.server.HistoryDB") as MockDB:
        mock_db = MagicMock()
        mock_db.list_entries.return_value = []
        MockDB.return_value = mock_db

        await _history_fn("https://example.com")

        mock_db.list_entries.assert_called_once_with("https://example.com", limit=10)


# ── Recommend MCP tool ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("context_cli.server.generate_recommendations")
@patch("context_cli.server.audit_url", new_callable=AsyncMock)
async def test_recommend_tool_returns_list(mock_audit, mock_gen_recs):
    """MCP recommend tool should return a list of recommendations."""
    mock_audit.return_value = _mock_report()
    mock_gen_recs.return_value = [
        Recommendation(
            pillar="llms_txt",
            action="Create llms.txt",
            estimated_impact=10.0,
            priority="high",
            detail="No llms.txt found",
        ),
    ]
    result = await _recommend_fn("https://example.com")

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["pillar"] == "llms_txt"
    assert result[0]["action"] == "Create llms.txt"


@pytest.mark.asyncio
@patch("context_cli.server.generate_recommendations")
@patch("context_cli.server.audit_url", new_callable=AsyncMock)
async def test_recommend_tool_audits_first(mock_audit, mock_gen_recs):
    """MCP recommend tool should audit the URL before generating recommendations."""
    report = _mock_report()
    mock_audit.return_value = report
    mock_gen_recs.return_value = []

    await _recommend_fn("https://example.com")

    mock_audit.assert_called_once_with("https://example.com")
    mock_gen_recs.assert_called_once_with(report)


@pytest.mark.asyncio
@patch("context_cli.server.generate_recommendations")
@patch("context_cli.server.audit_url", new_callable=AsyncMock)
async def test_recommend_tool_empty_recommendations(mock_audit, mock_gen_recs):
    """MCP recommend tool should return empty list when no recommendations."""
    mock_audit.return_value = _mock_report()
    mock_gen_recs.return_value = []

    result = await _recommend_fn("https://example.com")
    assert result == []
