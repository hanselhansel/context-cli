"""Tests for site-level audit aggregation and page content auditing."""

from __future__ import annotations

from context_cli.core.auditor import _page_weight, aggregate_page_scores, audit_page_content
from context_cli.core.models import (
    ContentReport,
    LlmsTxtReport,
    PageAudit,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)

# -- aggregate_page_scores -----------------------------------------------------


def _make_page(
    url: str,
    *,
    schema_score: float = 0,
    content_score: float = 0,
    word_count: int = 500,
    blocks_found: int = 0,
    schemas: list[SchemaOrgResult] | None = None,
    errors: list[str] | None = None,
) -> PageAudit:
    """Helper to build a PageAudit with controlled scores."""
    return PageAudit(
        url=url,
        schema_org=SchemaReport(
            blocks_found=blocks_found,
            schemas=schemas or [],
            score=schema_score,
            detail=f"{blocks_found} blocks",
        ),
        content=ContentReport(
            word_count=word_count,
            char_count=word_count * 5,
            has_headings=True,
            score=content_score,
            detail=f"{word_count} words",
        ),
        errors=errors or [],
    )


def test_aggregate_page_scores_averages():
    """Scores should be averaged across multiple successful pages."""
    pages = [
        _make_page("https://example.com/", schema_score=18, content_score=30, word_count=1000),
        _make_page("https://example.com/about", schema_score=8, content_score=20, word_count=400),
    ]
    robots = RobotsReport(found=True, score=20)
    llms = LlmsTxtReport(found=True, score=10)

    agg_schema, agg_content, overall = aggregate_page_scores(pages, robots, llms)

    # Schema avg: (18 + 8) / 2 = 13.0
    assert agg_schema.score == 13.0
    # Content avg: (30 + 20) / 2 = 25.0
    assert agg_content.score == 25.0
    # Word count avg: (1000 + 400) / 2 = 700
    assert agg_content.word_count == 700
    # Overall: robots(20) + llms(10) + schema(13) + content(25) = 68
    assert overall == 20 + 10 + 13.0 + 25.0


def test_aggregate_page_scores_single_page():
    """A single page should return its own scores without averaging artifacts."""
    pages = [
        _make_page("https://example.com/", schema_score=18, content_score=37, word_count=1500),
    ]
    robots = RobotsReport(found=True, score=25)
    llms = LlmsTxtReport(found=False, score=0)

    agg_schema, agg_content, overall = aggregate_page_scores(pages, robots, llms)

    assert agg_schema.score == 18.0
    assert agg_content.score == 37.0
    assert overall == 25 + 0 + 18.0 + 37.0


def test_aggregate_page_scores_empty_pages():
    """No pages should return zero for schema/content, only site-wide scores."""
    robots = RobotsReport(found=True, score=25)
    llms = LlmsTxtReport(found=True, score=10)

    agg_schema, agg_content, overall = aggregate_page_scores([], robots, llms)

    assert agg_schema.score == 0
    assert agg_content.score == 0
    # Only site-wide scores contribute
    assert overall == 25 + 10


def test_aggregate_page_scores_skips_failed_pages():
    """Pages with errors and no content should be excluded from averaging."""
    pages = [
        _make_page("https://example.com/", schema_score=20, content_score=30, word_count=1000),
        _make_page(
            "https://example.com/broken",
            schema_score=0,
            content_score=0,
            word_count=0,
            errors=["Crawl failed"],
        ),
    ]
    robots = RobotsReport(found=True, score=25)
    llms = LlmsTxtReport(found=False, score=0)

    agg_schema, agg_content, overall = aggregate_page_scores(pages, robots, llms)

    # Only the successful page should be counted
    assert agg_schema.score == 20.0
    assert agg_content.score == 30.0


# -- audit_page_content --------------------------------------------------------


def test_audit_page_content_returns_schema_and_content():
    """audit_page_content should return a (SchemaReport, ContentReport) tuple."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Article", "headline": "Test Article"}
    </script>
    </head><body></body></html>
    """
    md = "# Test Article\n\nThis is the body of the article with several words."

    schema, content = audit_page_content(html, md)

    assert isinstance(schema, SchemaReport)
    assert isinstance(content, ContentReport)
    assert schema.blocks_found == 1
    assert schema.schemas[0].schema_type == "Article"
    assert content.word_count > 0
    assert content.has_headings is True


def test_audit_page_content_empty_inputs():
    """Empty HTML and markdown should return reports with zero/default values."""
    schema, content = audit_page_content("", "")

    assert schema.blocks_found == 0
    assert content.word_count == 0


# -- _page_weight --------------------------------------------------------------


def test_page_weight():
    """URL depth should map to descending weights: root=3, 1-deep=3, 2-deep=2, 3+-deep=1."""
    assert _page_weight("https://example.com/") == 3
    assert _page_weight("https://example.com/about") == 3
    assert _page_weight("https://example.com/blog/post") == 2
    assert _page_weight("https://example.com/blog/2024/03/slug") == 1


# -- depth-weighted aggregation ------------------------------------------------


def test_aggregate_page_scores_depth_weighting():
    """Pages closer to root should contribute more to the aggregate scores."""
    pages = [
        _make_page(
            "https://example.com/",
            schema_score=20, content_score=35, word_count=1500,
        ),
        _make_page(
            "https://example.com/blog/post",
            schema_score=13, content_score=20, word_count=800,
        ),
        _make_page(
            "https://example.com/blog/2024/03/slug",
            schema_score=8, content_score=10, word_count=300,
        ),
    ]
    robots = RobotsReport(found=True, score=25)
    llms = LlmsTxtReport(found=True, score=10)

    agg_schema, agg_content, overall = aggregate_page_scores(pages, robots, llms)

    # Weights: root=3, blog/post=2, blog/2024/03/slug=1  → total=6
    # Weighted schema: (20*3 + 13*2 + 8*1) / 6 = 94/6 ≈ 15.7
    assert agg_schema.score == 15.7
    # Weighted content: (35*3 + 20*2 + 10*1) / 6 = 155/6 ≈ 25.8
    assert agg_content.score == 25.8
    # Overall: robots(25) + llms(10) + schema(15.7) + content(25.8) = 76.5
    assert overall == 25 + 10 + 15.7 + 25.8
