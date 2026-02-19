"""Pillar 4: Content density analysis."""

from __future__ import annotations

import re

from context_cli.core.models import ContentReport

_VOWELS = re.compile(r"[aeiou]+", re.IGNORECASE)


def _count_syllables(word: str) -> int:
    """Count syllables by counting vowel groups. Minimum 1 per word."""
    groups = _VOWELS.findall(word)
    return max(1, len(groups))


def _readability_grade(text: str) -> float | None:
    """Compute Flesch-Kincaid Grade Level. Returns None if <30 words."""
    words = text.split()
    if len(words) < 30:
        return None
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        sentences = [text]  # treat entire text as one sentence
    total_syllables = sum(_count_syllables(w) for w in words)
    grade = 0.39 * (len(words) / len(sentences)) + 11.8 * (total_syllables / len(words)) - 15.59
    return round(grade, 1)


def _analyze_headings(markdown: str) -> tuple[int, bool]:
    """Count headings and validate hierarchy.

    Returns (heading_count, heading_hierarchy_valid).
    Hierarchy rule: each heading can go at most one level deeper than the previous.
    Going back up (e.g., H3 → H2) is always valid.
    """
    heading_pattern = re.compile(r"^(#{1,6})\s", re.MULTILINE)
    levels = [len(m.group(1)) for m in heading_pattern.finditer(markdown)]
    if not levels:
        return 0, True
    valid = True
    max_seen = levels[0]
    for level in levels[1:]:
        if level > max_seen + 1:
            valid = False
            break
        max_seen = level
    return len(levels), valid


def _answer_first_ratio(markdown: str) -> float:
    """Calculate fraction of sections where the first sentence is a statement.

    Sections are split by headings. A question is any sentence ending with '?'.
    Returns 0.0 if there are no sections with text.
    """
    if not markdown.strip():
        return 0.0
    sections = re.split(r"^#{1,6}\s.*$", markdown, flags=re.MULTILINE)
    non_empty = [s.strip() for s in sections if s.strip()]
    if not non_empty:
        return 0.0
    answer_first = 0
    for section in non_empty:
        # Extract first sentence: split on sentence-ending punctuation
        sentences = re.split(r"(?<=[.!?])\s", section, maxsplit=1)
        first = sentences[0].strip()
        if first and not first.rstrip().endswith("?"):
            answer_first += 1
    return round(answer_first / len(non_empty), 2)


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
    readability_grade = _readability_grade(markdown)
    heading_count, heading_hierarchy_valid = _analyze_headings(markdown)
    answer_first = _answer_first_ratio(markdown)

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
        readability_grade=readability_grade,
        heading_count=heading_count,
        heading_hierarchy_valid=heading_hierarchy_valid,
        answer_first_ratio=answer_first,
        detail=detail,
    )
