"""Benchmark cost estimation — per-model pricing and total cost calculation."""

from __future__ import annotations

from context_cli.core.models import BenchmarkConfig

# Approximate per-query cost in USD for each model.
# These represent the combined input + output cost for a typical benchmark query.
MODEL_COSTS: dict[str, float] = {
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.0003,
    "gpt-4": 0.01,
    "claude-3-haiku-20240307": 0.0003,
    "claude-3-sonnet-20240229": 0.003,
    "claude-3-opus-20240229": 0.015,
}

# Default cost for unknown models.
_DEFAULT_COST = 0.001

# The judge model used to evaluate responses.
_JUDGE_MODEL = "gpt-4o-mini"


def estimate_benchmark_cost(config: BenchmarkConfig) -> float:
    """Estimate the total USD cost for a benchmark run.

    Formula: num_prompts * sum_over_models(runs_per_model * (query_cost + judge_cost))

    Where:
    - query_cost = MODEL_COSTS.get(model, _DEFAULT_COST)
    - judge_cost = MODEL_COSTS.get(_JUDGE_MODEL, _DEFAULT_COST)
    - Unknown models default to _DEFAULT_COST ($0.001)
    """
    num_prompts = len(config.prompts)
    if num_prompts == 0:
        return 0.0

    judge_cost = MODEL_COSTS.get(_JUDGE_MODEL, _DEFAULT_COST)
    total = 0.0
    for model in config.models:
        query_cost = MODEL_COSTS.get(model, _DEFAULT_COST)
        total += config.runs_per_model * (query_cost + judge_cost)

    return num_prompts * total


def format_cost(cost: float) -> str:
    """Format a cost as a dollar string (e.g., '$1.50', '$0.003').

    Returns '$0.00' for zero cost, 3 decimal places for sub-cent amounts,
    and 2 decimal places otherwise.
    """
    if cost == 0.0:
        return "$0.00"
    if cost < 0.01:
        return f"${cost:.3f}"
    return f"${cost:.2f}"
