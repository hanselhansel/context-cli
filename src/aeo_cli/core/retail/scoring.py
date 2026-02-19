"""Retail 5-pillar scoring engine.

Evaluates product listings across five pillars of AI-readiness:
- Product Schema (25 pts): JSON-LD Product, Offer, AggregateRating
- Content Quality (30 pts): bullets, description, A+, spec chart
- Visual Assets (15 pts): image count, alt text, video
- Social Proof (20 pts): reviews, rating, Q&A
- Feed Compliance (10 pts): OpenAI Product Feed Spec fields
"""

from __future__ import annotations

from aeo_cli.core.models import (
    ContentQualityReport,
    FeedComplianceReport,
    ProductData,
    ProductSchemaReport,
    RetailAuditReport,
    SocialProofReport,
    VisualAssetsReport,
)
from aeo_cli.core.retail.feed_spec import check_feed_compliance


def _has_product_type(schema: dict) -> bool:
    """Check if schema has @type Product (string or list)."""
    schema_type = schema.get("@type", "")
    if isinstance(schema_type, list):
        return "Product" in schema_type
    return schema_type == "Product"


def score_product_schema(data: ProductData) -> ProductSchemaReport:
    """Score the Product Schema pillar (max 25 points).

    Breakdown:
    - 10 pts: Product JSON-LD exists
    - 8 pts: Offer data present
    - 7 pts: AggregateRating present

    Args:
        data: Parsed product data with schema_org field.

    Returns:
        ProductSchemaReport with score and field presence flags.
    """
    schema = data.schema_org
    score = 0.0
    missing: list[str] = []

    has_product = _has_product_type(schema)
    has_offer = "offers" in schema and bool(schema["offers"])
    has_rating = "aggregateRating" in schema and bool(schema["aggregateRating"])

    if has_product:
        score += 10.0
    if has_offer:
        score += 8.0
    else:
        missing.append("offers")
    if has_rating:
        score += 7.0
    else:
        missing.append("aggregateRating")

    score = min(score, 25.0)

    return ProductSchemaReport(
        score=score,
        has_product_schema=has_product,
        has_offer=has_offer,
        has_aggregate_rating=has_rating,
        missing_fields=missing,
    )


def score_content_quality(data: ProductData) -> ContentQualityReport:
    """Score the Content Quality pillar (max 30 points).

    Breakdown:
    - 10 pts: Bullet points (>= 5 for full score, proportional below)
    - 10 pts: Description length (>= 200 chars for full, proportional below)
    - 5 pts: A+ / enhanced content
    - 5 pts: Specification chart

    Args:
        data: Parsed product data.

    Returns:
        ContentQualityReport with score and quality indicators.
    """
    score = 0.0
    bullet_count = len(data.bullet_points)
    desc_length = len(data.description) if data.description else 0
    has_aplus = data.has_aplus_content
    has_spec = len(data.specifications) > 0

    # Bullet points: up to 10 pts
    bullet_score = min(bullet_count / 5, 1.0) * 10.0
    score += bullet_score

    # Description: up to 10 pts
    desc_score = min(desc_length / 200, 1.0) * 10.0
    score += desc_score

    # A+ content: 5 pts
    if has_aplus:
        score += 5.0

    # Spec chart: 5 pts
    if has_spec:
        score += 5.0

    score = min(score, 30.0)

    return ContentQualityReport(
        score=score,
        bullet_count=bullet_count,
        description_length=desc_length,
        has_aplus=has_aplus,
        has_spec_chart=has_spec,
    )


def score_visual_assets(data: ProductData) -> VisualAssetsReport:
    """Score the Visual Assets pillar (max 15 points).

    Breakdown:
    - 8 pts: Image count (>= 5 for full, proportional below)
    - 4 pts: Alt text coverage (fraction of images with alt text)
    - 3 pts: Video content

    Args:
        data: Parsed product data.

    Returns:
        VisualAssetsReport with score and asset indicators.
    """
    score = 0.0
    image_count = len(data.image_urls)
    # Cap alt text count at image count
    images_with_alt = min(len(data.alt_texts), image_count)
    has_video = data.has_video

    # Image count: up to 8 pts
    image_score = min(image_count / 5, 1.0) * 8.0
    score += image_score

    # Alt text coverage: up to 4 pts
    if image_count > 0:
        alt_coverage = images_with_alt / image_count
        score += alt_coverage * 4.0

    # Video: 3 pts
    if has_video:
        score += 3.0

    score = min(score, 15.0)

    return VisualAssetsReport(
        score=score,
        image_count=image_count,
        images_with_alt=images_with_alt,
        has_video=has_video,
    )


def score_social_proof(data: ProductData) -> SocialProofReport:
    """Score the Social Proof pillar (max 20 points).

    Breakdown:
    - 10 pts: Review count (>= 10 for full, proportional below)
    - 5 pts: Rating (>= 4.0 for full, proportional below)
    - 5 pts: Q&A presence (qa_count > 0)

    Args:
        data: Parsed product data.

    Returns:
        SocialProofReport with score and proof indicators.
    """
    score = 0.0
    review_count = data.review_count
    rating = data.rating
    has_qa = data.qa_count is not None and data.qa_count > 0

    # Review count: up to 10 pts
    if review_count is not None and review_count > 0:
        review_score = min(review_count / 10, 1.0) * 10.0
        score += review_score

    # Rating: up to 5 pts
    if rating is not None and rating > 0:
        rating_score = min(rating / 4.0, 1.0) * 5.0
        score += rating_score

    # Q&A: 5 pts
    if has_qa:
        score += 5.0

    score = min(score, 20.0)

    return SocialProofReport(
        score=score,
        review_count=review_count,
        rating=rating,
        has_qa=has_qa,
    )


def score_feed_compliance(data: ProductData) -> FeedComplianceReport:
    """Score the Feed Compliance pillar (max 10 points).

    Delegates to the feed_spec module for field checking.

    Args:
        data: Parsed product data.

    Returns:
        FeedComplianceReport with score and field presence lists.
    """
    return check_feed_compliance(data)


def compute_retail_score(data: ProductData) -> RetailAuditReport:
    """Compute the full retail AI-readiness score across all 5 pillars.

    Aggregates scores from all pillars and produces a comprehensive
    RetailAuditReport.

    Args:
        data: Parsed product data to score.

    Returns:
        RetailAuditReport with overall score and per-pillar breakdowns.
    """
    schema_report = score_product_schema(data)
    content_report = score_content_quality(data)
    visual_report = score_visual_assets(data)
    social_report = score_social_proof(data)
    feed_report = score_feed_compliance(data)

    total = (
        schema_report.score
        + content_report.score
        + visual_report.score
        + social_report.score
        + feed_report.score
    )
    total = min(total, 100.0)

    return RetailAuditReport(
        url=data.url,
        marketplace=data.marketplace,
        score=total,
        product_schema=schema_report,
        content_quality=content_report,
        visual_assets=visual_report,
        social_proof=social_report,
        feed_compliance=feed_report,
        product_data=data,
    )
