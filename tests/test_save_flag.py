"""Tests for --save flag and history integration in audit CLI."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console
from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.core.regression import RegressionReport
from context_cli.main import app

runner = CliRunner()

_URL = "https://example.com"


def _report(score: float = 65.0) -> AuditReport:
    return AuditReport(
        url=_URL,
        overall_score=score,
        robots=RobotsReport(found=True, score=20.0, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="ok"),
        schema_org=SchemaReport(score=15.0, detail="ok"),
        content=ContentReport(score=20.0, detail="ok"),
    )


def _site_report(score: float = 65.0) -> SiteAuditReport:
    return SiteAuditReport(
        url=_URL,
        domain="example.com",
        overall_score=score,
        robots=RobotsReport(found=True, score=20.0, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="ok"),
        schema_org=SchemaReport(score=15.0, detail="ok"),
        content=ContentReport(score=20.0, detail="ok"),
        discovery=DiscoveryResult(method="sitemap", urls_found=1, detail="ok"),
    )


def _regression(has_regression: bool = True, delta: float = -20.0) -> RegressionReport:
    return RegressionReport(
        url=_URL,
        previous_score=70.0,
        current_score=50.0,
        delta=delta,
        has_regression=has_regression,
        threshold=5.0,
        pillars=[],
    )


# ── _save_to_history unit tests ────────────────────────────────────────────


@patch("context_cli.cli.audit.detect_regression")
@patch("context_cli.cli.audit.HistoryDB")
def test_save_to_history_saves_report(mock_db_cls, mock_regress):
    """_save_to_history saves the report and closes the DB."""
    from context_cli.cli.audit import _save_to_history

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_latest_report.return_value = None

    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=80)
    _save_to_history(_report(), con)

    mock_db.save.assert_called_once()
    mock_db.close.assert_called_once()
    assert "Saved" in buf.getvalue()


@patch("context_cli.cli.audit.detect_regression")
@patch("context_cli.cli.audit.HistoryDB")
def test_save_to_history_closes_on_error(mock_db_cls, mock_regress):
    """DB is closed even when an error occurs."""
    from context_cli.cli.audit import _save_to_history

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_latest_report.side_effect = RuntimeError("db error")

    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=80)
    _save_to_history(_report(), con)

    mock_db.close.assert_called_once()
    assert "error" in buf.getvalue().lower()


@patch("context_cli.cli.audit.detect_regression")
@patch("context_cli.cli.audit.HistoryDB")
def test_save_to_history_no_regression_first_audit(mock_db_cls, mock_regress):
    """First audit for a URL — no previous, no regression check."""
    from context_cli.cli.audit import _save_to_history

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_latest_report.return_value = None

    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=80)
    _save_to_history(_report(), con)

    mock_regress.assert_not_called()


@patch("context_cli.cli.audit.detect_regression")
@patch("context_cli.cli.audit.HistoryDB")
def test_save_to_history_detects_regression(mock_db_cls, mock_regress):
    """Shows warning when score dropped beyond threshold."""
    from context_cli.cli.audit import _save_to_history

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_latest_report.return_value = _report(score=70.0)
    mock_regress.return_value = _regression(has_regression=True, delta=-20.0)

    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=80)
    _save_to_history(_report(score=50.0), con)

    mock_regress.assert_called_once()
    output = buf.getvalue().lower()
    assert "regression" in output


@patch("context_cli.cli.audit.detect_regression")
@patch("context_cli.cli.audit.HistoryDB")
def test_save_to_history_no_warning_when_score_improves(mock_db_cls, mock_regress):
    """No regression warning when score improves."""
    from context_cli.cli.audit import _save_to_history

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_latest_report.return_value = _report(score=50.0)
    mock_regress.return_value = _regression(has_regression=False, delta=15.0)

    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=80)
    _save_to_history(_report(score=65.0), con)

    mock_regress.assert_called_once()
    output = buf.getvalue().lower()
    assert "regression" not in output


# ── CLI integration tests ──────────────────────────────────────────────────


@patch("context_cli.cli.audit._save_to_history")
@patch("context_cli.cli.audit._run_audit")
def test_cli_save_flag_triggers_save(mock_run, mock_save):
    """--save triggers _save_to_history for single-page audit."""
    mock_run.return_value = _report()
    result = runner.invoke(app, ["audit", _URL, "--save", "--json"])
    assert result.exit_code == 0
    mock_save.assert_called_once()


@patch("context_cli.cli.audit._save_to_history")
@patch("context_cli.cli.audit._run_audit")
def test_cli_no_save_without_flag(mock_run, mock_save):
    """Without --save, _save_to_history is not called."""
    mock_run.return_value = _report()
    result = runner.invoke(app, ["audit", _URL, "--json"])
    assert result.exit_code == 0
    mock_save.assert_not_called()


@patch("context_cli.cli.audit._save_to_history")
@patch("context_cli.cli.audit._run_audit")
def test_cli_save_site_audit_shows_note(mock_run, mock_save):
    """--save with multi-page audit prints a note and skips save."""
    mock_run.return_value = _site_report()
    result = runner.invoke(app, ["audit", _URL, "--save", "--json"])
    assert result.exit_code == 0
    mock_save.assert_not_called()
    assert "--single" in result.output


@patch("context_cli.cli.audit._save_to_history")
@patch("context_cli.cli.audit._run_audit")
def test_cli_save_works_with_rich_output(mock_run, mock_save):
    """--save works with default Rich output (no --json)."""
    mock_run.return_value = _report()
    result = runner.invoke(app, ["audit", _URL, "--save"])
    assert result.exit_code == 0
    mock_save.assert_called_once()


@patch("context_cli.cli.audit._save_to_history")
@patch("context_cli.cli.audit._run_audit")
def test_cli_regression_threshold_flag(mock_run, mock_save):
    """--regression-threshold passes custom threshold to _save_to_history."""
    mock_run.return_value = _report()
    runner.invoke(app, ["audit", _URL, "--save", "--regression-threshold", "10", "--json"])
    mock_save.assert_called_once()
    _, kwargs = mock_save.call_args
    assert kwargs["threshold"] == 10.0


@patch("context_cli.cli.audit.detect_regression")
@patch("context_cli.cli.audit.HistoryDB")
def test_save_to_history_passes_threshold(mock_db_cls, mock_regress):
    """Custom threshold is forwarded to detect_regression."""
    from context_cli.cli.audit import _save_to_history

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    mock_db.get_latest_report.return_value = _report(score=70.0)
    mock_regress.return_value = _regression(has_regression=False, delta=-3.0)

    buf = StringIO()
    con = Console(file=buf, force_terminal=True, width=80)
    _save_to_history(_report(score=67.0), con, threshold=10.0)

    mock_regress.assert_called_once()
    _, kwargs = mock_regress.call_args
    assert kwargs["threshold"] == 10.0
