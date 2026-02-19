"""Parser registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aeo_cli.core.models import MarketplaceType

if TYPE_CHECKING:
    from aeo_cli.core.retail.parsers.base import BaseParser


def detect_marketplace(url: str) -> MarketplaceType:
    """Detect marketplace type from URL."""
    return MarketplaceType.GENERIC


def get_parser(marketplace: MarketplaceType) -> BaseParser:
    """Get parser instance for a marketplace type."""
    from aeo_cli.core.retail.parsers.generic import GenericParser

    return GenericParser()


__all__ = ["detect_marketplace", "get_parser"]
