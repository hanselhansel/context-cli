"""RSL (Really Simple Licensing) analysis of robots.txt directives."""

from __future__ import annotations

import re

from aeo_cli.core.models import RslReport

# Known AI bot user-agents (must match robots.py AI_BOTS list)
_AI_BOT_NAMES: set[str] = {
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "ClaudeBot",
    "PerplexityBot",
    "Amazonbot",
    "OAI-SearchBot",
    "DeepSeek-AI",
    "Grok",
    "Meta-ExternalAgent",
    "cohere-ai",
    "AI2Bot",
    "ByteSpider",
}

# Case-insensitive pattern for User-agent lines
_USER_AGENT_RE = re.compile(r"^user-agent:\s*(.+)$", re.IGNORECASE)
_CRAWL_DELAY_RE = re.compile(r"^crawl-delay:\s*(.+)$", re.IGNORECASE)
_SITEMAP_RE = re.compile(r"^sitemap:\s*(.+)$", re.IGNORECASE)


def check_rsl(raw_robots_txt: str | None) -> RslReport:
    """Analyse robots.txt for RSL-relevant signals.

    Extracts:
    - Crawl-delay directives
    - Sitemap declarations
    - AI-bot-specific User-agent blocks
    """
    if raw_robots_txt is None:
        return RslReport(detail="No robots.txt available for RSL analysis")

    lines = raw_robots_txt.splitlines()

    crawl_delay: float | None = None
    sitemap_urls: list[str] = []
    ai_agents: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Sitemap directives (top-level, not scoped to a User-agent)
        sitemap_match = _SITEMAP_RE.match(stripped)
        if sitemap_match:
            sitemap_urls.append(sitemap_match.group(1).strip())
            continue

        # Crawl-delay (take the first valid one found)
        if crawl_delay is None:
            delay_match = _CRAWL_DELAY_RE.match(stripped)
            if delay_match:
                try:
                    crawl_delay = float(delay_match.group(1).strip())
                except ValueError:
                    pass
                continue

        # User-agent lines: check if they name a known AI bot
        ua_match = _USER_AGENT_RE.match(stripped)
        if ua_match:
            agent_name = ua_match.group(1).strip()
            if agent_name != "*" and agent_name in _AI_BOT_NAMES:
                if agent_name not in ai_agents:
                    ai_agents.append(agent_name)

    # Build detail summary
    parts: list[str] = []
    has_crawl_delay = crawl_delay is not None
    if has_crawl_delay:
        parts.append(f"Crawl-delay: {crawl_delay}s")
    if sitemap_urls:
        parts.append(f"{len(sitemap_urls)} Sitemap URL(s)")
    if ai_agents:
        parts.append(f"AI-specific rules for: {', '.join(ai_agents)}")

    detail = "; ".join(parts) if parts else "No RSL signals found"

    return RslReport(
        has_crawl_delay=has_crawl_delay,
        crawl_delay_value=crawl_delay,
        has_sitemap_directive=len(sitemap_urls) > 0,
        sitemap_urls=sitemap_urls,
        has_ai_specific_rules=len(ai_agents) > 0,
        ai_specific_agents=ai_agents,
        detail=detail,
    )
