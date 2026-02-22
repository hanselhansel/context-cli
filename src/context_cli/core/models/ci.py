"""CI/CD threshold and baseline models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ThresholdFailure(BaseModel):
    """A single pillar that failed its minimum threshold check."""

    pillar: str = Field(
        description="Pillar name that failed (e.g., robots, content, overall)"
    )
    actual: float = Field(description="Actual pillar score from the audit")
    minimum: float = Field(description="Minimum threshold that was required")


class ThresholdResult(BaseModel):
    """Result of checking audit scores against per-pillar thresholds."""

    passed: bool = Field(description="True if all configured thresholds were met")
    failures: list[ThresholdFailure] = Field(
        default_factory=list, description="List of pillar threshold failures"
    )


class PillarThresholds(BaseModel):
    """Per-pillar minimum score thresholds for CI/CD gating."""

    robots_min: float | None = Field(
        default=None, description="Minimum robots.txt pillar score (0-25)"
    )
    schema_min: float | None = Field(
        default=None, description="Minimum schema.org pillar score (0-25)"
    )
    content_min: float | None = Field(
        default=None, description="Minimum content density pillar score (0-40)"
    )
    llms_min: float | None = Field(
        default=None, description="Minimum llms.txt pillar score (0-10)"
    )
    overall_min: float | None = Field(
        default=None, description="Minimum overall Readiness Score (0-100)"
    )
    max_context_waste: float | None = Field(
        default=None,
        description="Maximum context waste percentage (0-100, fail if exceeded)",
    )
    require_llms_txt: bool = Field(
        default=False, description="Fail if llms.txt is not present"
    )
    require_bot_access: bool = Field(
        default=False, description="Fail if any AI bot is blocked"
    )


class BaselineScores(BaseModel):
    """Saved baseline scores for CI regression comparison."""

    url: str = Field(description="The audited URL")
    overall: float = Field(description="Overall Readiness Score (0-100)")
    robots: float = Field(description="Robots pillar score (0-25)")
    schema_org: float = Field(description="Schema.org pillar score (0-25)")
    content: float = Field(description="Content pillar score (0-40)")
    llms_txt: float = Field(description="llms.txt pillar score (0-10)")
    context_waste_pct: float = Field(
        default=0.0, description="Context waste percentage from lint result"
    )
    timestamp: str = Field(description="ISO 8601 timestamp when baseline was saved")


class BaselineRegression(BaseModel):
    """A single pillar that regressed beyond the threshold."""

    pillar: str = Field(
        description="Pillar name (robots, llms_txt, schema_org, content, overall)"
    )
    previous_score: float = Field(description="Score from the saved baseline")
    current_score: float = Field(description="Score from the current audit")
    delta: float = Field(description="current - previous (negative = regression)")


class BaselineComparison(BaseModel):
    """Result of comparing current audit scores against a saved baseline."""

    url: str = Field(description="The audited URL")
    previous: BaselineScores = Field(description="Saved baseline scores")
    current: BaselineScores = Field(description="Current audit scores")
    regressions: list[BaselineRegression] = Field(
        default_factory=list, description="Pillars that regressed beyond threshold"
    )
    passed: bool = Field(description="Whether the comparison passed (no regressions)")
