"""Edge-case tests for _page_weight: trailing slashes, query strings, fragments."""

from __future__ import annotations

from context_cli.core.auditor import _page_weight


def test_root_url():
    """Root URL should have weight 3."""
    assert _page_weight("https://example.com/") == 3


def test_root_without_trailing_slash():
    """Root URL without trailing slash should have weight 3."""
    assert _page_weight("https://example.com") == 3


def test_single_segment_trailing_slash():
    """Single path segment with trailing slash should be depth 1 → weight 3."""
    assert _page_weight("https://example.com/about/") == 3


def test_single_segment_no_slash():
    """Single path segment should have weight 3."""
    assert _page_weight("https://example.com/about") == 3


def test_two_segments():
    """Two path segments should be depth 2 → weight 2."""
    assert _page_weight("https://example.com/blog/post") == 2


def test_three_segments():
    """Three or more segments should be depth 3+ → weight 1."""
    assert _page_weight("https://example.com/blog/2024/post") == 1


def test_deep_path():
    """Very deep paths should still have weight 1."""
    assert _page_weight("https://example.com/a/b/c/d/e/f") == 1


def test_query_string_ignored():
    """Query strings should not affect path depth calculation."""
    assert _page_weight("https://example.com/search?q=test") == 3
    assert _page_weight("https://example.com/blog/post?lang=en") == 2


def test_fragment_ignored():
    """Fragments should not affect path depth calculation."""
    assert _page_weight("https://example.com/about#team") == 3
    assert _page_weight("https://example.com/docs/api#methods") == 2


def test_empty_path():
    """URL with empty path should be treated as root (depth 0)."""
    assert _page_weight("https://example.com") == 3


def test_url_with_port():
    """URL with port number should still parse path correctly."""
    assert _page_weight("https://example.com:8080/api/v1/data") == 1
    assert _page_weight("https://example.com:3000/") == 3
