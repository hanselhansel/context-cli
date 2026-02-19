"""Tests for robots.txt caching."""

from __future__ import annotations

from context_cli.core.cache import RobotsCache
from context_cli.core.models import RobotsReport


def test_cache_miss():
    """Getting an uncached domain should return None."""
    cache = RobotsCache()
    assert cache.get("example.com") is None
    assert cache.has("example.com") is False


def test_cache_set_and_get():
    """Setting and getting a cache entry should round-trip correctly."""
    cache = RobotsCache()
    report = RobotsReport(found=True, detail="test")
    raw_text = "User-agent: *\nAllow: /\n"

    cache.set("example.com", report, raw_text)

    assert cache.has("example.com") is True
    result = cache.get("example.com")
    assert result is not None
    cached_report, cached_text = result
    assert cached_report.found is True
    assert cached_text == raw_text


def test_cache_overwrite():
    """Setting the same domain twice should overwrite the first entry."""
    cache = RobotsCache()
    report1 = RobotsReport(found=True, detail="first")
    report2 = RobotsReport(found=False, detail="second")

    cache.set("example.com", report1, "text1")
    cache.set("example.com", report2, "text2")

    result = cache.get("example.com")
    assert result is not None
    assert result[0].detail == "second"


def test_cache_clear():
    """Clearing the cache should remove all entries."""
    cache = RobotsCache()
    cache.set("example.com", RobotsReport(found=True), "text")
    cache.set("other.com", RobotsReport(found=False), None)

    cache.clear()

    assert cache.has("example.com") is False
    assert cache.has("other.com") is False


def test_cache_none_raw_text():
    """Cache should handle None raw_text (e.g., when robots.txt is not found)."""
    cache = RobotsCache()
    report = RobotsReport(found=False, detail="404")

    cache.set("example.com", report, None)

    result = cache.get("example.com")
    assert result is not None
    assert result[1] is None


def test_cache_multiple_domains():
    """Cache should store entries for different domains independently."""
    cache = RobotsCache()
    cache.set("example.com", RobotsReport(found=True, detail="ex"), "ex-text")
    cache.set("other.com", RobotsReport(found=False, detail="ot"), None)

    ex = cache.get("example.com")
    ot = cache.get("other.com")

    assert ex is not None and ex[0].detail == "ex"
    assert ot is not None and ot[0].detail == "ot"
