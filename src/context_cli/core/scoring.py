"""Scoring logic for readiness lint pillars."""

from __future__ import annotations

from context_cli.core.models import (
    ContentReport,
    LintCheck,
    LintResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)

# ── Scoring Constants ────────────────────────────────────────────────────────
# Exported so verbose output can display the actual thresholds used.

CONTENT_WORD_TIERS: list[tuple[int, int]] = [
    (1500, 25),
    (800, 20),
    (400, 15),
    (150, 8),
]
"""(min_words, base_score) — evaluated top-down, first match wins."""

CONTENT_HEADING_BONUS: int = 7
CONTENT_LIST_BONUS: int = 5
CONTENT_CODE_BONUS: int = 3
CONTENT_MAX: int = 40

SCHEMA_BASE_SCORE: int = 8
HIGH_VALUE_TYPES: set[str] = {"FAQPage", "HowTo", "Article", "Product", "Recipe"}
SCHEMA_HIGH_VALUE_BONUS: int = 5
SCHEMA_STANDARD_BONUS: int = 3
SCHEMA_MAX: int = 25

ROBOTS_MAX: int = 25
LLMS_TXT_MAX: int = 10


def compute_scores(
    robots: RobotsReport,
    llms_txt: LlmsTxtReport,
    schema_org: SchemaReport,
    content: ContentReport,
) -> tuple[RobotsReport, LlmsTxtReport, SchemaReport, ContentReport, float]:
    """Compute scores for each pillar and overall Readiness Score.

    Scoring weights (revised 2026-02-18):
        Content (max 40): most impactful — what LLMs actually extract and cite
        Schema  (max 25): structured signals help LLMs understand page entities
        Robots  (max 25): gatekeeper — blocked bots can't crawl at all
        llms.txt (max 10): forward-looking signal, minimal real impact today

    Rationale: When AI search engines (ChatGPT, Perplexity, Claude) look up
    products or answer questions, they crawl pages and extract text content.
    Content quality dominates what gets cited. Schema.org gives structured
    "cheat sheets" (Product, Article, FAQ). Robots.txt is pass/fail per bot.
    llms.txt is emerging but not yet weighted by any major AI search engine.
    """
    # Robots: max ROBOTS_MAX — proportional to bots allowed
    if robots.found and robots.bots:
        allowed = sum(1 for b in robots.bots if b.allowed)
        robots.score = round(ROBOTS_MAX * allowed / len(robots.bots), 1)
    else:
        robots.score = 0

    # llms.txt: max LLMS_TXT_MAX — either llms.txt or llms-full.txt qualifies
    llms_txt.score = (
        LLMS_TXT_MAX if (llms_txt.found or llms_txt.llms_full_found) else 0
    )

    # Schema: max SCHEMA_MAX — reward high-value types more
    if schema_org.blocks_found > 0:
        unique_types = {s.schema_type for s in schema_org.schemas}
        high = sum(1 for t in unique_types if t in HIGH_VALUE_TYPES)
        std = len(unique_types) - high
        schema_org.score = min(
            SCHEMA_MAX,
            SCHEMA_BASE_SCORE + SCHEMA_HIGH_VALUE_BONUS * high + SCHEMA_STANDARD_BONUS * std,
        )
    else:
        schema_org.score = 0

    # Content: max CONTENT_MAX — word count tiers + structure bonuses
    score = 0
    for min_words, tier_score in CONTENT_WORD_TIERS:
        if content.word_count >= min_words:
            score = tier_score
            break
    if content.has_headings:
        score += CONTENT_HEADING_BONUS
    if content.has_lists:
        score += CONTENT_LIST_BONUS
    if content.has_code_blocks:
        score += CONTENT_CODE_BONUS
    content.score = min(CONTENT_MAX, score)

    overall = robots.score + llms_txt.score + schema_org.score + content.score
    return robots, llms_txt, schema_org, content, overall


def compute_lint_results(
    robots: RobotsReport,
    llms_txt: LlmsTxtReport,
    schema_org: SchemaReport,
    content: ContentReport,
) -> LintResult:
    """Compute pass/fail checks and token waste metrics."""
    checks: list[LintCheck] = []

    # AI Primitives check
    ai_prim_pass = llms_txt.found or llms_txt.llms_full_found
    checks.append(LintCheck(
        name="AI Primitives",
        passed=ai_prim_pass,
        detail="llms.txt found" if ai_prim_pass else "No llms.txt found",
    ))

    # Bot Access check
    bot_pass = True
    bot_detail = "No robots.txt found"
    if robots.found and robots.bots:
        blocked = [b.bot for b in robots.bots if not b.allowed]
        bot_pass = len(blocked) == 0
        total = len(robots.bots)
        allowed = total - len(blocked)
        bot_detail = f"{allowed}/{total} AI bots allowed"
        if blocked:
            bot_detail += f" ({', '.join(blocked[:3])} blocked)"
    checks.append(LintCheck(name="Bot Access", passed=bot_pass, detail=bot_detail))

    # Data Structuring check
    schema_pass = schema_org.blocks_found > 0
    schema_detail = f"{schema_org.blocks_found} JSON-LD blocks"
    if schema_org.schemas:
        types_found = [s.schema_type for s in schema_org.schemas]
        schema_detail += f" ({', '.join(types_found[:3])})"
    checks.append(LintCheck(name="Data Structuring", passed=schema_pass, detail=schema_detail))

    # Token Efficiency check
    waste = content.context_waste_pct
    eff_pass = waste < 70
    eff_detail = f"{waste:.0f}% Context Waste"
    if content.estimated_raw_tokens > 0:
        eff_detail += (
            f" ({content.estimated_raw_tokens:,} raw"
            f" -> {content.estimated_clean_tokens:,} clean tokens)"
        )
    checks.append(LintCheck(name="Token Efficiency", passed=eff_pass, detail=eff_detail))

    return LintResult(
        checks=checks,
        context_waste_pct=waste,
        raw_tokens=content.estimated_raw_tokens,
        clean_tokens=content.estimated_clean_tokens,
        passed=all(c.passed for c in checks),
    )
