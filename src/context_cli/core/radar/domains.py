"""Domain classification for citation radar sources."""

from __future__ import annotations

from context_cli.core.models import DomainCategory

# Predefined domain categories
DOMAIN_REGISTRY: dict[str, str] = {
    "reddit.com": "reddit",
    "news.ycombinator.com": "news",
    "nytimes.com": "news",
    "bbc.com": "news",
    "cnn.com": "news",
    "theverge.com": "news",
    "wirecutter.com": "review_site",
    "rtings.com": "review_site",
    "tomsguide.com": "review_site",
    "amazon.com": "marketplace",
    "shopee.com": "marketplace",
    "lazada.com": "marketplace",
    "wikipedia.org": "reference",
    "medium.com": "blog",
    "substack.com": "blog",
    "forbes.com": "news",
    "techcrunch.com": "news",
    "wired.com": "news",
}


def _extract_root_domain(domain: str) -> str:
    """Extract root domain from a full domain, handling subdomains and ports.

    Examples:
        en.wikipedia.org -> wikipedia.org
        www.reddit.com -> reddit.com
        example.com:8080 -> example.com
    """
    # Strip port if present
    domain = domain.split(":")[0]

    # Strip trailing dots
    domain = domain.rstrip(".")

    parts = domain.split(".")
    if len(parts) <= 2:
        return domain

    # Try progressively shorter suffixes to match the registry
    # e.g., for "en.wikipedia.org" try "en.wikipedia.org", then "wikipedia.org"
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in DOMAIN_REGISTRY:
            return candidate

    # Default: return last two parts (root domain)
    return ".".join(parts[-2:])


def classify_domain(domain: str) -> DomainCategory:
    """Classify a domain into a category using the registry.

    Falls back to 'other' for unknown domains.
    Handles subdomains (e.g., en.wikipedia.org -> wikipedia.org).
    """
    if not domain:
        return DomainCategory(domain=domain, category="other")

    root = _extract_root_domain(domain.lower())
    category = DOMAIN_REGISTRY.get(root, "other")
    return DomainCategory(domain=domain, category=category)


def classify_domains(domains: list[str]) -> list[DomainCategory]:
    """Classify multiple domains. Deduplicates by domain name."""
    seen: set[str] = set()
    results: list[DomainCategory] = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            results.append(classify_domain(d))
    return results
