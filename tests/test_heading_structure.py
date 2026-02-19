"""Tests for heading structure analysis.

Validates heading counting by level and hierarchy checking:
no H3 without preceding H2, no H4 without H3, etc.
"""

from __future__ import annotations

from context_cli.core.checks.content import _analyze_headings, check_content

# ── Heading count tests ──────────────────────────────────────────────────────


def test_no_headings():
    """Content without headings: count=0, hierarchy valid (vacuously true)."""
    count, valid = _analyze_headings("Just some text without any headings.")
    assert count == 0
    assert valid is True


def test_single_h1():
    """A single H1 heading."""
    count, valid = _analyze_headings("# Title\n\nSome content.")
    assert count == 1
    assert valid is True


def test_multiple_same_level():
    """Multiple headings at the same level."""
    md = "## Section A\n\nText.\n\n## Section B\n\nMore text."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is True


def test_proper_hierarchy_h1_h2_h3():
    """H1 -> H2 -> H3 is a valid hierarchy."""
    md = "# Title\n\n## Section\n\n### Subsection\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 3
    assert valid is True


def test_h3_without_h2_invalid():
    """H3 appearing without any preceding H2 is invalid hierarchy."""
    md = "# Title\n\n### Subsection\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is False


def test_h4_without_h3_invalid():
    """H4 appearing without any preceding H3 is invalid."""
    md = "## Section\n\n#### Deep\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is False


def test_h2_then_h4_skips_h3_invalid():
    """H2 -> H4 (skipping H3) is invalid hierarchy."""
    md = "## Section\n\n#### Deep\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is False


def test_all_levels_proper():
    """H1 through H6 in order is valid."""
    md = (
        "# H1\n\n## H2\n\n### H3\n\n"
        "#### H4\n\n##### H5\n\n###### H6\n\nContent."
    )
    count, valid = _analyze_headings(md)
    assert count == 6
    assert valid is True


def test_h2_without_h1_is_valid():
    """Starting with H2 (no H1) should be valid — H1 is optional."""
    md = "## Section\n\n### Sub\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is True


def test_h5_without_h4_invalid():
    """H5 without preceding H4 is invalid."""
    md = "### H3\n\n##### H5\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is False


def test_h6_without_h5_invalid():
    """H6 without preceding H5 is invalid."""
    md = "#### H4\n\n###### H6\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 2
    assert valid is False


def test_repeated_h2_with_h3_under_each():
    """Multiple H2 sections each with their own H3 is valid."""
    md = "## A\n\n### A1\n\n## B\n\n### B1\n\nContent."
    count, valid = _analyze_headings(md)
    assert count == 4
    assert valid is True


def test_empty_string():
    """Empty string: no headings."""
    count, valid = _analyze_headings("")
    assert count == 0
    assert valid is True


# ── Integration with check_content ───────────────────────────────────────────


def test_check_content_heading_fields():
    """check_content should populate heading_count and heading_hierarchy_valid."""
    md = "# Title\n\n## Section\n\nSome content here."
    report = check_content(md)
    assert report.heading_count == 2
    assert report.heading_hierarchy_valid is True


def test_check_content_invalid_hierarchy():
    """check_content should detect invalid hierarchy."""
    md = "# Title\n\n### Skipped H2\n\nContent."
    report = check_content(md)
    assert report.heading_count == 2
    assert report.heading_hierarchy_valid is False


def test_check_content_no_headings_defaults():
    """Empty content should have heading_count=0 and hierarchy_valid=True."""
    report = check_content("")
    assert report.heading_count == 0
    assert report.heading_hierarchy_valid is True
