"""Tests for answer-first pattern detection.

Sections starting with direct statements (not questions) score higher.
answer_first_ratio = fraction of sections with statement-first pattern.
"""

from __future__ import annotations

from aeo_cli.core.checks.content import _answer_first_ratio, check_content

# ── Direct answer_first_ratio tests ──────────────────────────────────────────


def test_all_sections_answer_first():
    """All sections start with statements → ratio 1.0."""
    md = (
        "# Section 1\n\nThis is a direct answer.\n\n"
        "## Section 2\n\nThe solution involves three steps.\n\n"
    )
    assert _answer_first_ratio(md) == 1.0


def test_all_sections_question_first():
    """All sections start with questions → ratio 0.0."""
    md = (
        "# Section 1\n\nWhat is the answer?\n\n"
        "## Section 2\n\nHow does this work?\n\n"
    )
    assert _answer_first_ratio(md) == 0.0


def test_mixed_sections():
    """Half statement, half question → ratio 0.5."""
    md = (
        "# Section 1\n\nThis is a statement.\n\n"
        "## Section 2\n\nWhat about this?\n\n"
    )
    assert _answer_first_ratio(md) == 0.5


def test_no_headings_single_section():
    """Content without headings is one section."""
    md = "This is a direct statement about the topic."
    assert _answer_first_ratio(md) == 1.0


def test_no_headings_question():
    """Content without headings starting with a question."""
    md = "What is this thing? It does stuff."
    assert _answer_first_ratio(md) == 0.0


def test_empty_content():
    """Empty content returns 0.0."""
    assert _answer_first_ratio("") == 0.0


def test_heading_only_no_body():
    """Heading with no body text has no sections to evaluate."""
    md = "# Just a heading"
    # The heading text itself is stripped; section body is empty
    assert _answer_first_ratio(md) == 0.0


def test_three_sections_two_answer_first():
    """2 of 3 sections are answer-first → ratio ~0.67."""
    md = (
        "# Intro\n\nThe answer is yes.\n\n"
        "## Details\n\nWhy would anyone do this?\n\n"
        "## Conclusion\n\nIn summary, this works well.\n\n"
    )
    ratio = _answer_first_ratio(md)
    assert abs(ratio - 2 / 3) < 0.01


def test_exclamation_is_statement():
    """Sentences ending with ! are statements, not questions."""
    md = "# Section\n\nThis is amazing!"
    assert _answer_first_ratio(md) == 1.0


def test_section_with_multiple_sentences():
    """Only the first sentence matters for answer-first detection."""
    md = "# Section\n\nFirst a statement. Then a question? More text."
    assert _answer_first_ratio(md) == 1.0  # first sentence is a statement


def test_question_then_statement():
    """First sentence is a question even though rest is statements."""
    md = "# Section\n\nIs this true? Yes, it is. Definitely."
    assert _answer_first_ratio(md) == 0.0  # first sentence ends with ?


# ── Integration with check_content ───────────────────────────────────────────


def test_check_content_answer_first_ratio():
    """check_content should populate answer_first_ratio."""
    md = "# Title\n\nThis is direct. More content follows.\n\n## Sub\n\nAlso direct."
    report = check_content(md)
    assert report.answer_first_ratio == 1.0


def test_check_content_answer_first_empty():
    """Empty content should have answer_first_ratio=0.0."""
    report = check_content("")
    assert report.answer_first_ratio == 0.0


def test_check_content_answer_first_mixed():
    """Mixed content should report correct ratio."""
    md = "# Q\n\nWhat is it?\n\n## A\n\nIt is this."
    report = check_content(md)
    assert report.answer_first_ratio == 0.5
