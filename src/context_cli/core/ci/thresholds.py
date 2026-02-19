"""Per-pillar threshold checking for CI/CD integration."""

from __future__ import annotations

from context_cli.core.models import (
    AuditReport,
    PillarThresholds,
    SiteAuditReport,
    ThresholdFailure,
    ThresholdResult,
)


def check_thresholds(
    report: AuditReport | SiteAuditReport,
    thresholds: PillarThresholds,
) -> ThresholdResult:
    """Check audit report scores against per-pillar thresholds.

    Compares each pillar score in the report against the corresponding
    threshold in PillarThresholds. Returns ThresholdResult with passed=True
    only if every configured threshold is met (score >= threshold).

    Args:
        report: An AuditReport or SiteAuditReport with pillar scores.
        thresholds: Per-pillar minimum score thresholds (None = skip check).

    Returns:
        ThresholdResult indicating pass/fail with details of any failures.
    """
    failures: list[ThresholdFailure] = []

    # Map threshold fields to (pillar_name, actual_score)
    checks: list[tuple[str, float | None, float]] = [
        ("robots", thresholds.robots_min, report.robots.score),
        ("llms_txt", thresholds.llms_min, report.llms_txt.score),
        ("schema_org", thresholds.schema_min, report.schema_org.score),
        ("content", thresholds.content_min, report.content.score),
        ("overall", thresholds.overall_min, report.overall_score),
    ]

    for pillar, minimum, actual in checks:
        if minimum is not None and actual < minimum:
            failures.append(
                ThresholdFailure(pillar=pillar, actual=actual, minimum=minimum)
            )

    return ThresholdResult(passed=len(failures) == 0, failures=failures)
