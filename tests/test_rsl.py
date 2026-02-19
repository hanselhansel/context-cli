"""Tests for RSL (Really Simple Licensing) robots.txt analysis."""

from context_cli.core.checks.rsl import check_rsl
from context_cli.core.models import RslReport


class TestCheckRsl:
    """Tests for check_rsl() function."""

    def test_empty_robots_txt(self) -> None:
        report = check_rsl("")
        assert isinstance(report, RslReport)
        assert not report.has_crawl_delay
        assert report.crawl_delay_value is None
        assert not report.has_sitemap_directive
        assert report.sitemap_urls == []
        assert not report.has_ai_specific_rules
        assert report.ai_specific_agents == []

    def test_none_robots_txt(self) -> None:
        report = check_rsl(None)
        assert isinstance(report, RslReport)
        assert not report.has_crawl_delay
        assert "No robots.txt" in report.detail

    def test_crawl_delay_found(self) -> None:
        robots = "User-agent: *\nCrawl-delay: 10\nAllow: /"
        report = check_rsl(robots)
        assert report.has_crawl_delay
        assert report.crawl_delay_value == 10.0

    def test_crawl_delay_float(self) -> None:
        robots = "User-agent: *\nCrawl-delay: 2.5\nAllow: /"
        report = check_rsl(robots)
        assert report.has_crawl_delay
        assert report.crawl_delay_value == 2.5

    def test_crawl_delay_invalid_value(self) -> None:
        robots = "User-agent: *\nCrawl-delay: abc\nAllow: /"
        report = check_rsl(robots)
        assert not report.has_crawl_delay
        assert report.crawl_delay_value is None

    def test_sitemap_single(self) -> None:
        robots = "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml"
        report = check_rsl(robots)
        assert report.has_sitemap_directive
        assert report.sitemap_urls == ["https://example.com/sitemap.xml"]

    def test_sitemap_multiple(self) -> None:
        robots = (
            "User-agent: *\nAllow: /\n"
            "Sitemap: https://example.com/sitemap.xml\n"
            "Sitemap: https://example.com/sitemap-news.xml\n"
        )
        report = check_rsl(robots)
        assert report.has_sitemap_directive
        assert len(report.sitemap_urls) == 2

    def test_no_sitemap(self) -> None:
        robots = "User-agent: *\nAllow: /"
        report = check_rsl(robots)
        assert not report.has_sitemap_directive
        assert report.sitemap_urls == []

    def test_ai_specific_rules_gptbot(self) -> None:
        robots = (
            "User-agent: *\nAllow: /\n\n"
            "User-agent: GPTBot\nDisallow: /private/\n"
        )
        report = check_rsl(robots)
        assert report.has_ai_specific_rules
        assert "GPTBot" in report.ai_specific_agents

    def test_ai_specific_rules_multiple(self) -> None:
        robots = (
            "User-agent: *\nAllow: /\n\n"
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: ClaudeBot\nDisallow: /\n\n"
            "User-agent: Googlebot\nAllow: /\n"
        )
        report = check_rsl(robots)
        assert report.has_ai_specific_rules
        assert "GPTBot" in report.ai_specific_agents
        assert "ClaudeBot" in report.ai_specific_agents
        # Googlebot is not an AI bot
        assert "Googlebot" not in report.ai_specific_agents

    def test_no_ai_specific_rules(self) -> None:
        robots = "User-agent: *\nDisallow: /admin/\n"
        report = check_rsl(robots)
        assert not report.has_ai_specific_rules
        assert report.ai_specific_agents == []

    def test_wildcard_only_not_ai_specific(self) -> None:
        """Wildcard User-agent (*) should not count as AI-specific."""
        robots = "User-agent: *\nDisallow: /\n"
        report = check_rsl(robots)
        assert not report.has_ai_specific_rules

    def test_case_insensitive_directives(self) -> None:
        robots = "User-agent: *\ncrawl-delay: 5\nsitemap: https://example.com/sitemap.xml"
        report = check_rsl(robots)
        assert report.has_crawl_delay
        assert report.crawl_delay_value == 5.0
        assert report.has_sitemap_directive

    def test_detail_summary(self) -> None:
        robots = (
            "User-agent: *\nCrawl-delay: 10\n"
            "Sitemap: https://example.com/sitemap.xml\n\n"
            "User-agent: GPTBot\nDisallow: /\n"
        )
        report = check_rsl(robots)
        assert "Crawl-delay" in report.detail
        assert "Sitemap" in report.detail or "sitemap" in report.detail
        assert "GPTBot" in report.detail or "AI-specific" in report.detail

    def test_all_known_ai_bots_detected(self) -> None:
        """All 13 AI bots from the checklist should be recognized."""
        robots = "\n\n".join(
            f"User-agent: {bot}\nDisallow: /"
            for bot in [
                "GPTBot", "ChatGPT-User", "Google-Extended", "ClaudeBot",
                "PerplexityBot", "Amazonbot", "OAI-SearchBot", "DeepSeek-AI",
                "Grok", "Meta-ExternalAgent", "cohere-ai", "AI2Bot", "ByteSpider",
            ]
        )
        report = check_rsl(robots)
        assert report.has_ai_specific_rules
        assert len(report.ai_specific_agents) == 13

    def test_combined_signals(self) -> None:
        """Full robots.txt with all RSL signals."""
        robots = (
            "User-agent: *\n"
            "Crawl-delay: 5\n"
            "Allow: /\n\n"
            "User-agent: GPTBot\n"
            "Disallow: /private/\n\n"
            "User-agent: ClaudeBot\n"
            "Disallow: /\n\n"
            "Sitemap: https://example.com/sitemap.xml\n"
            "Sitemap: https://example.com/sitemap-blog.xml\n"
        )
        report = check_rsl(robots)
        assert report.has_crawl_delay
        assert report.crawl_delay_value == 5.0
        assert report.has_sitemap_directive
        assert len(report.sitemap_urls) == 2
        assert report.has_ai_specific_rules
        assert len(report.ai_specific_agents) == 2
