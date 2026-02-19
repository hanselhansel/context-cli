"""Tests for benchmark metrics module — statistical aggregation."""

from __future__ import annotations

from aeo_cli.core.benchmark.metrics import compute_model_summary, compute_report
from aeo_cli.core.models import (
    BenchmarkConfig,
    BenchmarkReport,
    JudgeResult,
    PromptBenchmarkResult,
    PromptEntry,
)

# ── Helpers ────────────────────────────────────────────────────────────────


def _pe(text: str) -> PromptEntry:
    """Shorthand to create a PromptEntry."""
    return PromptEntry(prompt=text)


def _make_result(
    prompt: str = "test",
    model: str = "gpt-4o-mini",
    brands: list[str] | None = None,
    recommended: str | None = None,
    position: int | None = None,
    sentiment: str = "neutral",
    error: str | None = None,
) -> PromptBenchmarkResult:
    """Build a PromptBenchmarkResult with JudgeResult."""
    judge = JudgeResult(
        brands_mentioned=brands or [],
        recommended_brand=recommended,
        target_brand_position=position,
        sentiment=sentiment,
    )
    return PromptBenchmarkResult(
        prompt=_pe(prompt),
        model=model,
        run_index=0,
        response_text=f"Response for {prompt}",
        judge_result=None if error else judge,
        error=error,
    )


# ── compute_model_summary tests ──────────────────────────────────────────


def test_compute_model_summary_basic() -> None:
    """compute_model_summary calculates rates correctly."""
    results = [
        _make_result(brands=["Acme"], recommended="Acme", position=1, sentiment="positive"),
        _make_result(
            brands=["Acme", "Rival"], recommended="Rival", position=2, sentiment="neutral",
        ),
        _make_result(brands=["Rival"], recommended="Rival", position=None, sentiment="negative"),
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="Acme")

    assert summary.model == "gpt-4o-mini"
    # Acme mentioned in 2 out of 3
    assert abs(summary.mention_rate - 2 / 3) < 1e-9
    # Acme recommended in 1 out of 3
    assert abs(summary.recommendation_rate - 1 / 3) < 1e-9
    # avg position: (1 + 2) / 2 = 1.5 (skip nulls)
    assert summary.avg_position is not None
    assert abs(summary.avg_position - 1.5) < 1e-9
    assert summary.sentiment_breakdown == {"positive": 1, "neutral": 1, "negative": 1}


def test_compute_model_summary_filters_by_model() -> None:
    """compute_model_summary only includes results for the specified model."""
    results = [
        _make_result(model="gpt-4o-mini", brands=["A"], recommended="A", sentiment="positive"),
        _make_result(model="gpt-4o", brands=["A"], recommended="A", sentiment="positive"),
        _make_result(model="gpt-4o-mini", brands=[], sentiment="neutral"),
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="A")

    # 2 judged results for gpt-4o-mini
    assert abs(summary.mention_rate - 0.5) < 1e-9


def test_compute_model_summary_no_mentions() -> None:
    """compute_model_summary handles zero mentions gracefully."""
    results = [
        _make_result(brands=[], recommended=None, sentiment="neutral"),
        _make_result(brands=["Rival"], recommended="Rival", sentiment="neutral"),
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="Acme")

    assert summary.mention_rate == 0.0
    assert summary.recommendation_rate == 0.0
    assert summary.avg_position is None
    assert summary.sentiment_breakdown == {"positive": 0, "neutral": 2, "negative": 0}


def test_compute_model_summary_all_mentioned() -> None:
    """compute_model_summary returns 1.0 when all responses mention brand."""
    results = [
        _make_result(brands=["X"], recommended="X", position=1, sentiment="positive"),
        _make_result(brands=["X", "Y"], recommended="X", position=1, sentiment="positive"),
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="X")

    assert summary.mention_rate == 1.0
    assert summary.recommendation_rate == 1.0
    assert summary.avg_position == 1.0


def test_compute_model_summary_empty_results() -> None:
    """compute_model_summary handles empty input gracefully."""
    summary = compute_model_summary([], model="gpt-4o-mini", brand="X")

    assert summary.mention_rate == 0.0
    assert summary.recommendation_rate == 0.0
    assert summary.avg_position is None
    assert summary.sentiment_breakdown == {"positive": 0, "neutral": 0, "negative": 0}


def test_compute_model_summary_skips_unjudged() -> None:
    """compute_model_summary skips results without judge_result."""
    results = [
        _make_result(brands=["A"], recommended="A", sentiment="positive"),
        _make_result(error="API failed"),  # no judge_result
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="A")

    # Only 1 judged result
    assert summary.mention_rate == 1.0


def test_compute_model_summary_no_positions() -> None:
    """avg_position is None when no results have position data."""
    results = [
        _make_result(brands=["A"], position=None, sentiment="positive"),
        _make_result(brands=["A"], position=None, sentiment="neutral"),
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="A")

    assert summary.avg_position is None


def test_compute_model_summary_mixed_positions() -> None:
    """avg_position correctly skips nulls and averages non-nulls."""
    results = [
        _make_result(position=1, sentiment="positive"),
        _make_result(position=None, sentiment="neutral"),
        _make_result(position=3, sentiment="negative"),
    ]

    summary = compute_model_summary(results, model="gpt-4o-mini", brand="test")

    assert summary.avg_position is not None
    assert abs(summary.avg_position - 2.0) < 1e-9


# ── compute_report tests ─────────────────────────────────────────────────


def test_compute_report_basic() -> None:
    """compute_report builds a complete BenchmarkReport."""
    config = BenchmarkConfig(
        brand="Acme",
        competitors=["Rival"],
        models=["gpt-4o-mini"],
        prompts=[_pe("test prompt")],
    )
    results = [
        _make_result(
            model="gpt-4o-mini",
            brands=["Acme"],
            recommended="Acme",
            sentiment="positive",
        ),
        _make_result(
            model="gpt-4o-mini",
            brands=["Rival"],
            recommended="Rival",
            sentiment="neutral",
        ),
    ]

    report = compute_report(config, results)

    assert isinstance(report, BenchmarkReport)
    assert report.config.brand == "Acme"
    assert report.config.competitors == ["Rival"]
    assert len(report.model_summaries) == 1
    assert report.model_summaries[0].model == "gpt-4o-mini"
    assert report.total_queries == 2
    assert abs(report.overall_mention_rate - 0.5) < 1e-9
    assert abs(report.overall_recommendation_rate - 0.5) < 1e-9
    assert report.results == results


def test_compute_report_multi_model() -> None:
    """compute_report handles multiple models correctly."""
    config = BenchmarkConfig(
        brand="X",
        competitors=[],
        models=["model-a", "model-b"],
        prompts=[_pe("p1"), _pe("p2")],
    )
    results = [
        # model-a: 2 responses, both mention X
        _make_result(model="model-a", brands=["X"], recommended="X", sentiment="positive"),
        _make_result(model="model-a", brands=["X"], recommended=None, sentiment="neutral"),
        # model-b: 2 responses, 1 mentions X
        _make_result(model="model-b", brands=["X"], recommended="X", sentiment="positive"),
        _make_result(model="model-b", brands=[], recommended=None, sentiment="neutral"),
    ]

    report = compute_report(config, results)

    assert len(report.model_summaries) == 2
    assert report.total_queries == 4

    # model-a: mention_rate=1.0, model-b: mention_rate=0.5
    # Weighted: (2*1.0 + 2*0.5) / 4 = 0.75
    assert abs(report.overall_mention_rate - 0.75) < 1e-9

    # model-a: rec_rate=0.5, model-b: rec_rate=0.5
    # Weighted: (2*0.5 + 2*0.5) / 4 = 0.5
    assert abs(report.overall_recommendation_rate - 0.5) < 1e-9


def test_compute_report_empty_results() -> None:
    """compute_report handles empty results gracefully."""
    config = BenchmarkConfig(
        brand="X",
        competitors=[],
        models=["gpt-4o-mini"],
        prompts=[],
    )

    report = compute_report(config, [])

    assert report.total_queries == 0
    assert report.overall_mention_rate == 0.0
    assert report.overall_recommendation_rate == 0.0
    # One summary per model in config, but with zero responses
    assert len(report.model_summaries) == 1
    assert report.model_summaries[0].model == "gpt-4o-mini"


def test_compute_report_with_unjudged_results() -> None:
    """compute_report includes unjudged results in total but skips in metrics."""
    config = BenchmarkConfig(
        brand="A",
        competitors=[],
        models=["gpt-4o-mini"],
        prompts=[_pe("p")],
    )
    results = [
        _make_result(brands=["A"], recommended="A", sentiment="positive"),
        _make_result(error="failed"),
    ]

    report = compute_report(config, results)

    # Total includes all results
    assert report.total_queries == 2


def test_compute_report_model_order() -> None:
    """compute_report preserves model order from config."""
    config = BenchmarkConfig(
        brand="X",
        competitors=[],
        models=["z-model", "a-model"],
        prompts=[_pe("p")],
    )
    results = [
        _make_result(model="z-model", brands=["X"], sentiment="positive"),
        _make_result(model="a-model", brands=["X"], sentiment="positive"),
    ]

    report = compute_report(config, results)

    assert report.model_summaries[0].model == "z-model"
    assert report.model_summaries[1].model == "a-model"


def test_compute_report_weighted_average_uneven_models() -> None:
    """Weighted average correctly handles models with different response counts."""
    config = BenchmarkConfig(
        brand="X",
        competitors=[],
        models=["model-a", "model-b"],
        prompts=[_pe("p")],
    )
    results = [
        # model-a: 3 responses, all mention X
        _make_result(model="model-a", brands=["X"], recommended="X", sentiment="positive"),
        _make_result(model="model-a", brands=["X"], recommended="X", sentiment="positive"),
        _make_result(model="model-a", brands=["X"], recommended="X", sentiment="positive"),
        # model-b: 1 response, no mention
        _make_result(model="model-b", brands=[], recommended=None, sentiment="neutral"),
    ]

    report = compute_report(config, results)

    # Weighted avg: (3*1.0 + 1*0.0) / 4 = 0.75
    assert abs(report.overall_mention_rate - 0.75) < 1e-9
    # Weighted avg: (3*1.0 + 1*0.0) / 4 = 0.75
    assert abs(report.overall_recommendation_rate - 0.75) < 1e-9


def test_compute_report_stores_all_results() -> None:
    """compute_report stores all individual results in report.results."""
    config = BenchmarkConfig(
        brand="X",
        competitors=[],
        models=["m"],
        prompts=[_pe("p")],
    )
    results = [
        _make_result(model="m", brands=["X"], sentiment="positive"),
        _make_result(model="m", error="fail"),
    ]

    report = compute_report(config, results)

    assert len(report.results) == 2
    assert report.results[0].judge_result is not None
    assert report.results[1].error == "fail"
