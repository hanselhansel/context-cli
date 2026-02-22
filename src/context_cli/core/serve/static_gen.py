"""Static site generator — crawl a website and emit .md files mirroring URL structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx

from context_cli.core.discovery import discover_pages
from context_cli.core.markdown_engine import convert_html_to_markdown
from context_cli.core.markdown_engine.config import MarkdownEngineConfig


@dataclass
class StaticGenReport:
    """Result summary from a static markdown generation run."""

    pages_converted: int = 0
    pages_failed: int = 0
    output_dir: str = ""
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def url_to_filepath(url: str, base_url: str) -> str:
    """Convert a URL to a relative file path for markdown output.

    Examples:
        https://example.com/           -> index.md
        https://example.com/about      -> about.md
        https://example.com/blog/post  -> blog/post.md
        https://example.com/dir/       -> dir/index.md
    """
    base_parsed = urlparse(base_url)
    url_parsed = urlparse(url)

    # Strip base path prefix and work with the remainder
    base_path = base_parsed.path.rstrip("/")
    url_path = url_parsed.path

    # Remove base path prefix
    if base_path and url_path.startswith(base_path):
        url_path = url_path[len(base_path):]

    # Strip leading slash
    url_path = url_path.lstrip("/")

    # Handle trailing slash or empty path -> index
    if not url_path or url_path.endswith("/"):
        url_path = url_path.rstrip("/")
        if url_path:
            url_path = f"{url_path}/index"
        else:
            url_path = "index"

    return f"{url_path}.md"


async def generate_static_markdown(
    url: str,
    output_dir: str | Path,
    *,
    max_pages: int = 50,
    config: MarkdownEngineConfig | None = None,
) -> StaticGenReport:
    """Crawl *url*, discover pages, and write .md files to *output_dir*.

    Returns a :class:`StaticGenReport` summarising the generation run.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    report = StaticGenReport(output_dir=str(out))

    async with httpx.AsyncClient(
        timeout=30, follow_redirects=True,
    ) as client:
        # Discover pages
        try:
            discovery = await discover_pages(
                url, client, max_pages=max_pages,
            )
        except Exception as exc:
            report.errors.append(f"Discovery failed: {exc}")
            return report

        urls = discovery.urls_sampled
        if not urls:
            return report

        # Fetch and convert each page
        for page_url in urls:
            try:
                resp = await client.get(
                    page_url,
                    headers={"User-Agent": "ContextCLI/3.0"},
                )
                resp.raise_for_status()
            except Exception as exc:
                report.pages_failed += 1
                report.errors.append(f"Fetch failed for {page_url}: {exc}")
                continue

            html = resp.text
            try:
                md = convert_html_to_markdown(html, config)
            except Exception as exc:
                report.pages_failed += 1
                report.errors.append(f"Convert failed for {page_url}: {exc}")
                continue

            rel_path = url_to_filepath(page_url, url)
            full_path = out / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(md or "")

            report.pages_converted += 1
            report.files.append(rel_path)

    return report
