"""Core audit report models: lint checks, audit reports, and site/batch reports."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .agent_readiness import AgentReadinessReport
from .content import ContentReport
from .llms_txt import LlmsTxtReport
from .robots import RobotsReport
from .schema import SchemaReport
from .signals import ContentUsageReport, EeatReport, RslReport


class LintCheck(BaseModel):
    """Result of a single lint check."""

    name: str = Field(description="Check name (e.g., 'AI Primitives')")
    passed: bool = Field(description="Whether the check passed")
    detail: str = Field(default="", description="Human-readable detail")
    severity: str = Field(
        default="pass", description="Severity: pass, warn, or fail"
    )


class Diagnostic(BaseModel):
    """A single diagnostic message (linter-style)."""

    code: str = Field(description="Diagnostic code (e.g., WARN-001)")
    severity: str = Field(description="Severity: error, warn, or info")
    message: str = Field(description="Human-readable diagnostic message")


class LintResult(BaseModel):
    """Aggregated lint results for a page."""

    checks: list[LintCheck] = Field(
        default_factory=list, description="Individual check results"
    )
    diagnostics: list[Diagnostic] = Field(
        default_factory=list, description="Diagnostic messages"
    )
    context_waste_pct: float = Field(default=0.0, description="Token waste percentage")
    raw_tokens: int = Field(default=0, description="Estimated raw HTML tokens")
    clean_tokens: int = Field(default=0, description="Estimated clean markdown tokens")
    passed: bool = Field(default=True, description="Whether all checks passed")


class Recommendation(BaseModel):
    """A single actionable recommendation to improve Readiness Score."""

    pillar: str = Field(description="Which pillar this recommendation targets")
    action: str = Field(description="What to do")
    estimated_impact: float = Field(description="Estimated score improvement in points")
    priority: str = Field(description="high, medium, or low")
    detail: str = Field(description="Detailed explanation")


class AuditReport(BaseModel):
    """Top-level lint report composing all pillar results."""

    url: str = Field(description="The audited URL")
    overall_score: float = Field(default=0, description="Overall Readiness Score (0-100)")
    robots: RobotsReport = Field(description="Robots.txt AI bot access analysis")
    llms_txt: LlmsTxtReport = Field(description="llms.txt presence check")
    schema_org: SchemaReport = Field(description="Schema.org JSON-LD analysis")
    content: ContentReport = Field(description="Content density analysis")
    lint_result: LintResult | None = Field(
        default=None, description="Pass/fail lint check results"
    )
    rsl: RslReport | None = Field(
        default=None, description="RSL analysis (informational, not scored)"
    )
    content_usage: ContentUsageReport | None = Field(
        default=None, description="IETF Content-Usage header (informational, not scored)"
    )
    eeat: EeatReport | None = Field(
        default=None, description="E-E-A-T signals (informational, not scored)"
    )
    agent_readiness: AgentReadinessReport | None = Field(
        default=None, description="Agent readiness pillar (V3 scoring only)"
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
    """Site-level lint report with aggregate scores and per-page breakdown."""

    url: str = Field(description="Seed URL for the audit")
    domain: str = Field(description="Domain of the audited site")
    overall_score: float = Field(default=0, description="Aggregate Readiness Score (0-100)")
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
    agent_readiness: AgentReadinessReport | None = Field(
        default=None, description="Agent readiness pillar (V3 scoring only)"
    )
    discovery: DiscoveryResult = Field(description="Page discovery details")
    pages: list[PageAudit] = Field(default_factory=list, description="Per-page audit results")
    pages_audited: int = Field(default=0, description="Number of pages successfully audited")
    pages_failed: int = Field(default=0, description="Number of pages that failed to audit")
    errors: list[str] = Field(
        default_factory=list, description="Non-fatal errors encountered during audit"
    )
    lint_result: LintResult | None = Field(
        default=None, description="Pass/fail lint check results (site-wide)"
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
