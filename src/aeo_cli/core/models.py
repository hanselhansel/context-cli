"""Pydantic models defining all AEO audit data contracts."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class OutputFormat(str, Enum):
    """Supported output formats for audit reports."""

    json = "json"
    csv = "csv"
    markdown = "markdown"


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
        default="./aeo-output", description="Directory to write generated files"
    )


class RetryConfig(BaseModel):
    """Configuration for HTTP request retries with exponential backoff."""

    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    backoff_base: float = Field(
        default=1.0, description="Base delay in seconds for exponential backoff"
    )
    backoff_max: float = Field(default=30.0, description="Maximum delay in seconds between retries")
    retry_on_status: list[int] = Field(
        default=[429, 500, 502, 503, 504],
        description="HTTP status codes that trigger a retry",
    )


class BotAccessResult(BaseModel):
    """Result of checking a single AI bot's access in robots.txt."""

    bot: str = Field(description="Name of the AI bot (e.g., GPTBot, ClaudeBot)")
    allowed: bool = Field(description="Whether the bot is allowed by robots.txt")
    detail: str = Field(default="", description="Additional detail (e.g., Disallow rule found)")


class RobotsReport(BaseModel):
    """Aggregated robots.txt analysis for AI bots. Max 25 points."""

    found: bool = Field(description="Whether robots.txt was accessible")
    bots: list[BotAccessResult] = Field(default_factory=list, description="Per-bot access results")
    score: float = Field(default=0, description="Robots pillar score (0-25)")
    detail: str = Field(default="", description="Summary of robots.txt findings")


class LlmsTxtReport(BaseModel):
    """llms.txt presence check. Max 10 points."""

    found: bool = Field(description="Whether llms.txt was found")
    url: str | None = Field(default=None, description="URL where llms.txt was found")
    score: float = Field(default=0, description="llms.txt pillar score (0-10)")
    detail: str = Field(default="", description="Summary of llms.txt findings")


class SchemaOrgResult(BaseModel):
    """A single JSON-LD structured data block found in the page."""

    schema_type: str = Field(description="The @type value (e.g., Organization, Article)")
    properties: list[str] = Field(
        default_factory=list, description="Top-level property names found"
    )


class SchemaReport(BaseModel):
    """Aggregated Schema.org JSON-LD analysis. Max 25 points."""

    blocks_found: int = Field(default=0, description="Number of JSON-LD blocks found")
    schemas: list[SchemaOrgResult] = Field(
        default_factory=list, description="Parsed JSON-LD blocks"
    )
    score: float = Field(default=0, description="Schema pillar score (0-25)")
    detail: str = Field(default="", description="Summary of schema findings")


class ContentReport(BaseModel):
    """Markdown content density metrics. Max 40 points."""

    word_count: int = Field(default=0, description="Total word count of extracted markdown")
    char_count: int = Field(default=0, description="Total character count of extracted markdown")
    has_headings: bool = Field(default=False, description="Whether headings were found")
    has_lists: bool = Field(default=False, description="Whether lists (ul/ol) were found")
    has_code_blocks: bool = Field(default=False, description="Whether code blocks were found")
    score: float = Field(default=0, description="Content pillar score (0-40)")
    detail: str = Field(default="", description="Summary of content density findings")


class AuditReport(BaseModel):
    """Top-level AEO audit report composing all pillar results."""

    url: str = Field(description="The audited URL")
    overall_score: float = Field(default=0, description="Overall AEO score (0-100)")
    robots: RobotsReport = Field(description="Robots.txt AI bot access analysis")
    llms_txt: LlmsTxtReport = Field(description="llms.txt presence check")
    schema_org: SchemaReport = Field(description="Schema.org JSON-LD analysis")
    content: ContentReport = Field(description="Content density analysis")
    errors: list[str] = Field(
        default_factory=list, description="Non-fatal errors encountered during audit"
    )


class PageAudit(BaseModel):
    """Per-page audit results (schema + content only)."""

    url: str = Field(description="URL of the audited page")
    schema_org: SchemaReport = Field(description="Schema.org JSON-LD analysis for this page")
    content: ContentReport = Field(description="Content density analysis for this page")
    errors: list[str] = Field(
        default_factory=list, description="Non-fatal errors encountered for this page"
    )


class DiscoveryResult(BaseModel):
    """How pages were discovered for multi-page audit."""

    method: str = Field(description="Discovery method: 'sitemap' or 'spider'")
    urls_found: int = Field(default=0, description="Total URLs discovered before sampling")
    urls_sampled: list[str] = Field(
        default_factory=list, description="URLs selected for auditing"
    )
    detail: str = Field(default="", description="Summary of discovery process")


class SiteAuditReport(BaseModel):
    """Site-level AEO audit with aggregate scores and per-page breakdown."""

    url: str = Field(description="Seed URL for the audit")
    domain: str = Field(description="Domain of the audited site")
    overall_score: float = Field(default=0, description="Aggregate AEO score (0-100)")
    robots: RobotsReport = Field(description="Robots.txt AI bot access (site-wide)")
    llms_txt: LlmsTxtReport = Field(description="llms.txt presence (site-wide)")
    schema_org: SchemaReport = Field(description="Aggregated Schema.org analysis across pages")
    content: ContentReport = Field(description="Aggregated content density across pages")
    discovery: DiscoveryResult = Field(description="Page discovery details")
    pages: list[PageAudit] = Field(default_factory=list, description="Per-page audit results")
    pages_audited: int = Field(default=0, description="Number of pages successfully audited")
    pages_failed: int = Field(default=0, description="Number of pages that failed to audit")
    errors: list[str] = Field(
        default_factory=list, description="Non-fatal errors encountered during audit"
    )


# ── Generate command models ──────────────────────────────────────────────────


class LlmsTxtLink(BaseModel):
    """A single link entry in an llms.txt section."""

    title: str = Field(description="Human-readable link title")
    url: str = Field(description="Absolute URL for the link")
    description: str = Field(default="", description="Brief description of the linked resource")


class LlmsTxtSection(BaseModel):
    """A section within an llms.txt file (e.g., ## Docs, ## API)."""

    heading: str = Field(description="Section heading (without ## prefix)")
    links: list[LlmsTxtLink] = Field(
        default_factory=list, description="Links in this section"
    )
