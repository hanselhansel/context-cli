"""Benchmark models for Share-of-Recommendation tracking."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptEntry(BaseModel):
    """A single benchmark prompt with optional category and intent metadata."""

    prompt: str = Field(description="The benchmark prompt text to send to LLMs")
    category: str | None = Field(
        default=None,
        description="Optional category for grouping prompts (e.g., comparison, review)",
    )
    intent: str | None = Field(
        default=None,
        description="Optional search intent classification (e.g., informational, transactional)",
    )


class BenchmarkConfig(BaseModel):
    """Configuration for running a Share-of-Recommendation benchmark."""

    prompt_file: str | None = Field(
        default=None, description="Path to CSV or text file containing prompts"
    )
    prompts: list[PromptEntry] = Field(
        default_factory=list, description="List of benchmark prompts to evaluate"
    )
    brand: str = Field(description="Target brand name to track in LLM responses")
    competitors: list[str] = Field(
        default_factory=list, description="Competitor brand names to track alongside target"
    )
    models: list[str] = Field(
        default_factory=lambda: ["gpt-4o-mini"],
        description="LLM models to query for the benchmark",
    )
    runs_per_model: int = Field(
        default=3,
        description="Number of runs per model per prompt for statistical significance",
    )


class JudgeResult(BaseModel):
    """Result from the benchmark judge analyzing a single LLM response."""

    brands_mentioned: list[str] = Field(
        default_factory=list, description="Brand names mentioned in the response"
    )
    recommended_brand: str | None = Field(
        default=None, description="The primary brand recommended in the response (if any)"
    )
    target_brand_position: int | None = Field(
        default=None,
        description=(
            "Position of target brand in recommendation list"
            " (1-based, None if absent)"
        ),
    )
    sentiment: str = Field(
        default="neutral",
        description="Sentiment toward target brand: positive, neutral, or negative",
    )


class PromptBenchmarkResult(BaseModel):
    """Result of sending a single prompt to a single model in one run."""

    prompt: PromptEntry = Field(description="The prompt that was evaluated")
    model: str = Field(description="LLM model identifier used for this query")
    run_index: int = Field(description="Run index (0-based) for this model-prompt pair")
    response_text: str = Field(description="Raw text response from the LLM")
    judge_result: JudgeResult | None = Field(
        default=None, description="Judge analysis result (populated by judge agent)"
    )
    error: str | None = Field(
        default=None, description="Error message if the query failed"
    )


class ModelBenchmarkSummary(BaseModel):
    """Aggregated benchmark metrics for a single model."""

    model: str = Field(description="LLM model identifier")
    mention_rate: float = Field(
        description="Fraction of responses that mention the target brand (0.0-1.0)"
    )
    recommendation_rate: float = Field(
        description="Fraction of responses that recommend the target brand (0.0-1.0)"
    )
    avg_position: float | None = Field(
        default=None,
        description=(
            "Average position of target brand in recommendation lists"
            " (None if never listed)"
        ),
    )
    sentiment_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Count of responses by sentiment (positive, neutral, negative)",
    )


class BenchmarkReport(BaseModel):
    """Complete benchmark report with per-model results and aggregate metrics."""

    config: BenchmarkConfig = Field(description="Configuration used for this benchmark run")
    results: list[PromptBenchmarkResult] = Field(
        default_factory=list, description="All individual prompt-model-run results"
    )
    model_summaries: list[ModelBenchmarkSummary] = Field(
        default_factory=list, description="Aggregated per-model benchmark summaries"
    )
    overall_mention_rate: float = Field(
        default=0.0, description="Overall fraction of responses mentioning target brand"
    )
    overall_recommendation_rate: float = Field(
        default=0.0, description="Overall fraction of responses recommending target brand"
    )
    total_queries: int = Field(default=0, description="Total number of LLM queries executed")
    total_cost_estimate: float | None = Field(
        default=None, description="Estimated total cost in USD (None if unavailable)"
    )
