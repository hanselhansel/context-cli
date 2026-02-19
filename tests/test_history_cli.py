"""Tests for the history CLI subcommand."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from context_cli.core.history import HistoryEntry
from context_cli.core.models import (
    AuditReport,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)
from context_cli.main import app

runner = CliRunner()

_URL = "https://example.com"


def _entry(
    id: int = 1, score: float = 65.0, timestamp: str = "2026-02-19T12:00:00+00:00",
) -> HistoryEntry:
    return HistoryEntry(
        id=id,
        url=_URL,
        timestamp=timestamp,
        overall_score=score,
        robots_score=20.0,
        llms_txt_score=10.0,
        schema_org_score=15.0,
        content_score=20.0,
    )


def _report(score: float = 65.0) -> AuditReport:
    return AuditReport(
        url=_URL,
        overall_score=score,
        robots=RobotsReport(found=True, score=20.0, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="ok"),
        schema_org=SchemaReport(score=15.0, detail="ok"),
        content=ContentReport(score=20.0, detail="ok"),
    )


# ── history list (default) ─────────────────────────────────────────────────


@patch("context_cli.cli.history.HistoryDB")
def test_history_list_shows_entries(mock_db_cls):
    """history <url> shows past audit entries."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.list_entries.return_value = [
        _entry(id=2, score=70.0, timestamp="2026-02-19T14:00:00+00:00"),
        _entry(id=1, score=60.0, timestamp="2026-02-19T12:00:00+00:00"),
    ]

    result = runner.invoke(app, ["history", _URL])
    assert result.exit_code == 0
    assert "70" in result.output
    assert "60" in result.output
    mock_db.close.assert_called_once()


@patch("context_cli.cli.history.HistoryDB")
def test_history_list_empty(mock_db_cls):
    """history <url> shows message when no entries exist."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.list_entries.return_value = []

    result = runner.invoke(app, ["history", _URL])
    assert result.exit_code == 0
    assert "No history" in result.output
    mock_db.close.assert_called_once()


@patch("context_cli.cli.history.HistoryDB")
def test_history_list_limit(mock_db_cls):
    """history <url> --limit passes limit to DB."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.list_entries.return_value = [_entry()]

    runner.invoke(app, ["history", _URL, "--limit", "5"])
    mock_db.list_entries.assert_called_once_with(_URL, limit=5)


# ── history --json ─────────────────────────────────────────────────────────


@patch("context_cli.cli.history.HistoryDB")
def test_history_json_output(mock_db_cls):
    """history <url> --json outputs valid JSON."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.list_entries.return_value = [_entry()]

    result = runner.invoke(app, ["history", _URL, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["overall_score"] == 65.0


# ── history --show <id> ────────────────────────────────────────────────────


@patch("context_cli.cli.history.HistoryDB")
def test_history_show_full_report(mock_db_cls):
    """history <url> --show <id> shows the full report."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_report.return_value = _report(score=75.0)

    result = runner.invoke(app, ["history", _URL, "--show", "1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["overall_score"] == 75.0


@patch("context_cli.cli.history.HistoryDB")
def test_history_show_rich_output(mock_db_cls):
    """history <url> --show <id> renders report in Rich format by default."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_report.return_value = _report(score=75.0)

    result = runner.invoke(app, ["history", _URL, "--show", "1"])
    assert result.exit_code == 0
    assert "75" in result.output


@patch("context_cli.cli.history.HistoryDB")
def test_history_show_not_found(mock_db_cls):
    """history <url> --show <id> when ID doesn't exist."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_report.return_value = None

    result = runner.invoke(app, ["history", _URL, "--show", "999"])
    assert result.exit_code == 0
    assert "not found" in result.output.lower()


# ── history --delete ───────────────────────────────────────────────────────


@patch("context_cli.cli.history.HistoryDB")
def test_history_delete(mock_db_cls):
    """history <url> --delete removes entries."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.delete_url.return_value = 3

    result = runner.invoke(app, ["history", _URL, "--delete"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_db.close.assert_called_once()


@patch("context_cli.cli.history.HistoryDB")
def test_history_delete_nothing(mock_db_cls):
    """history <url> --delete when no entries exist."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.delete_url.return_value = 0

    result = runner.invoke(app, ["history", _URL, "--delete"])
    assert result.exit_code == 0
    assert "No history" in result.output or "0" in result.output
