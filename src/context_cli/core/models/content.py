"""Content density metrics models."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
        default=0.0,
        description="Fraction of sections starting with a direct statement (0.0-1.0)",
    )
    raw_html_chars: int = Field(default=0, description="Character count of raw HTML")
    clean_markdown_chars: int = Field(
        default=0, description="Character count of extracted markdown"
    )
    estimated_raw_tokens: int = Field(
        default=0, description="Estimated token count of raw HTML (chars/4)"
    )
    estimated_clean_tokens: int = Field(
        default=0, description="Estimated token count of clean markdown (chars/4)"
    )
    context_waste_pct: float = Field(
        default=0.0, ge=0, le=100, description="Percentage of tokens wasted on HTML bloat"
    )
    score: float = Field(default=0, description="Content pillar score (0-40)")
    detail: str = Field(default="", description="Summary of content density findings")
