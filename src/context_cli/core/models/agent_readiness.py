"""Agent readiness check models — new V3 pillar (20 points max)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentsMdReport(BaseModel):
    """Result of checking for AGENTS.md presence."""

    found: bool = Field(default=False, description="Whether AGENTS.md was found")
    url: str | None = Field(default=None, description="URL where AGENTS.md was found")
    score: float = Field(default=0, description="AGENTS.md sub-score (0-5)")
    detail: str = Field(default="", description="Summary of AGENTS.md check")


class MarkdownAcceptReport(BaseModel):
    """Result of probing Accept: text/markdown support."""

    supported: bool = Field(
        default=False, description="Whether server responds to Accept: text/markdown"
    )
    content_type: str | None = Field(
        default=None, description="Content-Type of the markdown response"
    )
    score: float = Field(default=0, description="Markdown accept sub-score (0-5)")
    detail: str = Field(default="", description="Summary of markdown accept probe")


class McpEndpointReport(BaseModel):
    """Result of checking for MCP endpoint at /.well-known/mcp.json."""

    found: bool = Field(default=False, description="Whether MCP endpoint was found")
    url: str | None = Field(default=None, description="URL of MCP endpoint")
    tools_count: int | None = Field(
        default=None, description="Number of tools advertised in MCP manifest"
    )
    score: float = Field(default=0, description="MCP endpoint sub-score (0-4)")
    detail: str = Field(default="", description="Summary of MCP endpoint check")


class SemanticHtmlReport(BaseModel):
    """Result of evaluating semantic HTML quality."""

    has_main: bool = Field(default=False, description="Whether <main> element found")
    has_article: bool = Field(default=False, description="Whether <article> element found")
    has_header: bool = Field(default=False, description="Whether <header> element found")
    has_footer: bool = Field(default=False, description="Whether <footer> element found")
    has_nav: bool = Field(default=False, description="Whether <nav> element found")
    aria_landmarks: int = Field(
        default=0, description="Count of ARIA landmark roles"
    )
    score: float = Field(default=0, description="Semantic HTML sub-score (0-3)")
    detail: str = Field(default="", description="Summary of semantic HTML quality")


class X402Report(BaseModel):
    """Result of checking for x402 payment signaling."""

    found: bool = Field(
        default=False, description="Whether x402 payment signaling was detected"
    )
    has_402_status: bool = Field(
        default=False, description="Whether HTTP 402 status code was returned"
    )
    has_payment_header: bool = Field(
        default=False, description="Whether X-Payment or payment-related headers found"
    )
    score: float = Field(default=0, description="x402 sub-score (0-2)")
    detail: str = Field(default="", description="Summary of x402 detection")


class NlwebReport(BaseModel):
    """Result of checking for NLWeb support."""

    found: bool = Field(
        default=False, description="Whether NLWeb support was detected"
    )
    well_known_found: bool = Field(
        default=False, description="Whether /.well-known/nlweb was found"
    )
    schema_extensions: bool = Field(
        default=False, description="Whether NLWeb Schema.org extensions detected"
    )
    score: float = Field(default=0, description="NLWeb sub-score (0-1)")
    detail: str = Field(default="", description="Summary of NLWeb check")


class AgentReadinessReport(BaseModel):
    """Aggregated agent readiness pillar report. Max 20 points."""

    agents_md: AgentsMdReport = Field(
        default_factory=AgentsMdReport, description="AGENTS.md detection"
    )
    markdown_accept: MarkdownAcceptReport = Field(
        default_factory=MarkdownAcceptReport, description="Accept: text/markdown probe"
    )
    mcp_endpoint: McpEndpointReport = Field(
        default_factory=McpEndpointReport, description="MCP endpoint detection"
    )
    semantic_html: SemanticHtmlReport = Field(
        default_factory=SemanticHtmlReport, description="Semantic HTML quality"
    )
    x402: X402Report = Field(
        default_factory=X402Report, description="x402 payment signaling"
    )
    nlweb: NlwebReport = Field(
        default_factory=NlwebReport, description="NLWeb support"
    )
    score: float = Field(default=0, description="Agent readiness pillar score (0-20)")
    detail: str = Field(default="", description="Summary of agent readiness")
