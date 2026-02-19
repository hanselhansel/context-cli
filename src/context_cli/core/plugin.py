"""Plugin architecture — ABC, registry, discovery, and built-in MetaTagsPlugin."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from importlib.metadata import entry_points

from bs4 import BeautifulSoup

from context_cli.core.models import PluginResult

logger = logging.getLogger(__name__)

# ── Abstract base class ──────────────────────────────────────────────────────


class AuditPlugin(ABC):
    """Base class for custom audit plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin display name."""

    @property
    @abstractmethod
    def max_score(self) -> float:
        """Maximum points this plugin awards."""

    @abstractmethod
    async def check(self, url: str, html: str, headers: dict[str, str]) -> PluginResult:
        """Run the plugin check and return a result."""


# ── Plugin registry ──────────────────────────────────────────────────────────

_registry: list[AuditPlugin] = []


def register_plugin(plugin: AuditPlugin) -> None:
    """Add a plugin to the global registry."""
    _registry.append(plugin)


def get_plugins() -> list[AuditPlugin]:
    """Return a copy of all registered plugins."""
    return list(_registry)


def clear_plugins() -> None:
    """Clear the plugin registry (for testing)."""
    _registry.clear()


# ── Plugin discovery ─────────────────────────────────────────────────────────


def discover_plugins() -> None:
    """Load plugins from the 'context_cli.plugins' entry point group."""
    eps = entry_points()
    plugin_eps = list(eps.get("context_cli.plugins", []))
    for ep in plugin_eps:
        try:
            plugin_cls = ep.load()
            register_plugin(plugin_cls())
        except Exception:
            logger.warning("Failed to load plugin %s", ep.name, exc_info=True)


# ── Built-in example plugin ─────────────────────────────────────────────────


class MetaTagsPlugin(AuditPlugin):
    """Example plugin that checks for og:title and og:description meta tags."""

    @property
    def name(self) -> str:
        return "Meta Tags"

    @property
    def max_score(self) -> float:
        return 10.0

    async def check(self, url: str, html: str, headers: dict[str, str]) -> PluginResult:
        """Check for og:title and og:description. 5 points each."""
        soup = BeautifulSoup(html, "html.parser") if html else None
        found_tags: list[str] = []

        if soup:
            if soup.find("meta", attrs={"property": "og:title"}):
                found_tags.append("og:title")
            if soup.find("meta", attrs={"property": "og:description"}):
                found_tags.append("og:description")

        score = len(found_tags) * 5.0

        if found_tags:
            detail = f"Found: {', '.join(found_tags)}"
        else:
            detail = "No og:title or og:description meta tags found"

        return PluginResult(
            plugin_name=self.name,
            score=score,
            max_score=self.max_score,
            detail=detail,
            metadata={"found_tags": found_tags},
        )
