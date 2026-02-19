"""Tests for schema type weighting in scoring.

HIGH_VALUE_TYPES (FAQPage, HowTo, Article, Product, Recipe) get 5 pts each.
Standard types (Organization, WebSite, etc.) get 3 pts each.
Base score remains 8, max remains 25.
"""

from __future__ import annotations

from aeo_cli.core.models import (
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)
from aeo_cli.core.scoring import (
    HIGH_VALUE_TYPES,
    SCHEMA_BASE_SCORE,
    SCHEMA_HIGH_VALUE_BONUS,
    SCHEMA_STANDARD_BONUS,
    compute_scores,
)


def _schema_score(*types: str) -> float:
    """Helper: compute schema score for given type names."""
    schemas = [SchemaOrgResult(schema_type=t, properties=["name"]) for t in types]
    schema_org = SchemaReport(blocks_found=len(schemas), schemas=schemas)
    _, _, s, _, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        schema_org,
        ContentReport(),
    )
    return s.score


def test_high_value_types_contents():
    """HIGH_VALUE_TYPES should contain exactly the 5 expected types."""
    assert HIGH_VALUE_TYPES == {"FAQPage", "HowTo", "Article", "Product", "Recipe"}


def test_bonus_constants():
    """High-value bonus should be 5, standard bonus should be 3."""
    assert SCHEMA_HIGH_VALUE_BONUS == 5
    assert SCHEMA_STANDARD_BONUS == 3


def test_single_high_value_type():
    """A single high-value type: base 8 + 5 = 13."""
    assert _schema_score("FAQPage") == 13


def test_single_standard_type():
    """A single standard type: base 8 + 3 = 11."""
    assert _schema_score("Organization") == 11


def test_mixed_types():
    """Mix of 1 high-value + 1 standard: base 8 + 5 + 3 = 16."""
    assert _schema_score("Article", "WebSite") == 16


def test_all_five_high_value_types_capped():
    """All 5 high-value types: 8 + 5*5 = 33, capped at 25."""
    assert _schema_score("FAQPage", "HowTo", "Article", "Product", "Recipe") == 25


def test_many_standard_types_capped():
    """6 standard types: 8 + 3*6 = 26, capped at 25."""
    assert _schema_score(
        "Organization", "WebSite", "WebPage",
        "BreadcrumbList", "ImageObject", "VideoObject",
    ) == 25


def test_duplicate_types_counted_once():
    """Duplicate types should only count once."""
    schemas = [
        SchemaOrgResult(schema_type="Article", properties=["name"]),
        SchemaOrgResult(schema_type="Article", properties=["headline"]),
    ]
    schema_org = SchemaReport(blocks_found=2, schemas=schemas)
    _, _, s, _, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        schema_org,
        ContentReport(),
    )
    # Only 1 unique type (Article, high-value): 8 + 5 = 13
    assert s.score == 13


def test_each_high_value_type_gets_bonus():
    """Each individual high-value type should get 5-point bonus."""
    for t in HIGH_VALUE_TYPES:
        score = _schema_score(t)
        expected = SCHEMA_BASE_SCORE + SCHEMA_HIGH_VALUE_BONUS
        assert score == expected, f"{t} should score {expected}, got {score}"


def test_two_high_value_one_standard():
    """2 high-value + 1 standard: 8 + 5*2 + 3*1 = 21."""
    assert _schema_score("FAQPage", "Product", "Organization") == 21


def test_no_schemas_still_zero():
    """No schemas should still score 0."""
    schema_org = SchemaReport()
    _, _, s, _, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        schema_org,
        ContentReport(),
    )
    assert s.score == 0
