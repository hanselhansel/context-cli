"""HTML-to-Markdown converter — the core conversion pipeline."""

from __future__ import annotations

import httpx
from markdownify import markdownify

from context_cli.core.markdown_engine.config import MarkdownEngineConfig
from context_cli.core.markdown_engine.extractor import extract_content
from context_cli.core.markdown_engine.sanitizer import sanitize_html


def convert_html_to_markdown(
    html: str,
    config: MarkdownEngineConfig | None = None,
) -> str:
    """Convert HTML to clean markdown through the full pipeline.

    Pipeline:
    1. Sanitize — strip scripts, styles, nav, footer, ads, cookie banners
    2. Extract — find main content using readability algorithm
    3. Convert — transform HTML to markdown using markdownify

    Returns: Clean markdown string.
    """
    if not html or not html.strip():
        return ""

    # Step 1: Sanitize
    sanitized = sanitize_html(html, config)

    # Step 2: Extract main content
    extracted = extract_content(sanitized)

    # Step 3: Convert to markdown
    md = markdownify(
        extracted,
        heading_style="ATX",
        bullets="-",
    )

    # Clean up excessive whitespace
    lines = md.split("\n")
    cleaned_lines: list[str] = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        is_blank = not stripped
        if is_blank and prev_blank:
            continue  # Skip consecutive blank lines
        cleaned_lines.append(stripped)
        prev_blank = is_blank

    result = "\n".join(cleaned_lines).strip()
    if result:
        return result + "\n"
    return ""


async def convert_url_to_markdown(
    url: str,
    *,
    config: MarkdownEngineConfig | None = None,
    timeout: int = 30,
) -> tuple[str, dict[str, float | int]]:
    """Fetch a URL and convert its HTML to clean markdown.

    Returns:
        Tuple of (markdown_text, stats_dict) where stats contains:
        - raw_html_chars: length of original HTML
        - clean_md_chars: length of resulting markdown
        - raw_tokens: estimated tokens for raw HTML (chars / 4)
        - clean_tokens: estimated tokens for clean markdown (chars / 4)
        - reduction_pct: percentage reduction in tokens
    """
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True,
    ) as client:
        response = await client.get(
            url, headers={"User-Agent": "ContextCLI/3.0"},
        )
        response.raise_for_status()
        html = response.text

    md = convert_html_to_markdown(html, config)

    raw_chars = len(html)
    clean_chars = len(md)
    raw_tokens = raw_chars // 4
    clean_tokens = clean_chars // 4
    reduction = round(
        (raw_tokens - clean_tokens) / raw_tokens * 100, 1,
    ) if raw_tokens > 0 else 0.0

    stats: dict[str, float | int] = {
        "raw_html_chars": raw_chars,
        "clean_md_chars": clean_chars,
        "raw_tokens": raw_tokens,
        "clean_tokens": clean_tokens,
        "reduction_pct": reduction,
    }

    return md, stats
