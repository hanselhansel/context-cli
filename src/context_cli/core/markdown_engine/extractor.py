"""Content extractor -- identifies and extracts main content from HTML.

Uses readabilipy for readability-based extraction with semantic HTML fallbacks.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from readabilipy import simple_json_from_html_string


def extract_content(html: str) -> str:
    """Extract main content from HTML using readability algorithm.

    Strategy (in order of preference):
    1. Try readabilipy's readability algorithm (best quality)
    2. Fallback to <main> element if readability fails
    3. Fallback to <article> element (largest if multiple)
    4. Fallback to role="main" element
    5. Fallback to <body> element
    6. Return original HTML if all fallbacks fail

    Args:
        html: Raw HTML string to extract content from.

    Returns:
        HTML string containing only the main content.
    """
    if not html or not html.strip():
        return ""

    # Try readabilipy first (pure Python mode, no Node.js needed)
    try:
        result = simple_json_from_html_string(html, use_readability=False)
        content = result.get("plain_content") or result.get("content", "")
        if content and len(content.strip()) > 100:
            return content
    except Exception:
        pass

    # Fallback: semantic HTML elements
    soup = BeautifulSoup(html, "html.parser")

    # Try <main> element
    main = soup.find("main")
    if main and len(main.get_text(strip=True)) > 50:
        return str(main)

    # Try <article> element (pick the largest one)
    articles = soup.find_all("article")
    if articles:
        largest = max(articles, key=lambda a: len(a.get_text(strip=True)))
        if len(largest.get_text(strip=True)) > 50:
            return str(largest)

    # Try role="main"
    role_main = soup.find(attrs={"role": "main"})
    if role_main and len(role_main.get_text(strip=True)) > 50:
        return str(role_main)

    # Fallback to body
    body = soup.find("body")
    if body:
        return str(body)

    return html
