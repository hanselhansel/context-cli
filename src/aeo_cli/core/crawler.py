"""crawl4ai wrapper — extracts markdown and HTML from a URL via headless browser."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse


@dataclass
class CrawlResult:
    """Decoupled result from crawl4ai, insulating us from API changes."""

    url: str
    html: str
    markdown: str
    success: bool
    error: str | None = None
    internal_links: list[str] | None = None


def _extract_internal_links_bs4(html: str, base_url: str) -> list[str]:
    """Fallback: extract internal links from HTML using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    seen: set[str] = set()
    links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag.get("href", ""))
        # Resolve relative URLs
        absolute = urljoin(base_url, href)
        # Strip fragment
        absolute, _ = urldefrag(absolute)
        parsed = urlparse(absolute)
        # Keep only same-domain HTTP(S) links
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base_domain:
            continue
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


def _normalize_links(raw_links: list[dict[str, Any]], base_url: str) -> list[str]:
    """Normalize crawl4ai internal link dicts to deduplicated absolute URLs."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    seen: set[str] = set()
    links: list[str] = []

    for entry in raw_links:
        href = entry.get("href", "")
        if not href:
            continue
        absolute = urljoin(base_url, href)
        absolute, _ = urldefrag(absolute)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base_domain:
            continue
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


async def extract_page(url: str) -> CrawlResult:
    """Crawl a URL and extract its HTML + markdown content.

    Uses crawl4ai's AsyncWebCrawler. Handles API differences between versions
    where result.markdown may be a string or an object with .raw_markdown.
    Also extracts internal links for site discovery.
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

            # Extract internal links
            internal_links: list[str] | None = None
            try:
                raw_links = getattr(result, "links", None)
                if isinstance(raw_links, dict) and "internal" in raw_links:
                    internal_links = _normalize_links(raw_links["internal"], url)
                else:
                    # Fallback to BeautifulSoup parsing
                    html_content = result.html or ""
                    if html_content:
                        internal_links = _extract_internal_links_bs4(html_content, url)
            except Exception:
                # Link extraction is best-effort; don't fail the crawl
                pass

            return CrawlResult(
                url=url,
                html=result.html or "",
                markdown=md,
                success=result.success,
                internal_links=internal_links,
            )
    except Exception as e:
        return CrawlResult(
            url=url,
            html="",
            markdown="",
            success=False,
            error=str(e),
        )


async def extract_pages(
    urls: list[str],
    *,
    max_concurrent: int = 3,
    delay_seconds: float = 1.0,
    per_page_timeout: float = 15.0,
) -> list[CrawlResult]:
    """Crawl multiple URLs concurrently with rate limiting.

    Args:
        urls: List of URLs to crawl.
        max_concurrent: Maximum number of simultaneous crawls.
        delay_seconds: Staggered delay between task launches.
        per_page_timeout: Timeout in seconds for each individual page crawl.

    Returns:
        List of CrawlResult in the same order as input urls.
        Failed pages return CrawlResult with success=False — never raises.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _crawl_one(index: int, url: str) -> tuple[int, CrawlResult]:
        # Staggered start to be polite to servers
        await asyncio.sleep(delay_seconds * index)
        async with semaphore:
            try:
                result = await asyncio.wait_for(
                    extract_page(url), timeout=per_page_timeout
                )
                return (index, result)
            except asyncio.TimeoutError:
                return (
                    index,
                    CrawlResult(
                        url=url,
                        html="",
                        markdown="",
                        success=False,
                        error=f"Timed out after {per_page_timeout}s",
                    ),
                )
            except Exception as e:
                return (
                    index,
                    CrawlResult(
                        url=url,
                        html="",
                        markdown="",
                        success=False,
                        error=str(e),
                    ),
                )

    tasks = [_crawl_one(i, url) for i, url in enumerate(urls)]
    completed = await asyncio.gather(*tasks)

    # Restore original order
    results: list[CrawlResult] = [None] * len(urls)  # type: ignore[list-item]
    for index, result in completed:
        results[index] = result

    return results
