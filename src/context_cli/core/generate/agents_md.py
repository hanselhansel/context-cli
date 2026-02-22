"""AGENTS.md file generator -- creates an AGENTS.md for a given website."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT: int = 15
MAX_ENDPOINTS: int = 20


def _extract_site_info(html: str, url: str) -> dict[str, str | list[str]]:
    """Extract title, description, links, and headings from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(url)
    domain = parsed.netloc

    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()

    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = str(meta_desc["content"]).strip()

    links: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag["href"])
        if href.startswith("/") or domain in href:
            if href not in links:
                links.append(href)

    headings: list[str] = []
    for level in range(1, 4):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text and text not in headings:
                headings.append(text)

    return {
        "domain": domain,
        "title": title,
        "description": description,
        "links": links[:MAX_ENDPOINTS],
        "headings": headings,
    }


def _build_agents_md(info: dict[str, str | list[str]]) -> str:
    """Build the AGENTS.md content from extracted site information."""
    lines: list[str] = []
    lines.append("# AGENTS.md")
    lines.append("")
    lines.append("## Site Information")
    lines.append(f"- **Domain**: {info['domain']}")
    lines.append(f"- **Title**: {info['title']}")
    lines.append(f"- **Description**: {info['description']}")
    lines.append("")
    lines.append("## Allowed Actions")
    lines.append("- Browse public pages")
    lines.append("- Extract text content")
    lines.append("- Follow internal links")
    lines.append("- Read structured data (JSON-LD, microdata)")
    lines.append("")
    lines.append("## Rate Limits")
    lines.append("- **Default**: 1 request per second")
    lines.append("- **Crawl-delay**: 1")
    lines.append("")
    lines.append("## Authentication")
    lines.append("- **Required**: None (public content)")
    lines.append("")
    lines.append("## Endpoints")
    links = info["links"]
    assert isinstance(links, list)
    if links:
        for link in links:
            lines.append(f"- {link}")
    else:
        lines.append("- / (homepage)")
    lines.append("")
    lines.append("## Data Formats")
    lines.append("- text/html")
    lines.append("- application/json (if API available)")
    lines.append("- application/ld+json (structured data)")
    lines.append("")
    return "\n".join(lines)


def _build_error_agents_md(domain: str, error: str) -> str:
    """Build a minimal AGENTS.md when the site cannot be fetched."""
    lines: list[str] = [
        "# AGENTS.md",
        "",
        "## Site Information",
        f"- **Domain**: {domain}",
        f"- **Note**: Could not fetch site ({error})",
        "",
        "## Allowed Actions",
        "- Browse public pages",
        "- Extract text content",
        "",
        "## Rate Limits",
        "- **Default**: 1 request per second",
        "",
    ]
    return "\n".join(lines)


async def generate_agents_md(
    url: str,
    *,
    output_path: str | None = None,
) -> str:
    """Generate an AGENTS.md file for a website.

    Crawls the site to understand its structure, then produces an
    AGENTS.md file following the emerging standard.

    Returns: The AGENTS.md content as a string.
    """
    parsed = urlparse(url)
    domain = parsed.netloc or url

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as exc:
        content = _build_error_agents_md(domain, str(exc))
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w") as f:
                f.write(content)
        return content

    info = _extract_site_info(html, url)
    content = _build_agents_md(info)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content)

    return content
