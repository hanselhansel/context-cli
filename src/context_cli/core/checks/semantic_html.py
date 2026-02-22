"""Agent readiness sub-check: semantic HTML quality evaluation."""

from __future__ import annotations

from bs4 import BeautifulSoup

from context_cli.core.models import SemanticHtmlReport

ARIA_LANDMARK_ROLES = frozenset({
    "banner",
    "main",
    "navigation",
    "contentinfo",
    "complementary",
    "search",
    "region",
    "form",
})


def check_semantic_html(html: str) -> SemanticHtmlReport:
    """Evaluate semantic HTML quality from pre-fetched HTML content."""
    if not html:
        return SemanticHtmlReport(detail="No HTML to analyze")

    soup = BeautifulSoup(html, "html.parser")

    has_main = soup.find("main") is not None
    has_article = soup.find("article") is not None
    has_header = soup.find("header") is not None
    has_footer = soup.find("footer") is not None
    has_nav = soup.find("nav") is not None

    aria_landmarks = len(
        soup.find_all(attrs={"role": lambda v: v and v.lower() in ARIA_LANDMARK_ROLES})
    )

    score = 0.0
    if has_main or has_article:
        score += 1.0
    if has_header and has_nav:
        score += 1.0
    if aria_landmarks >= 2:
        score += 1.0

    parts: list[str] = []
    if has_main or has_article:
        parts.append("main/article present")
    if has_header and has_nav:
        parts.append("header+nav present")
    if aria_landmarks:
        parts.append(f"{aria_landmarks} ARIA landmark(s)")
    detail = "; ".join(parts) if parts else "No semantic HTML elements found"

    return SemanticHtmlReport(
        has_main=has_main,
        has_article=has_article,
        has_header=has_header,
        has_footer=has_footer,
        has_nav=has_nav,
        aria_landmarks=aria_landmarks,
        score=score,
        detail=detail,
    )
