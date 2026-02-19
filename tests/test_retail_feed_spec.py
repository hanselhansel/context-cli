"""Tests for retail feed spec compliance checker."""

from __future__ import annotations

from context_cli.core.models import (
    FeedComplianceReport,
    MarketplaceType,
    ProductData,
)
from context_cli.core.retail.feed_spec import (
    RECOMMENDED_FIELDS,
    REQUIRED_FIELDS,
    check_feed_compliance,
)


class TestRequiredFields:
    """Test that REQUIRED_FIELDS constant is correct."""

    def test_required_fields_contains_expected(self) -> None:
        expected = [
            "title",
            "description",
            "url",
            "price",
            "currency",
            "availability",
            "image_url",
            "brand",
        ]
        assert REQUIRED_FIELDS == expected

    def test_required_fields_count(self) -> None:
        assert len(REQUIRED_FIELDS) == 8


class TestRecommendedFields:
    """Test that RECOMMENDED_FIELDS constant is correct."""

    def test_recommended_fields_contains_expected(self) -> None:
        expected = [
            "reviews_count",
            "average_rating",
            "variants",
            "shipping_info",
            "category",
            "gtin",
        ]
        assert RECOMMENDED_FIELDS == expected

    def test_recommended_fields_count(self) -> None:
        assert len(RECOMMENDED_FIELDS) == 6


class TestCheckFeedCompliance:
    """Test the check_feed_compliance function."""

    def test_returns_feed_compliance_report(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = check_feed_compliance(data)
        assert isinstance(result, FeedComplianceReport)

    def test_empty_product_data(self) -> None:
        """Empty product data should have low compliance."""
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = check_feed_compliance(data)
        assert result.score >= 0.0
        assert result.score <= 10.0
        assert len(result.missing_fields) > 0
        assert result.compliance_rate < 1.0

    def test_fully_populated_product(self) -> None:
        """Product with all fields should have high compliance."""
        data = ProductData(
            title="Test Product",
            description="A great product",
            url="https://example.com/product",
            price="29.99",
            currency="USD",
            availability="InStock",
            image_urls=["https://example.com/img.jpg"],
            brand="TestBrand",
            review_count=50,
            rating=4.5,
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        # All 8 required fields present
        assert "title" in result.present_fields
        assert "description" in result.present_fields
        assert "url" in result.present_fields
        assert "price" in result.present_fields
        assert "currency" in result.present_fields
        assert "availability" in result.present_fields
        assert "image_url" in result.present_fields
        assert "brand" in result.present_fields
        assert result.compliance_rate == 1.0
        assert result.score == 10.0
        assert len(result.missing_fields) == 0

    def test_partial_fields(self) -> None:
        """Product with some fields should have proportional compliance."""
        data = ProductData(
            title="Test Product",
            description="A description",
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        assert "title" in result.present_fields
        assert "description" in result.present_fields
        assert "url" in result.present_fields
        # Missing fields should include the unprovided required ones
        assert "price" in result.missing_fields
        assert "currency" in result.missing_fields
        assert "availability" in result.missing_fields
        assert "brand" in result.missing_fields
        assert 0.0 < result.compliance_rate < 1.0
        assert 0.0 < result.score < 10.0

    def test_image_url_mapping(self) -> None:
        """image_url field maps from image_urls list (non-empty = present)."""
        data = ProductData(
            image_urls=["https://example.com/img.jpg"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        assert "image_url" in result.present_fields

    def test_image_url_missing_when_empty(self) -> None:
        """image_url field is missing when image_urls is empty."""
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = check_feed_compliance(data)
        assert "image_url" in result.missing_fields

    def test_reviews_count_mapping(self) -> None:
        """reviews_count maps from review_count field."""
        data = ProductData(
            review_count=10,
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        assert "reviews_count" in result.present_fields

    def test_average_rating_mapping(self) -> None:
        """average_rating maps from rating field."""
        data = ProductData(
            rating=4.5,
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        assert "average_rating" in result.present_fields

    def test_score_proportional_to_compliance(self) -> None:
        """Score should be proportional: score = compliance_rate * 10."""
        data = ProductData(
            title="Test",
            description="Desc",
            url="https://example.com",
            price="10",
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        expected_score = result.compliance_rate * 10.0
        assert abs(result.score - expected_score) < 0.01

    def test_score_never_exceeds_max(self) -> None:
        """Score should never exceed 10."""
        data = ProductData(
            title="Test",
            description="Desc",
            url="https://example.com",
            price="10",
            currency="USD",
            availability="InStock",
            image_urls=["img.jpg"],
            brand="Brand",
            review_count=100,
            rating=5.0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = check_feed_compliance(data)
        assert result.score <= 10.0

    def test_score_never_negative(self) -> None:
        """Score should never be negative."""
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = check_feed_compliance(data)
        assert result.score >= 0.0
