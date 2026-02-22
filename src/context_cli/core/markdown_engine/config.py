"""Markdown engine configuration — stub for agent merge."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MarkdownEngineConfig(BaseModel):
    """Configuration for the HTML-to-Markdown conversion pipeline."""

    strip_selectors: list[str] = Field(
        default_factory=lambda: [
            "script", "style", "nav", "footer", "header",
            "aside", "iframe", "noscript",
        ],
        description="CSS selectors for elements to strip during sanitization",
    )
    extract_main: bool = Field(
        default=True,
        description="Whether to extract main content using readability",
    )
