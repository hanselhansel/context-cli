"""HTML sanitizer that strips boilerplate elements before markdown conversion."""

from bs4 import BeautifulSoup, Tag

from context_cli.core.markdown_engine.config import MarkdownEngineConfig


def sanitize_html(
    html: str, config: MarkdownEngineConfig | None = None
) -> str:
    """Strip boilerplate elements from HTML, leaving main content.

    Removes scripts, styles, nav, footer, cookie banners, and ads
    based on configuration patterns.
    """
    if not html:
        return ""

    cfg = config or MarkdownEngineConfig()
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove script and style elements
    if cfg.strip_scripts:
        for tag in soup.find_all("script"):
            tag.decompose()
    if cfg.strip_styles:
        for tag in soup.find_all("style"):
            tag.decompose()

    # 2. Remove structural boilerplate
    if cfg.strip_nav:
        for tag in soup.find_all("nav"):
            tag.decompose()
    if cfg.strip_footer:
        for tag in soup.find_all("footer"):
            tag.decompose()
    if cfg.strip_header:
        for tag in soup.find_all("header"):
            tag.decompose()

    # 3. Remove cookie banners (match on id/class containing patterns)
    if cfg.strip_cookie_banners:
        _remove_by_patterns(soup, cfg.cookie_banner_patterns)

    # 4. Remove ad containers
    if cfg.strip_ads:
        _remove_by_patterns(soup, cfg.ad_patterns)

    # 5. Remove hidden elements
    for tag in soup.find_all(attrs={"aria-hidden": "true"}):
        if isinstance(tag, Tag):
            tag.decompose()
    for tag in soup.find_all(
        attrs={
            "style": lambda v: v
            and "display:none" in str(v).replace(" ", "").lower()
        }
    ):
        if isinstance(tag, Tag):
            tag.decompose()

    # 6. Remove common boilerplate elements (noscript, iframe)
    for tag_name in ["noscript", "iframe"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    return str(soup)


def _remove_by_patterns(
    soup: BeautifulSoup, patterns: list[str]
) -> None:
    """Remove elements whose id or class matches any of the given patterns."""
    for tag in soup.find_all(True):
        # Skip already-decomposed tags (parent was removed earlier in this loop)
        if not isinstance(tag, Tag) or tag.attrs is None:
            continue
        tag_id = tag.get("id", "") or ""
        tag_classes = " ".join(tag.get("class", []) or [])
        combined = f"{tag_id} {tag_classes}".lower()
        for pattern in patterns:
            if pattern.lower() in combined:
                tag.decompose()
                break
