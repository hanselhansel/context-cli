"""Compare two readiness lints side-by-side."""

from __future__ import annotations

import asyncio

from context_cli.core.auditor import audit_url
from context_cli.core.models import AuditReport, CompareReport, PillarDelta
from context_cli.core.scoring import CONTENT_MAX, LLMS_TXT_MAX, ROBOTS_MAX, SCHEMA_MAX


def build_compare_report(
    url_a: str,
    url_b: str,
    report_a: AuditReport,
    report_b: AuditReport,
) -> CompareReport:
    """Build a CompareReport from two completed audit reports."""
    pillars = [
        PillarDelta(
            pillar="robots",
            score_a=report_a.robots.score,
            score_b=report_b.robots.score,
            delta=round(report_a.robots.score - report_b.robots.score, 1),
            max_score=ROBOTS_MAX,
        ),
        PillarDelta(
            pillar="llms_txt",
            score_a=report_a.llms_txt.score,
            score_b=report_b.llms_txt.score,
            delta=round(report_a.llms_txt.score - report_b.llms_txt.score, 1),
            max_score=LLMS_TXT_MAX,
        ),
        PillarDelta(
            pillar="schema_org",
            score_a=report_a.schema_org.score,
            score_b=report_b.schema_org.score,
            delta=round(report_a.schema_org.score - report_b.schema_org.score, 1),
            max_score=SCHEMA_MAX,
        ),
        PillarDelta(
            pillar="content",
            score_a=report_a.content.score,
            score_b=report_b.content.score,
            delta=round(report_a.content.score - report_b.content.score, 1),
            max_score=CONTENT_MAX,
        ),
    ]
    return CompareReport(
        url_a=url_a,
        url_b=url_b,
        score_a=report_a.overall_score,
        score_b=report_b.overall_score,
        delta=round(report_a.overall_score - report_b.overall_score, 1),
        pillars=pillars,
        report_a=report_a,
        report_b=report_b,
    )


async def compare_urls(
    url_a: str,
    url_b: str,
    *,
    timeout: int = 15,
    bots: list[str] | None = None,
) -> CompareReport:
    """Run audits on two URLs concurrently and return a comparison report."""
    report_a, report_b = await asyncio.gather(
        audit_url(url_a, timeout=timeout, bots=bots),
        audit_url(url_b, timeout=timeout, bots=bots),
    )
    return build_compare_report(url_a, url_b, report_a, report_b)
