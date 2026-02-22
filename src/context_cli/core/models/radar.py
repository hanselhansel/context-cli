"""Citation radar models for multi-model citation extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RadarConfig(BaseModel):
    """Configuration for citation radar queries."""

    prompt: str = Field(description="The search prompt to send to AI models")
    models: list[str] = Field(
        default_factory=lambda: ["gpt-4o-mini"],
        description="LLM models to query",
    )
    brands: list[str] = Field(
        default_factory=list, description="Brand names to track in responses"
    )
    runs_per_model: int = Field(
        default=1, description="Number of runs per model for statistical significance"
    )


class CitationSource(BaseModel):
    """A single citation source extracted from an LLM response."""

    url: str | None = Field(default=None, description="URL of the cited source (if available)")
    title: str | None = Field(default=None, description="Title of the cited source")
    domain: str | None = Field(
        default=None, description="Domain of the source (e.g., reddit.com)"
    )
    snippet: str | None = Field(default=None, description="Text snippet around the citation")


class BrandMention(BaseModel):
    """A brand mention detected in an LLM response."""

    brand: str = Field(description="Brand name that was mentioned")
    count: int = Field(description="Number of times mentioned in the response")
    sentiment: str = Field(
        default="neutral",
        description="Detected sentiment: positive, neutral, negative",
    )
    context_snippets: list[str] = Field(
        default_factory=list, description="Surrounding text for each mention"
    )


class DomainCategory(BaseModel):
    """Classification of a source domain."""

    domain: str = Field(description="The domain name")
    category: str = Field(
        description=(
            "Category: reddit, news, review_site, marketplace, blog,"
            " official, reference, other"
        )
    )


class ModelRadarResult(BaseModel):
    """Result from querying a single model."""

    model: str = Field(description="Model identifier used")
    response_text: str = Field(description="Raw text response from the model")
    citations: list[CitationSource] = Field(
        default_factory=list, description="Extracted citations"
    )
    brands_mentioned: list[str] = Field(
        default_factory=list, description="Brands found in response"
    )
    error: str | None = Field(default=None, description="Error message if query failed")


class RadarReport(BaseModel):
    """Aggregated citation radar report across all models."""

    prompt: str = Field(description="The search prompt used")
    model_results: list[ModelRadarResult] = Field(description="Per-model results")
    brand_mentions: list[BrandMention] = Field(
        default_factory=list, description="Aggregated brand mentions"
    )
    domain_breakdown: list[DomainCategory] = Field(
        default_factory=list, description="Domain categorization of cited sources"
    )
    total_citations: int = Field(
        default=0, description="Total number of citations across all models"
    )
