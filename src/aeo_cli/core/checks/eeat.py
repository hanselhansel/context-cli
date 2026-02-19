"""E-E-A-T (Experience, Expertise, Authority, Trust) signal detection."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from aeo_cli.core.models import EeatReport

# Patterns for about/contact page links
_ABOUT_PATTERNS = re.compile(r"/about(?:-us)?(?:/|$)", re.IGNORECASE)
_CONTACT_PATTERNS = re.compile(r"/contact(?:-us)?(?:/|$)", re.IGNORECASE)
_PRIVACY_PATTERN = re.compile(r"privacy", re.IGNORECASE)
_TERMS_PATTERN = re.compile(r"terms", re.IGNORECASE)

# Date meta property names
_DATE_META_PROPERTIES = {
    "article:published_time",
    "article:modified_time",
    "datePublished",
    "dateModified",
    "og:updated_time",
}

# Meta name attributes for dates
_DATE_META_NAMES = {"date", "dcterms.date", "dc.date"}


def check_eeat(html: str, *, base_domain: str | None = None) -> EeatReport:
    """Detect E-E-A-T signals in HTML content.

    Args:
        html: Raw HTML string to analyse.
        base_domain: Domain of the page (for distinguishing external citations).
    """
    if not html.strip():
        return EeatReport(detail="No HTML content for E-E-A-T analysis")

    soup = BeautifulSoup(html, "html.parser")

    has_author, author_name = _detect_author(soup)
    has_date = _detect_date(soup)
    has_about = _detect_about_page(soup)
    has_contact = _detect_contact_info(soup)
    citation_count = _count_external_citations(soup, base_domain)
    trust_signals = _detect_trust_signals(soup)

    # Build detail
    signals_found: list[str] = []
    if has_author:
        signals_found.append(f"author: {author_name}" if author_name else "author found")
    if has_date:
        signals_found.append("publication date")
    if has_about:
        signals_found.append("about page")
    if has_contact:
        signals_found.append("contact info")
    if citation_count > 0:
        signals_found.append(f"{citation_count} external citation(s)")
    if trust_signals:
        signals_found.append(f"trust: {', '.join(trust_signals)}")

    detail = (
        f"E-E-A-T signals: {', '.join(signals_found)}"
        if signals_found
        else "No E-E-A-T signals detected"
    )

    return EeatReport(
        has_author=has_author,
        author_name=author_name,
        has_date=has_date,
        has_about_page=has_about,
        has_contact_info=has_contact,
        has_citations=citation_count > 0,
        citation_count=citation_count,
        trust_signals=trust_signals,
        detail=detail,
    )


def _detect_author(soup: BeautifulSoup) -> tuple[bool, str | None]:
    """Detect author attribution from meta tags, schema markup, or byline elements."""
    # Meta name="author"
    meta = soup.find("meta", attrs={"name": "author"})
    if meta:
        content = str(meta.get("content", "")).strip()
        if content:
            return True, content

    # rel="author" link
    author_link = soup.find("a", attrs={"rel": "author"})
    if author_link:
        name = author_link.get_text(strip=True)
        return True, name if name else None

    # Schema.org Person itemprop="author"
    author_elem = soup.find(attrs={"itemprop": "author"})
    if author_elem:
        name_elem = author_elem.find(attrs={"itemprop": "name"})
        author_name = name_elem.get_text(strip=True) if name_elem else None
        return True, author_name or None

    # Byline class patterns
    for class_pattern in ["byline", "author", "post-author"]:
        elem = soup.find(class_=re.compile(class_pattern, re.IGNORECASE))
        if elem:
            return True, None

    return False, None


def _detect_date(soup: BeautifulSoup) -> bool:
    """Detect publication or modification dates."""
    # Meta property tags
    for prop in _DATE_META_PROPERTIES:
        if soup.find("meta", attrs={"property": prop}):
            return True

    # Meta name tags
    for name in _DATE_META_NAMES:
        if soup.find("meta", attrs={"name": name}):
            return True

    # <time datetime="..."> tags
    if soup.find("time", attrs={"datetime": True}):
        return True

    return False


def _detect_about_page(soup: BeautifulSoup) -> bool:
    """Detect links to an about page."""
    for link in soup.find_all("a", href=True):
        if _ABOUT_PATTERNS.search(str(link["href"])):
            return True
    return False


def _detect_contact_info(soup: BeautifulSoup) -> bool:
    """Detect contact information (links, mailto, tel)."""
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if href.startswith("mailto:") or href.startswith("tel:"):
            return True
        if _CONTACT_PATTERNS.search(href):
            return True
    return False


def _count_external_citations(
    soup: BeautifulSoup, base_domain: str | None
) -> int:
    """Count links to external domains (potential citations/references)."""
    count = 0
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        parsed = urlparse(href)
        if not parsed.scheme or not parsed.netloc:
            continue  # Skip relative URLs
        if base_domain and parsed.netloc == base_domain:
            continue  # Skip internal links
        if not base_domain:
            count += 1  # Without base_domain, count all absolute URLs
        else:
            count += 1
    return count


def _detect_trust_signals(soup: BeautifulSoup) -> list[str]:
    """Detect trust-related signals (privacy policy, terms of service)."""
    signals: list[str] = []
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        text = link.get_text(strip=True).lower()
        combined = f"{href} {text}"
        if _PRIVACY_PATTERN.search(combined) and "privacy policy" not in signals:
            signals.append("privacy policy")
        if _TERMS_PATTERN.search(combined) and "terms of service" not in signals:
            signals.append("terms of service")
    return signals
