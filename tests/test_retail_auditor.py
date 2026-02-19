"""Tests for retail auditor orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_cli.core.crawler import CrawlResult
from context_cli.core.models import (
    MarketplaceType,
    ProductData,
    RetailAuditReport,
)
from context_cli.core.retail.auditor import retail_audit


@pytest.mark.asyncio
class TestRetailAudit:
    """Test the retail_audit async orchestrator."""

    async def test_returns_retail_audit_report(self) -> None:
        """retail_audit should return a RetailAuditReport."""
        mock_crawl = CrawlResult(
            url="https://www.amazon.com/dp/B123",
            html="<html><body>Product</body></html>",
            markdown="Product",
            success=True,
        )
        mock_product = ProductData(
            title="Test Product",
            marketplace=MarketplaceType.GENERIC,
        )
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_product

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
            patch(
                "context_cli.core.retail.auditor.get_parser",
                return_value=mock_parser,
            ),
        ):
            result = await retail_audit("https://www.amazon.com/dp/B123")

        assert isinstance(result, RetailAuditReport)

    async def test_sets_url_on_product_data(self) -> None:
        """Auditor should set the URL on product_data."""
        mock_crawl = CrawlResult(
            url="https://example.com/product",
            html="<html>test</html>",
            markdown="test",
            success=True,
        )
        mock_product = ProductData(marketplace=MarketplaceType.GENERIC)
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_product

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
            patch(
                "context_cli.core.retail.auditor.get_parser",
                return_value=mock_parser,
            ),
        ):
            result = await retail_audit("https://example.com/product")

        assert result.url == "https://example.com/product"
        assert result.product_data.url == "https://example.com/product"

    async def test_sets_marketplace_on_product_data(self) -> None:
        """Auditor should set marketplace on both report and product_data."""
        mock_crawl = CrawlResult(
            url="https://shopee.com/product",
            html="<html>test</html>",
            markdown="test",
            success=True,
        )
        mock_product = ProductData(marketplace=MarketplaceType.GENERIC)
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_product

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.SHOPEE,
            ),
            patch(
                "context_cli.core.retail.auditor.get_parser",
                return_value=mock_parser,
            ),
        ):
            result = await retail_audit("https://shopee.com/product")

        assert result.marketplace == MarketplaceType.SHOPEE
        assert result.product_data.marketplace == MarketplaceType.SHOPEE

    async def test_calls_parser_with_html(self) -> None:
        """Auditor should pass HTML from crawler to parser."""
        html_content = "<html><body>Product Page</body></html>"
        mock_crawl = CrawlResult(
            url="https://example.com/product",
            html=html_content,
            markdown="Product Page",
            success=True,
        )
        mock_product = ProductData(marketplace=MarketplaceType.GENERIC)
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_product

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
            patch(
                "context_cli.core.retail.auditor.get_parser",
                return_value=mock_parser,
            ),
        ):
            await retail_audit("https://example.com/product")

        mock_parser.parse.assert_called_once_with(html_content)

    async def test_crawl_failure_returns_report_with_error(self) -> None:
        """Failed crawl should return a report with errors."""
        mock_crawl = CrawlResult(
            url="https://example.com/product",
            html="",
            markdown="",
            success=False,
            error="Connection timeout",
        )

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
        ):
            result = await retail_audit("https://example.com/product")

        assert isinstance(result, RetailAuditReport)
        assert len(result.errors) > 0
        assert "Connection timeout" in result.errors[0]

    async def test_parser_exception_returns_report_with_error(self) -> None:
        """Parser exception should be caught and added to errors."""
        mock_crawl = CrawlResult(
            url="https://example.com/product",
            html="<html>test</html>",
            markdown="test",
            success=True,
        )
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = ValueError("Parse failed")

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
            patch(
                "context_cli.core.retail.auditor.get_parser",
                return_value=mock_parser,
            ),
        ):
            result = await retail_audit("https://example.com/product")

        assert isinstance(result, RetailAuditReport)
        assert len(result.errors) > 0
        assert "Parse failed" in result.errors[0]

    async def test_score_computed_from_product_data(self) -> None:
        """Score in report should come from scoring engine."""
        mock_crawl = CrawlResult(
            url="https://example.com/product",
            html="<html>test</html>",
            markdown="test",
            success=True,
        )
        mock_product = ProductData(
            title="Test Product",
            description="x" * 200,
            bullet_points=["a", "b", "c", "d", "e"],
            marketplace=MarketplaceType.GENERIC,
        )
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_product

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
            patch(
                "context_cli.core.retail.auditor.get_parser",
                return_value=mock_parser,
            ),
        ):
            result = await retail_audit("https://example.com/product")

        # Should have some positive score from content quality
        assert result.score > 0.0
        assert result.content_quality.score > 0.0

    async def test_crawl_failure_still_sets_url_and_marketplace(self) -> None:
        """Even on crawl failure, url and marketplace should be set."""
        mock_crawl = CrawlResult(
            url="https://example.com/product",
            html="",
            markdown="",
            success=False,
            error="Timeout",
        )

        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                return_value=mock_crawl,
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.AMAZON,
            ),
        ):
            result = await retail_audit("https://example.com/product")

        assert result.url == "https://example.com/product"
        assert result.marketplace == MarketplaceType.AMAZON

    async def test_crawl_exception_handled_gracefully(self) -> None:
        """If extract_page raises, auditor should handle gracefully."""
        with (
            patch(
                "context_cli.core.retail.auditor.extract_page",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Network error"),
            ),
            patch(
                "context_cli.core.retail.auditor.detect_marketplace",
                return_value=MarketplaceType.GENERIC,
            ),
        ):
            result = await retail_audit("https://example.com/product")

        assert isinstance(result, RetailAuditReport)
        assert len(result.errors) > 0
        assert "Network error" in result.errors[0]
