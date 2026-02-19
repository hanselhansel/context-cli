"""Tests for the leaderboard CLI command and formatter module."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    LintCheck,
    LintResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)
from context_cli.formatters.leaderboard import (
    format_leaderboard_json,
    format_leaderboard_md,
)
from context_cli.main import app

runner = CliRunner()


# ── Mock helpers ─────────────────────────────────────────────────────────────


def _mock_report(url: str, waste: float = 50.0, score: float = 55.0) -> AuditReport:
    """Create a mock AuditReport with configurable waste percentage."""
    return AuditReport(
        url=url,
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="OK"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(word_count=500, score=17, detail="500 words"),
        lint_result=LintResult(
            checks=[
                LintCheck(
                    name="Token Efficiency",
                    passed=waste < 70,
                    detail=f"{waste}%",
                ),
            ],
            context_waste_pct=waste,
            raw_tokens=10000,
            clean_tokens=int(10000 * (100 - waste) / 100),
            passed=waste < 70,
        ),
    )


def _mock_report_no_lint(url: str, waste: float = 50.0) -> AuditReport:
    """Create a mock AuditReport without lint_result (uses content.context_waste_pct)."""
    return AuditReport(
        url=url,
        overall_score=55.0,
        robots=RobotsReport(found=True, score=25, detail="OK"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(
            word_count=500, score=17, detail="500 words",
            context_waste_pct=waste,
        ),
    )


# ── Formatter unit tests ────────────────────────────────────────────────────


def test_format_leaderboard_md_basic():
    """Markdown formatter outputs a Markdown table sorted by waste ascending."""
    reports = [
        _mock_report("https://high-waste.com", waste=80.0, score=30.0),
        _mock_report("https://low-waste.com", waste=20.0, score=80.0),
        _mock_report("https://mid-waste.com", waste=50.0, score=55.0),
    ]
    md = format_leaderboard_md(reports)
    assert "# Context CLI Leaderboard" in md
    assert "Target URL" in md
    assert "Context Waste %" in md
    assert "RAG Ready?" in md
    # low-waste should be rank 1
    lines = md.strip().splitlines()
    data_lines = [
        ln for ln in lines
        if ln.startswith("| ") and "#" not in ln.split("|")[1] and "---" not in ln
    ]
    assert "low-waste.com" in data_lines[0]
    assert "mid-waste.com" in data_lines[1]
    assert "high-waste.com" in data_lines[2]


def test_format_leaderboard_md_rag_ready():
    """RAG Ready should be Yes if waste < threshold, No otherwise."""
    reports = [
        _mock_report("https://good.com", waste=60.0),
        _mock_report("https://bad.com", waste=80.0),
    ]
    md = format_leaderboard_md(reports, waste_threshold=70.0)
    # good.com is waste=60 < 70 => Yes
    assert "| Yes |" in md
    # bad.com is waste=80 >= 70 => No
    assert "| No |" in md


def test_format_leaderboard_md_custom_threshold():
    """Custom waste_threshold should change RAG Ready classification."""
    reports = [_mock_report("https://test.com", waste=60.0)]
    md_strict = format_leaderboard_md(reports, waste_threshold=50.0)
    assert "| No |" in md_strict
    md_loose = format_leaderboard_md(reports, waste_threshold=70.0)
    assert "| Yes |" in md_loose


def test_format_leaderboard_json_basic():
    """JSON formatter outputs sorted leaderboard entries."""
    reports = [
        _mock_report("https://b.com", waste=70.0, score=40.0),
        _mock_report("https://a.com", waste=30.0, score=80.0),
    ]
    raw = format_leaderboard_json(reports)
    data = json.loads(raw)
    assert "leaderboard" in data
    entries = data["leaderboard"]
    assert len(entries) == 2
    assert entries[0]["rank"] == 1
    assert entries[0]["url"] == "https://a.com"
    assert entries[0]["context_waste_pct"] == 30.0
    assert entries[0]["rag_ready"] is True
    assert entries[1]["rank"] == 2
    assert entries[1]["url"] == "https://b.com"
    assert entries[1]["rag_ready"] is False


def test_format_leaderboard_json_custom_threshold():
    """JSON format respects waste_threshold for rag_ready field."""
    reports = [_mock_report("https://test.com", waste=60.0)]
    raw = format_leaderboard_json(reports, waste_threshold=50.0)
    data = json.loads(raw)
    assert data["leaderboard"][0]["rag_ready"] is False


def test_format_leaderboard_md_no_lint_result():
    """Formatter treats no lint_result as 0 tokens and 0% waste in display."""
    reports = [_mock_report_no_lint("https://nolint.com", waste=45.0)]
    md = format_leaderboard_md(reports)
    assert "nolint.com" in md
    # Without lint_result, raw/clean tokens are 0 and waste displays as 0%
    assert "| 0 |" in md


def test_format_leaderboard_json_no_lint_result():
    """JSON formatter treats no lint_result as 0 context_waste_pct."""
    reports = [_mock_report_no_lint("https://nolint.com", waste=45.0)]
    raw = format_leaderboard_json(reports)
    data = json.loads(raw)
    assert data["leaderboard"][0]["context_waste_pct"] == 0.0


# ── CLI command tests ────────────────────────────────────────────────────────


def test_leaderboard_url_file(tmp_path):
    """Leaderboard reads URLs from a .txt file and outputs markdown."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\nhttps://b.com\n")

    reports = [
        _mock_report("https://a.com", waste=40.0),
        _mock_report("https://b.com", waste=60.0),
    ]

    async def _fake(url, **kwargs):
        for r in reports:
            if r.url == url:
                return r
        raise RuntimeError("unexpected URL")

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(app, ["leaderboard", str(url_file)])

    assert result.exit_code == 0
    assert "Context CLI Leaderboard" in result.output
    assert "a.com" in result.output
    assert "b.com" in result.output


def test_leaderboard_json_format(tmp_path):
    """Leaderboard --format json outputs valid JSON."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")

    async def _fake(url, **kwargs):
        return _mock_report("https://a.com", waste=50.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["leaderboard", str(url_file), "--format", "json"]
        )

    assert result.exit_code == 0
    assert "leaderboard" in result.output


def test_leaderboard_output_file(tmp_path):
    """Leaderboard --output flag writes result to file."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")
    out_file = tmp_path / "result.md"

    async def _fake(url, **kwargs):
        return _mock_report("https://a.com", waste=30.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["leaderboard", str(url_file), "--output", str(out_file)]
        )

    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "Context CLI Leaderboard" in content
    assert "saved to" in result.output


def test_leaderboard_waste_threshold_flag(tmp_path):
    """Leaderboard --waste-threshold changes RAG Ready classification."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")

    async def _fake(url, **kwargs):
        return _mock_report("https://a.com", waste=60.0)

    # Default threshold=70, waste=60 => Yes
    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(app, ["leaderboard", str(url_file)])
    assert result.exit_code == 0
    assert "Yes" in result.output

    # Strict threshold=50, waste=60 => No
    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["leaderboard", str(url_file), "--waste-threshold", "50"]
        )
    assert result.exit_code == 0
    assert "No" in result.output


def test_leaderboard_empty_file(tmp_path):
    """Empty URL file should show 'No URLs found' and exit 1."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("# just comments\n\n")

    result = runner.invoke(app, ["leaderboard", str(url_file)])

    assert result.exit_code == 1
    assert "No URLs found" in result.output


def test_leaderboard_file_not_found(tmp_path):
    """Non-existent source file should show error and exit 1."""
    result = runner.invoke(
        app, ["leaderboard", str(tmp_path / "nonexistent.txt")]
    )
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_leaderboard_all_audits_fail(tmp_path):
    """All audit failures should show error message and exit 1."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\nhttps://b.com\n")

    async def _fake(url, **kwargs):
        raise RuntimeError("Connection refused")

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(app, ["leaderboard", str(url_file)])

    assert result.exit_code == 1
    assert "All audits failed" in result.output
    assert "Connection refused" in result.output


def test_leaderboard_mixed_success_failure(tmp_path):
    """Mixed results: some succeed, some fail; output includes both."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://good.com\nhttps://bad.com\n")

    async def _fake(url, **kwargs):
        if "bad" in url:
            raise RuntimeError("Timeout")
        return _mock_report("https://good.com", waste=50.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(app, ["leaderboard", str(url_file)])

    assert result.exit_code == 0
    assert "good.com" in result.output
    assert "1 URL(s) failed" in result.output
    assert "Timeout" in result.output


def test_leaderboard_stdin(tmp_path):
    """Leaderboard with '-' reads URLs from stdin."""
    fake_stdin = StringIO("https://a.com\n# comment\nhttps://b.com\n")

    async def _fake(url, **kwargs):
        return _mock_report(url, waste=30.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake), \
         patch("context_cli.cli.leaderboard.sys") as mock_sys:
        mock_sys.stdin.read.return_value = fake_stdin.getvalue()
        result = runner.invoke(app, ["leaderboard", "-"])

    assert result.exit_code == 0
    assert "a.com" in result.output
    assert "b.com" in result.output


def test_leaderboard_stdin_auto_https():
    """Stdin URLs without scheme should get https:// prepended."""
    captured_urls: list[str] = []

    async def _fake(url, **kwargs):
        captured_urls.append(url)
        return _mock_report(url, waste=30.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake), \
         patch("context_cli.cli.leaderboard.sys") as mock_sys:
        mock_sys.stdin.read.return_value = "example.com\nhttps://already.com\n"
        result = runner.invoke(app, ["leaderboard", "-"])

    assert result.exit_code == 0
    assert "https://example.com" in captured_urls
    assert "https://already.com" in captured_urls


def test_leaderboard_stdin_empty():
    """Empty stdin should show 'No URLs found' and exit 1."""
    with patch("context_cli.cli.leaderboard.sys") as mock_sys:
        mock_sys.stdin.read.return_value = "\n# only comments\n  \n"
        result = runner.invoke(app, ["leaderboard", "-"])

    assert result.exit_code == 1
    assert "No URLs found" in result.output


def test_leaderboard_timeout_flag(tmp_path):
    """Leaderboard --timeout should be passed through to audit_url."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")
    captured_kwargs: list[dict] = []

    async def _fake(url, **kwargs):
        captured_kwargs.append(kwargs)
        return _mock_report(url, waste=30.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["leaderboard", str(url_file), "--timeout", "30"]
        )

    assert result.exit_code == 0
    assert captured_kwargs[0]["timeout"] == 30


def test_leaderboard_concurrency_flag(tmp_path):
    """Leaderboard --concurrency should limit parallel audits."""
    import asyncio

    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "https://a.com\nhttps://b.com\nhttps://c.com\nhttps://d.com\n"
    )

    active = 0
    max_active = 0

    async def _fake(url, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return _mock_report(url, waste=30.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, ["leaderboard", str(url_file), "--concurrency", "2"]
        )

    assert result.exit_code == 0
    assert max_active <= 2


def test_leaderboard_json_output_file(tmp_path):
    """Leaderboard --format json --output writes JSON to file."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")
    out_file = tmp_path / "result.json"

    async def _fake(url, **kwargs):
        return _mock_report("https://a.com", waste=45.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(
            app, [
                "leaderboard", str(url_file),
                "--format", "json",
                "--output", str(out_file),
            ]
        )

    assert result.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert data["leaderboard"][0]["url"] == "https://a.com"


def test_leaderboard_csv_urls(tmp_path):
    """Leaderboard should handle .csv URL files correctly."""
    url_file = tmp_path / "urls.csv"
    url_file.write_text("url,name\nhttps://a.com,Site A\nhttps://b.com,Site B\n")

    async def _fake(url, **kwargs):
        return _mock_report(url, waste=30.0)

    with patch("context_cli.cli.leaderboard.audit_url", side_effect=_fake):
        result = runner.invoke(app, ["leaderboard", str(url_file)])

    assert result.exit_code == 0
    assert "a.com" in result.output
    assert "b.com" in result.output


# ── Formatter edge cases ─────────────────────────────────────────────────────


def test_format_leaderboard_md_single_report():
    """Markdown formatter works with a single report."""
    reports = [_mock_report("https://only.com", waste=10.0, score=90.0)]
    md = format_leaderboard_md(reports)
    assert "| 1 |" in md
    assert "only.com" in md
    assert "10%" in md


def test_format_leaderboard_json_single_report():
    """JSON formatter works with a single report."""
    reports = [_mock_report("https://only.com", waste=10.0, score=90.0)]
    raw = format_leaderboard_json(reports)
    data = json.loads(raw)
    assert len(data["leaderboard"]) == 1
    assert data["leaderboard"][0]["url"] == "https://only.com"


def test_format_leaderboard_md_score_formatting():
    """Markdown formatter formats waste percentage."""
    reports = [_mock_report("https://test.com", waste=33.3, score=66.7)]
    md = format_leaderboard_md(reports)
    assert "33%" in md


def test_format_leaderboard_json_waste_rounding():
    """JSON formatter preserves context_waste_pct value."""
    reports = [_mock_report("https://test.com", waste=33.333)]
    raw = format_leaderboard_json(reports)
    data = json.loads(raw)
    assert data["leaderboard"][0]["context_waste_pct"] == 33.333
