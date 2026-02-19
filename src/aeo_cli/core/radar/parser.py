"""Citation parser — extract citations from LLM responses."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from aeo_cli.core.models import CitationSource

# Regex for http/https URLs — avoids trailing punctuation
_URL_RE = re.compile(
    r"https?://[^\s<>\"\'\)\]]+",
)

# Numbered ref patterns: [N] url, [N]: url, [N](url)
_REF_BRACKET_URL = re.compile(r"\[(\d+)\]\s*(https?://[^\s<>\"\'\)\]]+)")
_REF_BRACKET_COLON = re.compile(r"\[(\d+)\]:\s*(https?://[^\s<>\"\'\)\]]+)")
_REF_MARKDOWN = re.compile(r"\[(\d+)\]\((https?://[^\s<>\"\'\)]+)\)")

# Characters to strip from end of URLs
_TRAILING_PUNCT = ".,:;!?"


def _clean_url(url: str) -> str:
    """Strip trailing punctuation from a URL."""
    while url and url[-1] in _TRAILING_PUNCT:
        url = url[:-1]
    return url


def _is_valid_url(url: str) -> bool:
    """Check if URL has a valid netloc (not just 'http://')."""
    parsed = urlparse(url)
    return bool(parsed.scheme) and bool(parsed.netloc)


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text using regex."""
    if not text:
        return []
    raw = _URL_RE.findall(text)
    cleaned = [_clean_url(u) for u in raw]
    return [u for u in cleaned if _is_valid_url(u)]


def extract_numbered_refs(text: str) -> list[tuple[int, str]]:
    """Extract numbered references like [1] url, [1]: url, or [1](url)."""
    if not text:
        return []
    results: list[tuple[int, str]] = []
    seen: set[int] = set()

    for pattern in (_REF_MARKDOWN, _REF_BRACKET_COLON, _REF_BRACKET_URL):
        for match in pattern.finditer(text):
            num = int(match.group(1))
            url = _clean_url(match.group(2))
            if num not in seen and _is_valid_url(url):
                results.append((num, url))
                seen.add(num)

    results.sort(key=lambda x: x[0])
    return results


def extract_domain(url: str) -> str:
    """Extract domain from URL, stripping www. prefix."""
    if not url:
        return ""
    parsed = urlparse(url)
    netloc = parsed.hostname or ""
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _get_snippet(text: str, url: str, context_chars: int = 50) -> str:
    """Get surrounding text snippet around a URL mention."""
    idx = text.find(url)
    if idx == -1:
        return ""
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(url) + context_chars)
    return text[start:end].strip()


def parse_citations(response_text: str, model: str) -> list[CitationSource]:
    """Extract citations from an LLM response.

    Combines URL extraction with numbered reference parsing.
    Deduplicates by URL. Each citation includes domain and snippet.
    """
    if not response_text:
        return []

    seen_urls: set[str] = set()
    citations: list[CitationSource] = []

    # First, collect numbered refs (they have richer context)
    numbered = extract_numbered_refs(response_text)
    for _num, url in numbered:
        if url not in seen_urls:
            seen_urls.add(url)
            citations.append(
                CitationSource(
                    url=url,
                    domain=extract_domain(url),
                    snippet=_get_snippet(response_text, url),
                )
            )

    # Then collect inline URLs not already captured
    inline_urls = extract_urls(response_text)
    for url in inline_urls:
        if url not in seen_urls:
            seen_urls.add(url)
            citations.append(
                CitationSource(
                    url=url,
                    domain=extract_domain(url),
                    snippet=_get_snippet(response_text, url),
                )
            )

    return citations
