"""Tests for per-pillar CI/CD threshold checking."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from context_cli.core.ci.thresholds import check_thresholds
from context_cli.core.models import (
    AuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    PillarThresholds,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
    ThresholdFailure,
    ThresholdResult,
)
from context_cli.main import app

runner = CliRunner()


# -- Fixtures -----------------------------------------------------------------


def _make_report(
    robots_score: float = 20.0,
    llms_score: float = 8.0,
    schema_score: float = 18.0,
    content_score: float = 30.0,
    overall: float = 76.0,
) -> AuditReport:
    """Build a mock AuditReport with configurable per-pillar scores."""
    return AuditReport(
        url="https://example.com",
        overall_score=overall,
        robots=RobotsReport(found=True, score=robots_score, detail="test"),
        llms_txt=LlmsTxtReport(found=True, score=llms_score, detail="test"),
        schema_org=SchemaReport(blocks_found=1, score=schema_score, detail="test"),
        content=ContentReport(word_count=500, score=content_score, detail="test"),
    )


def _make_site_report(
    robots_score: float = 20.0,
    llms_score: float = 8.0,
    schema_score: float = 18.0,
    content_score: float = 30.0,
    overall: float = 76.0,
) -> SiteAuditReport:
    """Build a mock SiteAuditReport with configurable per-pillar scores."""
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=overall,
        robots=RobotsReport(found=True, score=robots_score, detail="test"),
        llms_txt=LlmsTxtReport(found=True, score=llms_score, detail="test"),
        schema_org=SchemaReport(blocks_found=1, score=schema_score, detail="test"),
        content=ContentReport(word_count=500, score=content_score, detail="test"),
        discovery=DiscoveryResult(method="sitemap", urls_found=5, detail="test"),
        pages_audited=2,
    )


# -- PillarThresholds model tests ---------------------------------------------


def test_pillar_thresholds_all_none_by_default():
    """All thresholds are None when not specified."""
    pt = PillarThresholds()
    assert pt.robots_min is None
    assert pt.schema_min is None
    assert pt.content_min is None
    assert pt.llms_min is None
    assert pt.overall_min is None


def test_pillar_thresholds_partial_set():
    """Can set some thresholds while leaving others as None."""
    pt = PillarThresholds(robots_min=20.0, content_min=30.0)
    assert pt.robots_min == 20.0
    assert pt.content_min == 30.0
    assert pt.schema_min is None
    assert pt.llms_min is None
    assert pt.overall_min is None


def test_pillar_thresholds_all_set():
    """Can set all thresholds at once."""
    pt = PillarThresholds(
        robots_min=15.0,
        schema_min=10.0,
        content_min=25.0,
        llms_min=5.0,
        overall_min=60.0,
    )
    assert pt.robots_min == 15.0
    assert pt.schema_min == 10.0
    assert pt.content_min == 25.0
    assert pt.llms_min == 5.0
    assert pt.overall_min == 60.0


# -- ThresholdResult / ThresholdFailure model tests ----------------------------


def test_threshold_result_passed():
    """ThresholdResult with passed=True and empty failures."""
    tr = ThresholdResult(passed=True, failures=[])
    assert tr.passed is True
    assert tr.failures == []


def test_threshold_failure_fields():
    """ThresholdFailure stores pillar name, actual, and minimum."""
    tf = ThresholdFailure(pillar="robots", actual=10.0, minimum=20.0)
    assert tf.pillar == "robots"
    assert tf.actual == 10.0
    assert tf.minimum == 20.0


# -- check_thresholds core logic tests ----------------------------------------


def test_check_thresholds_all_pass():
    """All pillars above their thresholds returns passed=True."""
    report = _make_report(robots_score=20.0, llms_score=8.0, schema_score=18.0, content_score=30.0)
    thresholds = PillarThresholds(
        robots_min=15.0,
        llms_min=5.0,
        schema_min=10.0,
        content_min=25.0,
        overall_min=50.0,
    )
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_single_pillar_failure():
    """One pillar below threshold returns passed=False with one failure."""
    report = _make_report(robots_score=10.0)
    thresholds = PillarThresholds(robots_min=15.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "robots"
    assert result.failures[0].actual == 10.0
    assert result.failures[0].minimum == 15.0


def test_check_thresholds_multiple_failures():
    """Multiple pillars below threshold returns all failures."""
    report = _make_report(robots_score=5.0, content_score=10.0, overall=40.0)
    thresholds = PillarThresholds(
        robots_min=15.0,
        content_min=25.0,
        overall_min=60.0,
    )
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 3
    pillar_names = {f.pillar for f in result.failures}
    assert pillar_names == {"robots", "content", "overall"}


def test_check_thresholds_no_thresholds_set():
    """No thresholds set should always pass."""
    report = _make_report(robots_score=0.0, content_score=0.0, overall=0.0)
    thresholds = PillarThresholds()
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_overall_min_only():
    """Only overall_min set, passes when score is above."""
    report = _make_report(overall=75.0)
    thresholds = PillarThresholds(overall_min=70.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_overall_min_fails():
    """Only overall_min set, fails when score is below."""
    report = _make_report(overall=50.0)
    thresholds = PillarThresholds(overall_min=70.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "overall"
    assert result.failures[0].actual == 50.0
    assert result.failures[0].minimum == 70.0


def test_check_thresholds_zero_threshold():
    """Zero threshold always passes (any score >= 0)."""
    report = _make_report(robots_score=0.0)
    thresholds = PillarThresholds(robots_min=0.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_100_threshold():
    """100 threshold only passes when score is exactly 100."""
    report = _make_report(robots_score=25.0)
    thresholds = PillarThresholds(robots_min=100.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert result.failures[0].actual == 25.0
    assert result.failures[0].minimum == 100.0


def test_check_thresholds_exactly_equal():
    """Score exactly at threshold should pass (>= comparison)."""
    report = _make_report(robots_score=15.0)
    thresholds = PillarThresholds(robots_min=15.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_llms_pillar():
    """llms_min threshold works correctly."""
    report = _make_report(llms_score=3.0)
    thresholds = PillarThresholds(llms_min=5.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "llms_txt"


def test_check_thresholds_schema_pillar():
    """schema_min threshold works correctly."""
    report = _make_report(schema_score=5.0)
    thresholds = PillarThresholds(schema_min=10.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "schema_org"


def test_check_thresholds_content_pillar():
    """content_min threshold works correctly."""
    report = _make_report(content_score=15.0)
    thresholds = PillarThresholds(content_min=20.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "content"


def test_check_thresholds_with_site_report():
    """check_thresholds works with SiteAuditReport."""
    report = _make_site_report(robots_score=10.0, overall=50.0)
    thresholds = PillarThresholds(robots_min=15.0, overall_min=60.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 2
    pillar_names = {f.pillar for f in result.failures}
    assert pillar_names == {"robots", "overall"}


def test_check_thresholds_site_report_all_pass():
    """SiteAuditReport with all pillars above thresholds passes."""
    report = _make_site_report(
        robots_score=20.0, llms_score=8.0, schema_score=18.0,
        content_score=30.0, overall=76.0,
    )
    thresholds = PillarThresholds(
        robots_min=15.0, llms_min=5.0, schema_min=10.0,
        content_min=25.0, overall_min=70.0,
    )
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


# -- CLI integration tests -----------------------------------------------------


async def _fake_audit_url(url: str, **kwargs) -> AuditReport:
    return _make_report(robots_score=10.0, content_score=15.0, overall=51.0)


async def _fake_audit_url_passing(url: str, **kwargs) -> AuditReport:
    return _make_report(robots_score=20.0, content_score=30.0, overall=76.0)


async def _fake_audit_site(url: str, *, max_pages: int = 10, **kwargs) -> SiteAuditReport:
    return _make_site_report(robots_score=10.0, content_score=15.0, overall=51.0)


def test_cli_robots_min_fails():
    """--robots-min triggers exit 1 when robots score is below threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--robots-min", "15"],
        )
    assert result.exit_code == 1
    assert "robots" in result.output.lower()


def test_cli_content_min_fails():
    """--content-min triggers exit 1 when content score is below threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--content-min", "25"],
        )
    assert result.exit_code == 1
    assert "content" in result.output.lower()


def test_cli_schema_min_fails():
    """--schema-min triggers exit 1 when schema score is below threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--schema-min", "25"],
        )
    assert result.exit_code == 1
    assert "schema" in result.output.lower()


def test_cli_llms_min_fails():
    """--llms-min triggers exit 1 when llms score is below threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--llms-min", "10"],
        )
    assert result.exit_code == 1
    assert "llms" in result.output.lower()


def test_cli_overall_min_fails():
    """--overall-min triggers exit 1 when overall score is below threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--overall-min", "70"],
        )
    assert result.exit_code == 1
    assert "overall" in result.output.lower()


def test_cli_thresholds_all_pass():
    """When all pillar scores meet thresholds, exit code is 0."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_passing):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--robots-min", "15",
                "--content-min", "25",
                "--schema-min", "10",
                "--llms-min", "5",
                "--overall-min", "70",
            ],
        )
    assert result.exit_code == 0


def test_cli_multiple_threshold_failures():
    """Multiple threshold failures are all reported."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--robots-min", "15",
                "--content-min", "25",
            ],
        )
    assert result.exit_code == 1
    output_lower = result.output.lower()
    assert "robots" in output_lower
    assert "content" in output_lower


def test_cli_thresholds_with_site_audit():
    """Per-pillar thresholds work with multi-page site audits."""
    with patch("context_cli.cli.audit.audit_site", side_effect=_fake_audit_site):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com",
                "--robots-min", "15",
                "--overall-min", "70",
            ],
        )
    assert result.exit_code == 1


def test_cli_no_thresholds_no_exit():
    """Without any threshold flags, audit exits cleanly."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_passing):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single"],
        )
    assert result.exit_code == 0


def test_cli_thresholds_with_json_output():
    """Threshold failures still print after JSON output."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url):
        result = runner.invoke(
            app,
            [
                "lint", "https://example.com", "--single",
                "--json", "--robots-min", "15",
            ],
        )
    assert result.exit_code == 1
    # JSON output should still be present
    assert '"url"' in result.output


# -- New threshold fields: max_context_waste, require_llms_txt, require_bot_access


def test_pillar_thresholds_new_fields_defaults():
    """New PillarThresholds fields should have proper defaults."""
    pt = PillarThresholds()
    assert pt.max_context_waste is None
    assert pt.require_llms_txt is False
    assert pt.require_bot_access is False


def test_check_thresholds_max_context_waste_exceeds():
    """max_context_waste fires when waste exceeds the threshold."""
    from context_cli.core.models import LintCheck, LintResult
    report = _make_report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=80.0,
        raw_tokens=1000,
        clean_tokens=200,
    )
    thresholds = PillarThresholds(max_context_waste=50.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "context_waste"
    assert result.failures[0].actual == 80.0
    assert result.failures[0].minimum == 50.0


def test_check_thresholds_max_context_waste_passes():
    """max_context_waste passes when waste is below the threshold."""
    from context_cli.core.models import LintCheck, LintResult
    report = _make_report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=30.0,
        raw_tokens=1000,
        clean_tokens=700,
    )
    thresholds = PillarThresholds(max_context_waste=50.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_max_context_waste_equal_passes():
    """max_context_waste passes when waste is exactly at the threshold."""
    from context_cli.core.models import LintCheck, LintResult
    report = _make_report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=50.0,
        raw_tokens=1000,
        clean_tokens=500,
    )
    thresholds = PillarThresholds(max_context_waste=50.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_max_context_waste_no_lint_result():
    """max_context_waste is skipped when lint_result is None."""
    report = _make_report()
    assert report.lint_result is None
    thresholds = PillarThresholds(max_context_waste=50.0)
    result = check_thresholds(report, thresholds)
    assert result.passed is True
    assert result.failures == []


def test_check_thresholds_require_llms_txt_fails():
    """require_llms_txt fires when llms.txt is not found."""
    report = _make_report()
    report.llms_txt = LlmsTxtReport(found=False, score=0, detail="Not found")
    thresholds = PillarThresholds(require_llms_txt=True)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "llms_txt_required"


def test_check_thresholds_require_llms_txt_passes():
    """require_llms_txt passes when llms.txt is found."""
    report = _make_report()
    thresholds = PillarThresholds(require_llms_txt=True)
    result = check_thresholds(report, thresholds)
    assert result.passed is True


def test_check_thresholds_require_bot_access_fails():
    """require_bot_access fires when any AI bot is blocked."""
    from context_cli.core.models import BotAccessResult
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked"),
    ]
    report = _make_report()
    report.robots = RobotsReport(found=True, bots=bots, score=15, detail="5/7")
    thresholds = PillarThresholds(require_bot_access=True)
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].pillar == "bot_access_required"


def test_check_thresholds_require_bot_access_passes():
    """require_bot_access passes when all bots are allowed."""
    from context_cli.core.models import BotAccessResult
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=True, detail="Allowed"),
    ]
    report = _make_report()
    report.robots = RobotsReport(found=True, bots=bots, score=25, detail="7/7")
    thresholds = PillarThresholds(require_bot_access=True)
    result = check_thresholds(report, thresholds)
    assert result.passed is True


def test_check_thresholds_require_bot_access_robots_not_found():
    """require_bot_access is skipped when robots.txt is not found."""
    report = _make_report()
    report.robots = RobotsReport(found=False, score=0, detail="not found")
    thresholds = PillarThresholds(require_bot_access=True)
    result = check_thresholds(report, thresholds)
    assert result.passed is True


def test_check_thresholds_combined_new_fields():
    """Multiple new threshold fields can fire together."""
    from context_cli.core.models import BotAccessResult, LintCheck, LintResult
    bots = [BotAccessResult(bot="GPTBot", allowed=False, detail="Blocked")]
    report = _make_report()
    report.robots = RobotsReport(found=True, bots=bots, score=0, detail="blocked")
    report.llms_txt = LlmsTxtReport(found=False, score=0, detail="Not found")
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=False, detail="fail")],
        context_waste_pct=90.0,
        raw_tokens=1000,
        clean_tokens=100,
        passed=False,
    )
    thresholds = PillarThresholds(
        max_context_waste=50.0,
        require_llms_txt=True,
        require_bot_access=True,
    )
    result = check_thresholds(report, thresholds)
    assert result.passed is False
    assert len(result.failures) == 3
    pillar_names = {f.pillar for f in result.failures}
    assert pillar_names == {"context_waste", "llms_txt_required", "bot_access_required"}


# -- CLI integration tests for new threshold options ----------------------------


def _make_report_with_lint(waste_pct: float = 80.0) -> AuditReport:
    """Build a report with lint_result for waste threshold testing."""
    from context_cli.core.models import LintCheck, LintResult
    report = _make_report()
    report.lint_result = LintResult(
        checks=[LintCheck(name="Test", passed=True, detail="ok")],
        context_waste_pct=waste_pct,
        raw_tokens=1000,
        clean_tokens=int(1000 * (1 - waste_pct / 100)),
    )
    return report


async def _fake_audit_url_with_lint(url: str, **kwargs) -> AuditReport:
    return _make_report_with_lint(waste_pct=80.0)


async def _fake_audit_url_low_waste(url: str, **kwargs) -> AuditReport:
    return _make_report_with_lint(waste_pct=20.0)


async def _fake_audit_url_llms_missing(url: str, **kwargs) -> AuditReport:
    report = _make_report()
    report.llms_txt = LlmsTxtReport(found=False, score=0, detail="Not found")
    return report


async def _fake_audit_url_bots_blocked(url: str, **kwargs) -> AuditReport:
    from context_cli.core.models import BotAccessResult
    bots = [BotAccessResult(bot="GPTBot", allowed=False, detail="Blocked")]
    report = _make_report()
    report.robots = RobotsReport(found=True, bots=bots, score=0, detail="blocked")
    return report


def test_cli_max_context_waste_fails():
    """--max-context-waste triggers exit 1 when waste exceeds threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_with_lint):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--max-context-waste", "50"],
        )
    assert result.exit_code == 1
    assert "context_waste" in result.output.lower()


def test_cli_max_context_waste_passes():
    """--max-context-waste passes when waste is below threshold."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_low_waste):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--max-context-waste", "50"],
        )
    assert result.exit_code == 0


def test_cli_require_llms_txt_fails():
    """--require-llms-txt triggers exit 1 when llms.txt is not found."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_llms_missing):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--require-llms-txt"],
        )
    assert result.exit_code == 1
    assert "llms_txt_required" in result.output.lower()


def test_cli_require_llms_txt_passes():
    """--require-llms-txt passes when llms.txt is found."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_passing):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--require-llms-txt"],
        )
    assert result.exit_code == 0


def test_cli_require_bot_access_fails():
    """--require-bot-access triggers exit 1 when bots are blocked."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_bots_blocked):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--require-bot-access"],
        )
    assert result.exit_code == 1
    assert "bot_access_required" in result.output.lower()


def test_cli_require_bot_access_passes():
    """--require-bot-access passes when all bots are allowed."""
    with patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit_url_passing):
        result = runner.invoke(
            app,
            ["lint", "https://example.com", "--single", "--require-bot-access"],
        )
    assert result.exit_code == 0
