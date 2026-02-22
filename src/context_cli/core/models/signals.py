"""Informational signal models (not scored, verbose output only)."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
