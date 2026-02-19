"""Generic fallback parser."""

from __future__ import annotations

from aeo_cli.core.models import MarketplaceType, ProductData
from aeo_cli.core.retail.parsers.base import BaseParser


class GenericParser(BaseParser):
    """Generic fallback parser for unrecognized marketplaces."""

    def parse(self, html: str) -> ProductData:
        """Parse HTML content using generic extraction logic."""
        return ProductData(marketplace=MarketplaceType.GENERIC)
