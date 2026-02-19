"""Tests for citation radar domain classifier."""

from __future__ import annotations

from context_cli.core.models import DomainCategory
from context_cli.core.radar.domains import (
    DOMAIN_REGISTRY,
    _extract_root_domain,
    classify_domain,
    classify_domains,
)


class TestDomainRegistry:
    """Verify expected entries exist in the registry."""

    def test_reddit_in_registry(self) -> None:
        assert DOMAIN_REGISTRY["reddit.com"] == "reddit"

    def test_news_sites_in_registry(self) -> None:
        for d in ["nytimes.com", "bbc.com", "cnn.com", "forbes.com", "techcrunch.com"]:
            assert DOMAIN_REGISTRY[d] == "news", f"{d} should be news"

    def test_review_sites_in_registry(self) -> None:
        for d in ["wirecutter.com", "rtings.com", "tomsguide.com"]:
            assert DOMAIN_REGISTRY[d] == "review_site", f"{d} should be review_site"

    def test_marketplace_in_registry(self) -> None:
        for d in ["amazon.com", "shopee.com", "lazada.com"]:
            assert DOMAIN_REGISTRY[d] == "marketplace", f"{d} should be marketplace"

    def test_reference_in_registry(self) -> None:
        assert DOMAIN_REGISTRY["wikipedia.org"] == "reference"

    def test_blog_in_registry(self) -> None:
        for d in ["medium.com", "substack.com"]:
            assert DOMAIN_REGISTRY[d] == "blog", f"{d} should be blog"


class TestExtractRootDomain:
    """Tests for internal _extract_root_domain helper."""

    def test_simple_domain(self) -> None:
        assert _extract_root_domain("reddit.com") == "reddit.com"

    def test_www_prefix(self) -> None:
        assert _extract_root_domain("www.reddit.com") == "reddit.com"

    def test_subdomain(self) -> None:
        assert _extract_root_domain("en.wikipedia.org") == "wikipedia.org"

    def test_port_stripped(self) -> None:
        assert _extract_root_domain("example.com:8080") == "example.com"

    def test_trailing_dot(self) -> None:
        assert _extract_root_domain("example.com.") == "example.com"

    def test_deep_subdomain(self) -> None:
        assert _extract_root_domain("a.b.c.reddit.com") == "reddit.com"

    def test_unknown_subdomain_returns_last_two(self) -> None:
        # sub.unknown.io is not in registry, so falls back to last two parts
        assert _extract_root_domain("sub.unknown.io") == "unknown.io"

    def test_registry_match_beats_last_two(self) -> None:
        # news.ycombinator.com is in the registry as a full match
        assert _extract_root_domain("news.ycombinator.com") == "news.ycombinator.com"


class TestClassifyDomain:
    """Tests for classify_domain function."""

    def test_known_reddit(self) -> None:
        result = classify_domain("reddit.com")
        assert result == DomainCategory(domain="reddit.com", category="reddit")

    def test_known_news(self) -> None:
        result = classify_domain("nytimes.com")
        assert result.category == "news"

    def test_known_review_site(self) -> None:
        result = classify_domain("wirecutter.com")
        assert result.category == "review_site"

    def test_known_marketplace(self) -> None:
        result = classify_domain("amazon.com")
        assert result.category == "marketplace"

    def test_known_reference(self) -> None:
        result = classify_domain("wikipedia.org")
        assert result.category == "reference"

    def test_known_blog(self) -> None:
        result = classify_domain("medium.com")
        assert result.category == "blog"

    def test_unknown_domain_returns_other(self) -> None:
        result = classify_domain("example.com")
        assert result == DomainCategory(domain="example.com", category="other")

    def test_subdomain_handling(self) -> None:
        result = classify_domain("en.wikipedia.org")
        assert result.category == "reference"
        assert result.domain == "en.wikipedia.org"

    def test_www_prefix_handling(self) -> None:
        result = classify_domain("www.reddit.com")
        assert result.category == "reddit"
        assert result.domain == "www.reddit.com"

    def test_case_insensitive(self) -> None:
        result = classify_domain("Reddit.Com")
        assert result.category == "reddit"

    def test_empty_string(self) -> None:
        result = classify_domain("")
        assert result == DomainCategory(domain="", category="other")

    def test_domain_with_port(self) -> None:
        result = classify_domain("reddit.com:443")
        assert result.category == "reddit"

    def test_news_ycombinator(self) -> None:
        result = classify_domain("news.ycombinator.com")
        assert result.category == "news"


class TestClassifyDomains:
    """Tests for classify_domains (batch classification)."""

    def test_multiple_domains(self) -> None:
        results = classify_domains(["reddit.com", "nytimes.com", "example.com"])
        assert len(results) == 3
        categories = {r.domain: r.category for r in results}
        assert categories["reddit.com"] == "reddit"
        assert categories["nytimes.com"] == "news"
        assert categories["example.com"] == "other"

    def test_deduplication(self) -> None:
        results = classify_domains(["reddit.com", "reddit.com", "bbc.com"])
        assert len(results) == 2
        domains = [r.domain for r in results]
        assert domains.count("reddit.com") == 1

    def test_mixed_known_unknown(self) -> None:
        results = classify_domains(["amazon.com", "mysite.io", "medium.com", "other.xyz"])
        assert len(results) == 4
        categories = [r.category for r in results]
        assert "marketplace" in categories
        assert "blog" in categories
        assert categories.count("other") == 2

    def test_empty_list(self) -> None:
        results = classify_domains([])
        assert results == []

    def test_preserves_order(self) -> None:
        results = classify_domains(["bbc.com", "amazon.com", "reddit.com"])
        assert [r.domain for r in results] == ["bbc.com", "amazon.com", "reddit.com"]
