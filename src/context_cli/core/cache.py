"""Simple in-memory cache for robots.txt during site audits."""

from __future__ import annotations

from dataclasses import dataclass, field

from context_cli.core.models import RobotsReport


@dataclass
class RobotsCache:
    """Cache robots.txt results to avoid re-fetching for every page in a site audit.

    Keyed by domain (netloc). A single site audit typically only needs one entry,
    but the design supports multi-domain usage if needed.
    """

    _store: dict[str, tuple[RobotsReport, str | None]] = field(default_factory=dict)

    def get(self, domain: str) -> tuple[RobotsReport, str | None] | None:
        """Return cached (RobotsReport, raw_text) or None if not cached."""
        return self._store.get(domain)

    def set(self, domain: str, report: RobotsReport, raw_text: str | None) -> None:
        """Cache a robots.txt result for a domain."""
        self._store[domain] = (report, raw_text)

    def has(self, domain: str) -> bool:
        """Check if a domain's robots.txt is cached."""
        return domain in self._store

    def clear(self) -> None:
        """Clear the cache."""
        self._store.clear()
