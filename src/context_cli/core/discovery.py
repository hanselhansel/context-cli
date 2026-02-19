"""Page discovery for multi-page audits — sitemap-first, spider-fallback."""

from __future__ import annotations

import random
import xml.etree.ElementTree as ET
from collections import defaultdict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from context_cli.core.models import DiscoveryResult

_SITEMAP_NS: str = "http://www.sitemaps.org/schemas/sitemap/0.9"
_MAX_CHILD_SITEMAPS: int = 10


# ── URL normalisation ────────────────────────────────────────────────────────


def normalize_url(url: str) -> str:
    """Normalise a URL for deduplication.

    * Lowercases scheme and host
    * Strips trailing slashes
    * Removes fragment (#...)
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return f"{scheme}://{netloc}{path}"


# ── Sitemap parsing ──────────────────────────────────────────────────────────


def _parse_sitemap_xml(xml_text: str) -> tuple[list[str], list[str]]:
    """Parse a sitemap XML document.

    Returns:
        (page_urls, child_sitemap_urls)
    """
    page_urls: list[str] = []
    child_urls: list[str] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return page_urls, child_urls

    # Sitemap index: <sitemapindex> → <sitemap> → <loc>
    for sitemap_el in root.findall(f"{{{_SITEMAP_NS}}}sitemap"):
        loc = sitemap_el.findtext(f"{{{_SITEMAP_NS}}}loc")
        if loc:
            child_urls.append(loc.strip())

    # Regular sitemap: <urlset> → <url> → <loc>
    for url_el in root.findall(f"{{{_SITEMAP_NS}}}url"):
        loc = url_el.findtext(f"{{{_SITEMAP_NS}}}loc")
        if loc:
            page_urls.append(loc.strip())

    return page_urls, child_urls


async def fetch_sitemap_urls(
    base_url: str,
    client: httpx.AsyncClient,
    *,
    max_urls: int = 500,
) -> list[str]:
    """Fetch and parse sitemap(s) from a site, returning up to *max_urls* page URLs.

    Tries ``/sitemap.xml`` first, then ``/sitemap_index.xml``.
    If a sitemap index is found, child sitemaps are fetched (capped at 10).
    """
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [f"{origin}/sitemap.xml", f"{origin}/sitemap_index.xml"]

    all_page_urls: list[str] = []

    for sitemap_url in candidates:
        try:
            resp = await client.get(sitemap_url, follow_redirects=True)
            if resp.status_code != 200:
                continue
        except httpx.HTTPError:
            continue

        page_urls, child_urls = _parse_sitemap_xml(resp.text)
        all_page_urls.extend(page_urls)

        # Fetch child sitemaps (index files)
        for child_url in child_urls[:_MAX_CHILD_SITEMAPS]:
            try:
                child_resp = await client.get(child_url, follow_redirects=True)
                if child_resp.status_code != 200:
                    continue
                child_pages, _ = _parse_sitemap_xml(child_resp.text)
                all_page_urls.extend(child_pages)
            except httpx.HTTPError:
                continue

            if len(all_page_urls) >= max_urls:
                break

        # If we got any URLs from this candidate, stop trying others
        if all_page_urls:
            break

    return all_page_urls[:max_urls]


# ── Diverse page selection ───────────────────────────────────────────────────


def select_diverse_pages(
    urls: list[str],
    seed_url: str,
    *,
    max_pages: int = 10,
) -> list[str]:
    """Pick a diverse sample of URLs, always including *seed_url* first.

    Groups URLs by first path segment (e.g. ``/blog/*``, ``/products/*``) and
    round-robins across groups so the sample covers different sections of the site.
    """
    seed_norm = normalize_url(seed_url)
    selected: list[str] = [seed_url]
    seen: set[str] = {seed_norm}

    if max_pages <= 1:
        return selected

    # Group remaining URLs by first path segment
    groups: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        norm = normalize_url(url)
        if norm in seen:
            continue
        path = urlparse(url).path.strip("/")
        segment = path.split("/")[0] if path else ""
        groups[segment].append(url)

    # Shuffle within each group for variety
    for group_urls in groups.values():
        random.shuffle(group_urls)

    # Round-robin across groups
    group_keys = sorted(groups.keys())
    idx = 0
    while len(selected) < max_pages and group_keys:
        key = group_keys[idx % len(group_keys)]
        if groups[key]:
            url = groups[key].pop(0)
            norm = normalize_url(url)
            if norm not in seen:
                selected.append(url)
                seen.add(norm)
        if not groups[key]:
            group_keys.remove(key)
            if not group_keys:
                break
            idx = idx % len(group_keys) if group_keys else 0
        else:
            idx += 1

    return selected


# ── Robots.txt filter ────────────────────────────────────────────────────────


def _filter_by_robots(urls: list[str], robots_txt: str, base_url: str) -> list[str]:
    """Remove URLs that are blocked for GPTBot in robots.txt."""
    rp = RobotFileParser()
    rp.parse(robots_txt.splitlines())

    return [url for url in urls if rp.can_fetch("GPTBot", url)]


# ── Main discovery entrypoint ────────────────────────────────────────────────


async def discover_pages(
    seed_url: str,
    client: httpx.AsyncClient,
    *,
    max_pages: int = 10,
    robots_txt: str | None = None,
    seed_links: list[str] | None = None,
) -> DiscoveryResult:
    """Discover pages to audit starting from *seed_url*.

    Strategy:
        1. Try sitemap discovery via :func:`fetch_sitemap_urls`.
        2. If no sitemap URLs found, fall back to *seed_links* (internal links
           extracted during the seed page crawl).
        3. Filter URLs through robots.txt if provided (GPTBot user-agent).
        4. Normalise and deduplicate.
        5. Select a diverse sample via :func:`select_diverse_pages`.
        6. Always include *seed_url*.
    """
    errors: list[str] = []
    method = "sitemap"

    # Step 1: Try sitemap
    try:
        sitemap_urls = await fetch_sitemap_urls(seed_url, client)
    except Exception as exc:
        errors.append(f"Sitemap fetch error: {exc}")
        sitemap_urls = []

    # Step 2: Fallback to spider links
    if not sitemap_urls:
        method = "spider"
        sitemap_urls = list(seed_links or [])

    urls_found = len(sitemap_urls)

    # Step 3: Filter through robots.txt
    if robots_txt and sitemap_urls:
        parsed = urlparse(seed_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        sitemap_urls = _filter_by_robots(sitemap_urls, robots_txt, base)

    # Step 4: Normalise and deduplicate
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in sitemap_urls:
        norm = normalize_url(url)
        if norm not in seen:
            seen.add(norm)
            unique_urls.append(url)

    # Step 5-6: Select diverse sample (seed_url always included)
    sampled = select_diverse_pages(unique_urls, seed_url, max_pages=max_pages)

    detail_parts = [f"method={method}", f"found={urls_found}", f"sampled={len(sampled)}"]
    if errors:
        detail_parts.append(f"errors={len(errors)}")

    return DiscoveryResult(
        method=method,
        urls_found=urls_found,
        urls_sampled=sampled,
        detail=", ".join(detail_parts),
    )
