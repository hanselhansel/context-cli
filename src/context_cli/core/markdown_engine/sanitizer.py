"""HTML sanitizer — stub for agent merge."""

from __future__ import annotations

from context_cli.core.markdown_engine.config import MarkdownEngineConfig


def sanitize_html(
    html: str,
    config: MarkdownEngineConfig | None = None,
) -> str:
    """Strip scripts, styles, nav, footer, ads, cookie banners from HTML.

    This is a stub implementation that passes HTML through unchanged.
    The full implementation will be provided by the sanitizer agent.
    """
    return html
