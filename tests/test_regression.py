"""Tests for regression detection."""

from __future__ import annotations

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)
from context_cli.core.regression import (
    PillarRegression,
    RegressionReport,
    detect_regression,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

_URL = "https://example.com"


def _report(overall: float, robots: float = 20.0, llms: float = 10.0,
            schema: float = 15.0, content: float = 20.0) -> AuditReport:
    return AuditReport(
        url=_URL,
        overall_score=overall,
        robots=RobotsReport(found=True, score=robots, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=llms, detail="ok"),
        schema_org=SchemaReport(score=schema, detail="ok"),
        content=ContentReport(score=content, detail="ok"),
    )


# ── detect_regression ────────────────────────────────────────────────────────


def test_no_regression_when_score_improves():
    previous = _report(60.0)
    current = _report(70.0)
    result = detect_regression(current, previous)
    assert not result.has_regression
    assert result.delta == 10.0


def test_no_regression_within_threshold():
    """A score drop of 3 points should not trigger regression (default threshold=5)."""
    previous = _report(60.0)
    current = _report(57.0)
    result = detect_regression(current, previous)
    assert not result.has_regression
    assert result.delta == -3.0


def test_regression_beyond_threshold():
    """A score drop of 10 points should trigger regression."""
    previous = _report(60.0)
    current = _report(50.0)
    result = detect_regression(current, previous)
    assert result.has_regression
    assert result.delta == -10.0


def test_regression_exactly_at_threshold():
    """A drop of exactly threshold should NOT trigger (must be beyond, not at)."""
    previous = _report(60.0)
    current = _report(55.0)
    result = detect_regression(current, previous, threshold=5.0)
    assert not result.has_regression


def test_regression_custom_threshold():
    """Custom threshold should be respected."""
    previous = _report(60.0)
    current = _report(57.0)
    result = detect_regression(current, previous, threshold=2.0)
    assert result.has_regression
    assert result.threshold == 2.0


def test_no_change():
    """Identical scores should not trigger regression."""
    previous = _report(60.0)
    current = _report(60.0)
    result = detect_regression(current, previous)
    assert not result.has_regression
    assert result.delta == 0.0


def test_pillar_count():
    result = detect_regression(_report(60.0), _report(60.0))
    assert len(result.pillars) == 4


def test_pillar_names():
    result = detect_regression(_report(60.0), _report(60.0))
    names = {p.pillar for p in result.pillars}
    assert names == {"robots", "llms_txt", "schema_org", "content"}


def test_pillar_deltas():
    previous = _report(65.0, robots=25.0, llms=10.0, schema=15.0, content=15.0)
    current = _report(55.0, robots=20.0, llms=0.0, schema=15.0, content=20.0)
    result = detect_regression(current, previous)

    robots = next(p for p in result.pillars if p.pillar == "robots")
    assert robots.previous == 25.0
    assert robots.current == 20.0
    assert robots.delta == -5.0

    llms = next(p for p in result.pillars if p.pillar == "llms_txt")
    assert llms.delta == -10.0

    schema = next(p for p in result.pillars if p.pillar == "schema_org")
    assert schema.delta == 0.0

    content = next(p for p in result.pillars if p.pillar == "content")
    assert content.delta == 5.0


def test_report_url():
    result = detect_regression(_report(60.0), _report(60.0))
    assert result.url == _URL


def test_report_scores():
    result = detect_regression(_report(70.0), _report(60.0))
    assert result.previous_score == 60.0
    assert result.current_score == 70.0


# ── Model fields ────────────────────────────────────────────────────────────


def test_pillar_regression_model():
    pr = PillarRegression(pillar="robots", previous=25.0, current=20.0, delta=-5.0)
    assert pr.pillar == "robots"
    assert pr.delta == -5.0


def test_regression_report_model():
    rr = RegressionReport(
        url=_URL,
        previous_score=60.0,
        current_score=50.0,
        delta=-10.0,
        has_regression=True,
        threshold=5.0,
        pillars=[],
    )
    assert rr.has_regression
    assert rr.threshold == 5.0


def test_regression_report_serializable():
    """RegressionReport should be serializable via model_dump."""
    result = detect_regression(_report(70.0), _report(60.0))
    data = result.model_dump()
    assert data["url"] == _URL
    assert len(data["pillars"]) == 4
