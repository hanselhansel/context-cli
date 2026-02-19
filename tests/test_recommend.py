"""Tests for the recommendation engine (core/recommend.py)."""

from __future__ import annotations

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    LlmsTxtReport,
    Recommendation,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)
from context_cli.core.recommend import generate_recommendations

# ── Helpers ──────────────────────────────────────────────────────────────────


def _perfect_report() -> AuditReport:
    """Report with max scores in all pillars — no recommendations expected."""
    return AuditReport(
        url="https://example.com",
        overall_score=100.0,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=True),
                BotAccessResult(bot="ClaudeBot", allowed=True),
                BotAccessResult(bot="PerplexityBot", allowed=True),
            ],
            score=25.0,
            detail="All bots allowed",
        ),
        llms_txt=LlmsTxtReport(
            found=True,
            llms_full_found=True,
            score=10.0,
        ),
        schema_org=SchemaReport(
            blocks_found=3,
            schemas=[
                SchemaOrgResult(schema_type="FAQPage", properties=["mainEntity"]),
                SchemaOrgResult(schema_type="Article", properties=["headline"]),
                SchemaOrgResult(schema_type="HowTo", properties=["step"]),
            ],
            score=25.0,
        ),
        content=ContentReport(
            word_count=2000,
            has_headings=True,
            has_lists=True,
            has_code_blocks=True,
            readability_grade=8.0,
            heading_count=10,
            heading_hierarchy_valid=True,
            answer_first_ratio=0.8,
            score=40.0,
        ),
    )


def _zero_report() -> AuditReport:
    """Report with zero scores in all pillars — max recommendations expected."""
    return AuditReport(
        url="https://example.com",
        overall_score=0.0,
        robots=RobotsReport(
            found=False,
            bots=[],
            score=0.0,
            detail="robots.txt not found",
        ),
        llms_txt=LlmsTxtReport(found=False, score=0.0),
        schema_org=SchemaReport(blocks_found=0, schemas=[], score=0.0),
        content=ContentReport(
            word_count=50,
            has_headings=False,
            has_lists=False,
            has_code_blocks=False,
            readability_grade=None,
            heading_count=0,
            answer_first_ratio=0.0,
            score=0.0,
        ),
    )


# ── Perfect score → no recommendations ──────────────────────────────────────


def test_perfect_score_no_recommendations():
    """A perfect-score report should produce no recommendations."""
    recs = generate_recommendations(_perfect_report())
    assert recs == []


# ── Zero score → multiple recommendations ───────────────────────────────────


def test_zero_score_has_recommendations():
    """A zero-score report should produce recommendations for all pillars."""
    recs = generate_recommendations(_zero_report())
    assert len(recs) > 0
    pillars_covered = {r.pillar for r in recs}
    assert "robots" in pillars_covered
    assert "llms_txt" in pillars_covered
    assert "schema" in pillars_covered
    assert "content" in pillars_covered


# ── Robots recommendations ──────────────────────────────────────────────────


def test_robots_not_found_recommends_creating():
    """When robots.txt not found, recommend creating one."""
    report = _zero_report()
    recs = generate_recommendations(report)
    robots_recs = [r for r in recs if r.pillar == "robots"]
    assert any("robots.txt" in r.action.lower() for r in robots_recs)


def test_robots_blocked_bots_recommends_unblocking():
    """When specific bots are blocked, recommend unblocking them."""
    report = AuditReport(
        url="https://example.com",
        overall_score=10.0,
        robots=RobotsReport(
            found=True,
            bots=[
                BotAccessResult(bot="GPTBot", allowed=False, detail="Disallow: /"),
                BotAccessResult(bot="ClaudeBot", allowed=True),
                BotAccessResult(bot="PerplexityBot", allowed=False, detail="Disallow: /"),
            ],
            score=8.3,
        ),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(score=25.0, blocks_found=1),
        content=ContentReport(score=40.0, word_count=2000),
    )
    recs = generate_recommendations(report)
    robots_recs = [r for r in recs if r.pillar == "robots"]
    assert len(robots_recs) > 0
    # Should mention the blocked bots
    combined = " ".join(r.detail for r in robots_recs)
    assert "GPTBot" in combined
    assert "PerplexityBot" in combined


def test_robots_all_allowed_no_recommendation():
    """When all bots allowed and score is max, no robots recommendations."""
    report = _perfect_report()
    recs = generate_recommendations(report)
    robots_recs = [r for r in recs if r.pillar == "robots"]
    assert robots_recs == []


# ── llms.txt recommendations ────────────────────────────────────────────────


def test_llms_txt_missing_recommends_creating():
    """When llms.txt not found, recommend creating one."""
    report = _zero_report()
    recs = generate_recommendations(report)
    llms_recs = [r for r in recs if r.pillar == "llms_txt"]
    assert any("llms.txt" in r.action.lower() for r in llms_recs)


def test_llms_txt_found_no_full_recommends_adding_full():
    """When llms.txt found but not llms-full.txt, recommend adding it."""
    report = AuditReport(
        url="https://example.com",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, llms_full_found=False, score=10.0),
        schema_org=SchemaReport(score=15.0, blocks_found=1),
        content=ContentReport(score=40.0, word_count=2000),
    )
    recs = generate_recommendations(report)
    llms_recs = [r for r in recs if r.pillar == "llms_txt"]
    assert any("llms-full.txt" in r.action.lower() for r in llms_recs)


def test_llms_txt_both_found_no_recommendation():
    """When both llms.txt and llms-full.txt are found, no llms recommendations."""
    report = _perfect_report()
    recs = generate_recommendations(report)
    llms_recs = [r for r in recs if r.pillar == "llms_txt"]
    assert llms_recs == []


# ── Schema recommendations ──────────────────────────────────────────────────


def test_schema_low_score_recommends_high_value_types():
    """When schema score is low, recommend adding high-value types."""
    report = AuditReport(
        url="https://example.com",
        overall_score=30.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(blocks_found=0, schemas=[], score=0.0),
        content=ContentReport(score=40.0, word_count=2000),
    )
    recs = generate_recommendations(report)
    schema_recs = [r for r in recs if r.pillar == "schema"]
    assert len(schema_recs) > 0
    combined = " ".join(r.detail for r in schema_recs)
    # Should suggest at least one high-value type
    assert any(
        t in combined for t in ["FAQPage", "HowTo", "Article", "Product", "Recipe"]
    )


def test_schema_has_some_but_missing_high_value():
    """When schema has standard types but missing high-value, suggest adding them."""
    report = AuditReport(
        url="https://example.com",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(
            blocks_found=1,
            schemas=[SchemaOrgResult(schema_type="Organization", properties=["name"])],
            score=11.0,
        ),
        content=ContentReport(score=40.0, word_count=2000),
    )
    recs = generate_recommendations(report)
    schema_recs = [r for r in recs if r.pillar == "schema"]
    assert len(schema_recs) > 0


def test_schema_max_score_no_recommendation():
    """When schema is at max score, no schema recommendations."""
    report = _perfect_report()
    recs = generate_recommendations(report)
    schema_recs = [r for r in recs if r.pillar == "schema"]
    assert schema_recs == []


# ── Content recommendations ─────────────────────────────────────────────────


def test_content_low_score_recommends_improvements():
    """When content score is low, should recommend improvements."""
    report = _zero_report()
    recs = generate_recommendations(report)
    content_recs = [r for r in recs if r.pillar == "content"]
    assert len(content_recs) > 0


def test_content_no_headings_recommends_adding():
    """When headings are missing, recommend adding H2/H3 structure."""
    report = AuditReport(
        url="https://example.com",
        overall_score=30.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(score=25.0, blocks_found=1),
        content=ContentReport(
            word_count=800,
            has_headings=False,
            has_lists=True,
            score=25.0,
        ),
    )
    recs = generate_recommendations(report)
    content_recs = [r for r in recs if r.pillar == "content"]
    assert any("heading" in r.action.lower() for r in content_recs)


def test_content_low_word_count_recommends_more():
    """When word count is very low, recommend adding more content."""
    report = AuditReport(
        url="https://example.com",
        overall_score=10.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(score=25.0, blocks_found=1),
        content=ContentReport(
            word_count=50,
            has_headings=True,
            has_lists=False,
            score=8.0,
        ),
    )
    recs = generate_recommendations(report)
    content_recs = [r for r in recs if r.pillar == "content"]
    assert any("content" in r.action.lower() or "word" in r.action.lower()
               for r in content_recs)


def test_content_poor_readability_recommends_simplifying():
    """When readability grade is high (hard to read), recommend simplifying."""
    report = AuditReport(
        url="https://example.com",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(score=25.0, blocks_found=1),
        content=ContentReport(
            word_count=800,
            has_headings=True,
            has_lists=True,
            readability_grade=16.0,
            score=30.0,
        ),
    )
    recs = generate_recommendations(report)
    content_recs = [r for r in recs if r.pillar == "content"]
    assert any("readab" in r.action.lower() or "simplif" in r.action.lower()
               for r in content_recs)


def test_content_low_answer_first_recommends_restructuring():
    """When answer-first ratio is low, recommend restructuring."""
    report = AuditReport(
        url="https://example.com",
        overall_score=50.0,
        robots=RobotsReport(found=True, score=25.0),
        llms_txt=LlmsTxtReport(found=True, score=10.0),
        schema_org=SchemaReport(score=25.0, blocks_found=1),
        content=ContentReport(
            word_count=800,
            has_headings=True,
            has_lists=True,
            answer_first_ratio=0.1,
            score=30.0,
        ),
    )
    recs = generate_recommendations(report)
    content_recs = [r for r in recs if r.pillar == "content"]
    assert any("answer" in r.action.lower() for r in content_recs)


def test_content_max_score_no_recommendation():
    """When content is at max score, no content recommendations."""
    report = _perfect_report()
    recs = generate_recommendations(report)
    content_recs = [r for r in recs if r.pillar == "content"]
    assert content_recs == []


# ── Sorting ─────────────────────────────────────────────────────────────────


def test_recommendations_sorted_by_impact():
    """Recommendations should be sorted by estimated_impact descending."""
    recs = generate_recommendations(_zero_report())
    assert len(recs) >= 2
    for i in range(len(recs) - 1):
        assert recs[i].estimated_impact >= recs[i + 1].estimated_impact


# ── Model serialization ─────────────────────────────────────────────────────


def test_recommendation_model_serialization():
    """Recommendation model should serialize and deserialize correctly."""
    rec = Recommendation(
        pillar="robots",
        action="Unblock GPTBot",
        estimated_impact=5.0,
        priority="high",
        detail="GPTBot is currently blocked by robots.txt.",
    )
    data = rec.model_dump()
    assert data["pillar"] == "robots"
    assert data["action"] == "Unblock GPTBot"
    assert data["estimated_impact"] == 5.0
    assert data["priority"] == "high"
    assert data["detail"] == "GPTBot is currently blocked by robots.txt."

    # Round-trip
    rec2 = Recommendation.model_validate(data)
    assert rec2 == rec


def test_recommendation_model_fields_have_descriptions():
    """All Recommendation fields should have descriptions."""
    for name, field_info in Recommendation.model_fields.items():
        assert field_info.description is not None, f"Field {name!r} has no description"


# ── Priority levels ─────────────────────────────────────────────────────────


def test_recommendations_have_valid_priorities():
    """All recommendations should have valid priority levels."""
    recs = generate_recommendations(_zero_report())
    valid_priorities = {"high", "medium", "low"}
    for rec in recs:
        assert rec.priority in valid_priorities, f"Invalid priority: {rec.priority}"


def test_high_impact_gets_high_priority():
    """Recommendations with large score gaps should be high priority."""
    report = _zero_report()
    recs = generate_recommendations(report)
    high_recs = [r for r in recs if r.priority == "high"]
    assert len(high_recs) > 0
