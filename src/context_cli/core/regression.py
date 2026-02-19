"""Regression detection — compare current audit against stored history."""

from __future__ import annotations

from pydantic import BaseModel, Field

from context_cli.core.models import AuditReport


class PillarRegression(BaseModel):
    """Score change for a single pillar."""

    pillar: str = Field(description="Pillar name")
    previous: float = Field(description="Previous score")
    current: float = Field(description="Current score")
    delta: float = Field(description="current - previous (negative = regression)")


class RegressionReport(BaseModel):
    """Result of comparing current audit against the previous baseline."""

    url: str = Field(description="The audited URL")
    previous_score: float = Field(description="Previous overall score")
    current_score: float = Field(description="Current overall score")
    delta: float = Field(description="current - previous (negative = regression)")
    has_regression: bool = Field(description="Whether score dropped beyond threshold")
    threshold: float = Field(description="Regression threshold used")
    pillars: list[PillarRegression] = Field(description="Per-pillar changes")


def detect_regression(
    current: AuditReport,
    previous: AuditReport,
    threshold: float = 5.0,
) -> RegressionReport:
    """Compare current audit against a previous one and detect regressions.

    Args:
        current: The most recent audit report.
        previous: The baseline audit report to compare against.
        threshold: Minimum score drop to flag as regression (default 5 points).

    Returns:
        RegressionReport with per-pillar deltas and regression flag.
    """
    delta = round(current.overall_score - previous.overall_score, 1)
    pillars = [
        PillarRegression(
            pillar="robots",
            previous=previous.robots.score,
            current=current.robots.score,
            delta=round(current.robots.score - previous.robots.score, 1),
        ),
        PillarRegression(
            pillar="llms_txt",
            previous=previous.llms_txt.score,
            current=current.llms_txt.score,
            delta=round(current.llms_txt.score - previous.llms_txt.score, 1),
        ),
        PillarRegression(
            pillar="schema_org",
            previous=previous.schema_org.score,
            current=current.schema_org.score,
            delta=round(current.schema_org.score - previous.schema_org.score, 1),
        ),
        PillarRegression(
            pillar="content",
            previous=previous.content.score,
            current=current.content.score,
            delta=round(current.content.score - previous.content.score, 1),
        ),
    ]
    return RegressionReport(
        url=current.url,
        previous_score=previous.overall_score,
        current_score=current.overall_score,
        delta=delta,
        has_regression=delta < -threshold,
        threshold=threshold,
        pillars=pillars,
    )
