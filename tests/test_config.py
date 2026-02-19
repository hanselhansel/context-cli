"""Tests for .aeorc.yml configuration file support."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from context_cli.core.config import AeoConfig, load_config

# ── AeoConfig model ────────────────────────────────────────────────────────


def test_default_config():
    """Default config should have sensible defaults."""
    cfg = AeoConfig()
    assert cfg.timeout == 15
    assert cfg.max_pages == 10
    assert cfg.single is False
    assert cfg.verbose is False
    assert cfg.save is False
    assert cfg.regression_threshold == 5.0
    assert cfg.bots is None
    assert cfg.format is None


def test_config_with_values():
    """Config should accept custom values."""
    cfg = AeoConfig(timeout=30, bots=["GPTBot", "ClaudeBot"], save=True)
    assert cfg.timeout == 30
    assert cfg.bots == ["GPTBot", "ClaudeBot"]
    assert cfg.save is True


def test_config_serializable():
    """Config should be serializable."""
    cfg = AeoConfig(timeout=30)
    data = cfg.model_dump()
    assert data["timeout"] == 30


# ── load_config ────────────────────────────────────────────────────────────


def test_load_config_from_cwd(tmp_path: Path):
    """Config loads from .aeorc.yml in CWD."""
    config_file = tmp_path / ".aeorc.yml"
    config_file.write_text("timeout: 30\nsave: true\n")

    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.timeout == 30
    assert cfg.save is True


def test_load_config_from_home(tmp_path: Path):
    """Config loads from ~/.aeorc.yml when CWD has none."""
    home_config = tmp_path / ".aeorc.yml"
    home_config.write_text("verbose: true\nmax_pages: 5\n")

    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.verbose is True
    assert cfg.max_pages == 5


def test_load_config_cwd_overrides_home(tmp_path: Path):
    """CWD config takes priority over home config."""
    cwd_dir = tmp_path / "project"
    cwd_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    (home_dir / ".aeorc.yml").write_text("timeout: 60\nverbose: true\n")
    (cwd_dir / ".aeorc.yml").write_text("timeout: 10\n")

    cfg = load_config(search_dirs=[cwd_dir, home_dir])
    assert cfg.timeout == 10
    # home's verbose is NOT inherited (CWD config replaces entirely)


def test_load_config_no_file(tmp_path: Path):
    """Returns default config when no file found."""
    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.timeout == 15  # default


def test_load_config_empty_file(tmp_path: Path):
    """Empty YAML file returns default config."""
    (tmp_path / ".aeorc.yml").write_text("")
    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.timeout == 15


def test_load_config_invalid_yaml(tmp_path: Path):
    """Invalid YAML returns default config without crashing."""
    (tmp_path / ".aeorc.yml").write_text(": : : invalid yaml [")
    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.timeout == 15


def test_load_config_bots_list(tmp_path: Path):
    """Bots should be parsed as a list."""
    (tmp_path / ".aeorc.yml").write_text("bots:\n  - GPTBot\n  - ClaudeBot\n")
    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.bots == ["GPTBot", "ClaudeBot"]


def test_load_config_format_string(tmp_path: Path):
    """Format should be parsed as a string."""
    (tmp_path / ".aeorc.yml").write_text("format: json\n")
    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.format == "json"


def test_load_config_unknown_keys_ignored(tmp_path: Path):
    """Unknown keys in config should be ignored."""
    (tmp_path / ".aeorc.yml").write_text("timeout: 20\nunknown_key: value\n")
    cfg = load_config(search_dirs=[tmp_path])
    assert cfg.timeout == 20


def test_load_config_default_search_dirs():
    """Default search dirs include CWD and home."""
    with patch("context_cli.core.config.Path.cwd", return_value=Path("/mock/cwd")):
        with patch("context_cli.core.config.Path.home", return_value=Path("/mock/home")):
            # This just tests the function runs without error with default dirs
            cfg = load_config()
            assert isinstance(cfg, AeoConfig)


# ── CLI integration ────────────────────────────────────────────────────────


@patch("context_cli.cli.audit._run_audit")
@patch("context_cli.cli.audit.load_config")
def test_cli_config_timeout_applies(mock_load, mock_run):
    """Config file timeout is used when CLI flag not explicitly set."""
    from typer.testing import CliRunner

    from context_cli.main import app

    mock_load.return_value = AeoConfig(timeout=45)
    mock_run.return_value = _make_report()

    runner = CliRunner()
    runner.invoke(app, ["audit", "https://example.com", "--json"])
    _, kwargs = mock_run.call_args
    assert kwargs.get("timeout") == 45 or mock_run.call_args[0][3] == 45


@patch("context_cli.cli.audit._save_to_history")
@patch("context_cli.cli.audit._run_audit")
@patch("context_cli.cli.audit.load_config")
def test_cli_config_save_applies(mock_load, mock_run, mock_save):
    """Config save=true auto-saves without --save flag."""
    from typer.testing import CliRunner

    from context_cli.main import app

    mock_load.return_value = AeoConfig(save=True)
    mock_run.return_value = _make_report()

    runner = CliRunner()
    runner.invoke(app, ["audit", "https://example.com", "--json"])
    mock_save.assert_called_once()


@patch("context_cli.cli.audit._run_audit")
@patch("context_cli.cli.audit.load_config")
def test_cli_config_format_applies(mock_load, mock_run):
    """Config format is used when CLI --format not specified."""
    from typer.testing import CliRunner

    from context_cli.main import app

    mock_load.return_value = AeoConfig(format="json")
    mock_run.return_value = _make_report()

    runner = CliRunner()
    result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0
    assert '"url"' in result.output  # JSON output


@patch("context_cli.cli.audit._run_audit")
@patch("context_cli.cli.audit.load_config")
def test_cli_config_format_invalid_ignored(mock_load, mock_run):
    """Invalid config format string is silently ignored."""
    from typer.testing import CliRunner

    from context_cli.main import app

    mock_load.return_value = AeoConfig(format="nonexistent")
    mock_run.return_value = _make_report()

    runner = CliRunner()
    result = runner.invoke(app, ["audit", "https://example.com"])
    assert result.exit_code == 0


@patch("context_cli.cli.audit._run_audit")
@patch("context_cli.cli.audit.load_config")
def test_cli_config_bots_applies(mock_load, mock_run):
    """Config bots list is used when --bots not passed."""
    from typer.testing import CliRunner

    from context_cli.main import app

    mock_load.return_value = AeoConfig(bots=["BotA", "BotB"])
    mock_run.return_value = _make_report()

    runner = CliRunner()
    runner.invoke(app, ["audit", "https://example.com", "--json"])
    _, kwargs = mock_run.call_args
    assert kwargs.get("bots") == ["BotA", "BotB"]


def _make_report():
    from context_cli.core.models import (
        AuditReport,
        ContentReport,
        LlmsTxtReport,
        RobotsReport,
        SchemaReport,
    )

    return AuditReport(
        url="https://example.com",
        overall_score=65.0,
        robots=RobotsReport(found=True, score=20.0, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="ok"),
        schema_org=SchemaReport(score=15.0, detail="ok"),
        content=ContentReport(score=20.0, detail="ok"),
    )
