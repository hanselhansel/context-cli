"""Tests for CI baseline comparison — save, load, compare, CLI integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from context_cli.core.ci.baseline import (
    compare_baseline,
    load_baseline,
    save_baseline,
)
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


def _report(
    overall: float = 65.0,
    robots: float = 20.0,
    llms: float = 8.0,
    schema: float = 17.0,
    content: float = 20.0,
) -> AuditReport:
    """Build a mock AuditReport with configurable scores."""
    return AuditReport(
        url=_URL,
        overall_score=overall,
        robots=RobotsReport(found=True, score=robots, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=llms, detail="ok"),
        schema_org=SchemaReport(score=schema, detail="ok"),
        content=ContentReport(score=content, detail="ok"),
    )


# ── BaselineScores model tests ──────────────────────────────────────────────


def test_baseline_scores_creation():
    """BaselineScores can be created with valid data."""
    from context_cli.core.models import BaselineScores

    bs = BaselineScores(
        url=_URL,
        overall=65.0,
        robots=20.0,
        schema_org=17.0,
        content=20.0,
        llms_txt=8.0,
        timestamp="2025-01-01T00:00:00",
    )
    assert bs.url == _URL
    assert bs.overall == 65.0
    assert bs.robots == 20.0
    assert bs.schema_org == 17.0
    assert bs.content == 20.0
    assert bs.llms_txt == 8.0
    assert bs.timestamp == "2025-01-01T00:00:00"


def test_baseline_scores_serializable():
    """BaselineScores should be JSON serializable via model_dump."""
    from context_cli.core.models import BaselineScores

    bs = BaselineScores(
        url=_URL,
        overall=65.0,
        robots=20.0,
        schema_org=17.0,
        content=20.0,
        llms_txt=8.0,
        timestamp="2025-01-01T00:00:00",
    )
    data = bs.model_dump()
    assert data["url"] == _URL
    assert data["overall"] == 65.0


# ── BaselineRegression model tests ──────────────────────────────────────────


def test_baseline_regression_model():
    """BaselineRegression captures pillar-level regression details."""
    from context_cli.core.models import BaselineRegression

    reg = BaselineRegression(
        pillar="robots",
        previous_score=25.0,
        current_score=18.0,
        delta=-7.0,
    )
    assert reg.pillar == "robots"
    assert reg.previous_score == 25.0
    assert reg.current_score == 18.0
    assert reg.delta == -7.0


# ── BaselineComparison model tests ──────────────────────────────────────────


def test_baseline_comparison_model():
    """BaselineComparison holds comparison result and pass/fail status."""
    from context_cli.core.models import BaselineComparison, BaselineRegression, BaselineScores

    prev = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    curr = BaselineScores(
        url=_URL, overall=55.0, robots=15.0, schema_org=17.0,
        content=15.0, llms_txt=8.0, timestamp="2025-01-02T00:00:00",
    )
    comp = BaselineComparison(
        url=_URL,
        previous=prev,
        current=curr,
        regressions=[
            BaselineRegression(
                pillar="robots", previous_score=20.0, current_score=15.0, delta=-5.0,
            ),
        ],
        passed=False,
    )
    assert comp.url == _URL
    assert not comp.passed
    assert len(comp.regressions) == 1


# ── save_baseline tests ─────────────────────────────────────────────────────


def test_save_baseline_writes_json(tmp_path: Path):
    """save_baseline writes a valid JSON file."""
    path = tmp_path / "baseline.json"
    report = _report()
    save_baseline(report, path)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["url"] == _URL
    assert data["overall"] == 65.0
    assert data["robots"] == 20.0
    assert data["schema_org"] == 17.0
    assert data["content"] == 20.0
    assert data["llms_txt"] == 8.0
    assert "timestamp" in data


def test_save_baseline_creates_parent_dirs(tmp_path: Path):
    """save_baseline creates parent directories if they don't exist."""
    path = tmp_path / "deep" / "nested" / "baseline.json"
    report = _report()
    save_baseline(report, path)
    assert path.exists()


def test_save_baseline_overwrites_existing(tmp_path: Path):
    """save_baseline overwrites an existing baseline file."""
    path = tmp_path / "baseline.json"
    save_baseline(_report(overall=50.0), path)
    save_baseline(_report(overall=75.0), path)
    data = json.loads(path.read_text())
    assert data["overall"] == 75.0


# ── load_baseline tests ─────────────────────────────────────────────────────


def test_load_baseline_reads_correctly(tmp_path: Path):
    """load_baseline reads back what save_baseline wrote."""
    path = tmp_path / "baseline.json"
    report = _report()
    save_baseline(report, path)
    baseline = load_baseline(path)
    assert baseline.url == _URL
    assert baseline.overall == 65.0
    assert baseline.robots == 20.0
    assert baseline.schema_org == 17.0
    assert baseline.content == 20.0
    assert baseline.llms_txt == 8.0


def test_load_baseline_missing_file_raises(tmp_path: Path):
    """load_baseline raises FileNotFoundError if the file doesn't exist."""
    path = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        load_baseline(path)


def test_load_baseline_roundtrip(tmp_path: Path):
    """Save then load preserves all values."""
    path = tmp_path / "baseline.json"
    report = _report(overall=80.0, robots=25.0, llms=10.0, schema=25.0, content=20.0)
    save_baseline(report, path)
    baseline = load_baseline(path)
    assert baseline.overall == 80.0
    assert baseline.robots == 25.0
    assert baseline.llms_txt == 10.0
    assert baseline.schema_org == 25.0
    assert baseline.content == 20.0


# ── compare_baseline tests ──────────────────────────────────────────────────


def test_compare_no_regressions():
    """No regressions when current scores are equal or better."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    report = _report(overall=70.0, robots=22.0, llms=8.0, schema=20.0, content=20.0)
    result = compare_baseline(report, baseline)
    assert result.passed
    assert len(result.regressions) == 0


def test_compare_regression_exceeds_threshold():
    """Regression detected when a pillar drops more than the threshold."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=25.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    # robots drops from 25 -> 15 = -10, exceeds default threshold of 5
    report = _report(overall=55.0, robots=15.0, llms=8.0, schema=17.0, content=15.0)
    result = compare_baseline(report, baseline)
    assert not result.passed
    pillar_names = [r.pillar for r in result.regressions]
    assert "robots" in pillar_names


def test_compare_regression_below_threshold_passes():
    """Small drops within the threshold should still pass."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    # robots drops from 20 -> 17 = -3, below default threshold of 5
    report = _report(overall=62.0, robots=17.0, llms=8.0, schema=17.0, content=20.0)
    result = compare_baseline(report, baseline)
    assert result.passed
    assert len(result.regressions) == 0


def test_compare_multiple_regressions():
    """Multiple pillars regressing should all be reported."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=80.0, robots=25.0, schema_org=25.0,
        content=20.0, llms_txt=10.0, timestamp="2025-01-01T00:00:00",
    )
    # robots: 25 -> 15 = -10, schema: 25 -> 12 = -13
    report = _report(overall=55.0, robots=15.0, llms=10.0, schema=12.0, content=18.0)
    result = compare_baseline(report, baseline)
    assert not result.passed
    assert len(result.regressions) >= 2
    pillar_names = {r.pillar for r in result.regressions}
    assert "robots" in pillar_names
    assert "schema_org" in pillar_names


def test_compare_custom_threshold():
    """Custom threshold should be respected."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    # robots drops from 20 -> 17 = -3; with threshold=2 this IS a regression
    report = _report(overall=62.0, robots=17.0, llms=8.0, schema=17.0, content=20.0)
    result = compare_baseline(report, baseline, threshold=2.0)
    assert not result.passed
    # Both overall (65 -> 62 = -3) and robots (20 -> 17 = -3) exceed threshold=2
    assert len(result.regressions) == 2
    pillar_names = {r.pillar for r in result.regressions}
    assert "overall" in pillar_names
    assert "robots" in pillar_names
    robots_reg = next(r for r in result.regressions if r.pillar == "robots")
    assert robots_reg.delta == -3.0


def test_compare_equal_scores():
    """Equal scores should pass with no regressions."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    report = _report(overall=65.0, robots=20.0, llms=8.0, schema=17.0, content=20.0)
    result = compare_baseline(report, baseline)
    assert result.passed
    assert len(result.regressions) == 0


def test_compare_improvement():
    """Score improvement should pass with no regressions."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=50.0, robots=15.0, schema_org=10.0,
        content=15.0, llms_txt=5.0, timestamp="2025-01-01T00:00:00",
    )
    report = _report(overall=80.0, robots=25.0, llms=10.0, schema=25.0, content=20.0)
    result = compare_baseline(report, baseline)
    assert result.passed
    assert len(result.regressions) == 0


def test_compare_zero_scores():
    """Both baseline and current with zero scores should pass."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=0.0, robots=0.0, schema_org=0.0,
        content=0.0, llms_txt=0.0, timestamp="2025-01-01T00:00:00",
    )
    report = _report(overall=0.0, robots=0.0, llms=0.0, schema=0.0, content=0.0)
    result = compare_baseline(report, baseline)
    assert result.passed
    assert len(result.regressions) == 0


def test_compare_overall_regression_check():
    """Overall score regression should also be flagged."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=80.0, robots=25.0, schema_org=25.0,
        content=20.0, llms_txt=10.0, timestamp="2025-01-01T00:00:00",
    )
    # overall drops 80 -> 65 = -15, a regression in overall
    report = _report(overall=65.0, robots=20.0, llms=8.0, schema=20.0, content=17.0)
    result = compare_baseline(report, baseline)
    assert not result.passed
    pillar_names = [r.pillar for r in result.regressions]
    assert "overall" in pillar_names


def test_compare_delta_values():
    """Verify delta values are calculated correctly."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    report = _report(overall=55.0, robots=10.0, llms=8.0, schema=17.0, content=20.0)
    result = compare_baseline(report, baseline)
    assert not result.passed
    robots_reg = next(r for r in result.regressions if r.pillar == "robots")
    assert robots_reg.previous_score == 20.0
    assert robots_reg.current_score == 10.0
    assert robots_reg.delta == -10.0


def test_compare_regression_at_exact_threshold_not_flagged():
    """A drop of exactly the threshold should NOT be flagged (must exceed)."""
    from context_cli.core.models import BaselineScores

    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, timestamp="2025-01-01T00:00:00",
    )
    # robots drops exactly 5 (threshold=5) -> should NOT be a regression
    report = _report(overall=60.0, robots=15.0, llms=8.0, schema=17.0, content=20.0)
    result = compare_baseline(report, baseline, threshold=5.0)
    # Regression needs delta < -threshold (strictly less)
    robots_regs = [r for r in result.regressions if r.pillar == "robots"]
    assert len(robots_regs) == 0


# ── CLI integration: --save-baseline ─────────────────────────────────────────


async def _fake_audit_url(url: str, **kwargs) -> AuditReport:
    return _report()


def test_cli_save_baseline_writes_file(tmp_path: Path):
    """--save-baseline writes a baseline JSON file."""
    baseline_path = tmp_path / "baseline.json"
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(baseline_path),
            ],
        )
    assert result.exit_code == 0
    assert baseline_path.exists()
    data = json.loads(baseline_path.read_text())
    assert data["url"] == _URL
    assert data["overall"] == 65.0


def test_cli_save_baseline_with_nested_dir(tmp_path: Path):
    """--save-baseline creates parent directories if needed."""
    baseline_path = tmp_path / "ci" / "baseline.json"
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(baseline_path),
            ],
        )
    assert result.exit_code == 0
    assert baseline_path.exists()


# ── CLI integration: --baseline comparison ───────────────────────────────────


def test_cli_baseline_no_regression(tmp_path: Path):
    """--baseline with no regression exits 0."""
    baseline_path = tmp_path / "baseline.json"
    # Save baseline first
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(baseline_path),
            ],
        )
    # Compare against same scores — no regression
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--baseline", str(baseline_path),
            ],
        )
    assert result.exit_code == 0


async def _fake_audit_url_regressed(url: str, **kwargs) -> AuditReport:
    """Return a report with significantly lower scores (regression)."""
    return _report(overall=40.0, robots=10.0, llms=3.0, schema=10.0, content=17.0)


def test_cli_baseline_with_regression_exits_1(tmp_path: Path):
    """--baseline with regression exits 1."""
    baseline_path = tmp_path / "baseline.json"
    # Save baseline with high scores
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(baseline_path),
            ],
        )
    # Compare with lower scores — regression
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_regressed):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--baseline", str(baseline_path),
            ],
        )
    assert result.exit_code == 1
    assert "regression" in result.output.lower() or "Regression" in result.output


def test_cli_baseline_missing_file_exits_1():
    """--baseline with a nonexistent file exits 1 with an error message."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--baseline", "/tmp/nonexistent_baseline_xxx.json",
            ],
        )
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_cli_baseline_custom_threshold(tmp_path: Path):
    """--regression-threshold with custom value is respected in baseline comparison."""
    baseline_path = tmp_path / "baseline.json"
    # Save baseline
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(baseline_path),
            ],
        )

    # Create a slightly regressed report (robots: 20 -> 17 = -3 drop)
    async def _fake_slight_regression(url: str, **kwargs) -> AuditReport:
        return _report(overall=62.0, robots=17.0, llms=8.0, schema=17.0, content=20.0)

    # With threshold=2, the -3 drop IS a regression
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_slight_regression):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--baseline", str(baseline_path),
                "--regression-threshold", "2",
            ],
        )
    assert result.exit_code == 1


def test_cli_save_and_compare_together(tmp_path: Path):
    """--save-baseline and --baseline can be used together."""
    old_baseline = tmp_path / "old.json"
    new_baseline = tmp_path / "new.json"
    # Save old baseline
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(old_baseline),
            ],
        )
    # Compare against old and save new at the same time
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--baseline", str(old_baseline),
                "--save-baseline", str(new_baseline),
            ],
        )
    assert result.exit_code == 0
    assert new_baseline.exists()


def test_cli_baseline_prints_comparison(tmp_path: Path):
    """--baseline prints comparison output when there are no regressions."""
    baseline_path = tmp_path / "baseline.json"
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(baseline_path),
            ],
        )
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--baseline", str(baseline_path),
            ],
        )
    assert result.exit_code == 0
    # Should have some baseline comparison output
    output_lower = result.output.lower()
    assert "baseline" in output_lower or "pass" in output_lower


def test_cli_save_baseline_error_handling(tmp_path: Path):
    """--save-baseline gracefully handles write errors."""
    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url),
        patch(
            "context_cli.core.ci.baseline.save_baseline",
            side_effect=PermissionError("Access denied"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--save-baseline", str(tmp_path / "baseline.json"),
            ],
        )
    # Should still exit 0 (save error is non-fatal)
    assert result.exit_code == 0
    assert "error" in result.output.lower()


# ── context_waste_pct in baseline ────────────────────────────────────────────


def test_save_baseline_includes_context_waste_pct(tmp_path: Path):
    """save_baseline should include context_waste_pct from lint_result."""
    from context_cli.core.models import LintCheck, LintResult
    path = tmp_path / "baseline.json"
    report = _report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=45.0,
        raw_tokens=1000,
        clean_tokens=550,
    )
    save_baseline(report, path)
    data = json.loads(path.read_text())
    assert data["context_waste_pct"] == 45.0


def test_save_baseline_zero_waste_without_lint(tmp_path: Path):
    """save_baseline should set context_waste_pct=0 when lint_result is None."""
    path = tmp_path / "baseline.json"
    report = _report()
    assert report.lint_result is None
    save_baseline(report, path)
    data = json.loads(path.read_text())
    assert data["context_waste_pct"] == 0.0


def test_load_baseline_with_context_waste_pct(tmp_path: Path):
    """load_baseline should read back context_waste_pct."""
    from context_cli.core.models import LintCheck, LintResult
    path = tmp_path / "baseline.json"
    report = _report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=60.0,
        raw_tokens=1000,
        clean_tokens=400,
    )
    save_baseline(report, path)
    baseline = load_baseline(path)
    assert baseline.context_waste_pct == 60.0


def test_load_baseline_defaults_context_waste_pct(tmp_path: Path):
    """load_baseline should default context_waste_pct=0 for old baselines."""
    path = tmp_path / "baseline.json"
    # Simulate an old baseline without context_waste_pct
    old_data = {
        "url": _URL,
        "overall": 65.0,
        "robots": 20.0,
        "schema_org": 17.0,
        "content": 20.0,
        "llms_txt": 8.0,
        "timestamp": "2025-01-01T00:00:00",
    }
    path.write_text(json.dumps(old_data))
    baseline = load_baseline(path)
    assert baseline.context_waste_pct == 0.0


def test_compare_baseline_waste_regression(tmp_path: Path):
    """compare_baseline should detect waste regression (increase in waste)."""
    from context_cli.core.models import BaselineScores, LintCheck, LintResult
    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, context_waste_pct=30.0,
        timestamp="2025-01-01T00:00:00",
    )
    report = _report()
    # Waste increased from 30% to 50% = +20, exceeds default threshold (5)
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=50.0,
        raw_tokens=1000,
        clean_tokens=500,
    )
    result = compare_baseline(report, baseline)
    assert not result.passed
    waste_regs = [r for r in result.regressions if r.pillar == "context_waste"]
    assert len(waste_regs) == 1
    assert waste_regs[0].delta == 20.0
    assert waste_regs[0].previous_score == 30.0
    assert waste_regs[0].current_score == 50.0


def test_compare_baseline_waste_no_regression():
    """compare_baseline should pass when waste stays the same."""
    from context_cli.core.models import BaselineScores, LintCheck, LintResult
    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, context_waste_pct=30.0,
        timestamp="2025-01-01T00:00:00",
    )
    report = _report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=30.0,
        raw_tokens=1000,
        clean_tokens=700,
    )
    result = compare_baseline(report, baseline)
    assert result.passed
    waste_regs = [r for r in result.regressions if r.pillar == "context_waste"]
    assert len(waste_regs) == 0


def test_compare_baseline_waste_improvement():
    """compare_baseline should pass when waste decreases."""
    from context_cli.core.models import BaselineScores, LintCheck, LintResult
    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, context_waste_pct=80.0,
        timestamp="2025-01-01T00:00:00",
    )
    report = _report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=40.0,
        raw_tokens=1000,
        clean_tokens=600,
    )
    result = compare_baseline(report, baseline)
    assert result.passed
    waste_regs = [r for r in result.regressions if r.pillar == "context_waste"]
    assert len(waste_regs) == 0


def test_compare_baseline_waste_within_threshold():
    """compare_baseline should pass when waste increase is within threshold."""
    from context_cli.core.models import BaselineScores, LintCheck, LintResult
    baseline = BaselineScores(
        url=_URL, overall=65.0, robots=20.0, schema_org=17.0,
        content=20.0, llms_txt=8.0, context_waste_pct=30.0,
        timestamp="2025-01-01T00:00:00",
    )
    report = _report()
    # Waste increased by 4 (30 -> 34), within default threshold (5)
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=34.0,
        raw_tokens=1000,
        clean_tokens=660,
    )
    result = compare_baseline(report, baseline)
    assert result.passed
    waste_regs = [r for r in result.regressions if r.pillar == "context_waste"]
    assert len(waste_regs) == 0
