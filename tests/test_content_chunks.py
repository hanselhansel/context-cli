"""Tests for content chunk analysis (citation readiness).

Chunks are sections of markdown split by headings.
Sweet spot: 50-150 words per chunk (2.3x more citations).
"""

from __future__ import annotations

from context_cli.core.checks.content import check_content


def test_no_headings_single_chunk():
    """Content without headings is one chunk."""
    md = " ".join(["word"] * 80)
    report = check_content(md)
    assert report.chunk_count == 1
    assert report.avg_chunk_words == 80
    assert report.chunks_in_sweet_spot == 1  # 80 is in 50-150 range


def test_two_sections():
    """Two heading sections should produce two chunks."""
    sec1 = "# Section 1\n\n" + " ".join(["word"] * 60)
    sec2 = "# Section 2\n\n" + " ".join(["word"] * 100)
    md = sec1 + "\n\n" + sec2
    report = check_content(md)
    assert report.chunk_count == 2
    assert report.chunks_in_sweet_spot == 2  # 60 and 100 are both in range


def test_avg_chunk_words():
    """Average should be integer average of word counts per chunk."""
    md = "# A\n\n" + " ".join(["word"] * 40) + "\n\n# B\n\n" + " ".join(["word"] * 60)
    report = check_content(md)
    assert report.chunk_count == 2
    assert report.avg_chunk_words == 50  # (40+60)/2 = 50


def test_sweet_spot_boundaries():
    """Exactly 50 and 150 words should be in sweet spot; 49 and 151 should not."""
    sections = []
    for count in [49, 50, 150, 151]:
        sections.append("# Heading\n\n" + " ".join(["word"] * count))
    md = "\n\n".join(sections)
    report = check_content(md)
    assert report.chunk_count == 4
    assert report.chunks_in_sweet_spot == 2  # 50 and 150 are in range


def test_empty_content_zero_chunks():
    """Empty markdown should have zero chunks."""
    report = check_content("")
    assert report.chunk_count == 0
    assert report.avg_chunk_words == 0
    assert report.chunks_in_sweet_spot == 0


def test_heading_only_no_content():
    """A heading with no body text should produce zero non-empty chunks."""
    md = "# Just a heading\n\n"
    report = check_content(md)
    # The heading line is stripped; remaining content after heading may be empty
    # But there could be text before or after — in this case "Just a heading" part
    # is consumed by the split, leaving empty chunks
    assert report.chunk_count == 0


def test_content_before_first_heading():
    """Text before the first heading should count as a chunk."""
    md = "Some intro text with enough words.\n\n# First heading\n\nSection content here."
    report = check_content(md)
    assert report.chunk_count == 2  # intro + section after heading


def test_multiple_heading_levels():
    """H1, H2, H3 etc. should all split chunks."""
    md = (
        "# H1\n\n" + " ".join(["alpha"] * 30) + "\n\n"
        "## H2\n\n" + " ".join(["beta"] * 70) + "\n\n"
        "### H3\n\n" + " ".join(["gamma"] * 120) + "\n\n"
    )
    report = check_content(md)
    assert report.chunk_count == 3
    assert report.chunks_in_sweet_spot == 2  # 70 and 120 are in range, 30 is not


def test_all_chunks_outside_sweet_spot():
    """When all chunks are too small or too large, sweet spot count is 0."""
    md = "# Short\n\n" + " ".join(["w"] * 10) + "\n\n# Long\n\n" + " ".join(["w"] * 200)
    report = check_content(md)
    assert report.chunk_count == 2
    assert report.chunks_in_sweet_spot == 0


def test_large_document_many_chunks():
    """A document with many headings should count all chunks."""
    sections = [f"# Section {i}\n\n" + " ".join(["word"] * 75) for i in range(10)]
    md = "\n\n".join(sections)
    report = check_content(md)
    assert report.chunk_count == 10
    assert report.chunks_in_sweet_spot == 10  # all 75 words = in sweet spot
    assert report.avg_chunk_words == 75
