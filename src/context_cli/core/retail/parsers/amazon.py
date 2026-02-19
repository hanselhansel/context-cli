"""Amazon marketplace parser."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from context_cli.core.models import MarketplaceType, ProductData
from context_cli.core.retail.parsers.base import BaseParser


class AmazonParser(BaseParser):
    """Parser for Amazon product pages (amazon.com, .co.uk, .de, etc.)."""

    marketplace: MarketplaceType = MarketplaceType.AMAZON

    def parse(self, html: str) -> ProductData:
        """Parse Amazon product HTML and return structured ProductData."""
        soup = BeautifulSoup(html, "html.parser")
        schema_org = self._extract_schema_org(html)

        title = self._extract_title(soup)
        price = self._extract_price(soup)
        brand = self._extract_brand(soup)
        rating = self._extract_rating(soup)
        review_count = self._extract_review_count(soup)
        bullet_points = self._extract_bullet_points(soup)
        specifications = self._extract_specifications(soup)
        description = self._extract_description(soup)
        availability = self._extract_availability(soup)
        image_urls, alt_texts = self._extract_images(soup)
        has_video = self._detect_video(soup)
        has_aplus = self._detect_aplus(soup)
        qa_count = self._extract_qa_count(soup)
        currency = self._detect_currency(price)

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
            specifications=specifications,
            has_video=has_video,
            has_aplus_content=has_aplus,
            qa_count=qa_count,
            schema_org=schema_org,
            marketplace=self.marketplace,
            alt_texts=alt_texts,
        )

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        el = soup.find(id="productTitle")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> str | None:
        el = soup.find(class_="a-price-whole")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_brand(soup: BeautifulSoup) -> str | None:
        el = soup.find(id="bylineInfo")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_rating(soup: BeautifulSoup) -> float | None:
        el = soup.find(id="acrPopover")
        if el:
            title = el.get("title", "")
            match = re.search(r"([\d.]+)", str(title))
            if match:
                try:
                    return float(match.group(1))
                except ValueError:  # pragma: no cover
                    return None
        return None

    @staticmethod
    def _extract_review_count(soup: BeautifulSoup) -> int | None:
        el = soup.find(id="acrCustomerReviewText")
        if el:
            text = el.get_text(strip=True)
            match = re.search(r"([\d,]+)", text)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:  # pragma: no cover
                    return None
        return None

    @staticmethod
    def _extract_bullet_points(soup: BeautifulSoup) -> list[str]:
        container = soup.find(id="feature-bullets")
        if not container:
            return []
        items = container.find_all(class_="a-list-item")
        return [item.get_text(strip=True) for item in items if item.get_text(strip=True)]

    @staticmethod
    def _extract_specifications(soup: BeautifulSoup) -> dict[str, str]:
        specs: dict[str, str] = {}
        table = soup.find(id="productDetails_techSpec_section_1")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.get_text(strip=True)
                    val = td.get_text(strip=True)
                    if key:
                        specs[key] = val
        return specs

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str | None:
        el = soup.find(id="productDescription")
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    @staticmethod
    def _extract_availability(soup: BeautifulSoup) -> str | None:
        container = soup.find(id="availability")
        if container:
            span = container.find("span")
            if span:
                text = span.get_text(strip=True)
                return text if text else None
        return None

    @staticmethod
    def _extract_images(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
        urls: list[str] = []
        alts: list[str] = []
        container = soup.find(id="altImages")
        if container:
            imgs = container.find_all("img")
            for img in imgs:
                src = img.get("src", "")
                alt = img.get("alt", "")
                if src:
                    urls.append(str(src))
                    alts.append(str(alt))
        return urls, alts

    @staticmethod
    def _detect_video(soup: BeautifulSoup) -> bool:
        return soup.find(class_="a-video-player") is not None

    @staticmethod
    def _detect_aplus(soup: BeautifulSoup) -> bool:
        return soup.find(id="aplus") is not None

    @staticmethod
    def _extract_qa_count(soup: BeautifulSoup) -> int | None:
        el = soup.find(id="askATFLink")
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
    def _detect_currency(price: str | None) -> str | None:
        if price is None:
            return None
        if "$" in price:
            return "USD"
        if "\u00a3" in price:  # £
            return "GBP"
        if "\u20ac" in price:  # €
            return "EUR"
        if "\u00a5" in price:  # ¥
            return "JPY"
        return None
