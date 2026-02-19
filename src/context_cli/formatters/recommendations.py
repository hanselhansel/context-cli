"""Recommendation engine for Context Lint reports.

Generates actionable suggestions based on pillar scores and renders
them as a Rich Panel for verbose CLI output.
"""

from __future__ import annotations

from rich.panel import Panel

from context_cli.core.models import (
    AuditReport,
    SiteAuditReport,
)
from context_cli.core.scoring import (
    CONTENT_HEADING_BONUS,
    CONTENT_LIST_BONUS,
    CONTENT_WORD_TIERS,
    LLMS_TXT_MAX,
    SCHEMA_HIGH_VALUE_BONUS,
    SCHEMA_MAX,
)


def generate_recommendations(report: AuditReport | SiteAuditReport) -> list[str]:
    """Generate actionable recommendations based on the audit report."""
    recs: list[str] = []

    # Robots recommendations
    if report.robots.found and report.robots.bots:
        blocked = [b.bot for b in report.robots.bots if not b.allowed]
        if blocked:
            bots_str = ", ".join(blocked)
            recs.append(f"Unblock {bots_str} in robots.txt")
    elif not report.robots.found:
        recs.append("Create a robots.txt file to explicitly allow AI bots")

    # llms.txt recommendations
    if not report.llms_txt.found:
        recs.append(f"Create /llms.txt to describe your site for AI agents (+{LLMS_TXT_MAX} pts)")

    # Schema recommendations
    if report.schema_org.blocks_found == 0:
        recs.append("Add JSON-LD structured data (Schema.org) to your pages")
    elif report.schema_org.score < SCHEMA_MAX:
        remaining = SCHEMA_MAX - report.schema_org.score
        if remaining > 0:
            more = -(-remaining // SCHEMA_HIGH_VALUE_BONUS)  # ceil division
            recs.append(
                f"Add {more} more high-value Schema.org type(s) to reach max score"
                f" (e.g., FAQPage, HowTo, Article, Product, Recipe)"
            )

    # Content recommendations
    if report.content.word_count == 0:
        recs.append("Add meaningful text content to your pages")
    else:
        # Find the next tier up (closest one above current word count)
        # Tiers are sorted descending, so iterate reversed to find lowest first
        current_tier = 0
        for mw, ts in CONTENT_WORD_TIERS:
            if report.content.word_count >= mw:
                current_tier = ts
                break
        next_tier = None
        for min_words, tier_score in reversed(CONTENT_WORD_TIERS):
            if report.content.word_count < min_words:
                next_tier = (min_words, tier_score)
                break
        if next_tier:
            min_words, tier_score = next_tier
            words_needed = min_words - report.content.word_count
            gain = tier_score - current_tier
            if gain > 0:
                recs.append(
                    f"Add {words_needed} more words to reach"
                    f" the {min_words}+ tier (+{gain} pts)"
                )
        # Structure bonuses
        if not report.content.has_headings:
            recs.append(
                f"Add headings (h1-h6) to structure your content (+{CONTENT_HEADING_BONUS} pts)"
            )
        if not report.content.has_lists:
            recs.append(
                f"Add bullet/numbered lists for scannability (+{CONTENT_LIST_BONUS} pts)"
            )

    return recs


def render_recommendations(report: AuditReport | SiteAuditReport) -> Panel | None:
    """Render recommendations panel. Returns None if no recommendations."""
    recs = generate_recommendations(report)
    if not recs:
        return None

    lines = ["[bold]How to improve your Readiness Score:[/bold]", ""]
    for i, rec in enumerate(recs, 1):
        lines.append(f"  {i}. {rec}")

    return Panel(
        "\n".join(lines),
        title="Recommendations",
        border_style="cyan",
    )
