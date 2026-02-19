"""Tests for retail CLI command and MCP tool."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from aeo_cli.core.models import (
    ContentQualityReport,
    FeedComplianceReport,
    MarketplaceType,
    ProductData,
    ProductSchemaReport,
    RetailAuditReport,
    SocialProofReport,
    VisualAssetsReport,
)
from aeo_cli.main import app
from aeo_cli.server import retail_audit_tool as _retail_tool_obj

runner = CliRunner()


def _make_retail_report(
    url: str = "https://www.amazon.com/dp/B09V3KXJPB",
    marketplace: MarketplaceType = MarketplaceType.AMAZON,
    score: float = 72.5,
) -> RetailAuditReport:
    """Create a realistic RetailAuditReport for testing."""
    return RetailAuditReport(
        url=url,
        marketplace=marketplace,
        score=score,
        product_schema=ProductSchemaReport(
            score=18.0,
            has_product_schema=True,
            has_offer=True,
            has_aggregate_rating=True,
            missing_fields=["gtin", "mpn"],
        ),
        content_quality=ContentQualityReport(
            score=22.5,
            bullet_count=5,
            description_length=850,
            has_aplus=True,
            has_spec_chart=True,
        ),
        visual_assets=VisualAssetsReport(
            score=12.0,
            image_count=7,
            images_with_alt=5,
            has_video=True,
        ),
        social_proof=SocialProofReport(
            score=15.0,
            review_count=1247,
            rating=4.3,
            has_qa=True,
        ),
        feed_compliance=FeedComplianceReport(
            score=5.0,
            present_fields=["title", "price", "image", "availability"],
            missing_fields=["gtin", "brand"],
            compliance_rate=0.67,
        ),
        product_data=ProductData(
            title="Wireless Bluetooth Headphones",
            description="Premium noise-cancelling headphones with 30hr battery",
            price="$79.99",
            currency="USD",
            availability="InStock",
            image_urls=[
                "https://images.example.com/1.jpg",
                "https://images.example.com/2.jpg",
            ],
            brand="AudioBrand",
            rating=4.3,
            review_count=1247,
            bullet_points=[
                "Active noise cancellation",
                "30-hour battery life",
                "Bluetooth 5.2",
                "Foldable design",
                "Built-in microphone",
            ],
            specifications={"weight": "250g", "driver_size": "40mm"},
            has_video=True,
            has_aplus_content=True,
            qa_count=42,
            marketplace=MarketplaceType.AMAZON,
            url=url,
            alt_texts=["Front view", "Side view", "Folded"],
        ),
        errors=[],
    )


# ── CLI Registration Tests ──────────────────────────────────────────────────


class TestRetailCLIRegistration:
    """Test that the retail command is registered and shows in help."""

    def test_retail_command_in_help(self) -> None:
        """The 'retail' command should appear in --help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "retail" in result.output

    def test_retail_help(self) -> None:
        """The 'retail' subcommand should have its own --help."""
        result = runner.invoke(app, ["retail", "--help"])
        assert result.exit_code == 0
        assert "url" in result.output.lower()
        assert "--json" in result.output
        assert "--verbose" in result.output


# ── CLI JSON Output Tests ────────────────────────────────────────────────────


class TestRetailCLIJsonOutput:
    """Test JSON output from the retail command."""

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_json_output_valid(self, mock_audit: AsyncMock) -> None:
        """--json should produce valid JSON with expected fields."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["url"] == "https://www.amazon.com/dp/B09V3KXJPB"
        assert data["marketplace"] == "amazon"
        assert data["score"] == 72.5
        assert "product_schema" in data
        assert "content_quality" in data
        assert "visual_assets" in data
        assert "social_proof" in data
        assert "feed_compliance" in data
        assert "product_data" in data

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_json_output_pillar_scores(self, mock_audit: AsyncMock) -> None:
        """JSON output should include correct per-pillar scores."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "--json"]
        )
        data = json.loads(result.output)
        assert data["product_schema"]["score"] == 18.0
        assert data["content_quality"]["score"] == 22.5
        assert data["visual_assets"]["score"] == 12.0
        assert data["social_proof"]["score"] == 15.0
        assert data["feed_compliance"]["score"] == 5.0

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_json_output_with_errors(self, mock_audit: AsyncMock) -> None:
        """JSON output should include errors list."""
        report = _make_retail_report()
        report.errors = ["Could not parse specifications"]
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://example.com/product", "--json"]
        )
        data = json.loads(result.output)
        assert data["errors"] == ["Could not parse specifications"]


# ── CLI Rich Output Tests ────────────────────────────────────────────────────


class TestRetailCLIRichOutput:
    """Test Rich (human-readable) output from the retail command."""

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_rich_output_shows_score(self, mock_audit: AsyncMock) -> None:
        """Rich output should show URL, marketplace, and overall score."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB"]
        )
        assert result.exit_code == 0
        assert "amazon" in result.output.lower()
        assert "72.5" in result.output
        assert "/100" in result.output

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_rich_output_shows_pillar_scores(self, mock_audit: AsyncMock) -> None:
        """Rich output should show per-pillar score breakdown."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB"]
        )
        assert "18.0" in result.output  # product schema
        assert "/25" in result.output
        assert "22.5" in result.output  # content quality
        assert "/30" in result.output
        assert "12.0" in result.output  # visual assets
        assert "/15" in result.output
        assert "15.0" in result.output  # social proof
        assert "/20" in result.output
        assert "5.0" in result.output  # feed compliance
        assert "/10" in result.output

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_rich_output_generic_marketplace(self, mock_audit: AsyncMock) -> None:
        """Rich output should handle generic marketplace type."""
        report = _make_retail_report(
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
            score=45.0,
        )
        mock_audit.return_value = report

        result = runner.invoke(app, ["retail", "https://example.com/product"])
        assert result.exit_code == 0
        assert "generic" in result.output.lower()
        assert "45.0" in result.output


# ── CLI Verbose Output Tests ─────────────────────────────────────────────────


class TestRetailCLIVerboseOutput:
    """Test verbose output with per-pillar details."""

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_verbose_shows_bullet_count(self, mock_audit: AsyncMock) -> None:
        """Verbose mode should show content details like bullet count."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "--verbose"]
        )
        assert result.exit_code == 0
        assert "5" in result.output  # bullet_count
        assert "850" in result.output  # description_length

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_verbose_shows_image_info(self, mock_audit: AsyncMock) -> None:
        """Verbose mode should show visual assets details."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "-v"]
        )
        assert result.exit_code == 0
        assert "7" in result.output  # image_count
        assert "5" in result.output  # images_with_alt

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_verbose_shows_review_info(self, mock_audit: AsyncMock) -> None:
        """Verbose mode should show social proof details."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "--verbose"]
        )
        assert result.exit_code == 0
        assert "1247" in result.output  # review_count
        assert "4.3" in result.output  # rating

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_verbose_shows_schema_details(self, mock_audit: AsyncMock) -> None:
        """Verbose mode should show schema analysis details."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "--verbose"]
        )
        assert result.exit_code == 0
        # Should mention schema presence
        assert "product" in result.output.lower() or "schema" in result.output.lower()

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_verbose_shows_feed_compliance(self, mock_audit: AsyncMock) -> None:
        """Verbose mode should show feed compliance details."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = runner.invoke(
            app, ["retail", "https://www.amazon.com/dp/B09V3KXJPB", "--verbose"]
        )
        assert result.exit_code == 0
        assert "67" in result.output  # compliance_rate shown as percentage


# ── CLI Error Handling Tests ─────────────────────────────────────────────────


class TestRetailCLIErrorHandling:
    """Test error handling in the retail CLI command."""

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_error_exits_with_code_1(self, mock_audit: AsyncMock) -> None:
        """Audit errors should produce exit code 1."""
        mock_audit.side_effect = RuntimeError("Connection refused")

        result = runner.invoke(app, ["retail", "https://bad.example.com/product"])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_error_message_displayed(self, mock_audit: AsyncMock) -> None:
        """Error message should be displayed to user."""
        mock_audit.side_effect = ValueError("Invalid product URL")

        result = runner.invoke(app, ["retail", "https://bad.example.com"])
        assert result.exit_code == 1
        assert "Invalid product URL" in result.output

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_report_with_errors_still_succeeds(self, mock_audit: AsyncMock) -> None:
        """Report with non-fatal errors should still exit 0."""
        report = _make_retail_report()
        report.errors = ["Could not parse specifications"]
        mock_audit.return_value = report

        result = runner.invoke(app, ["retail", "https://example.com/product"])
        assert result.exit_code == 0

    @patch("aeo_cli.cli.retail.retail_audit")
    def test_json_error_exits_with_code_1(self, mock_audit: AsyncMock) -> None:
        """Errors in --json mode should also exit with code 1."""
        mock_audit.side_effect = RuntimeError("Timeout")

        result = runner.invoke(
            app, ["retail", "https://bad.example.com", "--json"]
        )
        assert result.exit_code == 1


# ── MCP Tool Tests ───────────────────────────────────────────────────────────

# FastMCP 2.x wraps @mcp.tool functions in a FunctionTool object.
# The underlying async function is accessible via .fn

_retail_fn = _retail_tool_obj.fn if hasattr(_retail_tool_obj, "fn") else _retail_tool_obj


class TestRetailMCPTool:
    """Test the retail_audit MCP tool in server.py."""

    @pytest.mark.asyncio
    @patch("aeo_cli.core.retail.auditor.retail_audit")
    async def test_mcp_tool_returns_dict(self, mock_audit: AsyncMock) -> None:
        """MCP tool should return a dict with correct structure."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = await _retail_fn(url="https://www.amazon.com/dp/B09V3KXJPB")
        assert isinstance(result, dict)
        assert result["url"] == "https://www.amazon.com/dp/B09V3KXJPB"
        assert result["marketplace"] == "amazon"
        assert result["score"] == 72.5
        assert "product_schema" in result
        assert "content_quality" in result
        assert "visual_assets" in result
        assert "social_proof" in result
        assert "feed_compliance" in result

    @pytest.mark.asyncio
    @patch("aeo_cli.core.retail.auditor.retail_audit")
    async def test_mcp_tool_error_handling(self, mock_audit: AsyncMock) -> None:
        """MCP tool should propagate errors from retail_audit."""
        mock_audit.side_effect = RuntimeError("Network error")

        with pytest.raises(RuntimeError, match="Network error"):
            await _retail_fn(url="https://bad.example.com")

    @pytest.mark.asyncio
    @patch("aeo_cli.core.retail.auditor.retail_audit")
    async def test_mcp_tool_pillar_scores(self, mock_audit: AsyncMock) -> None:
        """MCP tool should include correct pillar scores in response."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = await _retail_fn(url="https://www.amazon.com/dp/B09V3KXJPB")
        assert result["product_schema"]["score"] == 18.0
        assert result["content_quality"]["score"] == 22.5
        assert result["visual_assets"]["score"] == 12.0
        assert result["social_proof"]["score"] == 15.0
        assert result["feed_compliance"]["score"] == 5.0

    @pytest.mark.asyncio
    @patch("aeo_cli.core.retail.auditor.retail_audit")
    async def test_mcp_tool_product_data(self, mock_audit: AsyncMock) -> None:
        """MCP tool should include parsed product data."""
        report = _make_retail_report()
        mock_audit.return_value = report

        result = await _retail_fn(url="https://www.amazon.com/dp/B09V3KXJPB")
        pd = result["product_data"]
        assert pd["title"] == "Wireless Bluetooth Headphones"
        assert pd["brand"] == "AudioBrand"
        assert pd["rating"] == 4.3
        assert pd["review_count"] == 1247


# ── Model Tests ──────────────────────────────────────────────────────────────


class TestRetailModels:
    """Test that retail models work correctly."""

    def test_marketplace_type_values(self) -> None:
        """MarketplaceType enum should have all expected values."""
        assert MarketplaceType.AMAZON == "amazon"
        assert MarketplaceType.SHOPEE == "shopee"
        assert MarketplaceType.LAZADA == "lazada"
        assert MarketplaceType.TOKOPEDIA == "tokopedia"
        assert MarketplaceType.TIKTOK_SHOP == "tiktok_shop"
        assert MarketplaceType.BLIBLI == "blibli"
        assert MarketplaceType.ZALORA == "zalora"
        assert MarketplaceType.GENERIC == "generic"

    def test_retail_audit_report_defaults(self) -> None:
        """RetailAuditReport should have sensible defaults."""
        report = RetailAuditReport(
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
        )
        assert report.score == 0.0
        assert report.product_schema.score == 0.0
        assert report.content_quality.score == 0.0
        assert report.visual_assets.score == 0.0
        assert report.social_proof.score == 0.0
        assert report.feed_compliance.score == 0.0
        assert report.errors == []

    def test_retail_audit_report_json_roundtrip(self) -> None:
        """RetailAuditReport should survive JSON serialization roundtrip."""
        report = _make_retail_report()
        json_str = report.model_dump_json()
        restored = RetailAuditReport.model_validate_json(json_str)
        assert restored.url == report.url
        assert restored.marketplace == report.marketplace
        assert restored.score == report.score
        assert restored.product_schema.score == report.product_schema.score

    def test_product_data_defaults(self) -> None:
        """ProductData should have sensible defaults."""
        pd = ProductData()
        assert pd.title is None
        assert pd.image_urls == []
        assert pd.bullet_points == []
        assert pd.specifications == {}
        assert pd.has_video is False
        assert pd.marketplace == MarketplaceType.GENERIC
