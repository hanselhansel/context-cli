"""Tests for the markdown converter module, public API, and CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from context_cli.core.markdown_engine.config import MarkdownEngineConfig
from context_cli.core.markdown_engine.converter import (
    convert_html_to_markdown,
    convert_url_to_markdown,
)
from context_cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# convert_html_to_markdown — unit tests
# ---------------------------------------------------------------------------


class TestConvertHtmlToMarkdownEmpty:
    """Empty / whitespace input edge cases."""

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_empty_string_returns_empty(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        assert convert_html_to_markdown("") == ""
        mock_sanitize.assert_not_called()
        mock_extract.assert_not_called()

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_whitespace_only_returns_empty(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        assert convert_html_to_markdown("   \n\t  ") == ""
        mock_sanitize.assert_not_called()
        mock_extract.assert_not_called()


class TestConvertHtmlToMarkdownBasic:
    """Basic HTML-to-markdown conversion tests."""

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_basic_paragraph(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Hello world</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "Hello world" in result
        mock_sanitize.assert_called_once()
        mock_extract.assert_called_once()

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_heading_preservation_h1_to_h6(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = (
            "<h1>H1</h1><h2>H2</h2><h3>H3</h3>"
            "<h4>H4</h4><h5>H5</h5><h6>H6</h6>"
        )
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "# H1" in result
        assert "## H2" in result
        assert "### H3" in result
        assert "#### H4" in result
        assert "##### H5" in result
        assert "###### H6" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_unordered_list(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "- Item 1" in result
        assert "- Item 2" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_ordered_list(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<ol><li>First</li><li>Second</li></ol>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "First" in result
        assert "Second" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_link_preservation(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = '<p><a href="https://example.com">Click here</a></p>'
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "[Click here](https://example.com)" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_table_conversion(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = (
            "<table><tr><th>Name</th><th>Score</th></tr>"
            "<tr><td>Alice</td><td>95</td></tr></table>"
        )
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "Name" in result
        assert "Score" in result
        assert "Alice" in result
        assert "95" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_code_block_preservation(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<pre><code>print('hello')</code></pre>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "print('hello')" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_inline_code(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Use <code>pip install</code> to install</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "`pip install`" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_bold_and_italic(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p><strong>Bold</strong> and <em>italic</em></p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert "**Bold**" in result
        assert "*italic*" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_blockquote(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<blockquote><p>A wise quote</p></blockquote>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert ">" in result
        assert "A wise quote" in result


class TestConvertHtmlToMarkdownCleanup:
    """Whitespace cleanup tests."""

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_consecutive_blank_lines_collapsed(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Line 1</p><p>Line 2</p>"
        # Simulate markdownify output that might have extra blank lines
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in result

    @patch("context_cli.core.markdown_engine.converter.markdownify")
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_consecutive_blank_lines_actually_collapsed(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
        mock_markdownify: MagicMock,
    ) -> None:
        """Force markdownify to output consecutive blank lines and verify collapse."""
        mock_sanitize.return_value = "<p>x</p>"
        mock_extract.return_value = "<p>x</p>"
        # Simulate markdownify producing multiple consecutive blank lines
        mock_markdownify.return_value = "Line 1\n\n\n\n\nLine 2\n"
        result = convert_html_to_markdown("<p>x</p>")
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_trailing_whitespace_stripped(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Content</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        for line in result.split("\n"):
            assert line == line.rstrip(), f"Trailing whitespace on: {line!r}"

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_result_ends_with_newline(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Content</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        result = convert_html_to_markdown(html)
        assert result.endswith("\n")

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_sanitizer_returns_empty_gives_empty(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        """If sanitizer + extractor strip everything, result is empty."""
        mock_sanitize.return_value = ""
        mock_extract.return_value = ""
        result = convert_html_to_markdown("<html><body></body></html>")
        assert result == ""


class TestConvertHtmlToMarkdownConfig:
    """Config passthrough tests."""

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_custom_config_passed_to_sanitizer(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        config = MarkdownEngineConfig(strip_selectors=["div.ad"])
        html = "<p>Content</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        convert_html_to_markdown(html, config=config)
        mock_sanitize.assert_called_once_with(html, config)

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_none_config_passed_to_sanitizer(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Content</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        convert_html_to_markdown(html)
        mock_sanitize.assert_called_once_with(html, None)


class TestConvertHtmlToMarkdownComplex:
    """Complex / real-world-like HTML tests."""

    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    def test_full_pipeline_complex_html(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        complex_html = """
        <article>
            <h1>Getting Started with Python</h1>
            <p>Python is a <strong>versatile</strong> language.</p>
            <h2>Installation</h2>
            <p>Use <code>pip install</code> to install packages.</p>
            <ul>
                <li>Easy to learn</li>
                <li>Great community</li>
            </ul>
            <h2>Links</h2>
            <p>Visit <a href="https://python.org">Python.org</a>.</p>
            <pre><code>print("Hello, World!")</code></pre>
        </article>
        """
        mock_sanitize.return_value = complex_html
        mock_extract.return_value = complex_html
        result = convert_html_to_markdown(complex_html)
        assert "# Getting Started with Python" in result
        assert "**versatile**" in result
        assert "## Installation" in result
        assert "`pip install`" in result
        assert "- Easy to learn" in result
        assert "- Great community" in result
        assert "[Python.org](https://python.org)" in result
        assert 'print("Hello, World!")' in result


class TestConvertHtmlToMarkdownPublicApi:
    """Test the public API re-export from __init__.py."""

    def test_import_from_package(self) -> None:
        from context_cli.core.markdown_engine import convert_html_to_markdown as fn
        assert callable(fn)


# ---------------------------------------------------------------------------
# convert_url_to_markdown — async tests
# ---------------------------------------------------------------------------


class TestConvertUrlToMarkdown:
    """Async URL-to-markdown conversion tests."""

    @pytest.mark.asyncio
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    async def test_fetches_and_converts(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<h1>Test Page</h1><p>Content here.</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            md, stats = await convert_url_to_markdown("https://example.com")

        assert "# Test Page" in md
        assert "Content here." in md
        mock_instance.get.assert_called_once_with(
            "https://example.com",
            headers={"User-Agent": "ContextCLI/3.0"},
        )

    @pytest.mark.asyncio
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    async def test_stats_dict_keys(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Hello</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            _, stats = await convert_url_to_markdown("https://example.com")

        expected_keys = {
            "raw_html_chars", "clean_md_chars",
            "raw_tokens", "clean_tokens", "reduction_pct",
        }
        assert set(stats.keys()) == expected_keys

    @pytest.mark.asyncio
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    async def test_stats_values_correct(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "x" * 400  # 400 chars = 100 raw tokens
        md_content = "<p>short</p>"
        mock_sanitize.return_value = md_content
        mock_extract.return_value = md_content

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            md, stats = await convert_url_to_markdown("https://example.com")

        assert stats["raw_html_chars"] == 400
        assert stats["raw_tokens"] == 100
        assert stats["clean_md_chars"] == len(md)
        assert stats["clean_tokens"] == len(md) // 4
        assert isinstance(stats["reduction_pct"], float)
        assert stats["reduction_pct"] > 0

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(),
        )

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            with pytest.raises(httpx.HTTPStatusError):
                await convert_url_to_markdown("https://example.com/404")

    @pytest.mark.asyncio
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    async def test_reduction_pct_zero_for_empty_html(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        """When raw HTML is empty, reduction should be 0.0."""
        mock_sanitize.return_value = ""
        mock_extract.return_value = ""

        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            _, stats = await convert_url_to_markdown("https://example.com")

        assert stats["reduction_pct"] == 0.0
        assert stats["raw_tokens"] == 0

    @pytest.mark.asyncio
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    async def test_custom_config_passed_through(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Content</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html
        config = MarkdownEngineConfig(strip_selectors=["nav"])

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            await convert_url_to_markdown(
                "https://example.com", config=config,
            )

        mock_sanitize.assert_called_once_with(html, config)

    @pytest.mark.asyncio
    @patch("context_cli.core.markdown_engine.converter.extract_content")
    @patch("context_cli.core.markdown_engine.converter.sanitize_html")
    async def test_custom_timeout(
        self, mock_sanitize: MagicMock, mock_extract: MagicMock,
    ) -> None:
        html = "<p>Content</p>"
        mock_sanitize.return_value = html
        mock_extract.return_value = html

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch("context_cli.core.markdown_engine.converter.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            await convert_url_to_markdown(
                "https://example.com", timeout=60,
            )

        mock_client.assert_called_once_with(
            timeout=60, follow_redirects=True,
        )


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestMarkdownCli:
    """CLI command tests."""

    @patch("context_cli.cli.markdown.convert_url_to_markdown", new_callable=AsyncMock)
    def test_markdown_command_outputs_text(
        self, mock_convert: AsyncMock,
    ) -> None:
        md = "# Hello\n\nWorld\n"
        stats: dict[str, float | int] = {
            "raw_html_chars": 100,
            "clean_md_chars": 20,
            "raw_tokens": 25,
            "clean_tokens": 5,
            "reduction_pct": 80.0,
        }
        mock_convert.return_value = (md, stats)

        result = runner.invoke(app, ["markdown", "https://example.com"])
        assert result.exit_code == 0
        assert "Hello" in result.output

    @patch("context_cli.cli.markdown.convert_url_to_markdown", new_callable=AsyncMock)
    def test_markdown_command_with_stats(
        self, mock_convert: AsyncMock,
    ) -> None:
        md = "# Hello\n"
        stats: dict[str, float | int] = {
            "raw_html_chars": 100,
            "clean_md_chars": 10,
            "raw_tokens": 25,
            "clean_tokens": 2,
            "reduction_pct": 92.0,
        }
        mock_convert.return_value = (md, stats)

        result = runner.invoke(
            app, ["markdown", "https://example.com", "--stats"],
        )
        assert result.exit_code == 0
        assert "Conversion Stats" in result.output
        assert "92.0%" in result.output

    @patch("context_cli.cli.markdown.convert_url_to_markdown", new_callable=AsyncMock)
    def test_markdown_command_with_output_file(
        self, mock_convert: AsyncMock, tmp_path: Path,
    ) -> None:
        md = "# Hello\n\nOutput test\n"
        stats: dict[str, float | int] = {
            "raw_html_chars": 50,
            "clean_md_chars": 25,
            "raw_tokens": 12,
            "clean_tokens": 6,
            "reduction_pct": 50.0,
        }
        mock_convert.return_value = (md, stats)

        outfile = tmp_path / "output.md"
        result = runner.invoke(
            app,
            ["markdown", "https://example.com", "--output", str(outfile)],
        )
        assert result.exit_code == 0
        assert "Markdown written to" in result.output
        assert outfile.read_text() == md

    @patch("context_cli.cli.markdown.convert_url_to_markdown", new_callable=AsyncMock)
    def test_markdown_command_error_handling(
        self, mock_convert: AsyncMock,
    ) -> None:
        mock_convert.side_effect = RuntimeError("Connection failed")

        result = runner.invoke(app, ["markdown", "https://bad.example.com"])
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Connection failed" in result.output

    @patch("context_cli.cli.markdown.convert_url_to_markdown", new_callable=AsyncMock)
    def test_markdown_command_no_stats_by_default(
        self, mock_convert: AsyncMock,
    ) -> None:
        md = "# Test\n"
        stats: dict[str, float | int] = {
            "raw_html_chars": 50,
            "clean_md_chars": 10,
            "raw_tokens": 12,
            "clean_tokens": 2,
            "reduction_pct": 83.3,
        }
        mock_convert.return_value = (md, stats)

        result = runner.invoke(app, ["markdown", "https://example.com"])
        assert result.exit_code == 0
        assert "Conversion Stats" not in result.output


# ---------------------------------------------------------------------------
# MarkdownEngineConfig — model tests
# ---------------------------------------------------------------------------


class TestMarkdownEngineConfig:
    """Tests for the config model."""

    def test_default_config(self) -> None:
        config = MarkdownEngineConfig()
        assert "script" in config.strip_selectors
        assert "style" in config.strip_selectors
        assert config.extract_main is True

    def test_custom_config(self) -> None:
        config = MarkdownEngineConfig(
            strip_selectors=["div.ad"],
            extract_main=False,
        )
        assert config.strip_selectors == ["div.ad"]
        assert config.extract_main is False


# ---------------------------------------------------------------------------
# Stub module tests (sanitizer + extractor stubs pass through unchanged)
# ---------------------------------------------------------------------------


class TestSanitizerStub:
    """Tests for the sanitizer stub module."""

    def test_sanitize_html_passthrough(self) -> None:
        from context_cli.core.markdown_engine.sanitizer import sanitize_html
        html = "<p>Test content</p>"
        assert sanitize_html(html) == html

    def test_sanitize_html_with_config(self) -> None:
        from context_cli.core.markdown_engine.sanitizer import sanitize_html
        config = MarkdownEngineConfig(strip_selectors=["nav"])
        html = "<nav>Nav</nav><p>Content</p>"
        # Stub just passes through
        assert sanitize_html(html, config) == html


class TestExtractorStub:
    """Tests for the extractor stub module."""

    def test_extract_content_passthrough(self) -> None:
        from context_cli.core.markdown_engine.extractor import extract_content
        html = "<article><p>Main content</p></article>"
        assert extract_content(html) == html
