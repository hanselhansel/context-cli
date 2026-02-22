"""Compare command models for side-by-side audit comparison."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .audit import AuditReport


class PillarDelta(BaseModel):
    """Score difference for one pillar between two audits."""

    pillar: str = Field(description="Pillar name (robots, llms_txt, schema_org, content)")
    score_a: float = Field(description="Score for URL A")
    score_b: float = Field(description="Score for URL B")
    delta: float = Field(description="score_a - score_b (positive = A wins)")
    max_score: float = Field(description="Maximum possible score for this pillar")


class CompareReport(BaseModel):
    """Side-by-side comparison of two lint reports."""

    url_a: str = Field(description="First URL audited")
    url_b: str = Field(description="Second URL audited")
    score_a: float = Field(description="Overall score for URL A")
    score_b: float = Field(description="Overall score for URL B")
    delta: float = Field(description="score_a - score_b")
    pillars: list[PillarDelta] = Field(description="Per-pillar score comparisons")
    report_a: AuditReport = Field(description="Full audit report for URL A")
    report_b: AuditReport = Field(description="Full audit report for URL B")
