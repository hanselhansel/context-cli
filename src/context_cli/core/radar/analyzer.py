"""Brand analyzer for citation radar — detects mentions and sentiment."""

from __future__ import annotations

import re

from context_cli.core.models import (
    BrandMention,
    DomainCategory,
    ModelRadarResult,
    RadarConfig,
    RadarReport,
)

from .domains import classify_domains

POSITIVE_WORDS: set[str] = {
    "best",
    "great",
    "excellent",
    "recommended",
    "top",
    "leading",
    "trusted",
    "reliable",
    "quality",
    "favorite",
}

NEGATIVE_WORDS: set[str] = {
    "worst",
    "avoid",
    "bad",
    "poor",
    "overpriced",
    "disappointing",
    "mediocre",
    "unreliable",
}

_SENTIMENT_WINDOW = 100  # chars around mention for sentiment detection
_CONTEXT_WINDOW = 50  # chars around mention for snippet extraction


def _detect_sentiment(text: str, start: int, end: int) -> str:
    """Detect sentiment around a brand mention using word proximity."""
    window_start = max(0, start - _SENTIMENT_WINDOW)
    window_end = min(len(text), end + _SENTIMENT_WINDOW)
    window = text[window_start:window_end].lower()

    words = set(re.findall(r"\b\w+\b", window))
    has_positive = bool(words & POSITIVE_WORDS)
    has_negative = bool(words & NEGATIVE_WORDS)

    if has_positive and not has_negative:
        return "positive"
    if has_negative and not has_positive:
        return "negative"
    return "neutral"


def _extract_context(text: str, start: int, end: int) -> str:
    """Extract a context snippet around a mention."""
    ctx_start = max(0, start - _CONTEXT_WINDOW)
    ctx_end = min(len(text), end + _CONTEXT_WINDOW)
    snippet = text[ctx_start:ctx_end]
    if ctx_start > 0:
        snippet = "..." + snippet
    if ctx_end < len(text):
        snippet = snippet + "..."
    return snippet


def detect_brand_mentions(text: str, brands: list[str]) -> list[BrandMention]:
    """Find all mentions of tracked brands in a response text.

    Case-insensitive matching. For each brand:
    - Count occurrences
    - Extract context snippets (±50 chars around each mention)
    - Simple sentiment: positive/negative/neutral based on nearby words
    """
    results: list[BrandMention] = []

    for brand in brands:
        if not brand:
            continue
        pattern = re.compile(re.escape(brand), re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if not matches:
            continue

        snippets: list[str] = []
        sentiments: list[str] = []
        for m in matches:
            snippets.append(_extract_context(text, m.start(), m.end()))
            sentiments.append(_detect_sentiment(text, m.start(), m.end()))

        # Overall sentiment: majority vote
        pos = sentiments.count("positive")
        neg = sentiments.count("negative")
        if pos > neg:
            overall = "positive"
        elif neg > pos:
            overall = "negative"
        else:
            overall = "neutral"

        results.append(
            BrandMention(
                brand=brand,
                count=len(matches),
                sentiment=overall,
                context_snippets=snippets,
            )
        )

    return results


def aggregate_brand_mentions(
    results: list[ModelRadarResult], brands: list[str]
) -> list[BrandMention]:
    """Aggregate brand mentions across all model results."""
    aggregated: dict[str, BrandMention] = {}

    for result in results:
        mentions = detect_brand_mentions(result.response_text, brands)
        for m in mentions:
            if m.brand in aggregated:
                existing = aggregated[m.brand]
                aggregated[m.brand] = BrandMention(
                    brand=m.brand,
                    count=existing.count + m.count,
                    sentiment=_merge_sentiments(existing.sentiment, m.sentiment),
                    context_snippets=existing.context_snippets + m.context_snippets,
                )
            else:
                aggregated[m.brand] = m

    return list(aggregated.values())


def _merge_sentiments(a: str, b: str) -> str:
    """Merge two sentiment labels: positive > negative > neutral when tied."""
    scores = {"positive": 1, "neutral": 0, "negative": -1}
    total = scores.get(a, 0) + scores.get(b, 0)
    if total > 0:
        return "positive"
    if total < 0:
        return "negative"
    return "neutral"


def _collect_domains(results: list[ModelRadarResult]) -> list[str]:
    """Collect all domains from citations across model results."""
    domains: list[str] = []
    for result in results:
        for citation in result.citations:
            if citation.domain:
                domains.append(citation.domain)
    return domains


def build_radar_report(
    config: RadarConfig, results: list[ModelRadarResult]
) -> RadarReport:
    """Build the final RadarReport from config and model results.

    Aggregates:
    - Brand mentions across all models
    - Domain classification of all cited URLs
    - Total citation count
    """
    brand_mentions: list[BrandMention] = aggregate_brand_mentions(results, config.brands)
    domains = _collect_domains(results)
    domain_breakdown: list[DomainCategory] = classify_domains(domains)
    total_citations = sum(len(r.citations) for r in results)

    return RadarReport(
        prompt=config.prompt,
        model_results=results,
        brand_mentions=brand_mentions,
        domain_breakdown=domain_breakdown,
        total_citations=total_citations,
    )
