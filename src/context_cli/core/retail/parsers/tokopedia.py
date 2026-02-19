"""Tokopedia marketplace parser."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from context_cli.core.models import MarketplaceType, ProductData
from context_cli.core.retail.parsers.base import BaseParser


class TokopediaParser(BaseParser):
    """Parser for Tokopedia product pages (tokopedia.com)."""

    marketplace: MarketplaceType = MarketplaceType.TOKOPEDIA

    def parse(self, html: str) -> ProductData:
        """Parse Tokopedia product HTML and return structured ProductData."""
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
        currency = self._detect_currency(price)

        return ProductData(
            title=title,
            description=description,
            price=price,
            currency=currency,
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
        el = soup.find(attrs={"data-testid": "lblPDPDetailProductName"})
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> str | None:
        el = soup.find(attrs={"data-testid": "lblPDPDetailProductPrice"})
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_brand(soup: BeautifulSoup) -> str | None:
        el = soup.find(attrs={"data-testid": "llbPDPFooterShopName"})
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_rating(soup: BeautifulSoup) -> float | None:
        el = soup.find(attrs={"data-testid": "lblPDPDetailProductRatingNumber"})
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
        el = soup.find(attrs={"data-testid": "lblPDPDetailProductRatingCounter"})
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
        el = soup.find(attrs={"data-testid": "lblPDPDescriptionProduk"})
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_specifications(soup: BeautifulSoup) -> dict[str, str]:
        specs: dict[str, str] = {}
        items = soup.find_all(attrs={"data-testid": "lblPDPInfoProduk"})
        for item in items:
            spans = item.find_all("span")
            if len(spans) >= 2:
                key = spans[0].get_text(strip=True)
                val = spans[1].get_text(strip=True)
                if key:
                    specs[key] = val
        return specs

    @staticmethod
    def _extract_images(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
        urls: list[str] = []
        alts: list[str] = []
        containers = soup.find_all(class_="css-image")
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
        return soup.find(attrs={"data-testid": "pdpVideoPlayer"}) is not None

    @staticmethod
    def _detect_currency(price: str | None) -> str | None:
        if price is None:
            return None
        if "Rp" in price:
            return "IDR"
        return None
