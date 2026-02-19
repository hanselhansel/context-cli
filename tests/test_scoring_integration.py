"""Integration tests for the full compute_scores pipeline."""

from __future__ import annotations

from context_cli.core.models import (
    BotAccessResult,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)
from context_cli.core.scoring import compute_scores

AI_BOT_NAMES = [
    "GPTBot", "ChatGPT-User", "Google-Extended",
    "ClaudeBot", "PerplexityBot", "Amazonbot", "OAI-SearchBot",
    "DeepSeek-AI", "Grok", "Meta-ExternalAgent",
    "cohere-ai", "AI2Bot", "ByteSpider",
]


def test_perfect_score():
    """All pillars maxed out should yield a score of 100."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in AI_BOT_NAMES]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True, url="https://example.com/llms.txt")
    # Need enough unique types to hit 25: base 8 + 5*N >= 25 → N >= 4
    schema_org = SchemaReport(
        blocks_found=4,
        schemas=[
            SchemaOrgResult(schema_type="Organization", properties=["name"]),
            SchemaOrgResult(schema_type="Article", properties=["headline"]),
            SchemaOrgResult(schema_type="Product", properties=["name"]),
            SchemaOrgResult(schema_type="FAQPage", properties=["mainEntity"]),
        ],
    )
    content = ContentReport(
        word_count=2000,
        has_headings=True,
        has_lists=True,
        has_code_blocks=True,
    )

    r, lt, s, c, overall = compute_scores(robots, llms_txt, schema_org, content)

    assert r.score == 25
    assert lt.score == 10
    assert s.score == 25  # 8 + 5*4 = 28, capped at 25
    assert c.score == 40  # 25 + 7 + 5 + 3 = 40
    assert overall == 100


def test_zero_score():
    """Everything missing should yield 0."""
    r, lt, s, c, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
    )

    assert r.score == 0
    assert lt.score == 0
    assert s.score == 0
    assert c.score == 0
    assert overall == 0


def test_half_bots_allowed():
    """7 of 13 bots allowed should score proportionally: round(25 * 7/13, 1)."""
    bots = [
        BotAccessResult(bot=AI_BOT_NAMES[i], allowed=(i < 7), detail="test")
        for i in range(13)
    ]
    robots = RobotsReport(found=True, bots=bots)

    r, _, _, _, _ = compute_scores(
        robots, LlmsTxtReport(found=False), SchemaReport(), ContentReport()
    )

    assert r.score == round(25 * 7 / 13, 1)


def test_schema_score_capped_at_25():
    """Even with many unique types, schema score should cap at 25."""
    schemas = [
        SchemaOrgResult(schema_type=f"Type{i}", properties=["name"])
        for i in range(10)
    ]
    schema_org = SchemaReport(blocks_found=10, schemas=schemas)

    _, _, s, _, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        schema_org,
        ContentReport(),
    )

    assert s.score == 25


def test_overall_is_sum_of_pillars():
    """Overall score should always equal the sum of individual pillar scores."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in AI_BOT_NAMES[:3]]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True)
    schema_org = SchemaReport(
        blocks_found=1,
        schemas=[SchemaOrgResult(schema_type="WebSite", properties=["name"])],
    )
    content = ContentReport(word_count=500, has_headings=True)

    r, lt, s, c, overall = compute_scores(robots, llms_txt, schema_org, content)

    assert overall == r.score + lt.score + s.score + c.score


def test_llms_full_only_scores_10():
    """Only llms-full.txt found (no llms.txt) should still score 10."""
    llms_txt = LlmsTxtReport(
        found=False,
        llms_full_found=True,
        llms_full_url="https://example.com/llms-full.txt",
    )

    _, lt, _, _, _ = compute_scores(
        RobotsReport(found=False), llms_txt, SchemaReport(), ContentReport()
    )

    assert lt.score == 10


def test_both_llms_files_scores_10():
    """Both llms.txt and llms-full.txt found should still score max 10."""
    llms_txt = LlmsTxtReport(
        found=True,
        url="https://example.com/llms.txt",
        llms_full_found=True,
        llms_full_url="https://example.com/llms-full.txt",
    )

    _, lt, _, _, _ = compute_scores(
        RobotsReport(found=False), llms_txt, SchemaReport(), ContentReport()
    )

    assert lt.score == 10


def test_neither_llms_scores_0():
    """Neither llms.txt nor llms-full.txt should score 0."""
    llms_txt = LlmsTxtReport(found=False, llms_full_found=False)

    _, lt, _, _, _ = compute_scores(
        RobotsReport(found=False), llms_txt, SchemaReport(), ContentReport()
    )

    assert lt.score == 0
