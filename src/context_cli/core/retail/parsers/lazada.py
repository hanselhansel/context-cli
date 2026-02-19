"""Lazada marketplace parser."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from context_cli.core.models import MarketplaceType, ProductData
from context_cli.core.retail.parsers.base import BaseParser


class LazadaParser(BaseParser):
    """Parser for Lazada product pages (lazada.sg, .co.id, .com.my, etc.)."""

    marketplace: MarketplaceType = MarketplaceType.LAZADA

    def parse(self, html: str) -> ProductData:
        """Parse Lazada product HTML and return structured ProductData."""
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
        el = soup.find(class_="pdp-mod-product-badge-title")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> str | None:
        el = soup.find(class_="pdp-price")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_brand(soup: BeautifulSoup) -> str | None:
        el = soup.find(class_="pdp-product-brand__brand-link")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_rating(soup: BeautifulSoup) -> float | None:
        el = soup.find(class_="score-average")
        if el:
            text = el.get_text(strip=True)
            match = re.search(r"([\d.]+)", text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:  # pragma: no cover
                    return None
        return None

    @staticmethod
    def _extract_review_count(soup: BeautifulSoup) -> int | None:
        el = soup.find(class_="pdp-review-summary__link")
        if el:
            text = el.get_text(strip=True)
            match = re.search(r"(\d+)", text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:  # pragma: no cover
                    return None
        return None

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str | None:
        el = soup.find(class_="detail-content")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_specifications(soup: BeautifulSoup) -> dict[str, str]:
        specs: dict[str, str] = {}
        items = soup.find_all(class_="specification-key")
        for item in items:
            key_el = item.find(class_="key-title")
            val_el = item.find(class_="key-value")
            if key_el and val_el:
                key = key_el.get_text(strip=True)
                val = val_el.get_text(strip=True)
                if key:
                    specs[key] = val
        return specs

    @staticmethod
    def _extract_images(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
        urls: list[str] = []
        alts: list[str] = []
        containers = soup.find_all(class_="gallery-preview-panel__content")
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
        return soup.find(class_="pdp-video-player") is not None
