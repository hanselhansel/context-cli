"""Generate command models: config, output formats, and batch generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .llms_txt import LlmsTxtContent


class OutputFormat(str, Enum):
    """Supported output formats for audit reports."""

    json = "json"
    csv = "csv"
    markdown = "markdown"
    html = "html"


class ProfileType(str, Enum):
    """Industry profile for generate command prompt tuning."""

    generic = "generic"
    cpg = "cpg"
    saas = "saas"
    ecommerce = "ecommerce"
    blog = "blog"


class GenerateConfig(BaseModel):
    """Configuration for the generate command."""

    url: str = Field(description="URL to generate assets for")
    profile: ProfileType = Field(
        default=ProfileType.generic, description="Industry profile for prompt tuning"
    )
    model: str | None = Field(
        default=None, description="LLM model to use (auto-detected if not set)"
    )
    output_dir: str = Field(
        default="./context-output", description="Directory to write generated files"
    )


class RetryConfig(BaseModel):
    """Configuration for HTTP request retries with exponential backoff."""

    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    backoff_base: float = Field(
        default=1.0, description="Base delay in seconds for exponential backoff"
    )
    backoff_max: float = Field(
        default=30.0, description="Maximum delay in seconds between retries"
    )
    retry_on_status: list[int] = Field(
        default=[429, 500, 502, 503, 504],
        description="HTTP status codes that trigger a retry",
    )


class SchemaJsonLdOutput(BaseModel):
    """LLM-generated Schema.org JSON-LD structured data."""

    schema_type: str = Field(description="Primary @type (e.g., Organization, Product)")
    json_ld: dict = Field(description="Complete JSON-LD object ready to embed in HTML")


class GenerateResult(BaseModel):
    """Result of the generate command — both generated assets plus metadata."""

    url: str = Field(description="Source URL used for generation")
    model_used: str = Field(description="LLM model that produced the output")
    profile: ProfileType = Field(description="Industry profile used for prompt tuning")
    llms_txt: LlmsTxtContent = Field(description="Generated llms.txt content")
    schema_jsonld: SchemaJsonLdOutput = Field(description="Generated Schema.org JSON-LD")
    llms_txt_path: str | None = Field(
        default=None, description="File path where llms.txt was written"
    )
    schema_jsonld_path: str | None = Field(
        default=None, description="File path where schema.jsonld was written"
    )
    errors: list[str] = Field(
        default_factory=list, description="Non-fatal errors during generation"
    )


class BatchGenerateConfig(BaseModel):
    """Configuration for batch asset generation."""

    urls: list[str] = Field(description="URLs to generate assets for")
    profile: ProfileType = Field(default=ProfileType.generic, description="Industry profile")
    model: str | None = Field(default=None, description="LLM model (auto-detected if not set)")
    output_dir: str = Field(default="./context-output", description="Output directory")
    concurrency: int = Field(default=3, description="Max concurrent generations")


class BatchPageResult(BaseModel):
    """Result of generating assets for a single page in a batch."""

    url: str = Field(description="The processed URL")
    success: bool = Field(description="Whether generation succeeded")
    llms_txt_path: str | None = Field(default=None, description="Path to generated llms.txt")
    schema_jsonld_path: str | None = Field(
        default=None, description="Path to generated schema.jsonld"
    )
    error: str | None = Field(default=None, description="Error message if generation failed")


class BatchGenerateResult(BaseModel):
    """Aggregated result of batch generation."""

    total: int = Field(description="Total URLs processed")
    succeeded: int = Field(description="Number of successful generations")
    failed: int = Field(description="Number of failed generations")
    results: list[BatchPageResult] = Field(description="Per-URL results")
    model_used: str = Field(description="LLM model used for generation")
    profile: ProfileType = Field(description="Profile used")
    output_dir: str = Field(description="Output directory")
