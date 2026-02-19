"""Statistical aggregation for benchmark results — mention rates, positions, sentiment."""

from __future__ import annotations

from aeo_cli.core.models import (
    BenchmarkConfig,
    BenchmarkReport,
    ModelBenchmarkSummary,
    PromptBenchmarkResult,
)


def compute_model_summary(
    results: list[PromptBenchmarkResult],
    model: str,
    brand: str,
) -> ModelBenchmarkSummary:
    """Compute aggregated metrics for a single model from benchmark results.

    Filters results for the specified model. Skips results without judge_result.
    Calculates mention_rate, recommendation_rate, avg_position, and sentiment_breakdown.
    """
    model_results = [r for r in results if r.model == model and r.judge_result is not None]
    total = len(model_results)

    if total == 0:
        return ModelBenchmarkSummary(model=model)

    mentions = sum(
        1 for r in model_results if brand in r.judge_result.brands_mentioned  # type: ignore[union-attr]
    )
    recommendations = sum(
        1 for r in model_results if r.judge_result.recommended_brand == brand  # type: ignore[union-attr]
    )

    positions = [
        r.judge_result.target_brand_position  # type: ignore[union-attr]
        for r in model_results
        if r.judge_result.target_brand_position is not None  # type: ignore[union-attr]
    ]
    avg_pos = sum(positions) / len(positions) if positions else None

    sentiment: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    for r in model_results:
        s = r.judge_result.sentiment  # type: ignore[union-attr]
        if s in sentiment:
            sentiment[s] += 1

    return ModelBenchmarkSummary(
        model=model,
        total_responses=total,
        mention_rate=mentions / total,
        recommendation_rate=recommendations / total,
        avg_position=avg_pos,
        sentiment_breakdown=sentiment,
    )


def compute_report(
    config: BenchmarkConfig,
    results: list[PromptBenchmarkResult],
) -> BenchmarkReport:
    """Build a complete BenchmarkReport from config and per-prompt results.

    Computes per-model summaries and overall weighted averages.
    """
    summaries = [
        compute_model_summary(results, model=m, brand=config.brand) for m in config.models
    ]

    # Filter to only models with actual responses
    active_summaries = [s for s in summaries if s.total_responses > 0]
    total_judged = sum(s.total_responses for s in active_summaries)

    if total_judged > 0:
        overall_mention = sum(
            s.mention_rate * s.total_responses for s in active_summaries
        ) / total_judged
        overall_rec = sum(
            s.recommendation_rate * s.total_responses for s in active_summaries
        ) / total_judged
    else:
        overall_mention = 0.0
        overall_rec = 0.0

    return BenchmarkReport(
        brand=config.brand,
        competitors=config.competitors,
        model_summaries=summaries,
        overall_mention_rate=overall_mention,
        overall_recommendation_rate=overall_rec,
        total_prompts=len(config.prompts),
        total_responses=len(results),
        results=results,
    )
