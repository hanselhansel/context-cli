"""Tests for static markdown site generation and CLI --static flag."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from context_cli.core.markdown_engine.config import MarkdownEngineConfig
from context_cli.core.models import DiscoveryResult
from context_cli.core.serve.static_gen import (
    StaticGenReport,
    generate_static_markdown,
    url_to_filepath,
)
from context_cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# url_to_filepath — unit tests
# ---------------------------------------------------------------------------


class TestUrlToFilepath:
    """URL-to-filepath mapping tests."""

    def test_root_url_maps_to_index(self) -> None:
        assert url_to_filepath("https://example.com/", "https://example.com") == "index.md"

    def test_root_without_trailing_slash(self) -> None:
        assert url_to_filepath("https://example.com", "https://example.com") == "index.md"

    def test_simple_page(self) -> None:
        assert url_to_filepath(
            "https://example.com/about", "https://example.com",
        ) == "about.md"

    def test_nested_path(self) -> None:
        assert url_to_filepath(
            "https://example.com/blog/post-1", "https://example.com",
        ) == "blog/post-1.md"

    def test_deeply_nested_path(self) -> None:
        assert url_to_filepath(
            "https://example.com/a/b/c/d", "https://example.com",
        ) == "a/b/c/d.md"

    def test_trailing_slash_maps_to_index(self) -> None:
        assert url_to_filepath(
            "https://example.com/blog/", "https://example.com",
        ) == "blog/index.md"

    def test_query_params_stripped(self) -> None:
        """Query parameters should be ignored (url_to_filepath uses urlparse path only)."""
        result = url_to_filepath(
            "https://example.com/page?q=test&lang=en", "https://example.com",
        )
        assert result == "page.md"

    def test_fragment_stripped(self) -> None:
        result = url_to_filepath(
            "https://example.com/page#section", "https://example.com",
        )
        assert result == "page.md"

    def test_base_with_path_prefix(self) -> None:
        """Base URL with path prefix should be stripped."""
        result = url_to_filepath(
            "https://example.com/docs/guide", "https://example.com/docs",
        )
        assert result == "guide.md"

    def test_base_with_path_prefix_and_trailing_slash(self) -> None:
        result = url_to_filepath(
            "https://example.com/docs/guide", "https://example.com/docs/",
        )
        assert result == "guide.md"

    def test_same_as_base_url(self) -> None:
        """URL identical to base should map to index.md."""
        result = url_to_filepath(
            "https://example.com/docs", "https://example.com/docs",
        )
        assert result == "index.md"


# ---------------------------------------------------------------------------
# StaticGenReport — dataclass tests
# ---------------------------------------------------------------------------


class TestStaticGenReport:
    """StaticGenReport dataclass behaviour."""

    def test_defaults(self) -> None:
        report = StaticGenReport()
        assert report.pages_converted == 0
        assert report.pages_failed == 0
        assert report.output_dir == ""
        assert report.files == []
        assert report.errors == []

    def test_custom_values(self) -> None:
        report = StaticGenReport(
            pages_converted=3,
            pages_failed=1,
            output_dir="/tmp/out",
            files=["index.md", "about.md"],
            errors=["one error"],
        )
        assert report.pages_converted == 3
        assert report.pages_failed == 1
        assert len(report.files) == 2
        assert len(report.errors) == 1


# ---------------------------------------------------------------------------
# generate_static_markdown — async tests
# ---------------------------------------------------------------------------


def _make_discovery(urls: list[str]) -> DiscoveryResult:
    """Helper to create a DiscoveryResult with given URLs."""
    return DiscoveryResult(
        method="sitemap",
        urls_found=len(urls),
        urls_sampled=urls,
        detail=f"found={len(urls)}",
    )


def _mock_response(html: str, status: int = 200) -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status}", request=MagicMock(), response=resp,
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


class TestGenerateStaticMarkdown:
    """Core generation logic tests."""

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_successful_generation(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/",
            "https://example.com/about",
        ])
        mock_convert.return_value = "# Page\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<h1>Page</h1>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 2
        assert report.pages_failed == 0
        assert len(report.files) == 2
        assert "index.md" in report.files
        assert "about.md" in report.files
        assert (tmp_path / "index.md").exists()
        assert (tmp_path / "about.md").exists()

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    async def test_empty_site_no_pages(
        self,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([])

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 0
        assert report.pages_failed == 0
        assert report.files == []

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_fetch_failure_graceful(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/good",
            "https://example.com/bad",
        ])
        mock_convert.return_value = "# Good\n"

        good_resp = _mock_response("<h1>Good</h1>")
        bad_resp = _mock_response("", status=404)

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.side_effect = [good_resp, bad_resp]
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 1
        assert report.pages_failed == 1
        assert len(report.errors) == 1
        assert "bad" in report.errors[0]

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_convert_failure_graceful(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/page",
        ])
        mock_convert.side_effect = ValueError("bad html")

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<broken>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 0
        assert report.pages_failed == 1
        assert "Convert failed" in report.errors[0]

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_nested_directories_created(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/blog/post-1",
            "https://example.com/docs/api/ref",
        ])
        mock_convert.return_value = "# Content\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<p>Content</p>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert (tmp_path / "blog" / "post-1.md").exists()
        assert (tmp_path / "docs" / "api" / "ref.md").exists()
        assert report.pages_converted == 2

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_output_dir_created_if_missing(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        out_dir = tmp_path / "deep" / "nested" / "output"
        assert not out_dir.exists()

        mock_discover.return_value = _make_discovery([
            "https://example.com/",
        ])
        mock_convert.return_value = "# Index\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<h1>Index</h1>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", out_dir,
            )

        assert out_dir.exists()
        assert report.pages_converted == 1

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_max_pages_passed_to_discovery(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([])

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            await generate_static_markdown(
                "https://example.com", tmp_path, max_pages=5,
            )

        mock_discover.assert_called_once()
        _, kwargs = mock_discover.call_args
        assert kwargs["max_pages"] == 5

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_custom_config_passed_to_converter(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        config = MarkdownEngineConfig(strip_nav=False)
        mock_discover.return_value = _make_discovery([
            "https://example.com/page",
        ])
        mock_convert.return_value = "# Page\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<h1>Page</h1>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            await generate_static_markdown(
                "https://example.com", tmp_path, config=config,
            )

        mock_convert.assert_called_once()
        _, call_kwargs = mock_convert.call_args
        assert call_kwargs.get("config") is None or mock_convert.call_args[0][1] is config
        # The positional arg is (html, config)
        assert mock_convert.call_args[0][1] is config

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_report_output_dir_is_string(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([])

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.output_dir == str(tmp_path)

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_empty_markdown_written(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Even when converter returns empty string, file is created."""
        mock_discover.return_value = _make_discovery([
            "https://example.com/empty",
        ])
        mock_convert.return_value = ""

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<p></p>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 1
        assert (tmp_path / "empty.md").exists()
        assert (tmp_path / "empty.md").read_text() == ""

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_files_list_contains_relative_paths(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/",
            "https://example.com/blog/post",
        ])
        mock_convert.return_value = "# X\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<p>X</p>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        # All paths should be relative (no leading /)
        for f in report.files:
            assert not f.startswith("/")
            assert f.endswith(".md")

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    async def test_discovery_exception_handled(
        self,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.side_effect = RuntimeError("network down")

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 0
        assert report.pages_failed == 0
        assert len(report.errors) == 1
        assert "Discovery failed" in report.errors[0]

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_httpx_connection_error_graceful(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/timeout",
        ])

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.side_effect = httpx.ConnectError("refused")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_failed == 1
        assert report.pages_converted == 0
        assert "Fetch failed" in report.errors[0]

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_mixed_success_and_failure(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        mock_discover.return_value = _make_discovery([
            "https://example.com/ok1",
            "https://example.com/fail",
            "https://example.com/ok2",
        ])
        mock_convert.return_value = "# OK\n"

        ok_resp = _mock_response("<p>OK</p>")
        fail_resp = _mock_response("", status=500)

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.side_effect = [ok_resp, fail_resp, ok_resp]
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert report.pages_converted == 2
        assert report.pages_failed == 1
        assert len(report.files) == 2
        assert len(report.errors) == 1

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_index_page_trailing_slash(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """URL with trailing slash should generate index.md in subdirectory."""
        mock_discover.return_value = _make_discovery([
            "https://example.com/blog/",
        ])
        mock_convert.return_value = "# Blog\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<h1>Blog</h1>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", tmp_path,
            )

        assert "blog/index.md" in report.files
        assert (tmp_path / "blog" / "index.md").exists()

    @pytest.mark.asyncio
    @patch("context_cli.core.serve.static_gen.discover_pages")
    @patch("context_cli.core.serve.static_gen.convert_html_to_markdown")
    async def test_string_output_dir(
        self,
        mock_convert: MagicMock,
        mock_discover: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Output dir can be passed as a string."""
        out = str(tmp_path / "str_out")
        mock_discover.return_value = _make_discovery([
            "https://example.com/",
        ])
        mock_convert.return_value = "# Home\n"

        with patch("context_cli.core.serve.static_gen.httpx.AsyncClient") as mc:
            instance = AsyncMock()
            instance.get.return_value = _mock_response("<h1>Home</h1>")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mc.return_value = instance

            report = await generate_static_markdown(
                "https://example.com", out,
            )

        assert report.pages_converted == 1
        assert Path(out).exists()


# ---------------------------------------------------------------------------
# CLI --static flag tests
# ---------------------------------------------------------------------------


class TestMarkdownCliStatic:
    """CLI integration for --static flag."""

    def test_static_requires_output(self) -> None:
        """--static without --output should fail."""
        result = runner.invoke(
            app, ["markdown", "https://example.com", "--static"],
        )
        assert result.exit_code == 1
        assert "--output" in result.output or "required" in result.output

    def test_static_success(self, tmp_path: Path) -> None:
        report = StaticGenReport(
            pages_converted=3,
            pages_failed=0,
            output_dir=str(tmp_path),
            files=["index.md", "about.md", "blog/post.md"],
            errors=[],
        )

        with patch(
            "context_cli.core.serve.static_gen.generate_static_markdown",
            new_callable=AsyncMock,
            return_value=report,
        ):
            result = runner.invoke(
                app,
                [
                    "markdown", "https://example.com",
                    "--static", "--output", str(tmp_path),
                ],
            )

        assert result.exit_code == 0
        assert "3 pages converted" in result.output
        assert "0 failed" in result.output

    def test_static_with_errors_shows_warnings(
        self, tmp_path: Path,
    ) -> None:
        report = StaticGenReport(
            pages_converted=1,
            pages_failed=2,
            output_dir=str(tmp_path),
            files=["index.md"],
            errors=["Fetch failed for /bad1", "Fetch failed for /bad2"],
        )

        with patch(
            "context_cli.core.serve.static_gen.generate_static_markdown",
            new_callable=AsyncMock,
            return_value=report,
        ):
            result = runner.invoke(
                app,
                [
                    "markdown", "https://example.com",
                    "--static", "--output", str(tmp_path),
                ],
            )

        assert result.exit_code == 0
        assert "1 pages converted" in result.output
        assert "2 failed" in result.output
        assert "Errors (2)" in result.output

    def test_static_exception_exits_with_error(
        self, tmp_path: Path,
    ) -> None:
        with patch(
            "context_cli.core.serve.static_gen.generate_static_markdown",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            result = runner.invoke(
                app,
                [
                    "markdown", "https://example.com",
                    "--static", "--output", str(tmp_path),
                ],
            )

        assert result.exit_code == 1
        assert "Error" in result.output

    @patch("context_cli.cli.markdown.convert_url_to_markdown", new_callable=AsyncMock)
    def test_non_static_still_works(
        self, mock_convert: AsyncMock,
    ) -> None:
        """Existing markdown command behaviour unchanged without --static."""
        md = "# Hello\n"
        stats: dict[str, float | int] = {
            "raw_html_chars": 100,
            "clean_md_chars": 10,
            "raw_tokens": 25,
            "clean_tokens": 2,
            "reduction_pct": 92.0,
        }
        mock_convert.return_value = (md, stats)

        result = runner.invoke(app, ["markdown", "https://example.com"])
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_static_shows_file_list(
        self, tmp_path: Path,
    ) -> None:
        report = StaticGenReport(
            pages_converted=2,
            pages_failed=0,
            output_dir=str(tmp_path),
            files=["index.md", "about.md"],
            errors=[],
        )

        with patch(
            "context_cli.core.serve.static_gen.generate_static_markdown",
            new_callable=AsyncMock,
            return_value=report,
        ):
            result = runner.invoke(
                app,
                [
                    "markdown", "https://example.com",
                    "--static", "--output", str(tmp_path),
                ],
            )

        assert "index.md" in result.output
        assert "about.md" in result.output
        assert "Files: 2" in result.output

    def test_static_shows_output_dir(
        self, tmp_path: Path,
    ) -> None:
        report = StaticGenReport(
            pages_converted=0,
            pages_failed=0,
            output_dir=str(tmp_path),
            files=[],
            errors=[],
        )

        with patch(
            "context_cli.core.serve.static_gen.generate_static_markdown",
            new_callable=AsyncMock,
            return_value=report,
        ):
            result = runner.invoke(
                app,
                [
                    "markdown", "https://example.com",
                    "--static", "--output", str(tmp_path),
                ],
            )

        assert "Output directory:" in result.output
