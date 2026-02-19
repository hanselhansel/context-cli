"""Retail audit orchestrator.

Coordinates the end-to-end retail product audit flow:
1. Detect marketplace from URL
2. Get appropriate parser
3. Crawl the product page
4. Parse HTML into structured product data
5. Score across all 5 retail pillars
6. Return comprehensive RetailAuditReport
"""

from __future__ import annotations

from context_cli.core.crawler import extract_page
from context_cli.core.models import (
    RetailAuditReport,
)
from context_cli.core.retail.parsers import detect_marketplace, get_parser
from context_cli.core.retail.scoring import compute_retail_score


async def retail_audit(url: str) -> RetailAuditReport:
    """Run a full retail AI-readiness audit on a product URL.

    Orchestrates marketplace detection, page crawling, HTML parsing,
    and 5-pillar scoring. Errors are captured in the report rather
    than raised.

    Args:
        url: The product page URL to audit.

    Returns:
        RetailAuditReport with scores and any errors encountered.
    """
    marketplace = detect_marketplace(url)

    # Attempt to crawl the page
    try:
        crawl_result = await extract_page(url)
    except Exception as exc:
        return RetailAuditReport(
            url=url,
            marketplace=marketplace,
            errors=[f"Crawl error: {exc}"],
        )

    # Handle crawl failure
    if not crawl_result.success:
        error_msg = crawl_result.error or "Unknown crawl failure"
        return RetailAuditReport(
            url=url,
            marketplace=marketplace,
            errors=[f"Crawl failed: {error_msg}"],
        )

    # Parse HTML into product data
    try:
        parser = get_parser(marketplace)
        product_data = parser.parse(crawl_result.html)
    except Exception as exc:
        return RetailAuditReport(
            url=url,
            marketplace=marketplace,
            errors=[f"Parse error: {exc}"],
        )

    # Set URL and marketplace on product data
    product_data.url = url
    product_data.marketplace = marketplace

    # Score the product data
    report = compute_retail_score(product_data)

    return report
