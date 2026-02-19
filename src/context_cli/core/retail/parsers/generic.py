"""Generic fallback parser using Schema.org, OpenGraph, and meta tags."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from context_cli.core.models import MarketplaceType, ProductData
from context_cli.core.retail.parsers.base import BaseParser


class GenericParser(BaseParser):
    """Fallback parser for any URL: Schema.org > OpenGraph > meta tags."""

    def parse(self, html: str) -> ProductData:
        """Parse generic product page HTML into ProductData."""
        soup = BeautifulSoup(html, "html.parser")
        schema = self._extract_schema_product(soup)
        og = self._extract_opengraph(soup)

        title = self._coalesce(
            schema.get("name"),
            og.get("og:title"),
            self._get_meta_title(soup),
        )
        description = self._coalesce(
            schema.get("description"),
            og.get("og:description"),
            self._get_meta_description(soup),
        )

        offers = schema.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        price = self._coalesce(
            str(offers["price"]) if offers.get("price") else None,
            og.get("og:price:amount"),
        )
        currency = self._coalesce(
            str(offers["priceCurrency"]) if offers.get("priceCurrency") else None,
            og.get("og:price:currency"),
        )

        brand = self._extract_brand(schema, og)
        rating, review_count = self._extract_rating(schema)
        availability = self._extract_availability(offers, og)
        image_urls = self._extract_images(schema, og, soup)
        alt_texts = self._extract_alt_texts(soup)
        has_video = self._detect_video(soup)

        return ProductData(
            title=title,
            description=description,
            price=price,
            currency=currency,
            availability=availability,
            image_urls=image_urls,
            brand=brand,
            rating=rating,
            review_count=review_count,
            has_video=has_video,
            schema_org=schema,
            marketplace=MarketplaceType.GENERIC,
            alt_texts=alt_texts,
        )

    # ------------------------------------------------------------------
    # Schema.org extraction
    # ------------------------------------------------------------------

    def _extract_schema_product(self, soup: BeautifulSoup) -> dict:
        """Find the first Schema.org Product in any ld+json script tag."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            product = self._find_product_in_schema(data)
            if product:
                return product
        return {}

    def _find_product_in_schema(self, data: dict | list) -> dict | None:
        """Recursively find a Product type in schema data."""
        if isinstance(data, dict):
            if data.get("@type") == "Product":
                return data
            # Check @graph array
            graph = data.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    return item
        return None

    # ------------------------------------------------------------------
    # OpenGraph extraction
    # ------------------------------------------------------------------

    def _extract_opengraph(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract OpenGraph and product meta tags."""
        og: dict[str, str] = {}
        for meta in soup.find_all("meta"):
            prop = str(meta.get("property", ""))
            content = str(meta.get("content", ""))
            if prop and content and (
                prop.startswith("og:") or prop.startswith("product:")
            ):
                og[prop] = content
        return og

    # ------------------------------------------------------------------
    # Meta tag fallbacks
    # ------------------------------------------------------------------

    def _get_meta_title(self, soup: BeautifulSoup) -> str | None:
        """Get title from <title> tag."""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True) or None
        return None

    def _get_meta_description(self, soup: BeautifulSoup) -> str | None:
        """Get description from meta description tag."""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            content = meta.get("content", "")
            return str(content) if content else None
        return None

    # ------------------------------------------------------------------
    # Field extractors
    # ------------------------------------------------------------------

    def _extract_brand(self, schema: dict, og: dict[str, str]) -> str | None:
        """Extract brand from schema or OpenGraph."""
        brand = schema.get("brand")
        if isinstance(brand, dict):
            return str(brand.get("name", "")) or None
        if isinstance(brand, str) and brand:
            return brand
        og_brand = og.get("product:brand")
        if og_brand:
            return og_brand
        return None

    def _extract_rating(self, schema: dict) -> tuple[float | None, int | None]:
        """Extract rating and review count from schema."""
        agg = schema.get("aggregateRating", {})
        rating: float | None = None
        review_count: int | None = None
        if agg.get("ratingValue"):
            try:
                rating = float(agg["ratingValue"])
            except (ValueError, TypeError):
                pass
        if agg.get("reviewCount"):
            try:
                review_count = int(agg["reviewCount"])
            except (ValueError, TypeError):
                pass
        return rating, review_count

    def _extract_availability(
        self, offers: dict, og: dict[str, str]
    ) -> str | None:
        """Extract availability from schema offers or OpenGraph."""
        avail = offers.get("availability")
        if avail:
            return str(avail)
        og_avail = og.get("product:availability")
        if og_avail:
            return og_avail
        return None

    def _extract_images(
        self, schema: dict, og: dict[str, str], soup: BeautifulSoup
    ) -> list[str]:
        """Extract image URLs from schema, OpenGraph, and body."""
        urls: list[str] = []
        # Schema.org images
        schema_img = schema.get("image")
        if isinstance(schema_img, list):
            urls.extend(str(u) for u in schema_img if u)
        elif isinstance(schema_img, str) and schema_img:
            urls.append(schema_img)
        # OpenGraph image
        og_img = og.get("og:image")
        if og_img and og_img not in urls:
            urls.append(og_img)
        # Body images as last resort
        if not urls:
            for img in soup.find_all("img"):
                src = img.get("src")
                if src and str(src) not in urls:
                    urls.append(str(src))
        return urls

    def _extract_alt_texts(self, soup: BeautifulSoup) -> list[str]:
        """Extract alt text from all images in the body."""
        alts: list[str] = []
        for img in soup.find_all("img"):
            alt = img.get("alt")
            if alt:
                alts.append(str(alt))
        return alts

    def _detect_video(self, soup: BeautifulSoup) -> bool:
        """Check for video content in the page."""
        return bool(soup.find("video"))

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _coalesce(*values: str | None) -> str | None:
        """Return the first non-None, non-empty value."""
        for v in values:
            if v:
                return v
        return None
