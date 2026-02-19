"""Tests for citation radar parser — extract citations from LLM responses."""

from __future__ import annotations

from aeo_cli.core.radar.parser import (
    _get_snippet,
    extract_domain,
    extract_numbered_refs,
    extract_urls,
    parse_citations,
)


class TestExtractUrls:
    """Tests for extract_urls function."""

    def test_single_http_url(self) -> None:
        text = "Check out http://example.com for more info."
        urls = extract_urls(text)
        assert urls == ["http://example.com"]

    def test_single_https_url(self) -> None:
        text = "Visit https://example.com/page for details."
        urls = extract_urls(text)
        assert urls == ["https://example.com/page"]

    def test_url_with_path_and_params(self) -> None:
        text = "See https://example.com/path/to/resource?key=val&foo=bar"
        urls = extract_urls(text)
        assert urls == ["https://example.com/path/to/resource?key=val&foo=bar"]

    def test_multiple_urls(self) -> None:
        text = (
            "Sources: https://a.com/one and https://b.com/two "
            "and http://c.com/three"
        )
        urls = extract_urls(text)
        assert urls == [
            "https://a.com/one",
            "https://b.com/two",
            "http://c.com/three",
        ]

    def test_no_urls(self) -> None:
        text = "This text has no URLs at all."
        urls = extract_urls(text)
        assert urls == []

    def test_empty_string(self) -> None:
        urls = extract_urls("")
        assert urls == []

    def test_url_with_fragment(self) -> None:
        text = "See https://example.com/page#section for the heading."
        urls = extract_urls(text)
        assert urls == ["https://example.com/page#section"]

    def test_url_in_parentheses(self) -> None:
        text = "Reference (https://example.com/page) for more."
        urls = extract_urls(text)
        assert urls == ["https://example.com/page"]

    def test_url_with_trailing_punctuation_stripped(self) -> None:
        text = "See https://example.com/page."
        urls = extract_urls(text)
        # Trailing dot should be stripped
        assert urls == ["https://example.com/page"]

    def test_url_with_port(self) -> None:
        text = "Local: http://localhost:8080/api"
        urls = extract_urls(text)
        assert urls == ["http://localhost:8080/api"]


class TestExtractNumberedRefs:
    """Tests for extract_numbered_refs function."""

    def test_bracket_space_url(self) -> None:
        text = "[1] https://example.com/article"
        refs = extract_numbered_refs(text)
        assert refs == [(1, "https://example.com/article")]

    def test_bracket_colon_url(self) -> None:
        text = "[2]: https://example.com/paper"
        refs = extract_numbered_refs(text)
        assert refs == [(2, "https://example.com/paper")]

    def test_markdown_link_pattern(self) -> None:
        text = "[3](https://example.com/docs)"
        refs = extract_numbered_refs(text)
        assert refs == [(3, "https://example.com/docs")]

    def test_multiple_refs(self) -> None:
        text = (
            "[1] https://a.com\n"
            "[2]: https://b.com\n"
            "[3](https://c.com)"
        )
        refs = extract_numbered_refs(text)
        assert len(refs) == 3
        assert refs[0] == (1, "https://a.com")
        assert refs[1] == (2, "https://b.com")
        assert refs[2] == (3, "https://c.com")

    def test_no_refs(self) -> None:
        text = "No numbered references here."
        refs = extract_numbered_refs(text)
        assert refs == []

    def test_empty_string(self) -> None:
        refs = extract_numbered_refs("")
        assert refs == []

    def test_non_numeric_brackets_ignored(self) -> None:
        text = "[abc] https://example.com"
        refs = extract_numbered_refs(text)
        assert refs == []


class TestExtractDomain:
    """Tests for extract_domain function."""

    def test_simple_domain(self) -> None:
        assert extract_domain("https://example.com/page") == "example.com"

    def test_www_stripped(self) -> None:
        assert extract_domain("https://www.example.com/page") == "example.com"

    def test_subdomain_preserved(self) -> None:
        assert extract_domain("https://blog.example.com") == "blog.example.com"

    def test_with_port(self) -> None:
        assert extract_domain("http://localhost:8080/api") == "localhost"

    def test_invalid_url_returns_empty(self) -> None:
        assert extract_domain("not-a-url") == ""

    def test_empty_string(self) -> None:
        assert extract_domain("") == ""


class TestGetSnippet:
    """Tests for _get_snippet helper."""

    def test_url_not_in_text_returns_empty(self) -> None:
        assert _get_snippet("some text without url", "https://missing.com") == ""

    def test_url_found_returns_context(self) -> None:
        text = "Before context https://example.com/page after context here"
        snippet = _get_snippet(text, "https://example.com/page", context_chars=10)
        assert "https://example.com/page" in snippet
        assert len(snippet) > len("https://example.com/page")


class TestParseCitations:
    """Tests for parse_citations — the main citation extraction function."""

    def test_response_with_inline_urls(self) -> None:
        response = (
            "According to https://example.com/article, the data shows "
            "interesting results. See also https://other.com/page for context."
        )
        citations = parse_citations(response, model="gpt-4o-mini")
        assert len(citations) == 2
        assert citations[0].url == "https://example.com/article"
        assert citations[0].domain == "example.com"
        assert citations[1].url == "https://other.com/page"
        assert citations[1].domain == "other.com"

    def test_response_with_numbered_references(self) -> None:
        response = (
            "The study found significant results [1][2].\n\n"
            "References:\n"
            "[1] https://example.com/study\n"
            "[2]: https://journal.org/paper"
        )
        citations = parse_citations(response, model="gpt-4o-mini")
        assert len(citations) >= 2
        urls = [c.url for c in citations]
        assert "https://example.com/study" in urls
        assert "https://journal.org/paper" in urls

    def test_response_with_no_citations(self) -> None:
        response = "Paris is the capital of France. It has many landmarks."
        citations = parse_citations(response, model="gpt-4o-mini")
        assert citations == []

    def test_perplexity_style_response(self) -> None:
        response = (
            "The answer is based on several sources [1][2][3].\n\n"
            "[1](https://reddit.com/r/topic/123)\n"
            "[2](https://www.news.com/article)\n"
            "[3] https://blog.example.com/post"
        )
        citations = parse_citations(response, model="perplexity/sonar")
        assert len(citations) >= 3
        domains = [c.domain for c in citations]
        assert "reddit.com" in domains
        assert "news.com" in domains
        assert "blog.example.com" in domains

    def test_snippets_populated(self) -> None:
        response = (
            "According to a recent study at https://example.com/study, "
            "the earth is warming rapidly."
        )
        citations = parse_citations(response, model="gpt-4o-mini")
        assert len(citations) == 1
        assert citations[0].snippet is not None
        assert len(citations[0].snippet) > 0

    def test_empty_response(self) -> None:
        citations = parse_citations("", model="gpt-4o-mini")
        assert citations == []

    def test_duplicate_urls_deduplicated(self) -> None:
        response = (
            "See https://example.com/page for info.\n"
            "[1] https://example.com/page"
        )
        citations = parse_citations(response, model="gpt-4o-mini")
        # Should deduplicate by URL
        urls = [c.url for c in citations]
        assert urls.count("https://example.com/page") == 1

    def test_malformed_urls_skipped(self) -> None:
        response = "Visit http:// for info. Also see https://valid.com/page."
        citations = parse_citations(response, model="gpt-4o-mini")
        urls = [c.url for c in citations]
        assert "https://valid.com/page" in urls
        # Malformed URL should not appear
        assert "http://" not in urls
