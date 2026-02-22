"""Tests for context_cli.core.markdown_engine.extractor module."""

from __future__ import annotations

from unittest.mock import patch

from context_cli.core.markdown_engine.extractor import extract_content


class TestEmptyInput:
    """Test empty and whitespace-only inputs."""

    def test_empty_string_returns_empty(self):
        assert extract_content("") == ""

    def test_none_returns_empty(self):
        # None is falsy, so it should return ""
        assert extract_content(None) == ""  # type: ignore[arg-type]

    def test_whitespace_only_returns_empty(self):
        assert extract_content("   \n\t  ") == ""


class TestReadabilipy:
    """Test readabilipy-based extraction (primary strategy)."""

    def test_article_rich_html_extracted(self):
        """Readabilipy should extract content from well-structured HTML."""
        html = """<html><head><title>Test Article</title></head><body>
        <nav><a href="/">Home</a></nav>
        <article>
        <h1>Main Article Title</h1>
        <p>This is the main content of the article. It contains enough text
        to be meaningful and should be extracted by the readability algorithm
        as the primary content of the page for the LLM readiness linter.</p>
        <p>Here is a second paragraph with additional content to make this
        substantial enough. The extractor should recognize this as the main
        content and return it without the navigation elements.</p>
        </article>
        <footer><p>Copyright 2024</p></footer>
        </body></html>"""
        result = extract_content(html)
        # readabilipy should extract content; result should include article text
        assert "Main Article Title" in result
        assert "main content of the article" in result

    def test_readabilipy_returns_content_over_100_chars(self):
        """When readabilipy returns >100 chars, it should be used."""
        html = """<html><head><title>T</title></head><body>
        <div>
        <h1>Title Here</h1>
        <p>A paragraph with sufficient length to exceed one hundred characters
        when extracted by the readabilipy library, ensuring that the primary
        extraction path is taken and the fallback chain is not invoked.</p>
        </div>
        </body></html>"""
        result = extract_content(html)
        assert len(result.strip()) > 100


class TestReadabilipyShortContent:
    """Test when readabilipy returns content under 100 chars (triggers fallback)."""

    def test_short_readabilipy_falls_through_to_body(self):
        """When readabilipy returns <100 chars and no semantic elements, use body."""
        # Very short HTML where readabilipy output is < 100 chars
        # and no <main>/<article>/role=main elements exist
        html = "<html><head><title>X</title></head><body><p>Short.</p></body></html>"
        result = extract_content(html)
        # Should fall through to <body> since readabilipy output is short
        # and there's no <main> or <article>
        assert "Short." in result


class TestReadabilipyException:
    """Test readabilipy exception handling."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("readabilipy crashed"),
    )
    def test_readabilipy_exception_falls_to_main(self, mock_readabilipy):
        """When readabilipy raises, fallback to <main> element."""
        html = """<html><body>
        <main>
        <h1>Title</h1>
        <p>Main content here with enough text to exceed the fifty character threshold easily.</p>
        </main>
        </body></html>"""
        result = extract_content(html)
        assert "Main content here" in result
        mock_readabilipy.assert_called_once()

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=ValueError("bad HTML"),
    )
    def test_readabilipy_valueerror_falls_to_article(self, mock_readabilipy):
        """When readabilipy raises ValueError, fallback to <article>."""
        html = """<html><body>
        <article>
        <h2>Article Heading</h2>
        <p>Article content with enough text to exceed the threshold of fifty characters easily.</p>
        </article>
        </body></html>"""
        result = extract_content(html)
        assert "Article content" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        return_value={"plain_content": None, "content": ""},
    )
    def test_readabilipy_empty_result_triggers_fallback(self, mock_readabilipy):
        """When readabilipy returns empty content, fallback chain activates."""
        html = """<html><body>
        <main>
        <p>Fallback main content that is long enough to pass the threshold check.</p>
        </main>
        </body></html>"""
        result = extract_content(html)
        assert "Fallback main content" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        return_value={"plain_content": "", "content": ""},
    )
    def test_readabilipy_empty_string_result_triggers_fallback(self, mock_readabilipy):
        """When readabilipy returns empty strings, fallback chain activates."""
        html = """<html><body>
        <main>
        <p>Content in main element that should be found by the fallback extraction logic.</p>
        </main>
        </body></html>"""
        result = extract_content(html)
        assert "Content in main element" in result


class TestMainFallback:
    """Test fallback to <main> element."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_main_element_extracted(self, mock_readabilipy):
        html = """<html><body>
        <header><h1>Site Name</h1></header>
        <main>
        <h2>Page Title</h2>
        <p>Main content that is long enough to pass the fifty character minimum threshold.</p>
        </main>
        <footer><p>Footer info</p></footer>
        </body></html>"""
        result = extract_content(html)
        assert "<main>" in result
        assert "Page Title" in result
        # Footer should not be in the result since <main> was found
        assert "Footer info" not in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_main_element_too_short_skipped(self, mock_readabilipy):
        """When <main> has text < 50 chars, skip to next fallback."""
        html = """<html><body>
        <main><p>Short</p></main>
        <article>
        <p>Article fallback content with enough text to exceed the threshold of fifty chars.</p>
        </article>
        </body></html>"""
        result = extract_content(html)
        # Should skip short <main> and use <article>
        assert "Article fallback content" in result


class TestArticleFallback:
    """Test fallback to <article> element."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_single_article_extracted(self, mock_readabilipy):
        html = """<html><body>
        <article>
        <h2>Blog Post</h2>
        <p>The blog post content that is definitely long enough to pass the threshold check.</p>
        </article>
        </body></html>"""
        result = extract_content(html)
        assert "<article>" in result
        assert "Blog Post" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_largest_article_selected(self, mock_readabilipy):
        """When multiple <article> elements exist, pick the largest."""
        html = """<html><body>
        <article><p>Small article</p></article>
        <article>
        <h2>Big Article</h2>
        <p>This is a much larger article with enough content to exceed both
        the length of the smaller article and the fifty character threshold,
        making it the preferred extraction target.</p>
        </article>
        <article><p>Medium article with some more text than small.</p></article>
        </body></html>"""
        result = extract_content(html)
        assert "Big Article" in result
        assert "larger article" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_article_too_short_skipped(self, mock_readabilipy):
        """When all articles have < 50 chars, skip to role=main."""
        html = """<html><body>
        <article><p>Tiny</p></article>
        <div role="main">
        <p>Role main content that is long enough to exceed fifty characters for the check.</p>
        </div>
        </body></html>"""
        result = extract_content(html)
        assert "Role main content" in result


class TestRoleMainFallback:
    """Test fallback to role="main" element."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_role_main_extracted(self, mock_readabilipy):
        html = """<html><body>
        <div role="main">
        <h1>Content Area</h1>
        <p>Content in a div with role main, long enough to pass the threshold check.</p>
        </div>
        </body></html>"""
        result = extract_content(html)
        assert 'role="main"' in result
        assert "Content Area" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_role_main_too_short_skipped(self, mock_readabilipy):
        """When role=main has < 50 chars, fall through to <body>."""
        html = """<html><body>
        <div role="main"><p>Hi</p></div>
        <p>Body level content here.</p>
        </body></html>"""
        result = extract_content(html)
        assert "<body>" in result


class TestBodyFallback:
    """Test fallback to <body> element."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_body_used_as_last_resort(self, mock_readabilipy):
        """When no semantic elements found, use <body>."""
        html = """<html><body>
        <div>
        <p>Just some content in divs without any semantic HTML elements.</p>
        </div>
        </body></html>"""
        result = extract_content(html)
        assert "<body>" in result
        assert "Just some content" in result


class TestNoBodyFallback:
    """Test when even <body> is missing."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_raw_html_returned_when_no_body(self, mock_readabilipy):
        """When no <body> exists, return original HTML."""
        html = "<div><p>Fragment without body tags at all.</p></div>"
        result = extract_content(html)
        assert result == html


class TestComplexNestedHTML:
    """Test with complex nested HTML structures."""

    def test_deeply_nested_content_extracted(self):
        """Readabilipy should handle deeply nested structures."""
        html = """<html><head><title>Deep Nesting</title></head><body>
        <div class="wrapper">
          <div class="container">
            <div class="row">
              <div class="col-md-8">
                <div class="content-area">
                  <article>
                    <h1>Deeply Nested Article</h1>
                    <p>This content is buried deep in nested divs but should
                    still be properly extracted by the readability algorithm
                    or the semantic HTML fallback chain because article tags
                    are always recognized regardless of nesting depth.</p>
                    <p>A second paragraph provides additional text to ensure
                    the content length threshold is easily exceeded and the
                    extraction is successful.</p>
                  </article>
                </div>
              </div>
              <div class="col-md-4">
                <aside><p>Sidebar content</p></aside>
              </div>
            </div>
          </div>
        </div>
        </body></html>"""
        result = extract_content(html)
        assert "Deeply Nested Article" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_mixed_semantic_elements_prefers_main(self, mock_readabilipy):
        """When both <main> and <article> exist, <main> is preferred."""
        html = """<html><body>
        <main>
        <h1>Main Content</h1>
        <p>This is in the main element and should be preferred over article elements.</p>
        </main>
        <article>
        <h2>Article Content</h2>
        <p>This article should not be selected because main was found first.</p>
        </article>
        </body></html>"""
        result = extract_content(html)
        assert "<main>" in result
        assert "Main Content" in result


class TestReadabiliplyPlainContentVsContent:
    """Test readabilipy result field priority (plain_content vs content)."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
    )
    def test_plain_content_preferred_over_content(self, mock_readabilipy):
        """plain_content field should be preferred when available."""
        long_text = "x" * 150
        mock_readabilipy.return_value = {
            "plain_content": f"<div>{long_text}</div>",
            "content": "<div>content field value</div>",
        }
        html = "<html><head><title>T</title></head><body><p>test</p></body></html>"
        result = extract_content(html)
        assert long_text in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
    )
    def test_content_used_when_plain_content_empty(self, mock_readabilipy):
        """content field used when plain_content is None/empty."""
        long_text = "y" * 150
        mock_readabilipy.return_value = {
            "plain_content": None,
            "content": f"<div>{long_text}</div>",
        }
        html = "<html><head><title>T</title></head><body><p>test</p></body></html>"
        result = extract_content(html)
        assert long_text in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
    )
    def test_content_used_when_plain_content_is_empty_string(self, mock_readabilipy):
        """content field used when plain_content is empty string."""
        long_text = "z" * 150
        mock_readabilipy.return_value = {
            "plain_content": "",
            "content": f"<div>{long_text}</div>",
        }
        html = "<html><head><title>T</title></head><body><p>test</p></body></html>"
        result = extract_content(html)
        assert long_text in result


class TestMinimalHTMLBelowThresholds:
    """Test with content that's below various threshold limits."""

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_main_with_exactly_50_chars_is_borderline(self, mock_readabilipy):
        """<main> with exactly 50 chars of text should not pass (> 50 required)."""
        # Create text that is exactly 50 chars
        text = "A" * 50
        html = f"<html><body><main><p>{text}</p></main></body></html>"
        result = extract_content(html)
        # 50 chars is not > 50, so main should be skipped, body used
        assert "<body>" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        side_effect=Exception("fail"),
    )
    def test_main_with_51_chars_passes(self, mock_readabilipy):
        """<main> with 51 chars should pass the threshold."""
        text = "A" * 51
        html = f"<html><body><main><p>{text}</p></main></body></html>"
        result = extract_content(html)
        assert "<main>" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        return_value={"plain_content": "x" * 100, "content": ""},
    )
    def test_readabilipy_exactly_100_chars_is_borderline(self, mock_readabilipy):
        """readabilipy result of exactly 100 chars should not pass (> 100 required)."""
        html = "<html><body><main><p>fallback content that is long enough.</p></main></body></html>"
        result = extract_content(html)
        # 100 chars is not > 100, so readabilipy result should be skipped
        assert "fallback content" in result

    @patch(
        "context_cli.core.markdown_engine.extractor.simple_json_from_html_string",
        return_value={"plain_content": "x" * 101, "content": ""},
    )
    def test_readabilipy_101_chars_passes(self, mock_readabilipy):
        """readabilipy result of 101 chars should pass the threshold."""
        html = "<html><body><p>test</p></body></html>"
        result = extract_content(html)
        assert result == "x" * 101
