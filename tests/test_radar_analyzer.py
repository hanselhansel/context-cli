"""Tests for citation radar brand analyzer."""

from __future__ import annotations

from context_cli.core.models import (
    CitationSource,
    ModelRadarResult,
    RadarConfig,
    RadarReport,
)
from context_cli.core.radar.analyzer import (
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    _collect_domains,
    _detect_sentiment,
    _extract_context,
    _merge_sentiments,
    aggregate_brand_mentions,
    build_radar_report,
    detect_brand_mentions,
)


class TestDetectBrandMentions:
    """Tests for detect_brand_mentions function."""

    def test_brand_found_single_mention(self) -> None:
        text = "I recommend using Acme Corp for your needs."
        result = detect_brand_mentions(text, ["Acme Corp"])
        assert len(result) == 1
        assert result[0].brand == "Acme Corp"
        assert result[0].count == 1

    def test_brand_multiple_occurrences(self) -> None:
        text = "Nike makes great shoes. I love Nike. Nike is the best."
        result = detect_brand_mentions(text, ["Nike"])
        assert len(result) == 1
        assert result[0].brand == "Nike"
        assert result[0].count == 3

    def test_brand_not_found(self) -> None:
        text = "This is a review about some product."
        result = detect_brand_mentions(text, ["Acme Corp"])
        assert result == []

    def test_case_insensitive_matching(self) -> None:
        text = "I use SHOPEE for shopping. shopee is great."
        result = detect_brand_mentions(text, ["Shopee"])
        assert len(result) == 1
        assert result[0].count == 2

    def test_multiple_brands(self) -> None:
        text = "Compare Apple and Samsung phones for the best value."
        result = detect_brand_mentions(text, ["Apple", "Samsung"])
        assert len(result) == 2
        brands = {m.brand for m in result}
        assert brands == {"Apple", "Samsung"}

    def test_multiple_brands_one_missing(self) -> None:
        text = "Apple makes the best phones."
        result = detect_brand_mentions(text, ["Apple", "Samsung"])
        assert len(result) == 1
        assert result[0].brand == "Apple"

    def test_sentiment_positive(self) -> None:
        text = "Acme is the best and most trusted brand for quality products."
        result = detect_brand_mentions(text, ["Acme"])
        assert result[0].sentiment == "positive"

    def test_sentiment_negative(self) -> None:
        text = "Avoid Acme products, they are poor and unreliable."
        result = detect_brand_mentions(text, ["Acme"])
        assert result[0].sentiment == "negative"

    def test_sentiment_neutral(self) -> None:
        text = "Acme makes various products in different categories."
        result = detect_brand_mentions(text, ["Acme"])
        assert result[0].sentiment == "neutral"

    def test_sentiment_mixed_defaults_to_neutral(self) -> None:
        text = "Acme has the best design but poor customer service."
        result = detect_brand_mentions(text, ["Acme"])
        # Both positive ("best") and negative ("poor") → neutral
        assert result[0].sentiment == "neutral"

    def test_context_snippet_extraction(self) -> None:
        text = "A" * 100 + "BrandX" + "B" * 100
        result = detect_brand_mentions(text, ["BrandX"])
        snippet = result[0].context_snippets[0]
        # Should have ellipsis on both ends (50 chars of context)
        assert snippet.startswith("...")
        assert snippet.endswith("...")
        assert "BrandX" in snippet

    def test_context_snippet_at_start_of_text(self) -> None:
        text = "BrandX is mentioned here."
        result = detect_brand_mentions(text, ["BrandX"])
        snippet = result[0].context_snippets[0]
        # Should NOT start with ... since brand is at the start
        assert not snippet.startswith("...")
        assert snippet.startswith("BrandX")

    def test_context_snippet_at_end_of_text(self) -> None:
        text = "The top choice is BrandX"
        result = detect_brand_mentions(text, ["BrandX"])
        snippet = result[0].context_snippets[0]
        # Should NOT end with ... since brand is at the end
        assert not snippet.endswith("...")
        assert snippet.endswith("BrandX")

    def test_empty_text(self) -> None:
        result = detect_brand_mentions("", ["Acme"])
        assert result == []

    def test_empty_brands_list(self) -> None:
        result = detect_brand_mentions("Some text about brands.", [])
        assert result == []

    def test_empty_brand_string_skipped(self) -> None:
        result = detect_brand_mentions("Some text.", ["", "Acme"])
        # Empty brand string is skipped
        assert len(result) == 0  # "Acme" not in text either

    def test_special_regex_chars_in_brand(self) -> None:
        text = "I use C++ for programming. C++ is great."
        result = detect_brand_mentions(text, ["C++"])
        assert len(result) == 1
        assert result[0].count == 2

    def test_sentiment_majority_vote_across_mentions(self) -> None:
        # Two positive contexts, one neutral → overall positive
        text = (
            "Nike is the best brand. "
            "I also think Nike is excellent. "
            "Nike was founded in 1964."
        )
        result = detect_brand_mentions(text, ["Nike"])
        assert result[0].sentiment == "positive"
        assert result[0].count == 3


class TestAggregateBrandMentions:
    """Tests for aggregate_brand_mentions."""

    def test_aggregate_single_result(self) -> None:
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Nike is the best shoe brand.",
            )
        ]
        mentions = aggregate_brand_mentions(results, ["Nike"])
        assert len(mentions) == 1
        assert mentions[0].brand == "Nike"
        assert mentions[0].count == 1

    def test_aggregate_multiple_results(self) -> None:
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Nike makes great shoes.",
            ),
            ModelRadarResult(
                model="claude-sonnet",
                response_text="I recommend Nike for running.",
            ),
        ]
        mentions = aggregate_brand_mentions(results, ["Nike"])
        assert len(mentions) == 1
        assert mentions[0].brand == "Nike"
        assert mentions[0].count == 2
        assert len(mentions[0].context_snippets) == 2

    def test_aggregate_multiple_brands_across_results(self) -> None:
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Nike vs Adidas comparison.",
            ),
            ModelRadarResult(
                model="claude-sonnet",
                response_text="Adidas has good designs.",
            ),
        ]
        mentions = aggregate_brand_mentions(results, ["Nike", "Adidas"])
        brands = {m.brand: m.count for m in mentions}
        assert brands["Nike"] == 1
        assert brands["Adidas"] == 2

    def test_aggregate_empty_results(self) -> None:
        mentions = aggregate_brand_mentions([], ["Nike"])
        assert mentions == []

    def test_aggregate_no_brands(self) -> None:
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Some generic text.",
            ),
        ]
        mentions = aggregate_brand_mentions(results, [])
        assert mentions == []


class TestBuildRadarReport:
    """Tests for build_radar_report."""

    def test_complete_report(self) -> None:
        config = RadarConfig(
            prompt="best running shoes",
            brands=["Nike", "Adidas"],
        )
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Nike is the best. Adidas is also good.",
                citations=[
                    CitationSource(url="https://reddit.com/r/running", domain="reddit.com"),
                    CitationSource(url="https://nytimes.com/review", domain="nytimes.com"),
                ],
            ),
        ]
        report = build_radar_report(config, results)

        assert isinstance(report, RadarReport)
        assert report.prompt == "best running shoes"
        assert len(report.model_results) == 1
        assert report.total_citations == 2
        assert len(report.brand_mentions) == 2
        assert len(report.domain_breakdown) == 2

        # Check domain classifications
        domain_map = {d.domain: d.category for d in report.domain_breakdown}
        assert domain_map["reddit.com"] == "reddit"
        assert domain_map["nytimes.com"] == "news"

    def test_empty_results(self) -> None:
        config = RadarConfig(prompt="test query", brands=["Acme"])
        report = build_radar_report(config, [])

        assert report.prompt == "test query"
        assert report.model_results == []
        assert report.brand_mentions == []
        assert report.domain_breakdown == []
        assert report.total_citations == 0

    def test_no_citations(self) -> None:
        config = RadarConfig(prompt="query", brands=[])
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Just a plain answer with no citations.",
            ),
        ]
        report = build_radar_report(config, results)
        assert report.total_citations == 0
        assert report.domain_breakdown == []

    def test_multiple_models(self) -> None:
        config = RadarConfig(
            prompt="best laptop",
            models=["gpt-4o", "claude-sonnet"],
            brands=["Dell"],
        )
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Dell makes reliable laptops.",
                citations=[CitationSource(domain="wirecutter.com")],
            ),
            ModelRadarResult(
                model="claude-sonnet",
                response_text="Consider Dell for business use.",
                citations=[
                    CitationSource(domain="tomsguide.com"),
                    CitationSource(domain="wirecutter.com"),
                ],
            ),
        ]
        report = build_radar_report(config, results)
        assert len(report.model_results) == 2
        assert report.total_citations == 3
        # Domain deduplication
        assert len(report.domain_breakdown) == 2

    def test_citations_without_domain(self) -> None:
        config = RadarConfig(prompt="test", brands=[])
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="Answer.",
                citations=[
                    CitationSource(url="https://example.com", domain=None),
                    CitationSource(domain="reddit.com"),
                ],
            ),
        ]
        report = build_radar_report(config, results)
        assert report.total_citations == 2
        # Only domain="reddit.com" should appear in breakdown (None is skipped)
        assert len(report.domain_breakdown) == 1


class TestHelpers:
    """Tests for internal helper functions."""

    def test_detect_sentiment_positive(self) -> None:
        text = "This is the best product I have ever used."
        # "best" is at index 12-16 area
        result = _detect_sentiment(text, 12, 16)
        assert result == "positive"

    def test_detect_sentiment_negative(self) -> None:
        text = "This product is poor and unreliable overall."
        result = _detect_sentiment(text, 16, 20)
        assert result == "negative"

    def test_detect_sentiment_neutral(self) -> None:
        text = "This product exists and is available."
        result = _detect_sentiment(text, 5, 12)
        assert result == "neutral"

    def test_extract_context_middle(self) -> None:
        text = "A" * 100 + "BRAND" + "B" * 100
        ctx = _extract_context(text, 100, 105)
        assert ctx.startswith("...")
        assert ctx.endswith("...")
        assert "BRAND" in ctx

    def test_extract_context_start(self) -> None:
        text = "BRAND and some more text after it."
        ctx = _extract_context(text, 0, 5)
        assert not ctx.startswith("...")
        assert "BRAND" in ctx

    def test_extract_context_end(self) -> None:
        text = "text before BRAND"
        ctx = _extract_context(text, 12, 17)
        assert not ctx.endswith("...")
        assert "BRAND" in ctx

    def test_merge_sentiments_both_positive(self) -> None:
        assert _merge_sentiments("positive", "positive") == "positive"

    def test_merge_sentiments_both_negative(self) -> None:
        assert _merge_sentiments("negative", "negative") == "negative"

    def test_merge_sentiments_mixed(self) -> None:
        assert _merge_sentiments("positive", "negative") == "neutral"

    def test_merge_sentiments_positive_neutral(self) -> None:
        assert _merge_sentiments("positive", "neutral") == "positive"

    def test_merge_sentiments_negative_neutral(self) -> None:
        assert _merge_sentiments("negative", "neutral") == "negative"

    def test_collect_domains_with_nones(self) -> None:
        results = [
            ModelRadarResult(
                model="gpt-4o",
                response_text="test",
                citations=[
                    CitationSource(domain="reddit.com"),
                    CitationSource(domain=None),
                    CitationSource(domain="bbc.com"),
                ],
            ),
        ]
        domains = _collect_domains(results)
        assert domains == ["reddit.com", "bbc.com"]

    def test_collect_domains_empty(self) -> None:
        assert _collect_domains([]) == []

    def test_positive_and_negative_word_sets(self) -> None:
        """Verify the word sets are non-empty and disjoint."""
        assert len(POSITIVE_WORDS) > 0
        assert len(NEGATIVE_WORDS) > 0
        assert POSITIVE_WORDS.isdisjoint(NEGATIVE_WORDS)
