"""Pillar 4: Content density analysis."""

from __future__ import annotations

import re

from aeo_cli.core.models import ContentReport


def _analyze_chunks(markdown: str) -> tuple[int, int, int]:
    """Split markdown by headings and analyze chunk sizes.

    Returns (chunk_count, avg_chunk_words, chunks_in_sweet_spot).
    """
    chunks = re.split(r"^#{1,6}\s.*$", markdown, flags=re.MULTILINE)
    # Filter out empty/whitespace-only chunks
    chunk_words = [len(c.split()) for c in chunks if c.strip()]
    chunk_count = len(chunk_words)
    if chunk_count == 0:
        return 0, 0, 0
    avg = sum(chunk_words) // chunk_count
    sweet = sum(1 for w in chunk_words if 50 <= w <= 150)
    return chunk_count, avg, sweet


def check_content(markdown: str) -> ContentReport:
    """Analyze markdown content density."""
    if not markdown:
        return ContentReport(detail="No content extracted")

    words = markdown.split()
    word_count = len(words)
    char_count = len(markdown)
    has_headings = bool(re.search(r"^#{1,6}\s", markdown, re.MULTILINE))
    has_lists = bool(re.search(r"^[\s]*[-*+]\s", markdown, re.MULTILINE))
    has_code_blocks = "```" in markdown
    chunk_count, avg_chunk_words, chunks_in_sweet_spot = _analyze_chunks(markdown)

    detail = f"{word_count} words"
    if has_headings:
        detail += ", has headings"
    if has_lists:
        detail += ", has lists"
    if has_code_blocks:
        detail += ", has code blocks"

    return ContentReport(
        word_count=word_count,
        char_count=char_count,
        has_headings=has_headings,
        has_lists=has_lists,
        has_code_blocks=has_code_blocks,
        chunk_count=chunk_count,
        avg_chunk_words=avg_chunk_words,
        chunks_in_sweet_spot=chunks_in_sweet_spot,
        detail=detail,
    )
