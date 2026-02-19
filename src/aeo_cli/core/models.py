"""Pydantic models defining all AEO audit data contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
    llms_full_found: bool = Field(
        default=False, description="Whether llms-full.txt was found"
    )
    llms_full_url: str | None = Field(
        default=None, description="URL where llms-full.txt was found"
    )
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
    chunk_count: int = Field(default=0, description="Number of content chunks split by headings")
    avg_chunk_words: int = Field(default=0, description="Average word count per chunk")
    chunks_in_sweet_spot: int = Field(
        default=0, description="Chunks with 50-150 words (citation sweet spot)"
    )
    readability_grade: float | None = Field(
        default=None, description="Flesch-Kincaid Grade Level (None if <30 words)"
    )
    heading_count: int = Field(default=0, description="Total number of headings (H1-H6)")
    heading_hierarchy_valid: bool = Field(
        default=True, description="Whether heading levels follow proper hierarchy"
    )
    answer_first_ratio: float = Field(
        default=0.0, description="Fraction of sections starting with a direct statement (0.0-1.0)"
    )
    score: float = Field(default=0, description="Content pillar score (0-40)")
    detail: str = Field(default="", description="Summary of content density findings")


# ── Informational signal models (not scored, verbose output only) ─────────


class RslReport(BaseModel):
    """Robots Specification Language (RSL) analysis — informational signal."""

    has_crawl_delay: bool = Field(
        default=False, description="Whether Crawl-delay directive found"
    )
    crawl_delay_value: float | None = Field(
        default=None, description="Crawl-delay value in seconds if set"
    )
    has_sitemap_directive: bool = Field(
        default=False, description="Whether Sitemap directive found in robots.txt"
    )
    sitemap_urls: list[str] = Field(
        default_factory=list, description="Sitemap URLs declared in robots.txt"
    )
    has_ai_specific_rules: bool = Field(
        default=False, description="Whether AI-bot-specific User-agent blocks exist"
    )
    ai_specific_agents: list[str] = Field(
        default_factory=list, description="AI bots with dedicated User-agent blocks"
    )
    detail: str = Field(default="", description="Summary of RSL findings")


class ContentUsageReport(BaseModel):
    """IETF Content-Usage HTTP header analysis — informational signal."""

    header_found: bool = Field(
        default=False, description="Whether Content-Usage header was present"
    )
    header_value: str | None = Field(
        default=None, description="Raw Content-Usage header value"
    )
    allows_training: bool | None = Field(
        default=None, description="Whether training use is allowed"
    )
    allows_search: bool | None = Field(
        default=None, description="Whether search indexing is allowed"
    )
    detail: str = Field(default="", description="Summary of Content-Usage findings")


class EeatReport(BaseModel):
    """E-E-A-T (Experience, Expertise, Authority, Trust) signals — informational."""

    has_author: bool = Field(default=False, description="Whether author attribution found")
    author_name: str | None = Field(default=None, description="Author name if found")
    has_date: bool = Field(default=False, description="Whether publish/update date found")
    has_about_page: bool = Field(
        default=False, description="Whether link to about page found"
    )
    has_contact_info: bool = Field(
        default=False, description="Whether contact information found"
    )
    has_citations: bool = Field(
        default=False, description="Whether external citations/references found"
    )
    citation_count: int = Field(default=0, description="Number of external citations found")
    trust_signals: list[str] = Field(
        default_factory=list,
        description="Trust signals found (e.g., SSL, privacy policy link)",
    )
    detail: str = Field(default="", description="Summary of E-E-A-T findings")


class AuditReport(BaseModel):
    """Top-level AEO audit report composing all pillar results."""

    url: str = Field(description="The audited URL")
    overall_score: float = Field(default=0, description="Overall AEO score (0-100)")
    robots: RobotsReport = Field(description="Robots.txt AI bot access analysis")
    llms_txt: LlmsTxtReport = Field(description="llms.txt presence check")
    schema_org: SchemaReport = Field(description="Schema.org JSON-LD analysis")
    content: ContentReport = Field(description="Content density analysis")
    rsl: RslReport | None = Field(
        default=None, description="RSL analysis (informational, not scored)"
    )
    content_usage: ContentUsageReport | None = Field(
        default=None, description="IETF Content-Usage header (informational, not scored)"
    )
    eeat: EeatReport | None = Field(
        default=None, description="E-E-A-T signals (informational, not scored)"
    )
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
    rsl: RslReport | None = Field(
        default=None, description="RSL analysis (informational, not scored)"
    )
    content_usage: ContentUsageReport | None = Field(
        default=None, description="IETF Content-Usage header (informational, not scored)"
    )
    eeat: EeatReport | None = Field(
        default=None, description="E-E-A-T signals (informational, not scored)"
    )
    discovery: DiscoveryResult = Field(description="Page discovery details")
    pages: list[PageAudit] = Field(default_factory=list, description="Per-page audit results")
    pages_audited: int = Field(default=0, description="Number of pages successfully audited")
    pages_failed: int = Field(default=0, description="Number of pages that failed to audit")
    errors: list[str] = Field(
        default_factory=list, description="Non-fatal errors encountered during audit"
    )


class BatchAuditReport(BaseModel):
    """Batch audit results for multiple URLs."""

    urls: list[str] = Field(description="URLs that were audited")
    reports: list[AuditReport | SiteAuditReport] = Field(
        default_factory=list, description="Successful per-URL audit results"
    )
    errors: dict[str, str] = Field(
        default_factory=dict, description="URLs that failed, mapped to error messages"
    )


# ── Compare command models ──────────────────────────────────────────────────


class PillarDelta(BaseModel):
    """Score difference for one pillar between two audits."""

    pillar: str = Field(description="Pillar name (robots, llms_txt, schema_org, content)")
    score_a: float = Field(description="Score for URL A")
    score_b: float = Field(description="Score for URL B")
    delta: float = Field(description="score_a - score_b (positive = A wins)")
    max_score: float = Field(description="Maximum possible score for this pillar")


class CompareReport(BaseModel):
    """Side-by-side comparison of two AEO audit reports."""

    url_a: str = Field(description="First URL audited")
    url_b: str = Field(description="Second URL audited")
    score_a: float = Field(description="Overall score for URL A")
    score_b: float = Field(description="Overall score for URL B")
    delta: float = Field(description="score_a - score_b")
    pillars: list[PillarDelta] = Field(description="Per-pillar score comparisons")
    report_a: AuditReport = Field(description="Full audit report for URL A")
    report_b: AuditReport = Field(description="Full audit report for URL B")


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


class LlmsTxtContent(BaseModel):
    """Structured representation of a complete llms.txt file."""

    title: str = Field(description="Site/product title (first line of llms.txt)")
    description: str = Field(description="One-line description (> blockquote in llms.txt)")
    sections: list[LlmsTxtSection] = Field(
        default_factory=list, description="Sections with links"
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


# ── Recommendation model ────────────────────────────────────────────────────


class Recommendation(BaseModel):
    """A single actionable recommendation to improve AEO score."""

    pillar: str = Field(description="Which pillar this recommendation targets")
    action: str = Field(description="What to do")
    estimated_impact: float = Field(description="Estimated score improvement in points")
    priority: str = Field(description="high, medium, or low")
    detail: str = Field(description="Detailed explanation")


# ── Webhook models ───────────────────────────────────────────────────────────


class WebhookPayload(BaseModel):
    """Payload sent to webhook URLs after an audit completes."""

    url: str = Field(description="Audited URL")
    overall_score: float = Field(description="Overall AEO score")
    robots_score: float = Field(description="Robots pillar score")
    llms_txt_score: float = Field(description="llms.txt pillar score")
    schema_score: float = Field(description="Schema.org pillar score")
    content_score: float = Field(description="Content pillar score")
    timestamp: str = Field(description="ISO 8601 timestamp")
    regression: bool = Field(default=False, description="Whether regression was detected")


# ── Plugin models ────────────────────────────────────────────────────────────


class PluginResult(BaseModel):
    """Result returned by an audit plugin check."""

    plugin_name: str = Field(description="Name of the plugin")
    score: float = Field(description="Score awarded by plugin")
    max_score: float = Field(description="Maximum possible score")
    detail: str = Field(description="Human-readable detail")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional plugin-specific data"
    )


# ── CI Baseline models ──────────────────────────────────────────────────────


class BaselineScores(BaseModel):
    """Saved baseline scores for CI regression comparison."""

    url: str = Field(description="The audited URL")
    overall: float = Field(description="Overall AEO score (0-100)")
    robots: float = Field(description="Robots pillar score (0-25)")
    schema_org: float = Field(description="Schema.org pillar score (0-25)")
    content: float = Field(description="Content pillar score (0-40)")
    llms_txt: float = Field(description="llms.txt pillar score (0-10)")
    timestamp: str = Field(description="ISO 8601 timestamp when baseline was saved")


class BaselineRegression(BaseModel):
    """A single pillar that regressed beyond the threshold."""

    pillar: str = Field(description="Pillar name (robots, llms_txt, schema_org, content, overall)")
    previous_score: float = Field(description="Score from the saved baseline")
    current_score: float = Field(description="Score from the current audit")
    delta: float = Field(description="current - previous (negative = regression)")


class BaselineComparison(BaseModel):
    """Result of comparing current audit scores against a saved baseline."""

    url: str = Field(description="The audited URL")
    previous: BaselineScores = Field(description="Saved baseline scores")
    current: BaselineScores = Field(description="Current audit scores")
    regressions: list[BaselineRegression] = Field(
        default_factory=list, description="Pillars that regressed beyond threshold"
    )
    passed: bool = Field(description="Whether the comparison passed (no regressions)")
