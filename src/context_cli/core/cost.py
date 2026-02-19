"""Cost estimation for LLM API calls — model pricing and token cost formatting."""

from __future__ import annotations

# Per-token costs (USD) as of Feb 2026.
# Format: {model: (input_cost_per_1k, output_cost_per_1k)}
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3-opus-20240229": (0.015, 0.075),
    "claude-3-sonnet-20240229": (0.003, 0.015),
    "claude-3-haiku-20240307": (0.00025, 0.00125),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "ollama/llama3.2": (0.0, 0.0),
}


def estimate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    """Estimate USD cost for a given model and token count.

    Returns 0.0 for unknown models (local/self-hosted).
    """
    costs = MODEL_COSTS.get(model)
    if costs is None:
        return 0.0
    input_cost, output_cost = costs
    return (input_tokens / 1000) * input_cost + (output_tokens / 1000) * output_cost


def format_cost(cost: float) -> str:
    """Format a cost as a dollar string (e.g., '$1.50', '$0.003')."""
    if cost == 0.0:
        return "$0.00"
    if cost < 0.01:
        return f"${cost:.3f}"
    return f"${cost:.2f}"
