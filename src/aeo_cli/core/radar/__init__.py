"""Citation Radar — multi-model citation extraction and brand analysis."""

from __future__ import annotations

from .analyzer import aggregate_brand_mentions, build_radar_report, detect_brand_mentions
from .domains import DOMAIN_REGISTRY, classify_domain, classify_domains
from .parser import extract_domain, extract_urls, parse_citations
from .query import query_model, query_models

__all__ = [
    "DOMAIN_REGISTRY",
    "aggregate_brand_mentions",
    "build_radar_report",
    "classify_domain",
    "classify_domains",
    "detect_brand_mentions",
    "extract_domain",
    "extract_urls",
    "parse_citations",
    "query_model",
    "query_models",
]
