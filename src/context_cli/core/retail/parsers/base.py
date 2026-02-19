"""Base parser for marketplace product pages."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from context_cli.core.models import MarketplaceType, ProductData


class BaseParser:
    """Base parser with default behavior for unknown marketplaces.

    Extracts only Schema.org JSON-LD data from the HTML.
    Subclasses override ``parse()`` for marketplace-specific extraction.
    """

    marketplace: MarketplaceType = MarketplaceType.GENERIC

    def parse(self, html: str) -> ProductData:
        """Parse HTML and return product data with schema.org extraction."""
        schema_org = self._extract_schema_org(html)
        return ProductData(
            marketplace=self.marketplace,
            schema_org=schema_org,
        )

    @staticmethod
    def _extract_schema_org(html: str) -> dict:
        """Extract the first Product JSON-LD block, or any JSON-LD block."""
        if not html:
            return {}
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        first_valid: dict = {}
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        return data
                    if not first_valid:
                        first_valid = data
            except (json.JSONDecodeError, TypeError):
                continue
        return first_valid
