"""Boundary tests for content scoring word count thresholds."""

from __future__ import annotations

from context_cli.core.checks.content import check_content
from context_cli.core.models import LlmsTxtReport, RobotsReport, SchemaReport
from context_cli.core.scoring import compute_scores


def _score_content(word_count: int, **kwargs) -> float:
    """Helper: create content with exact word count and return its score."""
    words = " ".join(["word"] * word_count)
    content = check_content(words)
    _, _, _, scored_content, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        content,
    )
    return scored_content.score


def test_below_150_words():
    """Under 150 words should get 0 base score."""
    score = _score_content(100)
    assert score == 0


def test_exactly_150_words():
    """Exactly 150 words should reach the first tier (8 points)."""
    score = _score_content(150)
    assert score == 8


def test_between_150_and_400():
    """Between 150-399 words should score 8 base points."""
    score = _score_content(300)
    assert score == 8


def test_exactly_400_words():
    """Exactly 400 words should reach the second tier (15 points)."""
    score = _score_content(400)
    assert score == 15


def test_between_400_and_800():
    """Between 400-799 words should score 15 base points."""
    score = _score_content(600)
    assert score == 15


def test_exactly_800_words():
    """Exactly 800 words should reach the third tier (20 points)."""
    score = _score_content(800)
    assert score == 20


def test_between_800_and_1500():
    """Between 800-1499 words should score 20 base points."""
    score = _score_content(1200)
    assert score == 20


def test_exactly_1500_words():
    """Exactly 1500 words should reach the top tier (25 points)."""
    score = _score_content(1500)
    assert score == 25


def test_above_1500_words():
    """Above 1500 words should still score 25 base points (no extra)."""
    score = _score_content(3000)
    assert score == 25


def test_structure_bonuses_with_content():
    """Headings (+7) + lists (+5) + code (+3) should add to word count score."""
    md = "# Heading\n\n" + " ".join(["word"] * 1500) + "\n\n- list item\n\n```code```\n"
    content = check_content(md)
    _, _, _, scored, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        content,
    )
    # 25 (words) + 7 (headings) + 5 (lists) + 3 (code) = 40, capped at 40
    assert scored.score == 40


def test_content_score_cap_at_40():
    """Content score should never exceed 40 even with all bonuses."""
    md = "# Heading\n\n" + " ".join(["word"] * 2000) + "\n\n- item\n\n```code```\n"
    content = check_content(md)
    _, _, _, scored, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        content,
    )
    assert scored.score <= 40
