"""Recommendation engine — analyzes an AuditReport and produces actionable suggestions."""

from __future__ import annotations

from context_cli.core.models import AuditReport, Recommendation
from context_cli.core.scoring import (
    CONTENT_MAX,
    HIGH_VALUE_TYPES,
    LLMS_TXT_MAX,
    ROBOTS_MAX,
    SCHEMA_MAX,
)


def _priority_for_gap(gap: float, max_score: float) -> str:
    """Return priority based on how large the gap is relative to the pillar max."""
    ratio = gap / max_score if max_score > 0 else 0
    if ratio >= 0.5:
        return "high"
    if ratio >= 0.25:
        return "medium"
    return "low"


def _robots_recommendations(report: AuditReport) -> list[Recommendation]:
    """Generate recommendations for the robots pillar."""
    recs: list[Recommendation] = []
    robots = report.robots
    gap = ROBOTS_MAX - robots.score

    if gap <= 0:
        return recs

    if not robots.found:
        recs.append(Recommendation(
            pillar="robots",
            action="Create a robots.txt file",
            estimated_impact=round(gap, 1),
            priority=_priority_for_gap(gap, ROBOTS_MAX),
            detail=(
                "No robots.txt was found. Create one that allows AI bots "
                "(GPTBot, ClaudeBot, PerplexityBot, etc.) to crawl your site."
            ),
        ))
        return recs

    # Found but some bots blocked
    blocked = [b for b in robots.bots if not b.allowed]
    if blocked:
        bot_names = ", ".join(b.bot for b in blocked)
        per_bot_impact = round(gap / len(blocked), 1) if blocked else 0
        recs.append(Recommendation(
            pillar="robots",
            action=f"Unblock {len(blocked)} AI bot(s) in robots.txt",
            estimated_impact=round(gap, 1),
            priority=_priority_for_gap(gap, ROBOTS_MAX),
            detail=(
                f"The following AI bots are blocked: {bot_names}. "
                f"Each bot unblocked adds ~{per_bot_impact} points to the Robots score."
            ),
        ))

    return recs


def _llms_txt_recommendations(report: AuditReport) -> list[Recommendation]:
    """Generate recommendations for the llms.txt pillar."""
    recs: list[Recommendation] = []
    llms = report.llms_txt

    if not llms.found and not llms.llms_full_found:
        recs.append(Recommendation(
            pillar="llms_txt",
            action="Create an llms.txt file",
            estimated_impact=float(LLMS_TXT_MAX),
            priority=_priority_for_gap(LLMS_TXT_MAX, LLMS_TXT_MAX),
            detail=(
                "No llms.txt was found. Create one at /llms.txt to help "
                "AI models understand your site's structure and content."
            ),
        ))
    elif llms.found and not llms.llms_full_found:
        recs.append(Recommendation(
            pillar="llms_txt",
            action="Add an llms-full.txt file",
            estimated_impact=0.0,
            priority="low",
            detail=(
                "You have llms.txt but no llms-full.txt. Adding a detailed "
                "llms-full.txt gives AI models richer context about your content."
            ),
        ))

    return recs


def _schema_recommendations(report: AuditReport) -> list[Recommendation]:
    """Generate recommendations for the schema pillar."""
    recs: list[Recommendation] = []
    schema = report.schema_org
    gap = SCHEMA_MAX - schema.score

    if gap <= 0:
        return recs

    existing_types = {s.schema_type for s in schema.schemas}
    missing_high_value = HIGH_VALUE_TYPES - existing_types

    if schema.blocks_found == 0:
        suggested = ", ".join(sorted(missing_high_value)[:3])
        recs.append(Recommendation(
            pillar="schema",
            action="Add Schema.org JSON-LD structured data",
            estimated_impact=round(gap, 1),
            priority=_priority_for_gap(gap, SCHEMA_MAX),
            detail=(
                f"No JSON-LD blocks found. Add high-value types like {suggested} "
                "to help AI engines understand your page structure."
            ),
        ))
    elif missing_high_value:
        suggested = ", ".join(sorted(missing_high_value)[:3])
        impact = min(gap, 5.0 * len(missing_high_value))
        recs.append(Recommendation(
            pillar="schema",
            action="Add high-value Schema.org types",
            estimated_impact=round(impact, 1),
            priority=_priority_for_gap(gap, SCHEMA_MAX),
            detail=(
                f"Consider adding these high-value types: {suggested}. "
                "High-value types (FAQPage, HowTo, Article, Product, Recipe) "
                "receive a larger scoring bonus."
            ),
        ))

    return recs


def _content_recommendations(report: AuditReport) -> list[Recommendation]:
    """Generate recommendations for the content pillar."""
    recs: list[Recommendation] = []
    content = report.content
    gap = CONTENT_MAX - content.score

    if gap <= 0:
        return recs

    # Low word count
    if content.word_count < 400:
        impact = min(gap, 15.0)
        recs.append(Recommendation(
            pillar="content",
            action="Add more content to the page",
            estimated_impact=round(impact, 1),
            priority=_priority_for_gap(gap, CONTENT_MAX),
            detail=(
                f"Page has only {content.word_count} words. "
                "Aim for at least 400-800 words of substantive content "
                "for better AI engine citation."
            ),
        ))

    # No headings
    if not content.has_headings:
        impact = min(gap, 7.0)
        recs.append(Recommendation(
            pillar="content",
            action="Add heading structure (H2/H3)",
            estimated_impact=round(impact, 1),
            priority=_priority_for_gap(impact, CONTENT_MAX),
            detail=(
                "No headings found. Add H2/H3 headings to structure your content "
                "into clear sections. This helps AI engines parse and cite specific sections."
            ),
        ))

    # No lists
    if not content.has_lists:
        impact = min(gap, 5.0)
        recs.append(Recommendation(
            pillar="content",
            action="Add structured lists (ul/ol)",
            estimated_impact=round(impact, 1),
            priority=_priority_for_gap(impact, CONTENT_MAX),
            detail=(
                "No lists found. Bullet or numbered lists make content more "
                "scannable and extractable by AI engines."
            ),
        ))

    # Poor readability (high grade level)
    if content.readability_grade is not None and content.readability_grade > 12.0:
        impact = min(gap, 3.0)
        recs.append(Recommendation(
            pillar="content",
            action="Simplify readability",
            estimated_impact=round(impact, 1),
            priority="medium",
            detail=(
                f"Readability grade is {content.readability_grade:.1f} "
                "(target: 8-12). Simplify sentences and use common vocabulary "
                "for better AI extraction."
            ),
        ))

    # Low answer-first ratio
    if content.answer_first_ratio < 0.3 and content.has_headings:
        impact = min(gap, 3.0)
        recs.append(Recommendation(
            pillar="content",
            action="Restructure for answer-first pattern",
            estimated_impact=round(impact, 1),
            priority="medium",
            detail=(
                f"Only {content.answer_first_ratio:.0%} of sections lead with a direct answer. "
                "Start each section with a concise answer before elaborating."
            ),
        ))

    return recs


def generate_recommendations(report: AuditReport) -> list[Recommendation]:
    """Analyze an AuditReport and produce actionable recommendations.

    Returns recommendations sorted by estimated_impact descending.
    """
    recs: list[Recommendation] = []
    recs.extend(_robots_recommendations(report))
    recs.extend(_llms_txt_recommendations(report))
    recs.extend(_schema_recommendations(report))
    recs.extend(_content_recommendations(report))
    recs.sort(key=lambda r: r.estimated_impact, reverse=True)
    return recs
