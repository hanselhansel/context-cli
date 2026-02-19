"""Tests for benchmark cost estimation — src/aeo_cli/core/benchmark/cost.py."""

from __future__ import annotations

from aeo_cli.core.models import BenchmarkConfig


class TestModelCosts:
    """Tests for the MODEL_COSTS dictionary."""

    def test_model_costs_has_known_models(self) -> None:
        from aeo_cli.core.benchmark.cost import MODEL_COSTS

        expected_models = {
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4",
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        }
        assert expected_models.issubset(set(MODEL_COSTS.keys()))

    def test_model_costs_values_are_positive(self) -> None:
        from aeo_cli.core.benchmark.cost import MODEL_COSTS

        for model, cost in MODEL_COSTS.items():
            assert cost > 0, f"Cost for {model} should be positive"

    def test_gpt4o_mini_is_cheapest_openai(self) -> None:
        from aeo_cli.core.benchmark.cost import MODEL_COSTS

        assert MODEL_COSTS["gpt-4o-mini"] < MODEL_COSTS["gpt-4o"]

    def test_opus_is_most_expensive(self) -> None:
        from aeo_cli.core.benchmark.cost import MODEL_COSTS

        assert MODEL_COSTS["claude-3-opus-20240229"] > MODEL_COSTS["claude-3-sonnet-20240229"]


class TestEstimateBenchmarkCost:
    """Tests for estimate_benchmark_cost()."""

    def test_basic_cost_estimation(self) -> None:
        from aeo_cli.core.benchmark.cost import estimate_benchmark_cost

        config = BenchmarkConfig(
            prompts=["prompt1", "prompt2"],
            brand="TestBrand",
            models=["gpt-4o-mini"],
            runs_per_model=3,
        )
        cost = estimate_benchmark_cost(config)
        assert cost > 0
        assert isinstance(cost, float)

    def test_cost_scales_with_prompts(self) -> None:
        from aeo_cli.core.benchmark.cost import estimate_benchmark_cost

        config_small = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        config_large = BenchmarkConfig(
            prompts=["p1", "p2", "p3", "p4"],
            brand="B",
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        cost_small = estimate_benchmark_cost(config_small)
        cost_large = estimate_benchmark_cost(config_large)
        assert cost_large == cost_small * 4

    def test_cost_scales_with_models(self) -> None:
        from aeo_cli.core.benchmark.cost import estimate_benchmark_cost

        config_one = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        config_two = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o-mini", "gpt-4o-mini"],
            runs_per_model=1,
        )
        cost_one = estimate_benchmark_cost(config_one)
        cost_two = estimate_benchmark_cost(config_two)
        assert cost_two == cost_one * 2

    def test_cost_scales_with_runs(self) -> None:
        from aeo_cli.core.benchmark.cost import estimate_benchmark_cost

        config_1run = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o-mini"],
            runs_per_model=1,
        )
        config_5run = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o-mini"],
            runs_per_model=5,
        )
        cost_1 = estimate_benchmark_cost(config_1run)
        cost_5 = estimate_benchmark_cost(config_5run)
        assert cost_5 == cost_1 * 5

    def test_unknown_model_uses_default_cost(self) -> None:
        from aeo_cli.core.benchmark.cost import estimate_benchmark_cost

        config = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["some-unknown-model-xyz"],
            runs_per_model=1,
        )
        cost = estimate_benchmark_cost(config)
        assert cost > 0  # Default cost should be non-zero

    def test_includes_judge_cost(self) -> None:
        """Cost should include judge model (gpt-4o-mini) cost on top of query cost."""
        from aeo_cli.core.benchmark.cost import MODEL_COSTS, estimate_benchmark_cost

        config = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o"],
            runs_per_model=1,
        )
        cost = estimate_benchmark_cost(config)
        # Cost should be query_cost + judge_cost, not just query_cost
        gpt4o_cost = MODEL_COSTS["gpt-4o"]
        judge_cost = MODEL_COSTS["gpt-4o-mini"]
        expected = 1 * 1 * 1 * (gpt4o_cost + judge_cost)
        assert abs(cost - expected) < 1e-10

    def test_multiple_models_different_costs(self) -> None:
        from aeo_cli.core.benchmark.cost import MODEL_COSTS, estimate_benchmark_cost

        config = BenchmarkConfig(
            prompts=["p1"],
            brand="B",
            models=["gpt-4o", "gpt-4o-mini"],
            runs_per_model=1,
        )
        cost = estimate_benchmark_cost(config)
        judge_cost = MODEL_COSTS["gpt-4o-mini"]
        expected = (
            1 * (MODEL_COSTS["gpt-4o"] + judge_cost)
            + 1 * (MODEL_COSTS["gpt-4o-mini"] + judge_cost)
        )
        assert abs(cost - expected) < 1e-10

    def test_empty_prompts_zero_cost(self) -> None:
        from aeo_cli.core.benchmark.cost import estimate_benchmark_cost

        config = BenchmarkConfig(
            prompts=[],
            brand="B",
            models=["gpt-4o-mini"],
            runs_per_model=3,
        )
        cost = estimate_benchmark_cost(config)
        assert cost == 0.0

    def test_cost_formula_exact(self) -> None:
        """Verify exact formula: num_prompts * num_models * runs * (query + judge)."""
        from aeo_cli.core.benchmark.cost import MODEL_COSTS, estimate_benchmark_cost

        config = BenchmarkConfig(
            prompts=["p1", "p2", "p3"],
            brand="B",
            models=["gpt-4o", "claude-3-opus-20240229"],
            runs_per_model=2,
        )
        cost = estimate_benchmark_cost(config)
        judge_cost = MODEL_COSTS["gpt-4o-mini"]
        # Formula: num_prompts * runs * sum_over_models(model_cost + judge_cost)
        expected = 3 * 2 * (
            (MODEL_COSTS["gpt-4o"] + judge_cost)
            + (MODEL_COSTS["claude-3-opus-20240229"] + judge_cost)
        )
        assert abs(cost - expected) < 1e-10


class TestFormatCost:
    """Tests for format_cost()."""

    def test_format_zero(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        assert format_cost(0.0) == "$0.00"

    def test_format_small_amount(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        assert format_cost(0.005) == "$0.005"

    def test_format_normal_amount(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        assert format_cost(1.50) == "$1.50"

    def test_format_large_amount(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        assert format_cost(99.99) == "$99.99"

    def test_format_very_small(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        result = format_cost(0.001)
        assert result == "$0.001"

    def test_format_penny(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        assert format_cost(0.01) == "$0.01"

    def test_format_just_under_penny(self) -> None:
        from aeo_cli.core.benchmark.cost import format_cost

        result = format_cost(0.009)
        assert result == "$0.009"
