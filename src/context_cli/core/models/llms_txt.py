"""llms.txt presence and content models."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
