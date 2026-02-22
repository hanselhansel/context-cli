"""Core audit orchestration — runs all pillar checks and computes Readiness Score."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from urllib.parse import urlparse

import httpx

from context_cli.core.checks.agents_md import check_agents_md
from context_cli.core.checks.content import check_content
from context_cli.core.checks.content_usage import check_content_usage
from context_cli.core.checks.eeat import check_eeat
from context_cli.core.checks.llms_txt import check_llms_txt
from context_cli.core.checks.markdown_accept import check_markdown_accept
from context_cli.core.checks.mcp_endpoint import check_mcp_endpoint
from context_cli.core.checks.nlweb import check_nlweb
from context_cli.core.checks.robots import DEFAULT_TIMEOUT, check_robots
from context_cli.core.checks.rsl import check_rsl
from context_cli.core.checks.schema import check_schema_org
from context_cli.core.checks.semantic_html import check_semantic_html
from context_cli.core.checks.x402 import check_x402
from context_cli.core.crawler import CrawlResult, extract_page, extract_pages
from context_cli.core.discovery import discover_pages
from context_cli.core.models import (
    AgentReadinessReport,
    AgentsMdReport,
    AuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    MarkdownAcceptReport,
    McpEndpointReport,
    NlwebReport,
    PageAudit,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
    SiteAuditReport,
    X402Report,
)
from context_cli.core.scoring import compute_lint_results, compute_scores

# ── Orchestrator ──────────────────────────────────────────────────────────────


def audit_page_content(html: str, markdown: str) -> tuple[SchemaReport, ContentReport]:
    """Run page-specific checks (schema + content) on pre-crawled data."""
    return check_schema_org(html), check_content(markdown)


def _page_weight(url: str) -> int:
    """Return a weight for a page based on URL depth.

    Shallower pages (homepage, top-level sections) are more representative of a
    site's LLM readiness and therefore receive higher weight in aggregation.

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

    Content (40pts) and Schema (25pts) use weighted averages -- shallower pages
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


def _build_agent_readiness(
    agents_md_result: AgentsMdReport | BaseException,
    md_accept_result: MarkdownAcceptReport | BaseException,
    mcp_result: McpEndpointReport | BaseException,
    semantic_html_result: object,
    x402_result: X402Report | BaseException,
    nlweb_result: NlwebReport | BaseException,
    errors: list[str],
) -> AgentReadinessReport:
    """Build AgentReadinessReport from individual check results, handling errors."""
    if isinstance(agents_md_result, BaseException):
        errors.append(f"AGENTS.md check failed: {agents_md_result}")
        agents_md_result = AgentsMdReport()
    if isinstance(md_accept_result, BaseException):
        errors.append(f"Markdown accept check failed: {md_accept_result}")
        md_accept_result = MarkdownAcceptReport()
    if isinstance(mcp_result, BaseException):
        errors.append(f"MCP endpoint check failed: {mcp_result}")
        mcp_result = McpEndpointReport()
    if isinstance(x402_result, BaseException):
        errors.append(f"x402 check failed: {x402_result}")
        x402_result = X402Report()
    if isinstance(nlweb_result, BaseException):
        errors.append(f"NLWeb check failed: {nlweb_result}")
        nlweb_result = NlwebReport()
    # semantic_html is sync, should not be BaseException from gather
    from context_cli.core.models import SemanticHtmlReport
    if not isinstance(semantic_html_result, SemanticHtmlReport):
        semantic_html_result = SemanticHtmlReport()

    total_score = (
        agents_md_result.score
        + md_accept_result.score
        + mcp_result.score
        + semantic_html_result.score
        + x402_result.score
        + nlweb_result.score
    )

    return AgentReadinessReport(
        agents_md=agents_md_result,
        markdown_accept=md_accept_result,
        mcp_endpoint=mcp_result,
        semantic_html=semantic_html_result,
        x402=x402_result,
        nlweb=nlweb_result,
        score=total_score,
        detail=f"Agent readiness: {total_score}/20",
    )


async def audit_url(
    url: str, *, timeout: int = DEFAULT_TIMEOUT, bots: list[str] | None = None
) -> AuditReport:
    """Run a full readiness lint on a single URL. Returns AuditReport."""
    errors: list[str] = []
    raw_robots: str | None = None
    content_usage_result = None

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # Run HTTP checks and browser crawl concurrently
        robots_task = check_robots(url, client, bots=bots)
        llms_task = check_llms_txt(url, client)
        content_usage_task = check_content_usage(url, client)
        crawl_task = extract_page(url)

        # Agent readiness async checks
        agents_md_task = check_agents_md(url, client)
        markdown_accept_task = check_markdown_accept(url, client)
        mcp_endpoint_task = check_mcp_endpoint(url, client)
        x402_task = check_x402(url, client)
        nlweb_task = check_nlweb(url, client)

        (
            robots_result, llms_txt, cu_result, crawl_result,
            agents_md_result, md_accept_result, mcp_result,
            x402_result, nlweb_result,
        ) = await asyncio.gather(
            robots_task, llms_task, content_usage_task, crawl_task,
            agents_md_task, markdown_accept_task, mcp_endpoint_task,
            x402_task, nlweb_task,
            return_exceptions=True,
        )

    # Handle exceptions from gather
    if isinstance(robots_result, BaseException):
        errors.append(f"Robots check failed: {robots_result}")
        robots = RobotsReport(found=False, detail="Check failed")
    else:
        robots, raw_robots = robots_result  # destructure tuple

    if isinstance(llms_txt, BaseException):
        errors.append(f"llms.txt check failed: {llms_txt}")
        llms_txt = LlmsTxtReport(found=False, detail="Check failed")

    if isinstance(cu_result, BaseException):
        errors.append(f"Content-Usage check failed: {cu_result}")
    else:
        content_usage_result = cu_result

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

    # Sync agent readiness check (needs HTML)
    semantic_html_result = check_semantic_html(html)

    # Build agent readiness report
    agent_readiness = _build_agent_readiness(
        agents_md_result, md_accept_result, mcp_result,
        semantic_html_result, x402_result, nlweb_result, errors,
    )

    # Token waste metrics
    raw_html_chars = len(html) if html else 0
    clean_md_chars = len(markdown) if markdown else 0
    raw_tokens = raw_html_chars // 4
    clean_tokens = clean_md_chars // 4
    waste_pct = (
        (raw_tokens - clean_tokens) / raw_tokens * 100
    ) if raw_tokens > 0 else 0.0
    content.raw_html_chars = raw_html_chars
    content.clean_markdown_chars = clean_md_chars
    content.estimated_raw_tokens = raw_tokens
    content.estimated_clean_tokens = clean_tokens
    content.context_waste_pct = round(waste_pct, 1)

    # Informational signals (not scored)
    rsl_report = check_rsl(raw_robots)
    domain = urlparse(url).netloc
    eeat_report = check_eeat(html, base_domain=domain)

    # Compute scores
    robots, llms_txt, schema_org, content, overall = compute_scores(
        robots, llms_txt, schema_org, content
    )

    # Compute lint results
    lint_result = compute_lint_results(robots, llms_txt, schema_org, content)

    return AuditReport(
        url=url,
        overall_score=overall,
        robots=robots,
        llms_txt=llms_txt,
        schema_org=schema_org,
        content=content,
        lint_result=lint_result,
        rsl=rsl_report,
        content_usage=content_usage_result,
        eeat=eeat_report,
        agent_readiness=agent_readiness,
        errors=errors,
    )


SITE_AUDIT_TIMEOUT: int = 90


async def audit_site(
    url: str,
    *,
    max_pages: int = 10,
    delay_seconds: float = 1.0,
    progress_callback: Callable[[str], None] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    bots: list[str] | None = None,
) -> SiteAuditReport:
    """Run a multi-page readiness lint."""
    errors: list[str] = []
    domain = urlparse(url).netloc

    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    try:
        return await asyncio.wait_for(
            _audit_site_inner(
                url, domain, max_pages, delay_seconds, errors, _progress,
                timeout, bots=bots,
            ),
            timeout=SITE_AUDIT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        errors.append(
            f"Audit timed out after {SITE_AUDIT_TIMEOUT}s,"
            " returning partial results"
        )
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
    timeout: int = DEFAULT_TIMEOUT,
    *,
    bots: list[str] | None = None,
) -> SiteAuditReport:
    """Inner implementation of audit_site."""
    progress("Running site-wide checks...")

    content_usage_result = None

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True
    ) as client:
        # Phase 1: Site-wide checks + seed crawl in parallel
        robots_task = check_robots(url, client, bots=bots)
        llms_task = check_llms_txt(url, client)
        content_usage_task = check_content_usage(url, client)
        crawl_task = extract_page(url)

        # Agent readiness async checks (site-wide, on seed page)
        agents_md_task = check_agents_md(url, client)
        markdown_accept_task = check_markdown_accept(url, client)
        mcp_endpoint_task = check_mcp_endpoint(url, client)
        x402_task = check_x402(url, client)
        nlweb_task = check_nlweb(url, client)

        (
            robots_result, llms_txt, cu_result, seed_crawl,
            agents_md_result, md_accept_result, mcp_result,
            x402_result, nlweb_result,
        ) = await asyncio.gather(
            robots_task, llms_task, content_usage_task, crawl_task,
            agents_md_task, markdown_accept_task, mcp_endpoint_task,
            x402_task, nlweb_task,
            return_exceptions=True,
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

        if isinstance(cu_result, BaseException):
            errors.append(f"Content-Usage check failed: {cu_result}")
        else:
            content_usage_result = cu_result

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

    # Semantic HTML sync check on seed page HTML
    seed_html = seed.html if seed and seed.success else ""
    semantic_html_result = check_semantic_html(seed_html)

    # Build agent readiness report
    agent_readiness = _build_agent_readiness(
        agents_md_result, md_accept_result, mcp_result,
        semantic_html_result, x402_result, nlweb_result, errors,
    )

    # Phase 3: Audit seed page + batch crawl remaining pages
    pages: list[PageAudit] = []

    # Audit the seed page first
    if seed and seed.success:
        schema, content = audit_page_content(seed.html, seed.markdown)
        # Score the page-level pillar checks
        _, _, schema, content, _ = compute_scores(
            RobotsReport(found=False), LlmsTxtReport(found=False),
            schema, content,
        )
        pages.append(
            PageAudit(url=url, schema_org=schema, content=content)
        )
    elif seed and not seed.success:
        errors.append(f"Seed crawl error: {seed.error}")

    # Crawl remaining sampled pages
    remaining_urls = [u for u in discovery.urls_sampled if u != url]
    if remaining_urls:
        progress(f"Crawling {len(remaining_urls)} additional pages...")
        crawl_results = await extract_pages(
            remaining_urls, delay_seconds=delay_seconds
        )

        for i, result in enumerate(crawl_results):
            progress(
                f"Auditing page {i + 2}/{len(discovery.urls_sampled)}..."
            )
            if result.success:
                schema, content = audit_page_content(
                    result.html, result.markdown
                )
                _, _, schema, content, _ = compute_scores(
                    RobotsReport(found=False),
                    LlmsTxtReport(found=False),
                    schema, content,
                )
                pages.append(
                    PageAudit(
                        url=result.url,
                        schema_org=schema,
                        content=content,
                    )
                )
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
    agg_schema, agg_content, overall = aggregate_page_scores(
        pages, robots, llms_txt
    )

    # Informational signals from seed page
    rsl_report = check_rsl(raw_robots)
    eeat_report = check_eeat(seed_html, base_domain=domain)

    return SiteAuditReport(
        url=url,
        domain=domain,
        overall_score=overall,
        robots=robots,
        llms_txt=llms_txt,
        schema_org=agg_schema,
        content=agg_content,
        rsl=rsl_report,
        content_usage=content_usage_result,
        eeat=eeat_report,
        agent_readiness=agent_readiness,
        discovery=discovery,
        pages=pages,
        pages_audited=len(pages),
        pages_failed=pages_failed,
        errors=errors,
    )
