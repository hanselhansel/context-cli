"""Tests for Flesch-Kincaid readability scoring.

Formula: 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59
Syllable counting: count vowel groups (a,e,i,o,u), min 1 per word.
readability_grade is None when word count < 30.
"""

from __future__ import annotations

from context_cli.core.checks.content import _count_syllables, _readability_grade, check_content

# ── Syllable counter tests ───────────────────────────────────────────────────


def test_syllable_single_vowel():
    """A word with one vowel group has 1 syllable."""
    assert _count_syllables("cat") == 1


def test_syllable_multiple_groups():
    """A word with separated vowel groups has multiple syllables."""
    assert _count_syllables("beautiful") == 3  # beau-ti-ful


def test_syllable_consecutive_vowels():
    """Consecutive vowels count as one group."""
    assert _count_syllables("boat") == 1  # oa is one group


def test_syllable_no_vowels():
    """A word with no vowels should still return 1 (minimum)."""
    assert _count_syllables("rhythm") == 1  # no a,e,i,o,u vowels but min 1


def test_syllable_empty_string():
    """Empty string returns 1 (minimum per word)."""
    assert _count_syllables("") == 1


def test_syllable_all_vowels():
    """Word of all vowels — one group if consecutive."""
    assert _count_syllables("aeiou") == 1


def test_syllable_alternating():
    """Alternating consonant-vowel pattern."""
    assert _count_syllables("banana") == 3  # ba-na-na


def test_syllable_uppercase():
    """Syllable counting should be case-insensitive."""
    assert _count_syllables("HELLO") == 2  # HEL-LO


# ── Readability grade tests ──────────────────────────────────────────────────


def test_readability_below_threshold():
    """Less than 30 words should return None."""
    text = " ".join(["word"] * 20)
    assert _readability_grade(text) is None


def test_readability_exactly_30_words():
    """Exactly 30 words should compute a grade (not None)."""
    text = "This is a simple sentence. " * 6  # 30 words, 6 sentences
    grade = _readability_grade(text)
    assert grade is not None
    assert isinstance(grade, float)


def test_readability_simple_text():
    """Simple short sentences should produce a low grade level."""
    text = "The cat sat on the mat. " * 10  # simple, short sentences
    grade = _readability_grade(text)
    assert grade is not None
    assert grade < 6  # very simple text


def test_readability_complex_text():
    """Complex long sentences with multi-syllable words should produce higher grade."""
    text = (
        "The extraordinary characteristics of the international organization "
        "demonstrated unprecedented sophistication in their administrative "
        "implementation procedures. The revolutionary methodology incorporated "
        "comprehensive evaluation frameworks alongside sophisticated analytical "
        "instrumentation for unprecedented environmental characterization. "
    )
    grade = _readability_grade(text)
    assert grade is not None
    assert grade > 12  # very complex text


def test_readability_no_sentences():
    """Text without sentence-ending punctuation should handle gracefully."""
    text = " ".join(["word"] * 50)  # no periods, questions, or exclamation marks
    grade = _readability_grade(text)
    # Should treat as 1 sentence (fallback)
    assert grade is not None


def test_readability_only_punctuation_words():
    """Text of punctuation tokens should use entire text as one sentence."""
    text = " ".join(["!?"] * 35)  # 35 'words' that are all punctuation
    grade = _readability_grade(text)
    # All sentence splits are empty, so fallback to [text] as one sentence
    assert grade is not None


# ── Integration with check_content ───────────────────────────────────────────


def test_check_content_readability_set():
    """check_content should populate readability_grade for sufficient content."""
    md = "# Heading\n\n" + "This is a simple sentence. " * 10
    report = check_content(md)
    assert report.readability_grade is not None


def test_check_content_readability_none_for_short():
    """check_content should set readability_grade to None for short content."""
    md = "Just a few words."
    report = check_content(md)
    assert report.readability_grade is None


def test_check_content_readability_none_for_empty():
    """check_content should set readability_grade to None for empty content."""
    report = check_content("")
    assert report.readability_grade is None
