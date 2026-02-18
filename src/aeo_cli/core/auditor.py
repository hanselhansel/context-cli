"""Core audit orchestration — runs all pillar checks and computes AEO score."""

from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from aeo_cli.core.crawler import extract_page
from aeo_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)

AI_BOTS = [
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "ClaudeBot",
    "PerplexityBot",
    "Amazonbot",
    "OAI-SearchBot",
]

DEFAULT_TIMEOUT = 15


# ── Pillar 1: Robots.txt ──────────────────────────────────────────────────────


async def check_robots(url: str, client: httpx.AsyncClient) -> RobotsReport:
    """Fetch robots.txt and check AI bot access."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        resp = await client.get(robots_url, follow_redirects=True)
        if resp.status_code != 200:
            return RobotsReport(
                found=False, detail=f"robots.txt returned HTTP {resp.status_code}"
            )

        rp = RobotFileParser()
        rp.parse(resp.text.splitlines())

        bots = []
        for bot in AI_BOTS:
            allowed = rp.can_fetch(bot, "/")
            bots.append(BotAccessResult(
                bot=bot,
                allowed=allowed,
                detail="Allowed" if allowed else "Blocked by robots.txt",
            ))

        allowed_count = sum(1 for b in bots if b.allowed)
        return RobotsReport(
            found=True,
            bots=bots,
            detail=f"{allowed_count}/{len(AI_BOTS)} AI bots allowed",
        )

    except httpx.HTTPError as e:
        return RobotsReport(found=False, detail=f"Failed to fetch robots.txt: {e}")


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


def check_schema_org(html: str) -> SchemaReport:
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
    # Robots: max 25 — proportional to bots allowed
    if robots.found and robots.bots:
        allowed = sum(1 for b in robots.bots if b.allowed)
        robots.score = round(25 * allowed / len(robots.bots), 1)
    else:
        robots.score = 0

    # llms.txt: max 10
    llms_txt.score = 10 if llms_txt.found else 0

    # Schema: max 25 — reward high-value types more
    if schema_org.blocks_found > 0:
        unique_types = {s.schema_type for s in schema_org.schemas}
        # Base 8 for having any JSON-LD, +5 per unique type, capped at 25
        schema_org.score = min(25, 8 + 5 * len(unique_types))
    else:
        schema_org.score = 0

    # Content: max 40 — word count tiers + structure bonuses
    # Higher thresholds reflect that LLMs need substantial content to cite
    score = 0
    if content.word_count >= 1500:
        score = 25
    elif content.word_count >= 800:
        score = 20
    elif content.word_count >= 400:
        score = 15
    elif content.word_count >= 150:
        score = 8
    if content.has_headings:
        score += 7  # structure matters a lot for LLM extraction
    if content.has_lists:
        score += 5  # lists are highly extractable by LLMs
    if content.has_code_blocks:
        score += 3  # relevant for technical content
    content.score = min(40, score)

    overall = robots.score + llms_txt.score + schema_org.score + content.score
    return robots, llms_txt, schema_org, content, overall


# ── Orchestrator ──────────────────────────────────────────────────────────────


async def audit_url(url: str) -> AuditReport:
    """Run a full AEO audit on a URL. Returns AuditReport with all pillar scores."""
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        # Run HTTP checks and browser crawl concurrently
        robots_task = check_robots(url, client)
        llms_task = check_llms_txt(url, client)
        crawl_task = extract_page(url)

        robots, llms_txt, crawl_result = await asyncio.gather(
            robots_task, llms_task, crawl_task, return_exceptions=True
        )

    # Handle exceptions from gather
    if isinstance(robots, BaseException):
        errors.append(f"Robots check failed: {robots}")
        robots = RobotsReport(found=False, detail="Check failed")
    if isinstance(llms_txt, BaseException):
        errors.append(f"llms.txt check failed: {llms_txt}")
        llms_txt = LlmsTxtReport(found=False, detail="Check failed")
    if isinstance(crawl_result, BaseException):
        errors.append(f"Crawl failed: {crawl_result}")
        crawl_result = None

    # Run sync checks on crawl results
    html = crawl_result.html if crawl_result and crawl_result.success else ""
    markdown = crawl_result.markdown if crawl_result and crawl_result.success else ""

    if crawl_result and not crawl_result.success and crawl_result.error:
        errors.append(f"Crawl error: {crawl_result.error}")

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
