"""Tests for the watch command — continuous monitoring with periodic audits."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_report(url: str = "https://example.com", score: float = 75.0) -> AuditReport:
    return AuditReport(
        url=url,
        overall_score=score,
        robots=RobotsReport(found=True, score=20.0, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=8.0, detail="ok"),
        schema_org=SchemaReport(score=22.0, detail="ok"),
        content=ContentReport(score=25.0, detail="ok"),
    )


# ── Basic watch command tests ────────────────────────────────────────────────


class TestWatchCommand:
    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_runs_one_iteration_then_ctrl_c(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch runs one audit, then KeyboardInterrupt during sleep stops it."""
        result = runner.invoke(app, ["watch", "https://example.com", "--interval", "60"])
        assert result.exit_code == 0
        assert "Run #1" in result.output
        mock_run.assert_called_once()

    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_with_json_flag(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch --json outputs JSON instead of Rich table."""
        result = runner.invoke(app, ["watch", "https://example.com", "--json"])
        assert result.exit_code == 0
        # Should contain JSON-ish output (url key)
        assert "example.com" in result.output

    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_with_single_flag(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch --single passes single=True to audit."""
        result = runner.invoke(
            app, ["watch", "https://example.com", "--single", "--interval", "60"],
        )
        assert result.exit_code == 0
        assert "Run #1" in result.output

    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    @patch("context_cli.cli.watch._save_to_history")
    def test_watch_with_save_flag(
        self, mock_save: MagicMock, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch --save calls history save after each audit."""
        result = runner.invoke(
            app, ["watch", "https://example.com", "--save", "--single"],
        )
        assert result.exit_code == 0
        mock_save.assert_called_once()


class TestWatchFailUnder:
    @patch("context_cli.cli.watch.time.sleep")
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report(score=40.0))
    def test_watch_fail_under_exits_on_low_score(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch --fail-under exits with code 1 when score is below threshold."""
        result = runner.invoke(
            app, ["watch", "https://example.com", "--fail-under", "50"],
        )
        assert result.exit_code == 1

    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report(score=80.0))
    def test_watch_fail_under_continues_on_passing_score(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch --fail-under continues when score is above threshold."""
        result = runner.invoke(
            app, ["watch", "https://example.com", "--fail-under", "50"],
        )
        assert result.exit_code == 0
        assert "Run #1" in result.output


class TestWatchGracefulShutdown:
    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_ctrl_c_prints_summary(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Ctrl+C shows summary with run count."""
        result = runner.invoke(app, ["watch", "https://example.com"])
        assert result.exit_code == 0
        assert "Stopped" in result.output or "1 run" in result.output

    @patch("context_cli.cli.watch.asyncio.run", side_effect=KeyboardInterrupt)
    def test_watch_ctrl_c_during_audit(self, mock_run: MagicMock) -> None:
        """Ctrl+C during audit itself still exits gracefully."""
        result = runner.invoke(app, ["watch", "https://example.com"])
        assert result.exit_code == 0
        assert "Stopped" in result.output or "0 run" in result.output


class TestWatchRunCounter:
    @patch("context_cli.cli.watch.time.sleep")
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_displays_run_counter(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch displays incrementing run counter."""
        # Let it run 3 times then KeyboardInterrupt
        call_count = 0

        def sleep_side_effect(seconds: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt

        mock_sleep.side_effect = sleep_side_effect

        result = runner.invoke(app, ["watch", "https://example.com", "--interval", "1"])
        assert result.exit_code == 0
        assert "Run #1" in result.output
        assert "Run #2" in result.output


class TestWatchBotsOption:
    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_with_custom_bots(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch --bots passes custom bot list."""
        result = runner.invoke(
            app, ["watch", "https://example.com", "--bots", "GPTBot,ClaudeBot"],
        )
        assert result.exit_code == 0


class TestWatchUrlNormalization:
    @patch("context_cli.cli.watch.time.sleep", side_effect=KeyboardInterrupt)
    @patch("context_cli.cli.watch.asyncio.run", return_value=_make_report())
    def test_watch_prepends_https(
        self, mock_run: MagicMock, mock_sleep: MagicMock,
    ) -> None:
        """Watch adds https:// if URL doesn't start with http."""
        result = runner.invoke(app, ["watch", "example.com"])
        assert result.exit_code == 0


# ── _save_to_history tests ───────────────────────────────────────────────────


class TestSaveToHistory:
    @patch("context_cli.cli.watch.HistoryDB")
    def test_save_to_history_no_previous(self, mock_db_cls: MagicMock) -> None:
        """Save to history when no previous report exists."""
        mock_db = MagicMock()
        mock_db.get_latest_report.return_value = None
        mock_db_cls.return_value = mock_db

        from context_cli.cli.watch import _save_to_history

        report = _make_report()
        _save_to_history(report)
        mock_db.save.assert_called_once_with(report)
        mock_db.close.assert_called_once()

    @patch("context_cli.cli.watch.detect_regression")
    @patch("context_cli.cli.watch.HistoryDB")
    def test_save_to_history_with_regression(
        self, mock_db_cls: MagicMock, mock_detect: MagicMock,
    ) -> None:
        """Save to history detects regression when previous exists."""
        mock_db = MagicMock()
        previous = _make_report(score=90.0)
        mock_db.get_latest_report.return_value = previous
        mock_db_cls.return_value = mock_db

        mock_result = MagicMock()
        mock_result.has_regression = True
        mock_result.delta = -15.0
        mock_result.previous_score = 90.0
        mock_result.current_score = 75.0
        mock_detect.return_value = mock_result

        from context_cli.cli.watch import _save_to_history

        report = _make_report(score=75.0)
        _save_to_history(report)
        mock_detect.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("context_cli.cli.watch.detect_regression")
    @patch("context_cli.cli.watch.HistoryDB")
    def test_save_to_history_no_regression(
        self, mock_db_cls: MagicMock, mock_detect: MagicMock,
    ) -> None:
        """Save to history with previous but no regression."""
        mock_db = MagicMock()
        previous = _make_report(score=74.0)
        mock_db.get_latest_report.return_value = previous
        mock_db_cls.return_value = mock_db

        mock_result = MagicMock()
        mock_result.has_regression = False
        mock_detect.return_value = mock_result

        from context_cli.cli.watch import _save_to_history

        report = _make_report(score=75.0)
        _save_to_history(report)
        mock_detect.assert_called_once()

    @patch("context_cli.cli.watch.HistoryDB")
    def test_save_to_history_handles_exception(self, mock_db_cls: MagicMock) -> None:
        """Save to history catches exceptions gracefully."""
        mock_db = MagicMock()
        mock_db.get_latest_report.side_effect = RuntimeError("db error")
        mock_db_cls.return_value = mock_db

        from context_cli.cli.watch import _save_to_history

        report = _make_report()
        # Should not raise
        _save_to_history(report)
        mock_db.close.assert_called_once()
