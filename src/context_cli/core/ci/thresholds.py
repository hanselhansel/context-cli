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

    # Context waste threshold: fail if waste EXCEEDS max_context_waste
    if thresholds.max_context_waste is not None and report.lint_result is not None:
        waste_pct = report.lint_result.context_waste_pct
        if waste_pct > thresholds.max_context_waste:
            failures.append(
                ThresholdFailure(
                    pillar="context_waste",
                    actual=waste_pct,
                    minimum=thresholds.max_context_waste,
                )
            )

    # Require llms.txt: fail if llms.txt is not found
    if thresholds.require_llms_txt and not report.llms_txt.found:
        failures.append(
            ThresholdFailure(pillar="llms_txt_required", actual=0, minimum=1)
        )

    # Require bot access: fail if any AI bot is blocked
    if thresholds.require_bot_access and report.robots.found:
        if any(not b.allowed for b in report.robots.bots):
            failures.append(
                ThresholdFailure(pillar="bot_access_required", actual=0, minimum=1)
            )

    return ThresholdResult(passed=len(failures) == 0, failures=failures)
