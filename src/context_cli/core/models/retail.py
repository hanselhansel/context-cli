"""Retail marketplace audit models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MarketplaceType(str, Enum):
    """Supported marketplace types for retail auditing."""

    AMAZON = "amazon"
    SHOPEE = "shopee"
    LAZADA = "lazada"
    TOKOPEDIA = "tokopedia"
    TIKTOK_SHOP = "tiktok_shop"
    BLIBLI = "blibli"
    ZALORA = "zalora"
    GENERIC = "generic"


class ProductData(BaseModel):
    """Parsed product data from a marketplace listing."""

    title: str | None = Field(default=None, description="Product title")
    description: str | None = Field(default=None, description="Product description text")
    price: str | None = Field(default=None, description="Product price as displayed")
    currency: str | None = Field(default=None, description="Currency code (e.g., USD, SGD)")
    availability: str | None = Field(default=None, description="Availability status")
    image_urls: list[str] = Field(default_factory=list, description="Product image URLs")
    brand: str | None = Field(default=None, description="Brand name")
    rating: float | None = Field(default=None, description="Average rating (0-5)")
    review_count: int | None = Field(default=None, description="Number of reviews")
    bullet_points: list[str] = Field(
        default_factory=list, description="Product feature bullet points"
    )
    specifications: dict[str, str] = Field(
        default_factory=dict, description="Product specifications/attributes"
    )
    has_video: bool = Field(default=False, description="Whether listing has video content")
    has_aplus_content: bool = Field(
        default=False, description="Whether listing has A+ / enhanced content"
    )
    qa_count: int | None = Field(default=None, description="Number of Q&A entries")
    schema_org: dict = Field(
        default_factory=dict, description="Extracted Schema.org JSON-LD data"
    )
    marketplace: MarketplaceType = Field(
        default=MarketplaceType.GENERIC, description="Detected marketplace"
    )
    url: str = Field(default="", description="Product URL")
    alt_texts: list[str] = Field(
        default_factory=list, description="Alt text for product images"
    )


class ProductSchemaReport(BaseModel):
    """Product schema pillar analysis report."""

    score: float = Field(
        default=0.0, description="Product schema pillar score (0-25)"
    )
    has_product_schema: bool = Field(
        default=False, description="Whether Product JSON-LD exists"
    )
    has_offer: bool = Field(
        default=False, description="Whether Offer data exists"
    )
    has_aggregate_rating: bool = Field(
        default=False, description="Whether AggregateRating exists"
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Missing recommended schema fields",
    )


class ContentQualityReport(BaseModel):
    """Content quality pillar analysis report."""

    score: float = Field(
        default=0.0, description="Content quality pillar score (0-30)"
    )
    bullet_count: int = Field(
        default=0, description="Number of bullet points"
    )
    description_length: int = Field(
        default=0, description="Description character count"
    )
    has_aplus: bool = Field(
        default=False, description="Has A+/enhanced content"
    )
    has_spec_chart: bool = Field(
        default=False, description="Has specification chart"
    )


class VisualAssetsReport(BaseModel):
    """Visual assets pillar analysis report."""

    score: float = Field(
        default=0.0, description="Visual assets pillar score (0-15)"
    )
    image_count: int = Field(
        default=0, description="Number of product images"
    )
    images_with_alt: int = Field(
        default=0, description="Images with alt text"
    )
    has_video: bool = Field(
        default=False, description="Has video content"
    )


class SocialProofReport(BaseModel):
    """Social proof pillar analysis report."""

    score: float = Field(
        default=0.0, description="Social proof pillar score (0-20)"
    )
    review_count: int | None = Field(
        default=None, description="Number of reviews"
    )
    rating: float | None = Field(
        default=None, description="Average rating"
    )
    has_qa: bool = Field(
        default=False, description="Has Q&A section"
    )


class FeedComplianceReport(BaseModel):
    """Feed compliance pillar analysis report."""

    score: float = Field(
        default=0.0, description="Feed compliance pillar score (0-10)"
    )
    present_fields: list[str] = Field(
        default_factory=list, description="Present feed spec fields"
    )
    missing_fields: list[str] = Field(
        default_factory=list, description="Missing feed spec fields"
    )
    compliance_rate: float = Field(
        default=0.0, description="Fraction of required fields present"
    )


class RetailAuditReport(BaseModel):
    """Complete retail AI-readiness audit report."""

    url: str = Field(description="Audited product URL")
    marketplace: MarketplaceType = Field(
        description="Detected marketplace"
    )
    score: float = Field(
        default=0.0,
        description="Overall retail AI-readiness score (0-100)",
    )
    product_schema: ProductSchemaReport = Field(
        default_factory=ProductSchemaReport,
        description="Product schema analysis",
    )
    content_quality: ContentQualityReport = Field(
        default_factory=ContentQualityReport,
        description="Content quality analysis",
    )
    visual_assets: VisualAssetsReport = Field(
        default_factory=VisualAssetsReport,
        description="Visual assets analysis",
    )
    social_proof: SocialProofReport = Field(
        default_factory=SocialProofReport,
        description="Social proof analysis",
    )
    feed_compliance: FeedComplianceReport = Field(
        default_factory=FeedComplianceReport,
        description="Feed compliance analysis",
    )
    product_data: ProductData = Field(
        default_factory=ProductData,
        description="Parsed product data",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during audit",
    )
