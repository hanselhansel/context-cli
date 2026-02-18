"""crawl4ai wrapper — extracts markdown and HTML from a URL via headless browser."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrawlResult:
    """Decoupled result from crawl4ai, insulating us from API changes."""

    url: str
    html: str
    markdown: str
    success: bool
    error: str | None = None


async def extract_page(url: str) -> CrawlResult:
    """Crawl a URL and extract its HTML + markdown content.

    Uses crawl4ai's AsyncWebCrawler. Handles API differences between versions
    where result.markdown may be a string or an object with .raw_markdown.
    """
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)

            # crawl4ai version compat: markdown may be str or object
            md = result.markdown
            if hasattr(md, "raw_markdown"):
                md = md.raw_markdown
            if not isinstance(md, str):
                md = str(md) if md else ""

            return CrawlResult(
                url=url,
                html=result.html or "",
                markdown=md,
                success=result.success,
            )
    except Exception as e:
        return CrawlResult(
            url=url,
            html="",
            markdown="",
            success=False,
            error=str(e),
        )
