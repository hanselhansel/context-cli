"""Shopee marketplace parser."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from context_cli.core.models import MarketplaceType, ProductData
from context_cli.core.retail.parsers.base import BaseParser


class ShopeeParser(BaseParser):
    """Parser for Shopee product pages (shopee.sg, .co.id, .com.my, etc.)."""

    marketplace: MarketplaceType = MarketplaceType.SHOPEE

    def parse(self, html: str) -> ProductData:
        """Parse Shopee product HTML and return structured ProductData."""
        soup = BeautifulSoup(html, "html.parser")
        schema_org = self._extract_schema_org(html)

        title = self._extract_title(soup)
        price = self._extract_price(soup)
        brand = self._extract_brand(soup)
        rating = self._extract_rating(soup)
        review_count = self._extract_review_count(soup)
        description = self._extract_description(soup)
        specifications = self._extract_specifications(soup)
        image_urls, alt_texts = self._extract_images(soup)
        has_video = self._detect_video(soup)

        return ProductData(
            title=title,
            description=description,
            price=price,
            brand=brand,
            rating=rating,
            review_count=review_count,
            specifications=specifications,
            image_urls=image_urls,
            has_video=has_video,
            schema_org=schema_org,
            marketplace=self.marketplace,
            alt_texts=alt_texts,
        )

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        container = soup.find(class_="product-title")
        if container:
            span = container.find("span")
            if span:
                text = span.get_text(strip=True)
                return text if text else None
        return None

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> str | None:
        container = soup.find(class_="product-price")
        if container:
            span = container.find("span")
            if span:
                text = span.get_text(strip=True)
                return text if text else None
        return None

    @staticmethod
    def _extract_brand(soup: BeautifulSoup) -> str | None:
        container = soup.find(class_="product-brand")
        if container:
            a = container.find("a")
            if a:
                text = a.get_text(strip=True)
                return text if text else None
        return None

    @staticmethod
    def _extract_rating(soup: BeautifulSoup) -> float | None:
        container = soup.find(class_="product-rating")
        if container:
            span = container.find("span")
            if span:
                text = span.get_text(strip=True)
                match = re.search(r"([\d.]+)", text)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:  # pragma: no cover
                        return None
        return None

    @staticmethod
    def _extract_review_count(soup: BeautifulSoup) -> int | None:
        container = soup.find(class_="product-review-count")
        if container:
            span = container.find("span")
            if span:
                text = span.get_text(strip=True)
                match = re.search(r"(\d+)", text)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:  # pragma: no cover
                        return None
        return None

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str | None:
        el = soup.find(class_="product-description")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_specifications(soup: BeautifulSoup) -> dict[str, str]:
        specs: dict[str, str] = {}
        details = soup.find_all(class_="product-detail")
        for detail in details:
            label = detail.find("label")
            value = detail.find("span")
            if label and value:
                key = label.get_text(strip=True)
                val = value.get_text(strip=True)
                if key:
                    specs[key] = val
        return specs

    @staticmethod
    def _extract_images(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
        urls: list[str] = []
        alts: list[str] = []
        containers = soup.find_all(class_="shopee-image")
        for container in containers:
            img = container.find("img")
            if img:
                src = img.get("src", "")
                alt = img.get("alt", "")
                if src:
                    urls.append(str(src))
                    alts.append(str(alt))
        return urls, alts

    @staticmethod
    def _detect_video(soup: BeautifulSoup) -> bool:
        return soup.find(class_="shopee-video") is not None
