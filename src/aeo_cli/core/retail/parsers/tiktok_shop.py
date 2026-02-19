"""TikTok Shop product page parser."""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from aeo_cli.core.models import MarketplaceType, ProductData
from aeo_cli.core.retail.parsers.base import BaseParser


class TiktokShopParser(BaseParser):
    """Parse TikTok Shop product listing pages."""

    def parse(self, html: str) -> ProductData:
        """Parse TikTok Shop HTML into ProductData."""
        soup = BeautifulSoup(html, "html.parser")
        schema = self._extract_schema_org(soup)

        title = self._get_title(soup, schema)
        price, currency = self._get_price(soup, schema)
        description = self._get_description(soup, schema)
        brand = self._get_brand(soup, schema)
        rating, review_count = self._get_rating(soup, schema)
        image_urls, alt_texts = self._get_images(soup, schema)
        has_video = self._detect_video(soup)
        specs = self._get_specifications(soup)
        bullet_points = self._get_bullet_points(soup)
        availability = self._get_availability(schema)

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
            bullet_points=bullet_points,
            specifications=specs,
            has_video=has_video,
            schema_org=schema,
            marketplace=MarketplaceType.TIKTOK_SHOP,
            alt_texts=alt_texts,
        )

    def _extract_schema_org(self, soup: BeautifulSoup) -> dict:
        """Extract Schema.org Product JSON-LD from script tags."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(data, dict) and data.get("@type") == "Product":
                return data
        return {}

    def _get_title(self, soup: BeautifulSoup, schema: dict) -> str | None:
        """Extract product title from HTML or schema."""
        if schema.get("name"):
            return str(schema["name"])
        el = soup.find(attrs={"data-testid": "product-title"})
        if el:
            return el.get_text(strip=True)
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return None

    def _get_price(
        self, soup: BeautifulSoup, schema: dict
    ) -> tuple[str | None, str | None]:
        """Extract price and currency."""
        offers = schema.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = str(offers["price"]) if offers.get("price") else None
        currency = str(offers["priceCurrency"]) if offers.get("priceCurrency") else None
        if not price:
            el = soup.find(class_="product-price")
            if el:
                text = el.get_text(strip=True)
                match = re.search(r"[\d,.]+", text)
                if match:
                    price = match.group()
        return price, currency

    def _get_description(self, soup: BeautifulSoup, schema: dict) -> str | None:
        """Extract product description."""
        if schema.get("description"):
            return str(schema["description"])
        el = soup.find(class_="product-description")
        if el:
            return el.get_text(strip=True)
        return None

    def _get_brand(self, soup: BeautifulSoup, schema: dict) -> str | None:
        """Extract brand name."""
        brand = schema.get("brand")
        if isinstance(brand, dict):
            return str(brand.get("name", ""))
        if isinstance(brand, str):
            return brand
        el = soup.find(class_="product-brand")
        if el:
            return el.get_text(strip=True)
        return None

    def _get_rating(
        self, soup: BeautifulSoup, schema: dict
    ) -> tuple[float | None, int | None]:
        """Extract rating and review count."""
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
        if rating is None:
            el = soup.find(attrs={"data-testid": "rating-value"})
            if el:
                try:
                    rating = float(el.get_text(strip=True))
                except ValueError:
                    pass
        if review_count is None:
            el = soup.find(attrs={"data-testid": "review-count"})
            if el:
                match = re.search(r"\d+", el.get_text(strip=True))
                if match:
                    review_count = int(match.group())
        return rating, review_count

    def _get_images(
        self, soup: BeautifulSoup, schema: dict
    ) -> tuple[list[str], list[str]]:
        """Extract image URLs and alt texts."""
        urls: list[str] = []
        alts: list[str] = []
        for img in soup.find_all("img", class_="product-image"):
            src = img.get("src")
            if src:
                urls.append(str(src))
            alt = img.get("alt")
            if alt:
                alts.append(str(alt))
        return urls, alts

    def _detect_video(self, soup: BeautifulSoup) -> bool:
        """Check for video content."""
        return bool(soup.find("video"))

    def _get_specifications(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract product specifications."""
        specs: dict[str, str] = {}
        for item in soup.find_all(class_="spec-item"):
            label = item.find(class_="spec-label")
            value = item.find(class_="spec-value")
            if label and value:
                specs[label.get_text(strip=True)] = value.get_text(strip=True)
        return specs

    def _get_bullet_points(self, soup: BeautifulSoup) -> list[str]:
        """Extract feature bullet points."""
        points: list[str] = []
        features = soup.find(class_="product-features")
        if features:
            for li in features.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    points.append(text)
        return points

    def _get_availability(self, schema: dict) -> str | None:
        """Extract availability from schema."""
        offers = schema.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        avail = offers.get("availability")
        if avail:
            return str(avail)
        return None
