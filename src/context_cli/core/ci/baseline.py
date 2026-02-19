"""Baseline comparison for CI/CD regression detection.

Save audit scores as a JSON baseline file and compare future audits against it.
Regressions exceeding the threshold are flagged, enabling CI pipelines to fail
on Readiness Score drops.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from context_cli.core.models import (
    AuditReport,
    BaselineComparison,
    BaselineRegression,
    BaselineScores,
)


def save_baseline(report: AuditReport, path: Path) -> None:
    """Save current audit scores as a JSON baseline file.

    Args:
        report: The audit report to extract scores from.
        path: File path to write the baseline JSON to.
    """
    scores = BaselineScores(
        url=report.url,
        overall=report.overall_score,
        robots=report.robots.score,
        schema_org=report.schema_org.score,
        content=report.content.score,
        llms_txt=report.llms_txt.score,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scores.model_dump(), indent=2))


def load_baseline(path: Path) -> BaselineScores:
    """Load a saved baseline from a JSON file.

    Args:
        path: File path to read the baseline JSON from.

    Returns:
        BaselineScores parsed from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Baseline file not found: {path}")
    data = json.loads(path.read_text())
    return BaselineScores(**data)


def compare_baseline(
    report: AuditReport,
    baseline: BaselineScores,
    threshold: float = 5.0,
) -> BaselineComparison:
    """Compare current audit scores against a saved baseline.

    Args:
        report: The current audit report.
        baseline: Previously saved baseline scores.
        threshold: Minimum score drop to flag as regression (must exceed, not equal).

    Returns:
        BaselineComparison with regressions and pass/fail status.
    """
    current = BaselineScores(
        url=report.url,
        overall=report.overall_score,
        robots=report.robots.score,
        schema_org=report.schema_org.score,
        content=report.content.score,
        llms_txt=report.llms_txt.score,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    pillars = [
        ("overall", baseline.overall, current.overall),
        ("robots", baseline.robots, current.robots),
        ("schema_org", baseline.schema_org, current.schema_org),
        ("content", baseline.content, current.content),
        ("llms_txt", baseline.llms_txt, current.llms_txt),
    ]

    regressions: list[BaselineRegression] = []
    for pillar_name, prev_score, curr_score in pillars:
        delta = round(curr_score - prev_score, 1)
        # Regression only if drop strictly exceeds the threshold
        if delta < -threshold:
            regressions.append(
                BaselineRegression(
                    pillar=pillar_name,
                    previous_score=prev_score,
                    current_score=curr_score,
                    delta=delta,
                )
            )

    return BaselineComparison(
        url=report.url,
        previous=baseline,
        current=current,
        regressions=regressions,
        passed=len(regressions) == 0,
    )
