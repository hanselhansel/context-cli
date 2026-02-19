"""Core audit orchestration — runs all pillar checks and computes AEO score."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from aeo_cli.core.crawler import CrawlResult, extract_page, extract_pages
from aeo_cli.core.discovery import discover_pages
from aeo_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    PageAudit,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
    SiteAuditReport,
)

AI_BOTS: list[str] = [
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "ClaudeBot",
    "PerplexityBot",
    "Amazonbot",
    "OAI-SearchBot",
]

DEFAULT_TIMEOUT: int = 15

# ── Scoring Constants ────────────────────────────────────────────────────────
# Exported so verbose output can display the actual thresholds used.

CONTENT_WORD_TIERS: list[tuple[int, int]] = [
    (1500, 25),
    (800, 20),
    (400, 15),
    (150, 8),
]
"""(min_words, base_score) — evaluated top-down, first match wins."""

CONTENT_HEADING_BONUS: int = 7
CONTENT_LIST_BONUS: int = 5
CONTENT_CODE_BONUS: int = 3
CONTENT_MAX: int = 40

SCHEMA_BASE_SCORE: int = 8
SCHEMA_PER_TYPE_BONUS: int = 5
SCHEMA_MAX: int = 25

ROBOTS_MAX: int = 25
LLMS_TXT_MAX: int = 10


# ── Pillar 1: Robots.txt ──────────────────────────────────────────────────────


async def check_robots(
    url: str, client: httpx.AsyncClient
) -> tuple[RobotsReport, str | None]:
    """Fetch robots.txt and check AI bot access.

    Returns:
        (report, raw_robots_text) — raw text is provided so discovery can filter URLs.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        resp = await client.get(robots_url, follow_redirects=True)
        if resp.status_code != 200:
            return (
                RobotsReport(
                    found=False, detail=f"robots.txt returned HTTP {resp.status_code}"
                ),
                None,
            )

        raw_text = resp.text
        rp = RobotFileParser()
        rp.parse(raw_text.splitlines())

        bots = []
        for bot in AI_BOTS:
            allowed = rp.can_fetch(bot, "/")
            bots.append(BotAccessResult(
                bot=bot,
                allowed=allowed,
                detail="Allowed" if allowed else "Blocked by robots.txt",
            ))

        allowed_count = sum(1 for b in bots if b.allowed)
        return (
            RobotsReport(
                found=True,
                bots=bots,
                detail=f"{allowed_count}/{len(AI_BOTS)} AI bots allowed",
            ),
            raw_text,
        )

    except httpx.HTTPError as e:
        return RobotsReport(found=False, detail=f"Failed to fetch robots.txt: {e}"), None


# ── Pillar 2: llms.txt ────────────────────────────────────────────────────────


async def check_llms_txt(url: str, client: httpx.AsyncClient) -> LlmsTxtReport:
    """Probe /llms.txt and /.well-known/llms.txt."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    paths = ["/llms.txt", "/.well-known/llms.txt"]

    for path in paths:
        probe_url = base + path
        try:
            resp = await client.get(probe_url, follow_redirects=True)
            if resp.status_code == 200 and len(resp.text.strip()) > 0:
                return LlmsTxtReport(
                    found=True,
                    url=probe_url,
                    detail=f"Found at {probe_url}",
                )
        except httpx.HTTPError:
            continue

    return LlmsTxtReport(found=False, detail="llms.txt not found")


# ── Pillar 3: Schema.org JSON-LD ──────────────────────────────────────────────


def check_schema_org(html: str) -> SchemaReport:  # noqa: C901
    """Extract and analyze JSON-LD structured data from HTML."""
    if not html:
        return SchemaReport(detail="No HTML to analyze")

    soup = BeautifulSoup(html, "html.parser")
    ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    schemas: list[SchemaOrgResult] = []
    for script in ld_scripts:
        try:
            data = json.loads(script.string or "")
            # Handle both single objects and arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "Unknown")
                    if isinstance(schema_type, list):
                        schema_type = ", ".join(schema_type)
                    props = [k for k in item.keys() if not k.startswith("@")]
                    schemas.append(SchemaOrgResult(
                        schema_type=schema_type,
                        properties=props,
                    ))
        except (json.JSONDecodeError, TypeError):
            continue

    blocks_found = len(schemas)
    detail = f"{blocks_found} JSON-LD block(s) found" if blocks_found else "No JSON-LD found"

    return SchemaReport(blocks_found=blocks_found, schemas=schemas, detail=detail)


# ── Pillar 4: Content Density ─────────────────────────────────────────────────


def check_content(markdown: str) -> ContentReport:
    """Analyze markdown content density."""
    if not markdown:
        return ContentReport(detail="No content extracted")

    words = markdown.split()
    word_count = len(words)
    char_count = len(markdown)
    has_headings = bool(re.search(r"^#{1,6}\s", markdown, re.MULTILINE))
    has_lists = bool(re.search(r"^[\s]*[-*+]\s", markdown, re.MULTILINE))
    has_code_blocks = "```" in markdown

    detail = f"{word_count} words"
    if has_headings:
        detail += ", has headings"
    if has_lists:
        detail += ", has lists"
    if has_code_blocks:
        detail += ", has code blocks"

    return ContentReport(
        word_count=word_count,
        char_count=char_count,
        has_headings=has_headings,
        has_lists=has_lists,
        has_code_blocks=has_code_blocks,
        detail=detail,
    )


# ── Scoring ───────────────────────────────────────────────────────────────────


def compute_scores(
    robots: RobotsReport,
    llms_txt: LlmsTxtReport,
    schema_org: SchemaReport,
    content: ContentReport,
) -> tuple[RobotsReport, LlmsTxtReport, SchemaReport, ContentReport, float]:
    """Compute scores for each pillar and overall AEO score.

    Scoring weights (revised 2026-02-18):
        Content (max 40): most impactful — what LLMs actually extract and cite
        Schema  (max 25): structured signals help LLMs understand page entities
        Robots  (max 25): gatekeeper — blocked bots can't crawl at all
        llms.txt (max 10): forward-looking signal, minimal real impact today

    Rationale: When AI search engines (ChatGPT, Perplexity, Claude) look up
    products or answer questions, they crawl pages and extract text content.
    Content quality dominates what gets cited. Schema.org gives structured
    "cheat sheets" (Product, Article, FAQ). Robots.txt is pass/fail per bot.
    llms.txt is emerging but not yet weighted by any major AI search engine.
    """
    # Robots: max ROBOTS_MAX — proportional to bots allowed
    if robots.found and robots.bots:
        allowed = sum(1 for b in robots.bots if b.allowed)
        robots.score = round(ROBOTS_MAX * allowed / len(robots.bots), 1)
    else:
        robots.score = 0

    # llms.txt: max LLMS_TXT_MAX
    llms_txt.score = LLMS_TXT_MAX if llms_txt.found else 0

    # Schema: max SCHEMA_MAX — reward high-value types more
    if schema_org.blocks_found > 0:
        unique_types = {s.schema_type for s in schema_org.schemas}
        schema_org.score = min(
            SCHEMA_MAX, SCHEMA_BASE_SCORE + SCHEMA_PER_TYPE_BONUS * len(unique_types)
        )
    else:
        schema_org.score = 0

    # Content: max CONTENT_MAX — word count tiers + structure bonuses
    score = 0
    for min_words, tier_score in CONTENT_WORD_TIERS:
        if content.word_count >= min_words:
            score = tier_score
            break
    if content.has_headings:
        score += CONTENT_HEADING_BONUS
    if content.has_lists:
        score += CONTENT_LIST_BONUS
    if content.has_code_blocks:
        score += CONTENT_CODE_BONUS
    content.score = min(CONTENT_MAX, score)

    overall = robots.score + llms_txt.score + schema_org.score + content.score
    return robots, llms_txt, schema_org, content, overall


# ── Orchestrator ──────────────────────────────────────────────────────────────


def audit_page_content(html: str, markdown: str) -> tuple[SchemaReport, ContentReport]:
    """Run page-specific checks (schema + content) on pre-crawled data."""
    return check_schema_org(html), check_content(markdown)


def _page_weight(url: str) -> int:
    """Return a weight for a page based on URL depth.

    Shallower pages (homepage, top-level sections) are more representative of a
    site's AEO readiness and therefore receive higher weight in aggregation.

    Returns:
        3 for depth 0-1 (homepage or single path segment)
        2 for depth 2
        1 for depth 3+
    """
    path = urlparse(url).path.strip("/")
    depth = len(path.split("/")) if path else 0
    if depth <= 1:
        return 3
    if depth == 2:
        return 2
    return 1


def aggregate_page_scores(
    pages: list[PageAudit],
    robots: RobotsReport,
    llms_txt: LlmsTxtReport,
) -> tuple[SchemaReport, ContentReport, float]:
    """Aggregate per-page scores into site-level pillar scores.

    Content (40pts) and Schema (25pts) use weighted averages — shallower pages
    count more (see ``_page_weight``).
    Robots (25pts) and llms.txt (10pts) are site-wide, used as-is.
    Word/char counts remain simple averages.
    """
    successful = [p for p in pages if not p.errors or p.content.word_count > 0]
    if not successful:
        agg_schema = SchemaReport(detail="No pages audited successfully")
        agg_content = ContentReport(detail="No pages audited successfully")
        return agg_schema, agg_content, robots.score + llms_txt.score

    weights = [_page_weight(p.url) for p in successful]
    total_weight = sum(weights)

    # Aggregate schema: collect all blocks, weighted-average the score
    all_schemas: list[SchemaOrgResult] = []
    total_blocks = 0
    schema_score_sum = 0.0
    for p, w in zip(successful, weights):
        all_schemas.extend(p.schema_org.schemas)
        total_blocks += p.schema_org.blocks_found
        schema_score_sum += p.schema_org.score * w

    avg_schema_score = round(schema_score_sum / total_weight, 1)
    agg_schema = SchemaReport(
        blocks_found=total_blocks,
        schemas=all_schemas,
        score=avg_schema_score,
        detail=(
            f"{total_blocks} JSON-LD block(s) across {len(successful)} pages"
            f" (weighted avg score {avg_schema_score})"
        ),
    )

    # Aggregate content: weighted-average scores, simple-average metrics
    content_score_sum = 0.0
    word_sum = 0
    char_sum = 0
    any_headings = False
    any_lists = False
    any_code = False
    for p, w in zip(successful, weights):
        content_score_sum += p.content.score * w
        word_sum += p.content.word_count
        char_sum += p.content.char_count
        any_headings = any_headings or p.content.has_headings
        any_lists = any_lists or p.content.has_lists
        any_code = any_code or p.content.has_code_blocks

    n = len(successful)
    avg_content_score = round(content_score_sum / total_weight, 1)
    avg_words = word_sum // n
    agg_content = ContentReport(
        word_count=avg_words,
        char_count=char_sum // n,
        has_headings=any_headings,
        has_lists=any_lists,
        has_code_blocks=any_code,
        score=avg_content_score,
        detail=(
            f"avg {avg_words} words across {n} pages"
            f" (weighted avg score {avg_content_score})"
        ),
    )

    overall = robots.score + llms_txt.score + avg_schema_score + avg_content_score
    return agg_schema, agg_content, overall


async def audit_url(url: str) -> AuditReport:
    """Run a full AEO audit on a single URL. Returns AuditReport with all pillar scores."""
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        # Run HTTP checks and browser crawl concurrently
        robots_task = check_robots(url, client)
        llms_task = check_llms_txt(url, client)
        crawl_task = extract_page(url)

        robots_result, llms_txt, crawl_result = await asyncio.gather(
            robots_task, llms_task, crawl_task, return_exceptions=True
        )

    # Handle exceptions from gather
    if isinstance(robots_result, BaseException):
        errors.append(f"Robots check failed: {robots_result}")
        robots = RobotsReport(found=False, detail="Check failed")
    else:
        robots, _raw_robots = robots_result  # destructure tuple

    if isinstance(llms_txt, BaseException):
        errors.append(f"llms.txt check failed: {llms_txt}")
        llms_txt = LlmsTxtReport(found=False, detail="Check failed")
    crawl: CrawlResult | None = None
    if isinstance(crawl_result, BaseException):
        errors.append(f"Crawl failed: {crawl_result}")
    else:
        crawl = crawl_result

    # Run sync checks on crawl results
    html = crawl.html if crawl and crawl.success else ""
    markdown = crawl.markdown if crawl and crawl.success else ""

    if crawl and not crawl.success and crawl.error:
        errors.append(f"Crawl error: {crawl.error}")

    schema_org = check_schema_org(html)
    content = check_content(markdown)

    # Compute scores
    robots, llms_txt, schema_org, content, overall = compute_scores(
        robots, llms_txt, schema_org, content
    )

    return AuditReport(
        url=url,
        overall_score=overall,
        robots=robots,
        llms_txt=llms_txt,
        schema_org=schema_org,
        content=content,
        errors=errors,
    )


SITE_AUDIT_TIMEOUT: int = 90


async def audit_site(
    url: str,
    *,
    max_pages: int = 10,
    delay_seconds: float = 1.0,
    progress_callback: Callable[[str], None] | None = None,
) -> SiteAuditReport:
    """Run a multi-page AEO audit. Discovers pages via sitemap/spider and aggregates scores."""
    errors: list[str] = []
    domain = urlparse(url).netloc

    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    try:
        return await asyncio.wait_for(
            _audit_site_inner(url, domain, max_pages, delay_seconds, errors, _progress),
            timeout=SITE_AUDIT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        errors.append(f"Audit timed out after {SITE_AUDIT_TIMEOUT}s, returning partial results")
        # Return whatever we have — the inner function stores partial results
        return SiteAuditReport(
            url=url,
            domain=domain,
            overall_score=0,
            robots=RobotsReport(found=False, detail="Timed out"),
            llms_txt=LlmsTxtReport(found=False, detail="Timed out"),
            schema_org=SchemaReport(detail="Timed out"),
            content=ContentReport(detail="Timed out"),
            discovery=DiscoveryResult(method="timeout", detail="Timed out"),
            errors=errors,
        )


async def _audit_site_inner(
    url: str,
    domain: str,
    max_pages: int,
    delay_seconds: float,
    errors: list[str],
    progress: Callable[[str], None],
) -> SiteAuditReport:
    """Inner implementation of audit_site, wrapped with a timeout by the caller."""
    progress("Running site-wide checks...")

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        # Phase 1: Site-wide checks + seed crawl in parallel
        robots_task = check_robots(url, client)
        llms_task = check_llms_txt(url, client)
        crawl_task = extract_page(url)

        robots_result, llms_txt, seed_crawl = await asyncio.gather(
            robots_task, llms_task, crawl_task, return_exceptions=True
        )

        # Unpack results
        raw_robots: str | None = None
        if isinstance(robots_result, BaseException):
            errors.append(f"Robots check failed: {robots_result}")
            robots = RobotsReport(found=False, detail="Check failed")
        else:
            robots, raw_robots = robots_result

        if isinstance(llms_txt, BaseException):
            errors.append(f"llms.txt check failed: {llms_txt}")
            llms_txt = LlmsTxtReport(found=False, detail="Check failed")

        seed: CrawlResult | None = None
        if isinstance(seed_crawl, BaseException):
            errors.append(f"Seed crawl failed: {seed_crawl}")
        else:
            seed = seed_crawl

        # Phase 2: Discover pages
        progress("Discovering pages...")
        seed_links = None
        if seed and seed.success:
            seed_links = seed.internal_links

        discovery = await discover_pages(
            url,
            client,
            max_pages=max_pages,
            robots_txt=raw_robots,
            seed_links=seed_links,
        )

    # Phase 3: Audit seed page + batch crawl remaining pages
    pages: list[PageAudit] = []

    # Audit the seed page first
    if seed and seed.success:
        schema, content = audit_page_content(seed.html, seed.markdown)
        # Score the page-level pillar checks
        _, _, schema, content, _ = compute_scores(
            RobotsReport(found=False), LlmsTxtReport(found=False), schema, content
        )
        pages.append(PageAudit(url=url, schema_org=schema, content=content))
    elif seed and not seed.success:
        errors.append(f"Seed crawl error: {seed.error}")

    # Crawl remaining sampled pages (exclude seed which is already crawled)
    remaining_urls = [u for u in discovery.urls_sampled if u != url]
    if remaining_urls:
        progress(f"Crawling {len(remaining_urls)} additional pages...")
        crawl_results = await extract_pages(
            remaining_urls, delay_seconds=delay_seconds
        )

        for i, result in enumerate(crawl_results):
            progress(f"Auditing page {i + 2}/{len(discovery.urls_sampled)}...")
            if result.success:
                schema, content = audit_page_content(result.html, result.markdown)
                _, _, schema, content, _ = compute_scores(
                    RobotsReport(found=False), LlmsTxtReport(found=False), schema, content
                )
                pages.append(PageAudit(url=result.url, schema_org=schema, content=content))
            else:
                pages.append(PageAudit(
                    url=result.url,
                    schema_org=SchemaReport(detail="Crawl failed"),
                    content=ContentReport(detail="Crawl failed"),
                    errors=[result.error or "Unknown crawl error"],
                ))

    # Phase 4: Compute site-wide robot/llms scores
    robots, llms_txt, _, _, _ = compute_scores(
        robots, llms_txt, SchemaReport(), ContentReport()
    )

    # Phase 5: Aggregate
    pages_failed = sum(1 for p in pages if p.errors)
    agg_schema, agg_content, overall = aggregate_page_scores(pages, robots, llms_txt)

    return SiteAuditReport(
        url=url,
        domain=domain,
        overall_score=overall,
        robots=robots,
        llms_txt=llms_txt,
        schema_org=agg_schema,
        content=agg_content,
        discovery=discovery,
        pages=pages,
        pages_audited=len(pages),
        pages_failed=pages_failed,
        errors=errors,
    )
