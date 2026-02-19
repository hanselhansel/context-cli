"""Tests for retail scoring engine."""

from __future__ import annotations

from context_cli.core.models import (
    ContentQualityReport,
    FeedComplianceReport,
    MarketplaceType,
    ProductData,
    ProductSchemaReport,
    RetailAuditReport,
    SocialProofReport,
    VisualAssetsReport,
)
from context_cli.core.retail.scoring import (
    compute_retail_score,
    score_content_quality,
    score_feed_compliance,
    score_product_schema,
    score_social_proof,
    score_visual_assets,
)

# ── Product Schema Scoring (max 25) ────────────────────────────────────────


class TestScoreProductSchema:
    """Test score_product_schema function."""

    def test_returns_product_schema_report(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_product_schema(data)
        assert isinstance(result, ProductSchemaReport)

    def test_no_schema_org_yields_zero(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_product_schema(data)
        assert result.score == 0.0
        assert result.has_product_schema is False
        assert result.has_offer is False
        assert result.has_aggregate_rating is False

    def test_product_schema_gives_10_points(self) -> None:
        data = ProductData(
            schema_org={"@type": "Product", "name": "Test"},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert result.has_product_schema is True
        assert result.score >= 10.0

    def test_product_with_offer_gives_18_points(self) -> None:
        data = ProductData(
            schema_org={
                "@type": "Product",
                "name": "Test",
                "offers": {"@type": "Offer", "price": "29.99"},
            },
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert result.has_product_schema is True
        assert result.has_offer is True
        assert result.score >= 18.0

    def test_full_schema_gives_25_points(self) -> None:
        data = ProductData(
            schema_org={
                "@type": "Product",
                "name": "Test",
                "offers": {"@type": "Offer", "price": "29.99"},
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": "4.5",
                },
            },
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert result.has_product_schema is True
        assert result.has_offer is True
        assert result.has_aggregate_rating is True
        assert result.score == 25.0

    def test_missing_fields_tracked(self) -> None:
        data = ProductData(
            schema_org={"@type": "Product", "name": "Test"},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert "offers" in result.missing_fields
        assert "aggregateRating" in result.missing_fields

    def test_score_never_exceeds_25(self) -> None:
        data = ProductData(
            schema_org={
                "@type": "Product",
                "name": "Test",
                "offers": {"@type": "Offer"},
                "aggregateRating": {"@type": "AggregateRating"},
            },
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert result.score <= 25.0

    def test_score_never_negative(self) -> None:
        data = ProductData(
            schema_org={},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert result.score >= 0.0

    def test_product_type_in_list(self) -> None:
        """Schema with @type as list containing Product."""
        data = ProductData(
            schema_org={"@type": ["Product", "Thing"], "name": "Test"},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_product_schema(data)
        assert result.has_product_schema is True


# ── Content Quality Scoring (max 30) ───────────────────────────────────────


class TestScoreContentQuality:
    """Test score_content_quality function."""

    def test_returns_content_quality_report(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_content_quality(data)
        assert isinstance(result, ContentQualityReport)

    def test_empty_data_yields_zero(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_content_quality(data)
        assert result.score == 0.0
        assert result.bullet_count == 0
        assert result.description_length == 0
        assert result.has_aplus is False
        assert result.has_spec_chart is False

    def test_5_bullets_gives_full_bullet_score(self) -> None:
        data = ProductData(
            bullet_points=["a", "b", "c", "d", "e"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.bullet_count == 5
        # 10pts for >= 5 bullets
        assert result.score >= 10.0

    def test_3_bullets_gives_partial_score(self) -> None:
        data = ProductData(
            bullet_points=["a", "b", "c"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.bullet_count == 3
        # Partial: 3/5 * 10 = 6.0
        assert result.score == 6.0

    def test_description_200_chars_gives_full_score(self) -> None:
        data = ProductData(
            description="x" * 200,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.description_length == 200
        # 10pts for >= 200 chars
        assert result.score >= 10.0

    def test_description_100_chars_gives_partial(self) -> None:
        data = ProductData(
            description="x" * 100,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.description_length == 100
        # Partial: 100/200 * 10 = 5.0
        assert result.score == 5.0

    def test_aplus_gives_5_points(self) -> None:
        data = ProductData(
            has_aplus_content=True,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.has_aplus is True
        assert result.score >= 5.0

    def test_spec_chart_gives_5_points(self) -> None:
        data = ProductData(
            specifications={"color": "red", "size": "large"},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.has_spec_chart is True
        assert result.score >= 5.0

    def test_full_content_gives_30_points(self) -> None:
        data = ProductData(
            bullet_points=["a", "b", "c", "d", "e"],
            description="x" * 200,
            has_aplus_content=True,
            specifications={"color": "red"},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.score == 30.0

    def test_score_never_exceeds_30(self) -> None:
        data = ProductData(
            bullet_points=["a"] * 10,
            description="x" * 500,
            has_aplus_content=True,
            specifications={"a": "b", "c": "d"},
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.score <= 30.0

    def test_score_never_negative(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_content_quality(data)
        assert result.score >= 0.0

    def test_zero_bullets_zero_bullet_score(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_content_quality(data)
        assert result.bullet_count == 0

    def test_more_than_5_bullets_capped(self) -> None:
        """More than 5 bullets still gives max 10 points."""
        data = ProductData(
            bullet_points=["a"] * 8,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_content_quality(data)
        assert result.bullet_count == 8
        # Still only 10 pts max for bullets
        assert result.score == 10.0


# ── Visual Assets Scoring (max 15) ─────────────────────────────────────────


class TestScoreVisualAssets:
    """Test score_visual_assets function."""

    def test_returns_visual_assets_report(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_visual_assets(data)
        assert isinstance(result, VisualAssetsReport)

    def test_no_images_yields_zero(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_visual_assets(data)
        assert result.score == 0.0
        assert result.image_count == 0
        assert result.images_with_alt == 0
        assert result.has_video is False

    def test_5_images_gives_full_image_score(self) -> None:
        data = ProductData(
            image_urls=["img1", "img2", "img3", "img4", "img5"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.image_count == 5
        assert result.score >= 8.0

    def test_3_images_gives_partial_score(self) -> None:
        data = ProductData(
            image_urls=["img1", "img2", "img3"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.image_count == 3
        # Partial: 3/5 * 8 = 4.8
        assert abs(result.score - 4.8) < 0.01

    def test_alt_text_coverage(self) -> None:
        data = ProductData(
            image_urls=["img1", "img2", "img3", "img4"],
            alt_texts=["alt1", "alt2"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.images_with_alt == 2
        # 4 pts max for alt text, 2/4 coverage = 2.0
        expected_alt_score = (2 / 4) * 4.0
        # Total = image_score + alt_score
        image_score = min(4 / 5, 1.0) * 8.0  # 6.4
        assert abs(result.score - (image_score + expected_alt_score)) < 0.01

    def test_full_alt_text_coverage(self) -> None:
        data = ProductData(
            image_urls=["img1", "img2"],
            alt_texts=["alt1", "alt2"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.images_with_alt == 2
        # Full alt coverage for 2 images

    def test_video_gives_3_points(self) -> None:
        data = ProductData(
            has_video=True,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.has_video is True
        assert result.score >= 3.0

    def test_full_visual_assets(self) -> None:
        data = ProductData(
            image_urls=["img1", "img2", "img3", "img4", "img5"],
            alt_texts=["a1", "a2", "a3", "a4", "a5"],
            has_video=True,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.score == 15.0

    def test_score_never_exceeds_15(self) -> None:
        data = ProductData(
            image_urls=["img"] * 20,
            alt_texts=["alt"] * 20,
            has_video=True,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        assert result.score <= 15.0

    def test_score_never_negative(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_visual_assets(data)
        assert result.score >= 0.0

    def test_alt_texts_more_than_images_capped(self) -> None:
        """Alt texts count shouldn't exceed image count."""
        data = ProductData(
            image_urls=["img1", "img2"],
            alt_texts=["a1", "a2", "a3", "a4"],
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_visual_assets(data)
        # images_with_alt capped at image_count
        assert result.images_with_alt == 2


# ── Social Proof Scoring (max 20) ──────────────────────────────────────────


class TestScoreSocialProof:
    """Test score_social_proof function."""

    def test_returns_social_proof_report(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_social_proof(data)
        assert isinstance(result, SocialProofReport)

    def test_no_social_proof_yields_zero(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_social_proof(data)
        assert result.score == 0.0
        assert result.review_count is None
        assert result.rating is None
        assert result.has_qa is False

    def test_10_reviews_gives_full_review_score(self) -> None:
        data = ProductData(
            review_count=10,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.review_count == 10
        assert result.score >= 10.0

    def test_5_reviews_gives_partial(self) -> None:
        data = ProductData(
            review_count=5,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.review_count == 5
        # 5/10 * 10 = 5.0
        assert result.score == 5.0

    def test_zero_reviews_gives_zero(self) -> None:
        data = ProductData(
            review_count=0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.score == 0.0

    def test_rating_4_gives_full_rating_score(self) -> None:
        data = ProductData(
            rating=4.0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.rating == 4.0
        assert result.score >= 5.0

    def test_rating_3_gives_partial(self) -> None:
        data = ProductData(
            rating=3.0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.rating == 3.0
        # 3.0/4.0 * 5 = 3.75
        assert abs(result.score - 3.75) < 0.01

    def test_rating_above_4_capped(self) -> None:
        data = ProductData(
            rating=5.0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        # Still max 5 pts for rating
        assert result.score == 5.0

    def test_qa_gives_5_points(self) -> None:
        data = ProductData(
            qa_count=5,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.has_qa is True
        assert result.score >= 5.0

    def test_qa_count_zero_no_qa(self) -> None:
        data = ProductData(
            qa_count=0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.has_qa is False

    def test_full_social_proof(self) -> None:
        data = ProductData(
            review_count=10,
            rating=4.0,
            qa_count=3,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.score == 20.0

    def test_score_never_exceeds_20(self) -> None:
        data = ProductData(
            review_count=1000,
            rating=5.0,
            qa_count=100,
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_social_proof(data)
        assert result.score <= 20.0

    def test_score_never_negative(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_social_proof(data)
        assert result.score >= 0.0


# ── Feed Compliance Scoring (max 10) ───────────────────────────────────────


class TestScoreFeedCompliance:
    """Test score_feed_compliance function (delegates to feed_spec)."""

    def test_returns_feed_compliance_report(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_feed_compliance(data)
        assert isinstance(result, FeedComplianceReport)

    def test_empty_data_low_score(self) -> None:
        data = ProductData(marketplace=MarketplaceType.GENERIC)
        result = score_feed_compliance(data)
        assert result.score <= 10.0
        assert result.score >= 0.0

    def test_full_data_max_score(self) -> None:
        data = ProductData(
            title="Test",
            description="Desc",
            url="https://example.com",
            price="10",
            currency="USD",
            availability="InStock",
            image_urls=["img.jpg"],
            brand="Brand",
            marketplace=MarketplaceType.GENERIC,
        )
        result = score_feed_compliance(data)
        assert result.score == 10.0


# ── Compute Retail Score (aggregate) ────────────────────────────────────────


class TestComputeRetailScore:
    """Test compute_retail_score function."""

    def test_returns_retail_audit_report(self) -> None:
        data = ProductData(
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        assert isinstance(result, RetailAuditReport)

    def test_empty_product_yields_low_score(self) -> None:
        data = ProductData(
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        assert result.score >= 0.0
        assert result.score <= 100.0

    def test_full_product_yields_100(self) -> None:
        data = ProductData(
            title="Great Product",
            description="x" * 200,
            url="https://example.com/product",
            price="29.99",
            currency="USD",
            availability="InStock",
            image_urls=["img1", "img2", "img3", "img4", "img5"],
            alt_texts=["a1", "a2", "a3", "a4", "a5"],
            brand="TestBrand",
            rating=4.5,
            review_count=50,
            bullet_points=["a", "b", "c", "d", "e"],
            specifications={"color": "red"},
            has_video=True,
            has_aplus_content=True,
            qa_count=10,
            schema_org={
                "@type": "Product",
                "name": "Test",
                "offers": {"@type": "Offer", "price": "29.99"},
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": "4.5",
                },
            },
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        assert result.score == 100.0

    def test_report_contains_all_pillar_reports(self) -> None:
        data = ProductData(
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        assert isinstance(result.product_schema, ProductSchemaReport)
        assert isinstance(result.content_quality, ContentQualityReport)
        assert isinstance(result.visual_assets, VisualAssetsReport)
        assert isinstance(result.social_proof, SocialProofReport)
        assert isinstance(result.feed_compliance, FeedComplianceReport)

    def test_report_preserves_url(self) -> None:
        data = ProductData(
            url="https://example.com/product",
            marketplace=MarketplaceType.AMAZON,
        )
        result = compute_retail_score(data)
        assert result.url == "https://example.com/product"
        assert result.marketplace == MarketplaceType.AMAZON

    def test_report_includes_product_data(self) -> None:
        data = ProductData(
            title="Test",
            url="https://example.com/product",
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        assert result.product_data.title == "Test"

    def test_total_score_is_sum_of_pillars(self) -> None:
        data = ProductData(
            title="Test",
            description="x" * 100,
            url="https://example.com/product",
            image_urls=["img1", "img2"],
            review_count=5,
            rating=3.0,
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        expected = (
            result.product_schema.score
            + result.content_quality.score
            + result.visual_assets.score
            + result.social_proof.score
            + result.feed_compliance.score
        )
        assert abs(result.score - expected) < 0.01

    def test_score_capped_at_100(self) -> None:
        """Even with overflow in individual pillars, total should cap at 100."""
        data = ProductData(
            url="https://example.com",
            marketplace=MarketplaceType.GENERIC,
        )
        result = compute_retail_score(data)
        assert result.score <= 100.0
