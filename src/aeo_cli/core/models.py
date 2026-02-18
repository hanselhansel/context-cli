"""Pydantic models defining all AEO audit data contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
