"""Tests for batch audit: file parsing, batch orchestration, and CLI integration."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from context_cli.core.batch import parse_url_file, run_batch_audit
from context_cli.core.models import (
    AuditReport,
    BatchAuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
)
from context_cli.main import app

runner = CliRunner()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _report(url: str = "https://example.com", score: float = 55.0) -> AuditReport:
    return AuditReport(
        url=url,
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(word_count=500, score=17, detail="500 words"),
    )


def _site_report(url: str = "https://example.com", score: float = 68.0) -> SiteAuditReport:
    return SiteAuditReport(
        url=url,
        domain=url.replace("https://", ""),
        overall_score=score,
        robots=RobotsReport(found=True, score=25, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=13, detail="2 blocks"),
        content=ContentReport(word_count=700, score=20, detail="700 words"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="50 found"),
        pages_audited=2,
    )


# ── BatchAuditReport model ──────────────────────────────────────────────────


def test_batch_audit_report_model():
    """BatchAuditReport should hold urls, reports, and errors."""
    report = BatchAuditReport(
        urls=["https://a.com", "https://b.com"],
        reports=[_report("https://a.com")],
        errors={"https://b.com": "Connection refused"},
    )
    assert len(report.urls) == 2
    assert len(report.reports) == 1
    assert "https://b.com" in report.errors


def test_batch_audit_report_defaults():
    """BatchAuditReport should have sensible defaults."""
    report = BatchAuditReport(urls=[])
    assert report.reports == []
    assert report.errors == {}


# ── parse_url_file ───────────────────────────────────────────────────────────


def test_parse_url_file_txt(tmp_path):
    """Read URLs from a .txt file, one per line."""
    f = tmp_path / "urls.txt"
    f.write_text("https://a.com\nhttps://b.com\nhttps://c.com\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://a.com", "https://b.com", "https://c.com"]


def test_parse_url_file_skip_comments(tmp_path):
    """Lines starting with # should be skipped."""
    f = tmp_path / "urls.txt"
    f.write_text("# This is a comment\nhttps://a.com\n# Another comment\nhttps://b.com\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://a.com", "https://b.com"]


def test_parse_url_file_skip_empty_lines(tmp_path):
    """Empty lines and whitespace-only lines should be skipped."""
    f = tmp_path / "urls.txt"
    f.write_text("https://a.com\n\n   \nhttps://b.com\n\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://a.com", "https://b.com"]


def test_parse_url_file_csv(tmp_path):
    """For .csv files, use the first column as URL."""
    f = tmp_path / "urls.csv"
    f.write_text("url,name\nhttps://a.com,Site A\nhttps://b.com,Site B\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://a.com", "https://b.com"]


def test_parse_url_file_csv_comments(tmp_path):
    """CSV files should also skip # comment lines."""
    f = tmp_path / "urls.csv"
    f.write_text("# comment\nhttps://a.com,Site A\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://a.com"]


def test_parse_url_file_csv_empty_rows(tmp_path):
    """CSV files with empty rows should skip them gracefully."""
    f = tmp_path / "urls.csv"
    f.write_text("https://a.com,Site A\n\nhttps://b.com,Site B\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://a.com", "https://b.com"]


def test_parse_url_file_not_found():
    """Non-existent file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_url_file("/nonexistent/file.txt")


def test_parse_url_file_auto_https(tmp_path):
    """URLs without scheme should get https:// prepended."""
    f = tmp_path / "urls.txt"
    f.write_text("example.com\nhttps://already.com\n")
    urls = parse_url_file(str(f))
    assert urls == ["https://example.com", "https://already.com"]


# ── run_batch_audit ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_batch_audit_single_mode():
    """Batch audit in single mode calls audit_url for each URL."""
    async def _fake(url, **kwargs):
        return _report(url)

    with patch("context_cli.core.batch.audit_url", side_effect=_fake):
        result = await run_batch_audit(
            ["https://a.com", "https://b.com"], single=True
        )

    assert len(result.reports) == 2
    assert result.reports[0].url == "https://a.com"
    assert result.reports[1].url == "https://b.com"
    assert result.errors == {}


@pytest.mark.asyncio
async def test_run_batch_audit_site_mode():
    """Batch audit in site mode calls audit_site for each URL."""
    async def _fake(url, **kwargs):
        return _site_report(url)

    with patch("context_cli.core.batch.audit_site", side_effect=_fake):
        result = await run_batch_audit(
            ["https://a.com", "https://b.com"], single=False
        )

    assert len(result.reports) == 2
    assert result.errors == {}


@pytest.mark.asyncio
async def test_run_batch_audit_error_handling():
    """URLs that fail should be captured in errors, not crash the batch."""
    call_count = 0

    async def _fake(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "bad" in url:
            raise RuntimeError("Connection refused")
        return _report(url)

    with patch("context_cli.core.batch.audit_url", side_effect=_fake):
        result = await run_batch_audit(
            ["https://good.com", "https://bad.com"], single=True
        )

    assert len(result.reports) == 1
    assert result.reports[0].url == "https://good.com"
    assert "https://bad.com" in result.errors
    assert "Connection refused" in result.errors["https://bad.com"]


@pytest.mark.asyncio
async def test_run_batch_audit_concurrency():
    """Concurrency should limit parallel execution."""
    import asyncio

    active = 0
    max_active = 0

    async def _fake(url, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return _report(url)

    urls = [f"https://site{i}.com" for i in range(6)]
    with patch("context_cli.core.batch.audit_url", side_effect=_fake):
        result = await run_batch_audit(urls, single=True, concurrency=2)

    assert len(result.reports) == 6
    assert max_active <= 2


@pytest.mark.asyncio
async def test_run_batch_audit_passes_timeout():
    """Batch audit should pass timeout through to audit functions."""
    captured_kwargs: list[dict] = []

    async def _fake(url, **kwargs):
        captured_kwargs.append(kwargs)
        return _report(url)

    with patch("context_cli.core.batch.audit_url", side_effect=_fake):
        await run_batch_audit(["https://a.com"], single=True, timeout=45)

    assert captured_kwargs[0]["timeout"] == 45


@pytest.mark.asyncio
async def test_run_batch_audit_passes_max_pages():
    """Batch audit in site mode should pass max_pages through."""
    captured_kwargs: list[dict] = []

    async def _fake(url, **kwargs):
        captured_kwargs.append(kwargs)
        return _site_report(url)

    with patch("context_cli.core.batch.audit_site", side_effect=_fake):
        await run_batch_audit(["https://a.com"], single=False, max_pages=5)

    assert captured_kwargs[0]["max_pages"] == 5


@pytest.mark.asyncio
async def test_run_batch_audit_progress_callback():
    """Progress callback should be called for each URL."""
    msgs: list[str] = []

    async def _fake(url, **kwargs):
        return _report(url)

    with patch("context_cli.core.batch.audit_url", side_effect=_fake):
        await run_batch_audit(
            ["https://a.com", "https://b.com"],
            single=True,
            progress_callback=msgs.append,
        )

    assert len(msgs) >= 2


# ── CLI --file flag integration ──────────────────────────────────────────────


def test_cli_file_flag_json(tmp_path):
    """--file with --json should output BatchAuditReport JSON."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\nhttps://b.com\n")

    async def _fake(urls, **kwargs):
        return BatchAuditReport(
            urls=urls,
            reports=[_report("https://a.com"), _report("https://b.com")],
        )

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "--file", str(url_file), "--json"]
        )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "urls" in data
    assert len(data["reports"]) == 2


def test_cli_file_flag_rich(tmp_path):
    """--file should render a Rich summary table."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")

    async def _fake(urls, **kwargs):
        return BatchAuditReport(
            urls=urls,
            reports=[_report("https://a.com", score=55.0)],
        )

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(app, ["audit", "--file", str(url_file)])

    assert result.exit_code == 0
    assert "a.com" in result.output
    assert "55.0" in result.output


def test_cli_file_flag_with_errors(tmp_path):
    """Batch errors should be displayed in Rich output."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\nhttps://bad.com\n")

    async def _fake(urls, **kwargs):
        return BatchAuditReport(
            urls=urls,
            reports=[_report("https://a.com")],
            errors={"https://bad.com": "Connection refused"},
        )

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(app, ["audit", "--file", str(url_file)])

    assert result.exit_code == 0
    assert "bad.com" in result.output
    assert "Connection refused" in result.output


def test_cli_concurrency_flag(tmp_path):
    """--concurrency should be passed through to run_batch_audit."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")
    captured: list[dict] = []

    async def _fake(urls, **kwargs):
        captured.append(kwargs)
        return BatchAuditReport(urls=urls, reports=[_report("https://a.com")])

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "--file", str(url_file), "--concurrency", "5", "--json"]
        )

    assert result.exit_code == 0
    assert captured[0]["concurrency"] == 5


def test_cli_file_not_found(tmp_path):
    """--file with non-existent path should show error."""
    result = runner.invoke(
        app, ["audit", "--file", str(tmp_path / "nonexistent.txt")]
    )
    assert result.exit_code == 1


def test_cli_no_url_no_file():
    """Neither URL nor --file should show usage error."""
    result = runner.invoke(app, ["audit"])
    assert result.exit_code != 0


def test_cli_file_flag_csv_format(tmp_path):
    """--file with --format csv should output CSV."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")

    async def _fake(urls, **kwargs):
        return BatchAuditReport(urls=urls, reports=[_report("https://a.com")])

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "--file", str(url_file), "--format", "csv"]
        )

    assert result.exit_code == 0
    assert "url" in result.output
    assert "a.com" in result.output


def test_cli_file_flag_markdown_format(tmp_path):
    """--file with --format markdown should output markdown."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")

    async def _fake(urls, **kwargs):
        return BatchAuditReport(urls=urls, reports=[_report("https://a.com")])

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "--file", str(url_file), "--format", "markdown"]
        )

    assert result.exit_code == 0
    assert "AEO" in result.output or "a.com" in result.output


def test_cli_file_flag_passes_single(tmp_path):
    """--file --single should pass single=True to batch audit."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")
    captured: list[dict] = []

    async def _fake(urls, **kwargs):
        captured.append(kwargs)
        return BatchAuditReport(urls=urls, reports=[_report("https://a.com")])

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "--file", str(url_file), "--single", "--json"]
        )

    assert result.exit_code == 0
    assert captured[0]["single"] is True


def test_cli_file_flag_passes_timeout(tmp_path):
    """--file --timeout should pass timeout to batch audit."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://a.com\n")
    captured: list[dict] = []

    async def _fake(urls, **kwargs):
        captured.append(kwargs)
        return BatchAuditReport(urls=urls, reports=[_report("https://a.com")])

    with patch("context_cli.core.batch.run_batch_audit", side_effect=_fake):
        result = runner.invoke(
            app, ["audit", "--file", str(url_file), "--timeout", "30", "--json"]
        )

    assert result.exit_code == 0
    assert captured[0]["timeout"] == 30


def test_cli_file_empty_urls(tmp_path):
    """--file with a file containing only comments/blanks should warn and exit 0."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text("# just a comment\n\n   \n")

    result = runner.invoke(app, ["audit", "--file", str(url_file)])

    assert result.exit_code == 0
    assert "No URLs found" in result.output


def test_batch_markdown_with_errors():
    """format_batch_report_md should include error section when errors exist."""
    from context_cli.formatters.markdown import format_batch_report_md

    batch = BatchAuditReport(
        urls=["https://a.com", "https://bad.com"],
        reports=[_report("https://a.com")],
        errors={"https://bad.com": "Connection refused"},
    )
    md = format_batch_report_md(batch)
    assert "## Errors" in md
    assert "**https://bad.com**" in md
    assert "Connection refused" in md
